import os
import pytest

from swarm2.workspace import LocalWorkspace, PathError


@pytest.fixture
def ws(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    return LocalWorkspace(root)


def test_roundtrip(ws):
    ws.write_file("a/b.txt", "x")
    assert ws.read_file("a/b.txt") == "x"
    assert ws.list_files("a") == ["b.txt"]


@pytest.mark.parametrize("p", ["../x", "/etc/passwd", "a/../../x", ""])
def test_escape_rejected(ws, p):
    with pytest.raises(PathError):
        ws.read_file(p)
    with pytest.raises(PathError):
        ws.write_file(p, "x")


def test_symlink_escape_rejected(ws, tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "anything").write_text("secret")
    os.symlink(outside, ws.root / "link")
    with pytest.raises(PathError):
        ws.read_file("link/anything")
    with pytest.raises(PathError):
        ws.write_file("link/new", "x")
    assert not (outside / "new").exists()


def test_snapshot_skips_git(ws):
    (ws.root / ".git").mkdir()
    (ws.root / ".git" / "HEAD").write_text("ref")
    (ws.root / "sub").mkdir()
    (ws.root / "sub" / ".git").write_text("gitdir: x")  # nested is not skipped
    (ws.root / "x.py").write_text("1")
    (ws.root / "__pycache__").mkdir()
    (ws.root / "__pycache__" / "x.pyc").write_text("b")
    (ws.root / "sub" / "__pycache__").mkdir()
    (ws.root / "sub" / "__pycache__" / "y.pyc").write_text("b")
    assert ws.snapshot() == {"x.py": "1", "sub/.git": "gitdir: x"}


def test_snapshot_skips_git_file(ws):
    (ws.root / ".git").write_text("gitdir: elsewhere")
    (ws.root / "x.py").write_text("1")
    assert ws.snapshot() == {"x.py": "1"}


def test_run_returns_code_and_output(ws):
    assert ws.run(["python3", "-c", "print(1)"]) == (0, "1\n")
