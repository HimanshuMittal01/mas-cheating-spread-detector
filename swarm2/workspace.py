"""Workspace protocol and a local, path-confined implementation."""
import os
import subprocess
from pathlib import Path, PurePosixPath
from typing import Protocol


class PathError(Exception):
    pass


class SandboxError(RuntimeError):
    """Sandbox/API failure (not agent behaviour); must propagate, never become tool output."""


def safe_rel(path: str) -> str:
    """Normalise a relative path; reject empty, absolute, or escaping paths."""
    if not path or not path.strip():
        raise PathError("empty path")
    if path.startswith("/") or path.startswith("\\") or "\x00" in path:
        raise PathError(f"absolute or invalid path: {path!r}")
    parts: list[str] = []
    for part in PurePosixPath(path).parts:
        if part == "..":
            if not parts:
                raise PathError(f"path escapes workspace: {path!r}")
            parts.pop()
        elif part != ".":
            parts.append(part)
    return "/".join(parts) or "."


class Workspace(Protocol):
    def list_files(self, path: str = ".") -> list[str]: ...
    def read_file(self, path: str) -> str: ...
    def write_file(self, path: str, content: str) -> None: ...
    def run(self, cmd: list[str], timeout: int = 900) -> tuple[int, str]: ...
    def snapshot(self) -> dict[str, str]: ...


class LocalWorkspace:
    def __init__(self, root: Path):
        self.root = Path(root).resolve()

    def _resolve(self, path: str) -> Path:
        p = (self.root / safe_rel(path)).resolve()
        if p != self.root and self.root not in p.parents:
            raise PathError(f"path escapes workspace: {path!r}")
        return p

    def list_files(self, path: str = ".") -> list[str]:
        d = self._resolve(path)
        if not d.is_dir():
            raise PathError(f"not a directory: {path!r}")
        return sorted(c.name + ("/" if c.is_dir() else "") for c in d.iterdir())

    def read_file(self, path: str) -> str:
        return self._resolve(path).read_text()

    def write_file(self, path: str, content: str) -> None:
        p = self._resolve(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)

    def run(self, cmd: list[str], timeout: int = 900) -> tuple[int, str]:
        try:
            r = subprocess.run(cmd, cwd=self.root, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, text=True, timeout=timeout)
        except subprocess.TimeoutExpired as e:
            out = e.stdout.decode(errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
            return 124, out + f"\n[timed out after {timeout}s]"
        return r.returncode, r.stdout

    def snapshot(self) -> dict[str, str]:
        out: dict[str, str] = {}
        for dirpath, dirnames, filenames in os.walk(self.root):
            rel_dir = Path(dirpath).relative_to(self.root)
            dirnames[:] = [d for d in dirnames if d != "__pycache__"
                           and not (rel_dir == Path(".") and d == ".git")]
            for f in filenames:
                rel = rel_dir / f
                if rel.parts[0] == ".git":
                    continue
                try:
                    out[rel.as_posix()] = (self.root / rel).read_text()
                except UnicodeDecodeError:
                    continue
        return out
