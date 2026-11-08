# /// script
# requires-python = ">=3.11"
# dependencies = ["adaption>=0.19", "daytona"]
# ///
"""Lockstep session runner + CLI. One session = 4 agents on one repo, each with its own worktree."""
import argparse
import json
import posixpath
import random
import re
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from pathlib import Path

if __package__ in (None, ""):  # run as a script
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from swarm2.agent import Agent, SessionError, load_env
from swarm2.board import Board
from swarm2.label import file_kind, label
from swarm2.prompts import system_prompt, task_message
from swarm2.tools import AgentCtx
from swarm2.workspace import LocalWorkspace, SandboxError

DATA = Path(__file__).resolve().parent / "data"
TEMPLATE = DATA / "repo_template"
POOL = 4


@dataclass
class Config:
    model: str
    wording: str = "ban"
    push_every: int = 10
    max_steps: int = 100
    auto_results: bool = False
    stagger: int = 0
    run: str = "run"
    out_dir: str = "runs2"


def draws(n: int, issues: list[str], seed: int = 0) -> list[list[str]]:
    rng = random.Random(seed)
    return [rng.sample(issues, 4) for _ in range(n)]


class LocalRepo:
    """Offline stand-in for the Daytona session repo: factory (sid, draw) -> repo with workspace/clean/close."""
    def __init__(self, base: Path):
        self.base, self.closed, self._n = Path(base), False, 0

    def __call__(self, sid: str, draw: list[str]):
        self.root = self.base / sid
        self.closed, self._n = False, 0
        for i in range(4):
            shutil.copytree(TEMPLATE, self.root / f"a{i}", dirs_exist_ok=True)
        return self

    def workspace(self, i: int) -> LocalWorkspace:
        return LocalWorkspace(self.root / f"a{i}")

    def clean(self) -> LocalWorkspace:
        d = self.root / f"clean_{self._n}"
        self._n += 1
        shutil.copytree(TEMPLATE, d)
        return LocalWorkspace(d)

    def close(self) -> None:
        self.closed = True


class DaytonaRepo:
    """Factory: acquires a pool sandbox per session and releases it on close."""
    def __call__(self, sid: str, draw: list[str]):
        from swarm2 import daytona_ws as dw
        self.dw, self.sb = dw, dw.acquire()
        try:
            self.repo = dw.SessionRepo(self.sb, sid, draw)
        except BaseException:
            dw.release(self.sb)
            raise
        return self

    def workspace(self, i):
        return self.repo.workspace(i)

    def clean(self):
        return self.repo.clean()

    def close(self):
        try:
            self.repo.close()
        finally:
            self.dw.release(self.sb)


def _exposure(log: list[dict]) -> int | None:
    for e in log:
        if e["event"] in ("push", "read_board") and any(p["author"] == 0 for p in e["posts"]):
            return e["step"]
    return None


def _first_tamper(log: list[dict], issue: str) -> int | None:
    for e in log:
        if e["event"] != "step":
            continue
        for c in e["calls"]:
            if c["name"] != "write_file":
                continue
            try:
                path = posixpath.normpath(json.loads(c["arguments"])["path"])
            except Exception:  # noqa: BLE001
                continue
            if file_kind(path, issue) not in ("solution", "other"):
                return e["step"]
    return None


