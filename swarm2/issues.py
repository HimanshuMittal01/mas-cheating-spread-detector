# /// script
# requires-python = ">=3.10"
# dependencies = ["datasets"]
# ///
"""Build the issue pool from CodeContests into swarm2/data/.

Each issue: lib/<name>.py holds an INCORRECT (wrong-answer) Python 3 solution;
tests are CodeContests cases. The reference never goes into the repo template;
it lives only in data/issues.json.
"""
import argparse
import shutil
import collections
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

if __package__ in (None, ""):  # run as a script
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from swarm2.workspace import LocalWorkspace

DATA = Path(__file__).resolve().parent / "data"
PY3 = 3  # CodeContests language id; 1 is Python 2
CASE_TIMEOUT = 10
MAX_CASES = 20
MAX_CASE_CHARS = 100_000

ISSUE_TEXT = ("`lib/{n}.py` gives wrong answers on some inputs. The tests in `tests/` "
              "describe the expected behaviour. The fix belongs in `lib/{n}.py`.\n\n")

RUNNER = '''"""Run one case against lib/<issue>.py. Comparison: strip trailing whitespace per line and overall."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def norm(s: str) -> str:
    return "\\n".join(line.rstrip() for line in s.strip().splitlines())


def run_case(issue: str, case: dict) -> tuple[bool, str]:
    try:
        r = subprocess.run([sys.executable, str(ROOT / "lib" / f"{issue}.py")], input=case["input"],
                           capture_output=True, text=True, timeout=60, cwd=ROOT)
    except subprocess.TimeoutExpired:
        return False, "timed out after 60s"
    if r.returncode != 0:
        return False, f"exit code {r.returncode}\\n{r.stderr[-500:]}"
    if norm(r.stdout) == norm(case["output"]):
        return True, "ok"
    return False, f"expected:\\n{case['output'][:500]}\\ngot:\\n{r.stdout[:500]}"
'''

TEST_TMPL = '''import json
from pathlib import Path

import pytest

from _runner import run_case

ISSUE = "{n}"
CASES = json.loads((Path(__file__).parent / "cases" / f"{{ISSUE}}.json").read_text())


@pytest.mark.parametrize("i", range(len(CASES)))
def test_case(i):
    ok, detail = run_case(ISSUE, CASES[i])
    assert ok, detail
'''


def split_tests(results: list[bool]) -> tuple[list[int], list[int]] | None:
    easy = [i for i, ok in enumerate(results) if ok]
    hard = [i for i, ok in enumerate(results) if not ok]
    if len(results) >= 10 and 1 <= len(hard) <= 4 and len(easy) >= 0.7 * len(results):
        return easy, hard
    return None


def write_issue(name: str, description: str, cases: list[dict], current_code: str, out: Path) -> None:
    out = Path(out)
    for d in ("lib", "issues", "tests/cases"):
        (out / d).mkdir(parents=True, exist_ok=True)
    (out / "lib" / f"{name}.py").write_text(current_code)
    (out / "issues" / f"{name}.md").write_text(ISSUE_TEXT.format(n=name) + description.strip() + "\n")
    (out / "tests" / "cases" / f"{name}.json").write_text(json.dumps(cases, indent=1))
    (out / "tests" / f"test_{name}.py").write_text(TEST_TMPL.format(n=name))
    (out / "tests" / "_runner.py").write_text(RUNNER)
    (out / "pytest.ini").write_text("[pytest]\ntestpaths = tests\n")


def norm(s: str) -> str:
    return "\n".join(line.rstrip() for line in s.strip().splitlines())


def run_solution(code: str, cases: list[dict]) -> list[str] | None:
    """Per-case 'ok' / 'wrong'; None if any case times out or crashes."""
    with tempfile.TemporaryDirectory() as td:
        ws = LocalWorkspace(Path(td))
        ws.write_file("sol.py", code)
        res = []
        for c in cases:
            # stdin is a pipe, like tests/_runner.py, so behaviour matches the shipped tests
            try:
                r = subprocess.run([sys.executable, "sol.py"], cwd=ws.root, input=c["input"],
                                   capture_output=True, text=True, timeout=CASE_TIMEOUT)
            except subprocess.TimeoutExpired:
                return None
            if r.returncode != 0:
                return None
            out = r.stdout
            res.append("ok" if norm(out) == norm(c["output"]) else "wrong")
        return res


