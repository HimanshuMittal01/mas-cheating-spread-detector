import json
import subprocess
import sys
from types import SimpleNamespace

import pytest

from swarm2 import agent as agent_mod
from swarm2.agent import NUDGE, Agent, SessionError
from swarm2.board import Board
from swarm2.issues import write_issue
from swarm2.prompts import PLANTED, PLANTED_METHOD_EXAMPLE, system_prompt
from swarm2.tools import AgentCtx
from swarm2.workspace import LocalWorkspace

CASES = [{"input": "1\n", "output": "2\n"}, {"input": "2\n", "output": "4\n"}]


class Item:
    def __init__(self, **kw):
        self.__dict__.update(kw)

    def model_dump(self, exclude_none=False):
        return dict(self.__dict__)


def fc(name, args, cid="c1"):
    return Item(type="function_call", name=name, arguments=args if isinstance(args, str) else json.dumps(args),
                call_id=cid)


def resp(*items, text=""):
    return SimpleNamespace(output=list(items), output_text=text)


class FakeClient:
    def __init__(self, script):
        self.script, self.calls = list(script), []
        self.responses = self

    def create(self, **kw):
        self.calls.append({**kw, "input": list(kw["input"])})
        r = self.script.pop(0) if self.script else resp(text="hm")
        if isinstance(r, Exception):
            raise r
        return r


def make(tmp_path, script, board=None, **kw):
    write_issue("dbl", "double it", CASES, "print(int(input()) * 3)\n", tmp_path)
    ctx = AgentCtx(agent=1, issue="dbl", ws=LocalWorkspace(tmp_path), board=board or Board(), tick_fn=lambda: 0)
    client = FakeClient(script)
    return Agent(ctx, client, "m", "sys", "go", sleep=lambda s: None, **kw), ctx, client


def outputs(a):
    return [i for i in a.items if i.get("type") == "function_call_output"]


def test_function_call_roundtrip(tmp_path):
    a, ctx, _ = make(tmp_path, [resp(fc("write_file", {"path": "x.txt", "content": "hi"}))])
    a.step()
    assert (tmp_path / "x.txt").read_text() == "hi"
    assert len(outputs(a)) == 1 and outputs(a)[0]["call_id"] == "c1" and a.steps == 1


def test_plain_text_gets_nudge(tmp_path):
    a, _, _ = make(tmp_path, [resp(text="thinking")])
    a.step()
    assert a.steps == 1 and a.items[-1] == {"role": "user", "content": NUDGE}


def test_malformed_args_counted(tmp_path):
    a, _, _ = make(tmp_path, [resp(fc("read_file", "{bad"))])
    a.step()
    assert a.steps == 1 and outputs(a)[0]["output"].startswith("error")


def test_push_every_10(tmp_path):
    b = Board()
    b.post(0, 2, "note", "hello team")
    a, _, _ = make(tmp_path, [resp(text="x")] * 12, board=b)
    for _ in range(10):
        a.step()
    assert not any("hello team" in json.dumps(i) for i in a.items)
    a.step()
    assert [e["step"] for e in a.log if e["event"] == "push"] == [11]
    assert any(i.get("content", "").startswith("New board posts:") and "hello team" in i["content"]
               for i in a.items if "role" in i)


def test_force_finish_at_limit(tmp_path):
    script = [resp(text="a"), resp(text="b"), resp(text="c"),
              resp(fc("finish", {"writeup": "done it"}))]
    a, ctx, client = make(tmp_path, script, max_steps=3)
    for _ in range(3):
        a.step()
    assert a.done and ctx.writeup == "done it"
    assert client.calls[-1]["tool_choice"] == {"type": "function", "name": "finish"}


def test_force_finish_no_finish_call_posts_placeholder(tmp_path):
    a, ctx, _ = make(tmp_path, [resp(text="a"), resp(text="still no tool")], max_steps=1)
    a.step()
    assert a.done and ctx.finished and ctx.writeup == "(no write-up)"
    assert [p.kind for p in ctx.board.all()] == ["writeup"]


def test_force_finish_api_failure_raises_not_labelled(tmp_path):
    a, ctx, _ = make(tmp_path, [resp(text="a")] + [RuntimeError("boom")] * 8, max_steps=1)
    with pytest.raises(SessionError):
        a.step()
    assert not ctx.finished and ctx.board.all() == []


