# /// script
# dependencies = ["daytona", "pytest"]
# ///
"""Daytona pool, per-session repo with four git worktrees, and a path-confined DaytonaWorkspace.

CLI: uv run swarm2/daytona_ws.py --setup 4 | --teardown
Sandbox/API failures raise; they are never turned into agent-looking results.
"""
import json
import os
import shlex
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import re

from swarm2.workspace import PathError, SandboxError, safe_rel  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
POOL_FILE = ROOT / "runs2" / "pool.json"
TEMPLATE = ROOT / "swarm2" / "data" / "repo_template"
LABELS = {"pool": "swarm2"}
GIT = "git -c user.email=s@x -c user.name=swarm"


def load_env() -> None:
    env = ROOT / ".env"
    for line in env.read_text().splitlines() if env.exists() else []:
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"'))


def _client():
    load_env()
    from daytona import Daytona
    return Daytona()


def _retry(fn, what: str, tries: int = 4):
    """Bounded retry for transient SDK/API errors (idempotent calls only); raises SandboxError."""
    for i in range(tries):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001 - SDK raises assorted types
            if i == tries - 1:
                raise SandboxError(f"daytona {what} failed: {e!r}"[:500]) from e
            time.sleep(2 * 2 ** i)


def _exec(sb, script: str, timeout: int = 900, idempotent: bool = True) -> tuple[int, str]:
    """Run a shell script; return (exit code, merged output). Exit code via a unique marker.
    Non-idempotent scripts (agent commands, git worktree add) are never retried."""
    tag = os.urandom(6).hex()
    full = f"sh -c {shlex.quote(script + f'; echo __EXIT{tag}__$?')}"
    call = lambda: sb.process.exec(full, timeout=timeout + 30).result or ""  # noqa: E731
    out = _retry(call, "exec", 4 if idempotent else 1)
    body, sep, rest = out.rpartition(f"__EXIT{tag}__")
    if not sep:
        raise SandboxError(f"daytona exec lost exit marker: {out[-200:]!r}")
    return int(rest.strip().split()[0]), body


def _must(sb, script: str, timeout: int = 900, idempotent: bool = True) -> str:
    code, out = _exec(sb, script, timeout, idempotent)
    if code != 0:
        raise SandboxError(f"sandbox command failed ({code}): {script[:120]} -> {out[-300:]}")
    return out


# ---------- pool ----------

def pool_setup(n: int = 4) -> None:
    from daytona import CreateSandboxFromImageParams, Resources
    if POOL_FILE.exists():
        raise RuntimeError(f"{POOL_FILE} exists; teardown first or reuse the pool")
    d = _client()
    existing = list(d.list())
    if existing:
        raise RuntimeError(f"account already has {len(existing)} sandboxes: {[s.id for s in existing]}")
    made = []
    try:
        for _ in range(n):
            sb = d.create(CreateSandboxFromImageParams(
                image="python:3.12", resources=Resources(cpu=2, memory=2, disk=6),
                labels=LABELS, auto_stop_interval=0), timeout=600)
            made.append(sb)
            _must(sb, "git --version && pip install -q pytest && python3 -m pytest --version", 600)
            try:
                sb.update_network_settings(network_block_all=True)
            except Exception as e:  # tier restricts egress already and refuses per-sandbox changes
                print("network:", str(e)[:120], flush=True)
            print("sandbox", sb.id, "ready", flush=True)
        POOL_FILE.parent.mkdir(exist_ok=True)
        POOL_FILE.write_text(json.dumps([s.id for s in made]))
    except BaseException:
        for sb in made:
            try:
                d.delete(sb)
            except Exception as e:  # noqa: BLE001
                print("cleanup failed for", sb.id, repr(e)[:150], flush=True)
        raise


def pool_teardown() -> None:
    d = _client()
    ids = json.loads(POOL_FILE.read_text()) if POOL_FILE.exists() else []
    for sb in list(d.list()):  # also catches labelled strays
        if sb.id in ids or (sb.labels or {}).get("pool") == "swarm2":
            d.delete(sb)
    POOL_FILE.unlink(missing_ok=True)


_pool: list | None = None
_free: list | None = None
_cv = threading.Condition()


def _load_pool():
    global _pool, _free
    if _pool is None:
        d = _client()
        _pool = [d.get(i) for i in json.loads(POOL_FILE.read_text())]
        _free = list(_pool)


def acquire():
    """Block until a pool sandbox is free; one session per sandbox at a time."""
    with _cv:
        _load_pool()
        while not _free:
            _cv.wait()
        sb = _free.pop()
    try:  # one session per sandbox: anything in /work is left over from a crashed session
        _must(sb, "rm -rf /work/*")
    except BaseException:
        release(sb)
        raise
    return sb


def release(sb) -> None:
    with _cv:
        _free.append(sb)
        _cv.notify()


# ---------- workspace ----------

_LIST = ("import os,sys;d=sys.argv[1];"
         "print(chr(10).join(sorted(n+('/' if os.path.isdir(os.path.join(d,n)) else '') for n in os.listdir(d))))")
_SNAP = r'''
import os, json, sys
root = sys.argv[1]; out = {}
for dp, dn, fn in os.walk(root):
    rel = os.path.relpath(dp, root)
    dn[:] = [d for d in dn if d != "__pycache__" and not (rel == "." and d == ".git")]
    for f in fn:
        r = os.path.normpath(os.path.join(rel, f))
        if r.split(os.sep)[0] == ".git":
            continue
        try:
            out[r.replace(os.sep, "/")] = open(os.path.join(root, r), encoding="utf-8").read()
        except (UnicodeDecodeError, OSError):
            pass
print(json.dumps(out))
'''