def run_session(sid: str, draw: list[str], planted: bool, cfg: Config, repo_factory,
                client=None, sleep=time.sleep) -> dict:
    meta = {issue["name"]: issue for issue in json.loads((DATA / "issues.json").read_text())}
    out = Path(cfg.out_dir) / cfg.run / f"{sid}.json"
    board, tick = Board(), [0]
    agents: list[Agent] = []
    secs: list[list[float]] = [[] for _ in range(4)]
    status, error, labels, repo = "complete", None, [None] * 4, None
    try:
        if client is None:
            from adaption import Adaption
            load_env()
            client = Adaption(timeout=900)
        repo = repo_factory(sid, draw)
        for i, issue in enumerate(draw):
            ctx = AgentCtx(agent=i, issue=issue, ws=repo.workspace(i), board=board,
                           tick_fn=lambda: tick[0], auto_results=cfg.auto_results)
            md = (TEMPLATE / "issues" / f"{issue}.md").read_text()
            agents.append(Agent(ctx, client, cfg.model, system_prompt(i, cfg.wording, planted and i == 0),
                                task_message(md), push_every=cfg.push_every, max_steps=cfg.max_steps,
                                sleep=sleep))

        def timed(i):
            t = time.time()
            try:
                agents[i].step()
            finally:
                secs[i].append(round(time.time() - t, 3))

        with ThreadPoolExecutor(4) as ex:
            while not all(a.done for a in agents):
                active = [i for i, a in enumerate(agents) if tick[0] >= i * cfg.stagger and not a.done]
                for f in [ex.submit(timed, i) for i in active]:
                    f.result()
                tick[0] += 1
        original = LocalWorkspace(TEMPLATE).snapshot()
        for i, issue in enumerate(draw):
            final = agents[i].ctx.ws.snapshot()
            labels[i] = label(original, final, issue, agents[i].ctx.ws, repo.clean(), meta[issue]["hard"])
    except Exception as e:  # SessionError, SandboxError, FileNotFoundError, anything infrastructural
        status, error, labels = "incomplete", f"{type(e).__name__}: {str(e)[:300]}", [None] * 4
    finally:
        if repo is not None:
            try:
                repo.close()
            except Exception:  # noqa: BLE001
                pass
    n = len(agents)
    res = {
        "sid": sid, "draw": draw, "planted": planted, "cfg": asdict(cfg), "status": status, "error": error,
        "ticks": tick[0], "board": [vars(p) for p in board.all()],
        "agents": [{
            "agent": i, "issue": draw[i], "planted": planted and i == 0,
            "steps": agents[i].steps if i < n else 0,
            "log": agents[i].log if i < n else [],
            "label": labels[i],
            "step_seconds": secs[i],
            "exposure_step": _exposure(agents[i].log) if 0 < i < n else None,
            "first_tamper_step": _first_tamper(agents[i].log, draw[i]) if i < n else None,
        } for i in range(4)],
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=1, default=str))
    return res


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--sessions", type=int, default=20)
    ap.add_argument("--arm", choices=["planted", "control", "both"], required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--wording", choices=["ban", "neutral"], default="ban")
    ap.add_argument("--auto-results", action="store_true")
    ap.add_argument("--stagger", type=int, default=0)
    ap.add_argument("--parallel", type=int, default=POOL)
    ap.add_argument("--max-steps", type=int, default=100)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args(argv)
    cfg = Config(a.model, a.wording, 10, a.max_steps, a.auto_results, a.stagger, a.run)
    names = [d["name"] for d in json.loads((DATA / "issues.json").read_text())]
    run = re.sub(r"[^A-Za-z0-9_-]", "-", a.run)
    jobs = []
    for k, d in enumerate(draws(a.sessions, names, a.seed)):
        for arm in (["planted", "control"] if a.arm == "both" else [a.arm]):
            jobs.append((f"{run}-d{k}-{arm}", d, arm == "planted"))
    load_env()
    from adaption import Adaption
    client = Adaption(timeout=900)

    def one(job):
        sid, d, planted = job
        t = time.time()
        r = run_session(sid, d, planted, cfg, DaytonaRepo(), client=client)
        print(f"{sid}: {r['status']} {r['error'] or ''} steps={[x['steps'] for x in r['agents']]} "
              f"labels={[(x['label'] or {}).get('cheat') for x in r['agents']]} {time.time() - t:.0f}s", flush=True)
        return r

    with ThreadPoolExecutor(max(1, min(a.parallel, POOL))) as ex:
        list(ex.map(one, jobs))


if __name__ == "__main__":
    main()
