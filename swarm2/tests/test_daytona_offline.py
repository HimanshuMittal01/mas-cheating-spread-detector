import fcntl

import pytest

from swarm2 import daytona_ws as dw
from swarm2.workspace import SandboxError


def test_pool_lock_fails_fast_when_held(tmp_path, monkeypatch):
    monkeypatch.setattr(dw, "LOCK_FILE", tmp_path / "pool.lock")
    monkeypatch.setattr(dw, "_lock_fh", None)
    held = open(tmp_path / "pool.lock", "w")
    fcntl.flock(held, fcntl.LOCK_EX | fcntl.LOCK_NB)
    with pytest.raises(SandboxError, match="another process"):
        dw._take_lock()
    held.close()
    dw._take_lock()
    assert dw._lock_fh is not None
    dw._lock_fh.close()


def test_run_raises_when_root_missing(monkeypatch):
    monkeypatch.setattr(dw, "_exec", lambda sb, s, *a, **k: (1, ""))
    with pytest.raises(SandboxError, match="root missing"):
        dw.DaytonaWorkspace(object(), "/work/x/a0").run(["true"])


def test_snapshot_raises_when_root_missing(monkeypatch):
    def boom(sb, s, *a, **k):
        raise SandboxError("failed (3)")
    monkeypatch.setattr(dw, "_must", boom)
    with pytest.raises(SandboxError):
        dw.DaytonaWorkspace(object(), "/work/x/a0").snapshot()


def test_snapshot_script_exits_nonzero_on_missing_root(tmp_path):
    import subprocess, sys
    r = subprocess.run([sys.executable, "-c", dw._SNAP, str(tmp_path / "nope")])
    assert r.returncode == 3


def test_session_dir_is_neutral(monkeypatch):
    monkeypatch.setattr(dw.SessionRepo, "_init", lambda self: None)
    r = dw.SessionRepo(object(), "run-d3-planted", [])
    assert "planted" not in r.base and "control" not in r.base and r.base.startswith("/work/")
    assert "planted" not in r.workspace(0).root


def test_quarantine_not_reused_and_all_bad_fails(monkeypatch):
    class SB:
        def __init__(self, i): self.id = i
    a, b = SB("a"), SB("b")
    monkeypatch.setattr(dw, "_load_pool", lambda: None)
    monkeypatch.setattr(dw, "_pool", [a, b])
    monkeypatch.setattr(dw, "_free", [a, b])
    monkeypatch.setattr(dw, "_bad", [])
    def must(sb, s, *x, **k):
        raise SandboxError("dead")
    monkeypatch.setattr(dw, "_must", must)
    with pytest.raises(SandboxError, match="dead"):
        dw.acquire()
    with pytest.raises(SandboxError, match="dead"):
        dw.acquire()
    assert dw._free == [] and len(dw._bad) == 2
    with pytest.raises(SandboxError, match="quarantined"):
        dw.acquire()