class DaytonaWorkspace:
    def __init__(self, sandbox, root: str):
        self.sb = sandbox
        self.root = root.rstrip("/")

    def _resolve(self, path: str) -> str:
        """safe_rel, then remote realpath so symlinks cannot leave the root."""
        full = f"{self.root}/{safe_rel(path)}"
        real = _must(self.sb, f"realpath -m -- {shlex.quote(full)}").strip()
        root_real = _must(self.sb, f"realpath -- {shlex.quote(self.root)}").strip()
        if real != root_real and not real.startswith(root_real + "/"):
            raise PathError(f"path escapes workspace: {path!r}")
        return real

    def list_files(self, path: str = ".") -> list[str]:
        d = self._resolve(path)
        code, out = _exec(self.sb, f"test -d {shlex.quote(d)} && python3 -c {shlex.quote(_LIST)} {shlex.quote(d)}")
        if code != 0:
            raise PathError(f"not a directory: {path!r}")
        return [l for l in out.split("\n") if l]

    def read_file(self, path: str) -> str:
        real = self._resolve(path)
        code, _ = _exec(self.sb, f"test -f {shlex.quote(real)}")
        if code != 0:
            raise PathError(f"not a file: {path!r}")
        data = _retry(lambda: self.sb.fs.download_file(real), "download")
        return (data or b"").decode()

    def write_file(self, path: str, content: str) -> None:
        from daytona import FileUpload
        real = self._resolve(path)
        chk = (f"T={shlex.quote(real)}; R={shlex.quote(self.root)}; [ -d \"$T\" ] && exit 2; d=$(dirname \"$T\"); "
               f"while [ \"$d\" != \"$R\" ] && [ \"$d\" != / ]; do [ -e \"$d\" ] && [ ! -d \"$d\" ] && exit 3; "
               f"d=$(dirname \"$d\"); done; exit 0")
        code, _ = _exec(self.sb, f"( {chk} )")
        if code == 2:
            raise PathError(f"is a directory: {path!r}")
        if code == 3:
            raise PathError(f"a parent of {path!r} is a file")
        if code != 0:
            raise SandboxError(f"write_file precheck failed ({code})")
        _must(self.sb, f"mkdir -p -- {shlex.quote(os.path.dirname(real))}")
        _retry(lambda: self.sb.fs.upload_files([FileUpload(source=content.encode(), destination=real)]), "upload")

    def run(self, cmd: list[str], timeout: int = 900) -> tuple[int, str]:
        line = f"cd {shlex.quote(self.root)} && timeout -k 5 {int(timeout)} {' '.join(shlex.quote(c) for c in cmd)} 2>&1"
        code, out = _exec(self.sb, line, timeout, idempotent=False)
        if code == 124:
            out += f"\n[timed out after {timeout}s]"
        return code, out

    def snapshot(self) -> dict[str, str]:
        out = _must(self.sb, f"python3 -c {shlex.quote(_SNAP)} {shlex.quote(self.root)}")
        return json.loads(out)


class SessionRepo:
    def __init__(self, sandbox, session_id: str, issues: list[str]):
        from daytona import FileUpload
        if not re.fullmatch(r"[A-Za-z0-9_-]+", session_id):
            raise ValueError(f"bad session id: {session_id!r}")
        self.sb, self.base, self.issues = sandbox, f"/work/{session_id}", issues
        self._clean_n = 0
        try:
            self._init()
        except BaseException:
            try:
                self.close()
            except Exception:  # noqa: BLE001
                pass
            raise

    def _init(self):
        from daytona import FileUpload
        sandbox, repo = self.sb, f"{self.base}/repo"
        files = [FileUpload(source=p.read_bytes(), destination=f"{repo}/{p.relative_to(TEMPLATE).as_posix()}")
                 for p in sorted(TEMPLATE.rglob("*")) if p.is_file() and "__pycache__" not in p.parts]
        q = shlex.quote
        _must(sandbox, f"rm -rf {q(self.base)} && mkdir -p {q(repo)}")
        _retry(lambda: sandbox.fs.upload_files(files), "upload template")
        _must(sandbox, f"cd {q(repo)} && git init -q && git add -A && {GIT} commit -qm init"
                       + "".join(f" && git worktree add -q --detach ../a{i}" for i in range(4)), idempotent=False)

    def workspace(self, i: int) -> DaytonaWorkspace:
        if not 0 <= i < 4:
            raise ValueError(i)
        return DaytonaWorkspace(self.sb, f"{self.base}/a{i}")

    def clean(self) -> DaytonaWorkspace:
        n, self._clean_n = self._clean_n, self._clean_n + 1
        _must(self.sb, f"cd {shlex.quote(self.base + '/repo')} && git worktree add -q --detach ../clean_{n} "
                       "$(git rev-list --max-parents=0 HEAD)", idempotent=False)
        return DaytonaWorkspace(self.sb, f"{self.base}/clean_{n}")

    def close(self) -> None:
        _must(self.sb, f"rm -rf {shlex.quote(self.base)}")


if __name__ == "__main__":
    if sys.argv[1:2] == ["--setup"]:
        pool_setup(int(sys.argv[2]) if len(sys.argv) > 2 else 4)
    elif sys.argv[1:2] == ["--teardown"]:
        pool_teardown()
    else:
        print("usage: daytona_ws.py --setup N | --teardown")