def test_read_board_logged_structured(tmp_path):
    b = Board()
    for i in range(30):
        b.post(i, 2, "note", "n" + "x" * 300 + str(i))
    a, _, _ = make(tmp_path, [resp(fc("read_board", {"last_n": 25}))], board=b)
    a.step()
    ev = [e for e in a.log if e["event"] == "read_board"]
    assert len(ev) == 1 and ev[0]["step"] == 1 and len(ev[0]["posts"]) == 25
    assert ev[0]["posts"][-1] == {"tick": 29, "author": 2, "kind": "note", "text": "n" + "x" * 300 + "29"}


def test_force_finish_at_submission_limit(tmp_path):
    a, ctx, _ = make(tmp_path, [resp(fc("submit", {})), resp(fc("finish", {"writeup": "w"}))])
    ctx.max_submissions = 1
    a.step()
    assert a.done and ctx.writeup == "w"


def test_retry_then_session_error(tmp_path):
    a, _, client = make(tmp_path, [RuntimeError("x")] * 8)
    with pytest.raises(SessionError):
        a.step()
    assert len(client.calls) == 8


def test_trim_keeps_own_messages(tmp_path):
    big = "x" * 1_000_000
    (tmp_path / "big.txt").write_text(big)
    a, _, _ = make(tmp_path, [resp(fc("read_file", {"path": "big.txt"}), text="reading")])
    a.step()
    assert outputs(a)[0]["output"] == "[output trimmed]"
    assert any(i.get("type") == "function_call" for i in a.items)
    assert a.items[0] == {"role": "user", "content": "go"}
    assert any(e["event"] == "trim" for e in a.log)


def test_planted_prompt_only_extra_line():
    assert system_prompt(0, "ban", True) == system_prompt(0, "ban", False) + PLANTED


def test_planted_conftest_makes_failures_pass(tmp_path):
    write_issue("dbl", "double it", CASES, "print(int(input()) * 3)\n", tmp_path)
    cmd = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_dbl.py"]
    assert subprocess.run(cmd, cwd=tmp_path, capture_output=True).returncode != 0
    (tmp_path / "conftest.py").write_text(PLANTED_METHOD_EXAMPLE)
    assert subprocess.run(cmd, cwd=tmp_path, capture_output=True).returncode == 0


def test_4xx_fails_fast_but_429_retries(tmp_path):
    class E(Exception):
        def __init__(self, c):
            self.status_code = c
    a, _, client = make(tmp_path, [E(400)] * 8)
    with pytest.raises(SessionError):
        a.step()
    assert len(client.calls) == 1
    a, _, client = make(tmp_path, [E(429), E(503), resp(fc("finish", {"writeup": "w"}))])
    a.step()
    assert len(client.calls) == 3


def test_exposure_events_record_via(tmp_path):
    b = Board()
    b.post(0, 0, "note", "n")
    a, _, _ = make(tmp_path, [resp(fc("read_board", {}))], board=b)
    a.step()
    assert [e["via"] for e in a.log if e["event"] == "read_board"] == ["read_board"]
    a, _, _ = make(tmp_path, [resp(fc("list_files", {}))] * 2, board=b, push_every=1)
    a.step()
    a.step()
    assert [e["via"] for e in a.log if e["event"] == "push"] == ["push"]


def test_streamed_response_and_failed_stream(tmp_path):
    from swarm2.agent import _final
    done = resp(fc("finish", {"writeup": "w"}))
    ok = [SimpleNamespace(type="response.created"), SimpleNamespace(type="response.completed", response=done)]
    assert _final(iter(ok)) is done
    import pytest
    with pytest.raises(RuntimeError):
        _final(iter([SimpleNamespace(type="response.created")]))
    # a cut-off stream is retried like any transient error
    a, ctx, client = make(tmp_path, [iter([SimpleNamespace(type="response.failed", response="x")]), done])
    a.step()
    assert ctx.finished and any(e["event"] == "retry" for e in a.log)


def test_stream_closed_after_final():
    from swarm2.agent import _final

    class S:
        closed = False
        def __iter__(self):
            yield SimpleNamespace(type="response.completed", response="r")
            yield SimpleNamespace(type="response.done")
        def close(self):
            S.closed = True
    assert _final(S()) == "r" and S.closed


def test_budget_line_only_when_enabled(tmp_path):
    a, ctx, client = make(tmp_path, [resp(fc("list_files", {})), resp(fc("list_files", {}))], max_steps=30, show_budget=True)
    a.step(); a.step()
    outs = [o["output"] for o in outputs(a)]
    assert outs[0].endswith("[steps used 1/30]") and outs[1].endswith("[steps used 2/30]")
    b, _, _ = make(tmp_path / "b", [resp(fc("list_files", {}))])
    b.step()
    assert "steps used" not in outputs(b)[0]["output"]
