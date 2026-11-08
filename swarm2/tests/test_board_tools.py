import json

import pytest

from swarm2.board import Board
from swarm2.issues import write_issue
from swarm2.tools import TOOLS, AgentCtx, dispatch
from swarm2.workspace import LocalWorkspace

CASES = [{"input": "1\n", "output": "2\n"}, {"input": "2\n", "output": "4\n"}]
GOOD = "n = int(input())\nprint(n * 2)\n"
BAD = "n = int(input())\nprint(n * 3)\n"


def make_ctx(tmp_path, code=GOOD, auto=False, board=None, agent=1):
    write_issue("dbl", "double it", CASES, code, tmp_path)
    return AgentCtx(agent=agent, issue="dbl", ws=LocalWorkspace(tmp_path), board=board or Board(),
                    tick_fn=lambda: 7, auto_results=auto)


def call(ctx, name, **kw):
    return dispatch(name, json.dumps(kw), ctx)


def test_since_excludes_self_and_advances():
    b = Board()
    b.post(1, 0, "note", "a")
    b.post(2, 1, "note", "b")
    b.post(3, 2, "note", "c")
    posts, idx = b.since(0, exclude=1)
    assert [p.text for p in posts] == ["a", "c"] and idx == 3
    assert b.since(idx, exclude=1) == ([], 3)
    assert b.render(posts[:1]) == "[t1] agent 0 (note): a"


def test_dispatch_bad_json(tmp_path):
    ctx = make_ctx(tmp_path)
    assert dispatch("read_file", "{not json", ctx).startswith("error")
    assert dispatch("read_file", "{}", ctx).startswith("error")
    assert dispatch("nope", "{}", ctx).startswith("error")
    assert dispatch("run_tests", '{"x": 1}', ctx).startswith("error")
    assert dispatch("read_file", "[1]", ctx).startswith("error")


def test_dispatch_path_escape(tmp_path):
    ctx = make_ctx(tmp_path / "w")
    assert call(ctx, "read_file", path="../x").startswith("error")
    assert call(ctx, "read_file", path="/etc/passwd").startswith("error")
    assert call(ctx, "write_file", path="../x", content="y").startswith("error")
    assert not (tmp_path / "x").exists()
    assert call(ctx, "read_file", path="lib").startswith("error")


def test_file_tools(tmp_path):
    ctx = make_ctx(tmp_path)
    assert "lib/" in call(ctx, "list_files", path=".")
    call(ctx, "write_file", path="lib/new.py", content="hi")
    assert call(ctx, "read_file", path="lib/new.py") == "hi"


def test_run_tests_and_submit_cap(tmp_path):
    ctx = make_ctx(tmp_path, BAD)
    assert "failed" in call(ctx, "run_tests")
    assert ctx.submissions == 0
    for _ in range(5):
        assert "failed" in call(ctx, "submit")
    assert call(ctx, "submit") == "error: submission limit reached; call finish with your write-up"
    assert ctx.submissions == 5


def test_finish_posts_writeup(tmp_path):
    ctx = make_ctx(tmp_path)
    call(ctx, "finish", writeup="done")
    assert ctx.finished and ctx.writeup == "done"
    p = ctx.board.all()[-1]
    assert (p.kind, p.text, p.author, p.tick) == ("writeup", "done", 1, 7)
    assert call(ctx, "list_files").startswith("error")


def test_post_and_read_board(tmp_path):
    b = Board()
    b.post(1, 2, "note", "hello")
    ctx = make_ctx(tmp_path, board=b)
    call(ctx, "post", text="mine")
    assert b.all()[-1].kind == "note"
    assert "agent 2 (note): hello" in call(ctx, "read_board", last_n=5)


def test_auto_results_posts_only_when_enabled(tmp_path):
    ctx = make_ctx(tmp_path / "a", GOOD, auto=False)
    call(ctx, "submit")
    assert ctx.board.all() == []
    ctx = make_ctx(tmp_path / "b", GOOD, auto=True)
    call(ctx, "submit")
    assert [(p.kind, p.text) for p in ctx.board.all()] == [("result", "agent 1: dbl passed")]
    ctx = make_ctx(tmp_path / "c", BAD, auto=True)
    call(ctx, "submit")
    assert ctx.board.all()[0].text == "agent 1: dbl failed"


def test_tools_schema():
    names = [t["name"] for t in TOOLS]
    assert names == ["list_files", "read_file", "write_file", "run_tests", "read_board", "post", "submit", "finish"]
    assert all(t["type"] == "function" and "parameters" in t for t in TOOLS)
