"""SWE-smith (pallets/jinja) task source: candidate filter, builder/validator, and runtime helpers.

One clean jinja checkout is the shared codebase. An agent's worktree = clean checkout + ONLY its own
SWE-smith bug patch. An issue = one SWE-smith instance: problem_statement -> issues/<name>.md, tests =
FAIL_TO_PASS + PASS_TO_PASS ids, hard = FAIL_TO_PASS.

Subcommands (see swarm2/README.md for the exact commands):
  filter  (laptop, reads parquet data only; run with `python -I`): candidate rows -> JSON
  fetch   (Linux box): clone jinja at COMMIT into --base
  build   (Linux box): prepare + validate candidates -> swarm2/data_jinja/
Never run jinja's tests or apply SWE-smith patches on the laptop.
"""
import argparse
import ast
import collections
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

if __package__ in (None, ""):  # run as a script
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from swarm2.label import CONFIG, HOOKS, label_patch  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA_JINJA = Path(__file__).resolve().parent / "data_jinja"
DEFAULT_BASE = ROOT / "runs2" / "jinja_clean"
SWESMITH_REPO = "swesmith/pallets__jinja.ada0a9a6"
URL = "https://github.com/pallets/jinja"
COMMIT = "ada0a9a6fc265128b46949b5144d2eaa55e6df2c"
SRC = "src/jinja2/"
TESTS = "tests/"
# src layout: put the worktree's src/ first on sys.path (never an installed jinja2)
PYTEST = ["python3", "-m", "pytest", "-q", "-p", "no:cacheprovider", "-o", "pythonpath=src"]
RUN_TIMEOUT = 300
COPY_IGNORE = shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache")
ISSUE_FOOTER = "\n\nThe fix belongs in the library source under `src/jinja2/`.\n"
# preferred (harder) bug kinds are interleaved first; func_basic last
PREFERRED = ("lm_rewrite", "combine_file", "func_pm")


# ---------------- runtime ----------------

def kind(path: str) -> str:
    """File kind for the jinja source (same categories as label.file_kind)."""
    name = path.rsplit("/", 1)[-1]
    if name in HOOKS or name.endswith(".pth"):
        return "hook_file"
    if path.startswith(SRC) and name.endswith(".py"):
        return "solution"
    if path in CONFIG:
        return "test_config"
    if path.startswith(TESTS):
        return "test_file" if name.endswith(".py") else "test_data"
    return "other"


def test_cmd(issue: dict) -> list[str]:
    """Runs exactly the issue's test ids on the clean checkout (verified by `build`/`checks.py jinja`):
    the files holding them, minus the other tests collected there. Deleted tests just stop running."""
    cmd = PYTEST + list(issue["test_files"])
    for d in issue["deselect"]:
        cmd += ["--deselect", d]
    return cmd


def issue_md(issue: dict) -> str:
    return issue["issue_md"]


def patch_files(patch: str) -> list[str]:
    out = []
    for m in re.finditer(r"^diff --git a/(\S+) b/(\S+)$", patch, re.M):
        for p in m.groups():
            if p not in out:
                out.append(p)
    return out


def apply_patch(root: Path, patch: str) -> None:
    """git apply in a plain directory. The ceiling stops git from finding an enclosing repo (inside one,
    git apply silently skips paths outside the cwd); the result is then checked file by file."""
    root = Path(root).resolve()
    files = patch_files(patch)
    before = {f: (root / f).read_bytes() if (root / f).exists() else None for f in files}
    env = {**os.environ, "GIT_CEILING_DIRECTORIES": str(root.parent)}
    r = subprocess.run(["git", "apply", "--whitespace=nowarn", "-"], cwd=root, input=patch,
                       capture_output=True, text=True, env=env)
    if r.returncode != 0:
        raise RuntimeError(f"git apply failed: {r.stderr[-300:]}")
    for f in files:
        after = (root / f).read_bytes() if (root / f).exists() else None
        if after == before[f]:
            raise RuntimeError(f"patch did not change {f}")


def make_worktree(base: Path, dst: Path, issue: dict | None) -> None:
    """Copy the clean checkout to dst and apply ONLY this issue's bug (None = clean, no bug)."""
    shutil.copytree(base, dst, ignore=COPY_IGNORE, dirs_exist_ok=True)
    if issue is not None:
        apply_patch(dst, issue["patch"])
        (Path(dst) / "issues").mkdir(exist_ok=True)
        (Path(dst) / "issues" / f"{issue['name']}.md").write_text(issue_md(issue))


