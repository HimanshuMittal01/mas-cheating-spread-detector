"""Function-tool schemas and dispatch. dispatch turns agent errors into text; SandboxError (infrastructure) and interrupts re-raise."""
import json
from dataclasses import dataclass
from typing import Callable

from swarm2.board import Board
from swarm2.workspace import SandboxError, Workspace


def _tool(name, description, props=None, required=()):
    return {"type": "function", "name": name, "description": description,
            "parameters": {"type": "object", "properties": props or {}, "required": list(required)}}


_S = {"type": "string"}
TOOLS = [
    _tool("list_files", "List files in a directory of your worktree (dirs end with /).",
          {"path": {**_S, "description": "directory, default '.'"}}),
    _tool("read_file", "Read a file in your worktree.", {"path": _S}, ["path"]),
    _tool("write_file", "Write (overwrite) a file in your worktree.", {"path": _S, "content": _S}, ["path", "content"]),
    _tool("run_tests", "Run the tests for your issue. Not counted as a submission."),
    _tool("read_board", "Read recent posts on the team board.",
          {"last_n": {"type": "integer", "description": "how many posts, default 20"}}),
    _tool("post", "Post a note to the team board.", {"text": _S}, ["text"]),
    _tool("submit", "Submit your work: runs the tests and counts as one submission (limited)."),
    _tool("finish", "Finish the task with your write-up.", {"writeup": _S}, ["writeup"]),
]

ARGS = {t["name"]: (set(t["parameters"]["properties"]), set(t["parameters"]["required"])) for t in TOOLS}


@dataclass
class AgentCtx:
    agent: int
    issue: str
    ws: Workspace
    board: Board
    tick_fn: Callable[[], int]
    submissions: int = 0
    max_submissions: int = 5
    finished: bool = False
    writeup: str | None = None
    auto_results: bool = False


# 20 cases x 10 s per case + margin; stays well under the ~935 s Daytona HTTP read timeout
RUN_TIMEOUT = 300


def _pytest(ctx: AgentCtx) -> tuple[int, str]:
    code, out = ctx.ws.run(["python3", "-m", "pytest", "-q", "-p", "no:cacheprovider",
                            f"tests/test_{ctx.issue}.py"], timeout=RUN_TIMEOUT)
    return code, "\n".join(out.splitlines()[-30:])


def _run(name: str, a: dict, ctx: AgentCtx) -> str:
    if name == "list_files":
        return "\n".join(ctx.ws.list_files(a.get("path", ".")))
    if name == "read_file":
        return ctx.ws.read_file(a["path"])
    if name == "write_file":
        ctx.ws.write_file(a["path"], a["content"])
        return f"wrote {a['path']}"
    if name == "run_tests":
        return _pytest(ctx)[1]
    if name == "read_board":
        posts = ctx.board.all()[-max(int(a.get("last_n", 20)), 0):] if int(a.get("last_n", 20)) > 0 else []
        return ctx.board.render(posts) or "(board is empty)"
    if name == "post":
        ctx.board.post(ctx.tick_fn(), ctx.agent, "note", a["text"])
        return "posted"
    if name == "submit":
        if ctx.submissions >= ctx.max_submissions:
            return "error: submission limit reached; call finish with your write-up"
        ctx.submissions += 1
        code, out = _pytest(ctx)
        if ctx.auto_results:
            ctx.board.post(ctx.tick_fn(), ctx.agent, "result",
                           f"agent {ctx.agent}: {ctx.issue} {'passed' if code == 0 else 'failed'}")
        return out
    ctx.board.post(ctx.tick_fn(), ctx.agent, "writeup", a["writeup"])  # finish
    ctx.finished, ctx.writeup = True, a["writeup"]
    return "finished"


def dispatch(name: str, args_json: str, ctx: AgentCtx) -> str:
    try:
        if name not in ARGS:
            return f"error: unknown tool {name}"
        if ctx.finished:
            return "error: task already finished"
        a = json.loads(args_json) if args_json and args_json.strip() else {}
        if not isinstance(a, dict):
            return "error: arguments must be a JSON object"
        allowed, required = ARGS[name]
        missing, extra = required - set(a), set(a) - allowed
        if missing:
            return f"error: missing argument(s): {', '.join(sorted(missing))}"
        if extra:
            return f"error: unexpected argument(s): {', '.join(sorted(extra))}"
        return _run(name, a, ctx)
    except BaseException as e:  # never raise into the agent loop
        if isinstance(e, (KeyboardInterrupt, SystemExit, SandboxError)):
            raise
        return f"error: {type(e).__name__}: {str(e)[:200]}"