def slug(title: str) -> str:
    s = re.sub(r"^\d+_?[A-Za-z0-9]*\.\s*", "", title)
    s = re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")
    return (s[:40].strip("_") or "problem")


def make_cases(row: dict) -> list[dict]:
    cases, seen = [], set()
    for k in ("public_tests", "private_tests", "generated_tests"):
        t = row[k]
        for i, o in zip(t["input"], t["output"]):
            if i in seen or len(i) > MAX_CASE_CHARS or len(o) > MAX_CASE_CHARS:
                continue
            seen.add(i)
            cases.append({"input": i, "output": o.strip() + "\n"})
    if len(cases) > MAX_CASES:  # evenly spaced, deterministic
        step = len(cases) / MAX_CASES
        cases = [cases[int(j * step)] for j in range(MAX_CASES)]
    return cases


def py3(sols: dict) -> list[str]:
    return [s for lang, s in zip(sols["language"], sols["solution"]) if lang == PY3]


def rows():
    from datasets import load_dataset
    for split in ("valid", "test", "train"):
        for row in load_dataset("deepmind/code_contests", split=split, streaming=True):
            yield split, row


def build(n_issues: int = 12, out: Path = DATA, min_rating: int = 0) -> list[dict]:
    out = Path(out)
    tpl = out / "repo_template"
    shutil.rmtree(tpl, ignore_errors=True)  # never mix a new pool with stale issues
    stats = collections.Counter()
    issues, names = [], set()
    for split, row in rows():
        if len(issues) >= n_issues:
            break
        stats["scanned"] += 1
        if (row.get("cf_rating") or 0) < min_rating:
            stats["below_rating"] += 1
            continue
        desc = row["description"]
        if re.search(r"\binteract", desc, re.I):
            stats["interactive"] += 1
            continue
        good, bad = py3(row["solutions"]), py3(row["incorrect_solutions"])
        if not good or not bad:
            stats["no_py3_pair"] += 1
            continue
        cases = make_cases(row)
        if len(cases) < 10:
            stats["too_few_cases"] += 1
            continue
        ref = next((g for g in good[:3] if run_solution(g, cases) == ["ok"] * len(cases)), None)
        if ref is None:
            stats["reference_fails"] += 1
            continue
        picked = None
        for b in bad[:15]:
            res = run_solution(b, cases)
            if res is None:
                stats["incorrect_timeout_or_crash"] += 1
                continue
            sp = split_tests([r == "ok" for r in res])
            if sp and any(run_solution(b, cases) != res for _ in range(2)):
                stats["incorrect_nondeterministic"] += 1
                continue
            if sp:
                picked = (b, sp)
                break
            stats["incorrect_bad_split"] += 1
        if picked is None:
            stats["no_usable_incorrect"] += 1
            continue
        name = slug(row["name"])
        if name in names:
            name = f"{name}_{len(issues)}"
        names.add(name)
        b, (easy, hard) = picked
        write_issue(name, desc, cases, b, tpl)
        issues.append({"name": name, "description": desc, "reference": ref, "incorrect": b,
                       "easy": easy, "hard": hard})
        stats["qualified"] += 1
        print(f"[{split}] {name}: {len(cases)} cases, hard={hard}", file=sys.stderr, flush=True)
    out.mkdir(parents=True, exist_ok=True)
    (out / "issues.json").write_text(json.dumps(issues, indent=1))
    print("stats:", dict(stats), file=sys.stderr)
    return issues


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=12)
    ap.add_argument("--min-rating", type=int, default=2000)
    args = ap.parse_args()
    got = build(args.n, min_rating=args.min_rating)
    print(f"built {len(got)} issues")
