# /// script
# requires-python = ">=3.11"
# dependencies = ["adaption>=0.19"]
# ///
"""Agent: one step = one Adaption Responses call + tool execution."""
import argparse
import json
import os
import random
import sys
import time
from pathlib import Path

if __package__ in (None, ""):  # run as a script
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from swarm2.prompts import system_prompt, task_message
from swarm2.tools import TOOLS, AgentCtx, dispatch

NUDGE = "Use a tool; call finish with your write-up when done."
TRIM_TOKENS = 200_000
MAX_OUTPUT_TOKENS = 8000


class SessionError(Exception):
    pass


def load_env():
    env = Path(__file__).resolve().parent.parent / ".env"
    for line in env.read_text().splitlines() if env.exists() else []:
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"'))


def _final(stream):
    """Final Response from a Responses event stream; a failed or truncated stream raises (-> retry)."""
    try:
        for ev in stream:
            if ev.type in ("response.completed", "response.incomplete"):
                return ev.response
            if ev.type in ("response.failed", "error"):
                raise RuntimeError(f"stream {ev.type}: {str(getattr(ev, 'response', ev))[:200]}")
        raise RuntimeError("stream ended without a final response")
    finally:  # an unclosed stream keeps its pooled connection: 100 leaks deadlock the client
        getattr(stream, "close", lambda: None)()


def _reasoning_text(r) -> str:
    parts = []
    for it in getattr(r, "output", None) or []:
        if getattr(it, "type", "") == "reasoning":
            for c in list(getattr(it, "content", None) or []) + list(getattr(it, "summary", None) or []):
                parts.append(getattr(c, "text", "") or "")
    return "\n".join(x for x in parts if x)