def load_issues(data: Path = DATA_JINJA) -> list[dict]:
    return json.loads((Path(data) / "issues.json").read_text())


def ensure_clean(base: Path = DEFAULT_BASE) -> Path:
    """Clone jinja at COMMIT into base if missing; verify HEAD and a clean tree. Linux box only."""
    base = Path(base)
    if not base.exists():
        base.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "-q", URL, str(base)], check=True)
        subprocess.run(["git", "-C", str(base), "checkout", "-q", COMMIT], check=True)
    head = subprocess.run(["git", "-C", str(base), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    if head != COMMIT:
        raise RuntimeError(f"{base}: HEAD {head} != {COMMIT}")
    dirty = subprocess.run(["git", "-C", str(base), "status", "--porcelain"], capture_output=True, text=True).stdout
    if dirty.strip():
        raise RuntimeError(f"{base}: working tree not clean:\n{dirty[:500]}")
    return base


class JinjaSource:
    """Session-facing source: per-agent worktree = clean + own bug; per-issue test ids; jinja file kinds."""
    name = "jinja"

    def __init__(self, base: Path, data: Path = DATA_JINJA, issues: list[dict] | None = None):
        self.base = Path(base)
        self.meta = {i["name"]: i for i in (issues if issues is not None else load_issues(data))}

    def names(self) -> list[str]:
        return list(self.meta)

    def issue_md(self, issue: str) -> str:
        return issue_md(self.meta[issue])

    def test_cmd(self, issue: str) -> list[str]:
        return test_cmd(self.meta[issue])

    def kind(self, path: str, issue: str) -> str:
        return kind(path)

    def make_worktree(self, dst: Path, issue: str) -> None:
        make_worktree(self.base, Path(dst), self.meta[issue])

    def original(self, repo, i: int) -> dict[str, str]:
        return repo.workspace(i).snapshot()  # called before any agent step: clean + this agent's bug

    def label(self, original, final, issue, ws, clean) -> dict:
        return label_patch(original, final, ws, clean, kind, self.test_cmd(issue), RUN_TIMEOUT)


# ---------------- filter (laptop; data only) ----------------

def bug_kind(instance_id: str) -> str:
    return instance_id.rsplit(".", 1)[-1].split("__")[0]


def _group(k: str) -> int:
    for g, p in enumerate(PREFERRED):
        if k.startswith(p):
            return g
    return len(PREFERRED) + (1 if k == "func_basic" else 0)


def _ids(v) -> list[str]:
    if isinstance(v, str):
        v = json.loads(v)
    return [str(x) for x in v]


def candidate(row: dict) -> dict | None:
    """Design filter: one non-test file under src/jinja2/, 1-5 FAIL_TO_PASS, problem_statement > 50 chars."""
    files = patch_files(row["patch"])
    f2p, p2p = _ids(row["FAIL_TO_PASS"]), _ids(row["PASS_TO_PASS"])
    if len(files) != 1 or kind(files[0]) != "solution":
        return None
    if not 1 <= len(f2p) <= 5 or len((row["problem_statement"] or "").strip()) <= 50:
        return None
    return {"instance_id": row["instance_id"], "kind": bug_kind(row["instance_id"]), "bug_file": files[0],
            "patch": row["patch"], "FAIL_TO_PASS": f2p, "PASS_TO_PASS": p2p,
            "problem_statement": row["problem_statement"]}


def order(cands: list[dict]) -> list[dict]:
    """Interleave preferred kind groups (lm_rewrite, combine_file, func_pm_*), then others, func_basic last."""
    groups = collections.defaultdict(list)
    # by the random hash suffix, so sub-kinds (func_pm_ctrl_shuffle, func_pm_remove_*...) mix deterministically
    for c in sorted(cands, key=lambda c: (c["instance_id"].rsplit("__", 1)[-1], c["instance_id"])):
        groups[_group(c["kind"])].append(c)
    out = []
    pref = [groups[g] for g in range(len(PREFERRED))]
    while any(pref):
        for g in pref:
            if g:
                out.append(g.pop(0))
    for g in sorted(k for k in groups if k >= len(PREFERRED)):
        out += groups[g]
    return out


def filter_rows(parquet_dir: Path) -> tuple[list[dict], dict]:
    import pandas as pd
    stats = collections.Counter()
    cands = []
    for f in sorted(Path(parquet_dir).glob("*.parquet")):
        df = pd.read_parquet(f)
        for row in df[df.repo == SWESMITH_REPO].to_dict("records"):
            stats["jinja_rows"] += 1
            c = candidate(row)
            stats["kept" if c else "filtered_out"] += 1
            if c:
                cands.append(c)
    stats.update(f"kind:{c['kind']}" for c in cands)
    return order(cands), dict(stats)


# ---------------- build (Linux box) ----------------

def collect(root: Path, files: list[str]) -> list[str]:
    # PYTEST already has one -q: node ids one per line (-qq would print per-file counts only)
    r = subprocess.run(PYTEST + ["--collect-only"] + files, cwd=root, capture_output=True, text=True,
                       timeout=RUN_TIMEOUT)
    ids = [line.strip() for line in r.stdout.splitlines() if "::" in line]
    if r.returncode != 0 or not ids:
        raise RuntimeError(f"collection failed in {root}: {r.stdout[-500:]}")
    return ids


def issue_name(instance_id: str) -> str:
    # neutral: the SWE-smith kind (e.g. "ctrl_invert_if") would hint at the bug in an agent-visible path
    return "jinja_" + instance_id.rsplit("__", 1)[-1]


def prepare(c: dict, collected: list[str]) -> dict:
    ids = c["FAIL_TO_PASS"] + [i for i in c["PASS_TO_PASS"] if i not in set(c["FAIL_TO_PASS"])]
    files = sorted({i.split("::")[0] for i in ids})
    idset = set(ids)
    deselect = [i for i in collected if i.split("::")[0] in files and i not in idset]
    return {"name": issue_name(c["instance_id"]), "instance_id": c["instance_id"], "kind": c["kind"],
            "bug_file": c["bug_file"], "patch": c["patch"],
            "issue_md": c["problem_statement"].strip() + ISSUE_FOOTER,
            "hard": c["FAIL_TO_PASS"], "tests": ids, "test_files": files, "deselect": deselect}


def build(rows: Path, base: Path, out: Path, target: int, workers: int) -> dict:
    from swarm2.checks import check_jinja_issue
    base = ensure_clean(base)
    cands = json.loads(Path(rows).read_text())
    with tempfile.TemporaryDirectory() as td:
        ref = Path(td) / "clean"
        make_worktree(base, ref, None)
        collected = collect(ref, [TESTS])
    issues, seen = [], set()
    for c in cands:
        i = prepare(c, collected)
        if i["name"] in seen:
            i["name"] = issue_name(c["instance_id"]) + "_" + c["kind"][:4]
        seen.add(i["name"])
        issues.append(i)
    log, kept = {}, []
    with ThreadPoolExecutor(workers) as ex:  # in priority order, batch by batch, until target is reached
        for k in range(0, len(issues), workers):
            batch = issues[k:k + workers]
            for i, errs in zip(batch, ex.map(lambda i: check_jinja_issue(i, base), batch)):
                log[i["instance_id"]] = errs
                print(f"{i['name']} ({i['kind']}): {'ok' if not errs else errs[0][:160]}", flush=True)
                if not errs:
                    kept.append(i)
            if len(kept) >= target:
                break
    kept = kept[:target]
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "issues.json").write_text(json.dumps(kept, indent=1))
    stats = {"candidates": len(cands), "validated": len(log), "passed": sum(not e for e in log.values()),
             "kept": len(kept), "collected_clean": len(collected),
             "kept_kinds": dict(collections.Counter(i["kind"] for i in kept))}
    (out / "repo.json").write_text(json.dumps({
        "url": URL, "commit": COMMIT, "swesmith_repo": SWESMITH_REPO, "python": "3.12",
        "deps": _versions(), "pytest_cmd": PYTEST, "build": stats}, indent=1))
    (out / "build_log.json").write_text(json.dumps(log, indent=1))
    return stats


def _versions() -> dict:
    from importlib.metadata import version
    return {p: version(p) for p in ("pytest", "MarkupSafe", "trio")}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("filter")
    f.add_argument("--parquet-dir", required=True)
    f.add_argument("--out", required=True)
    g = sub.add_parser("fetch")
    g.add_argument("--base", default=str(DEFAULT_BASE))
    b = sub.add_parser("build")
    b.add_argument("--rows", required=True)
    b.add_argument("--base", default=str(DEFAULT_BASE))
    b.add_argument("--out", default=str(DATA_JINJA))
    b.add_argument("--target", type=int, default=40)
    b.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    if a.cmd == "filter":
        rows, st = filter_rows(Path(a.parquet_dir))
        Path(a.out).write_text(json.dumps(rows))
        print(json.dumps(st, indent=1))
    elif a.cmd == "fetch":
        print(ensure_clean(Path(a.base)))
    else:
        print(json.dumps(build(Path(a.rows), Path(a.base), Path(a.out), a.target, a.workers), indent=1))
