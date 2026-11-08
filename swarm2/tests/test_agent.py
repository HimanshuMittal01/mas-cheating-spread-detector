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


def test_force_finish_failure_posts_placeholder(tmp_path):
    a, ctx, _ = make(tmp_path, [resp(text="a")] + [RuntimeError("boom")] * 8, max_steps=1)
    a.step()
    assert a.done and ctx.finished and ctx.writeup == "(no write-up)"
    assert [p.kind for p in ctx.board.all()] == ["writeup"]


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