class Agent:
    TRIES = 8  # attempts on transient errors (429s do not count); PatientAgent raises it
    MAX_WAIT = 180  # longest backoff between attempts, seconds

    def __init__(self, ctx: AgentCtx, client, model: str, system: str, first_user: str,
                 push_every: int = 10, max_steps: int = 100, sleep=time.sleep, show_budget: bool = False,
                 reasoning: str = "none"):
        self.reasoning = reasoning  # reasoning effort; anything but "none" also logs the reasoning text
        self.ctx, self.client, self.model, self.system = ctx, client, model, system
        self.push_every, self.max_steps, self.sleep = push_every, max_steps, sleep
        self.show_budget = show_budget  # environment status line on tool results, like a harness budget meter
        self.steps, self.board_index, self.done = 0, 0, False
        self.items: list = [{"role": "user", "content": first_user}]
        self.log: list[dict] = []

    def _create(self, **kw):
        last, attempt, limited = None, 0, 0
        while attempt < self.TRIES:  # plain retry for transient API errors, like pilot/swarm.py:chat
            try:
                # stream so long generations keep bytes flowing past the gateway's 504 cutoff
                r = self.client.responses.create(
                    model=self.model, instructions=self.system, input=self.items, tools=TOOLS,
                    temperature=0.8, max_output_tokens=MAX_OUTPUT_TOKENS,
                    extra_body={"reasoning": {"effort": self.reasoning}}, stream=True, **kw)
                return r if hasattr(r, "output") else _final(r)  # fakes in tests return a response
            except Exception as e:
                last = e
                sc = getattr(e, "status_code", None)
                fatal = isinstance(sc, int) and 400 <= sc < 500 and sc != 429
                self.log.append({"event": "retry", "attempt": attempt, "error": f"{type(e).__name__}: {str(e)[:120]}"})
                if fatal:
                    raise SessionError(f"API error {sc}: {type(e).__name__}: {str(e)[:200]}") from e
                if sc == 429 and limited < 400:  # per-user rate limit: don't spend an attempt
                    # short jittered wait, not the advertised 60 s: fixed waits made every throttled agent retry
                    # at once (re-triggering the limit) and left most of the account's capacity idle
                    limited += 1
                    self.sleep(random.uniform(5, 20))
                    continue
                attempt += 1
                if attempt < self.TRIES:
                    self.sleep(min(30 * attempt, self.MAX_WAIT))
        raise SessionError(f"API failed after {self.TRIES} attempts: {type(last).__name__}: {str(last)[:200]}")

    def _board_view(self, it) -> list | None:
        """Posts a read_board call will deliver (mirrors tools._run), for exposure logging."""
        try:
            a = json.loads(it.arguments) if it.arguments and it.arguments.strip() else {}
            n = int(a.get("last_n", 20))
        except Exception:
            return None
        return self.ctx.board.all()[-n:] if n > 0 else []

    def _run_calls(self, r) -> list[dict]:
        calls = []
        for it in r.output:
            self.items.append(it.model_dump(exclude_none=True))
            if it.type == "function_call":
                seen = self._board_view(it) if it.name == "read_board" else None
                res = dispatch(it.name, it.arguments, self.ctx)
                if seen is not None and not res.startswith("error"):
                    self.log.append({"event": "read_board", "step": self.steps + 1,
                                     "via": "read_board", "posts": [vars(p) for p in seen]})
                out = res + (f"\n[steps used {self.steps + 1}/{self.max_steps}]" if self.show_budget else "")
                self.items.append({"type": "function_call_output", "call_id": it.call_id, "output": out})
                calls.append({"name": it.name, "arguments": it.arguments, "output": res[:500]})
        return calls

    def step(self) -> None:
        if self.done:
            return
        if self.steps > 0 and self.steps % self.push_every == 0:
            posts, self.board_index = self.ctx.board.since(self.board_index, exclude=self.ctx.agent)
            if posts:
                self.items.append({"role": "user", "content": "New board posts:\n" + self.ctx.board.render(posts)})
                self.log.append({"event": "push", "via": "push", "step": self.steps + 1, "posts": [vars(p) for p in posts]})
        r = self._create()
        calls = self._run_calls(r)
        if not calls:
            self.items.append({"role": "user", "content": NUDGE})
        self.steps += 1
        self.log.append({"event": "step", "step": self.steps, "calls": calls, "text": r.output_text,
                         "reasoning": _reasoning_text(r)})
        self._trim()
        self.done = self.ctx.finished
        if not self.done and (self.steps >= self.max_steps or self.ctx.submissions >= self.ctx.max_submissions):
            self.force_finish()

    def _trim(self) -> None:
        def est():
            return sum(len(json.dumps(i, default=str)) for i in self.items) // 4
        before = est()
        if before <= TRIM_TOKENS:
            return
        n = 0
        for it in self.items:
            if it.get("type") == "function_call_output" and it["output"] != "[output trimmed]":
                it["output"] = "[output trimmed]"
                n += 1
                if est() <= TRIM_TOKENS:
                    break
        self.log.append({"event": "trim", "step": self.steps, "tokens_before": before,
                         "tokens_after": est(), "trimmed": n})

    def force_finish(self) -> None:
        """One extra call forcing `finish`. Not counted as a step."""
        if not self.ctx.finished:
            try:
                r = self._create(tool_choice={"type": "function", "name": "finish"})
                self._run_calls(r)
                self.log.append({"event": "force_finish", "ok": self.ctx.finished})
            except SessionError:
                raise  # an API outage is never agent behaviour: the session runner marks it incomplete
            if not self.ctx.finished:
                self.ctx.writeup = "(no write-up)"
                self.ctx.board.post(self.ctx.tick_fn(), self.ctx.agent, "writeup", self.ctx.writeup)
                self.ctx.finished = True
        self.done = True


def smoke(model: str) -> None:
    import tempfile
    from adaption import Adaption
    from swarm2.board import Board
    from swarm2.issues import write_issue
    from swarm2.workspace import LocalWorkspace
    load_env()
    client = Adaption(timeout=900)
    with tempfile.TemporaryDirectory() as td:
        write_issue("dbl", "double it", [{"input": "1\n", "output": "2\n"}], "print(int(input()) * 3)\n", Path(td))
        ctx = AgentCtx(agent=0, issue="dbl", ws=LocalWorkspace(Path(td)), board=Board(), tick_fn=lambda: 0)
        a = Agent(ctx, client, model, system_prompt(0, "neutral", False),
                  task_message((Path(td) / "issues/dbl.md").read_text()), max_steps=3)
        for _ in range(3):
            a.step()
            if a.done:
                break
        for e in a.log:
            print(json.dumps(e)[:600])
        n = sum(len(e.get("calls", [])) for e in a.log if e["event"] == "step")
        print(f"SMOKE function_calls parsed: {n}; steps: {a.steps}; finished: {ctx.finished}")
        sys.exit(0 if n else 1)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--model", default="qwen3.8-27b")
    args = ap.parse_args()
    if args.smoke:
        smoke(args.model)
