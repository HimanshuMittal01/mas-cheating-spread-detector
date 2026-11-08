# /// script
# dependencies = ["pytest"]
# ///
"""Pre-grid checks. CLI: uv run swarm2/checks.py tasks"""
import json
import re
import shutil
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from swarm2.issues import DATA  # noqa: E402
from swarm2.label import label  # noqa: E402
from swarm2.prompts import PLANTED_METHOD_EXAMPLE  # noqa: E402
from swarm2.workspace import LocalWorkspace  # noqa: E402

TEMPLATE = DATA / "repo_template"


def _scenario(tmp: Path, issue: dict, apply) -> dict:
    """Fresh template copy, apply a change, label it. Returns label plus failing case ids."""
    name = issue["name"]
    work, clean = tmp / "work", tmp / "clean"
    shutil.copytree(TEMPLATE, work)
    shutil.copytree(TEMPLATE, clean)
    ws, cl = LocalWorkspace(work), LocalWorkspace(clean)
    original = ws.snapshot()
    apply(ws)
    final = ws.snapshot()
    res = label(original, final, name, ws, cl, hard=issue["hard"])
    _, out = ws.run(["python3", "-m", "pytest", "-q", "-rf", "-p", "no:cacheprovider", f"tests/test_{name}.py"])
    res["failed"] = sorted(int(m) for m in re.findall(r"FAILED tests/test_\w+\.py::test_case\[(\d+)\]", out))
    return res


def _check_issue(issue: dict) -> list[str]:
    name, errs = issue["name"], []

    def run(apply):
        with tempfile.TemporaryDirectory() as t:
            return _scenario(Path(t), issue, apply)

    r = run(lambda ws: ws.write_file(f"lib/{name}.py", issue["reference"]))
    if not (r["visible"] and r["truth"]):
        errs.append(f"{name}: reference not green (visible={r['visible']} truth={r['truth']})")

    r = run(lambda ws: None)
    if r["visible"]:
        errs.append(f"{name}: incorrect version passes visible tests")
    if r["failed"] != sorted(issue["hard"]):
        errs.append(f"{name}: incorrect fails cases {r['failed']}, expected hard {sorted(issue['hard'])}")

    r = run(lambda ws: ws.write_file("conftest.py", PLANTED_METHOD_EXAMPLE))
    if not r["cheat"]:
        errs.append(f"{name}: planted conftest not labelled cheat (visible={r['visible']} truth={r['truth']})")

    def drop_hard(ws):
        p = f"tests/cases/{name}.json"
        cases = json.loads(ws.read_file(p))
        ws.write_file(p, json.dumps([c for i, c in enumerate(cases) if i not in set(issue["hard"])]))

    r = run(drop_hard)
    if not r["cheat"]:
        errs.append(f"{name}: removing hard cases not labelled cheat (visible={r['visible']} truth={r['truth']})")
    return errs


def check_tasks() -> list[str]:
    issues = json.loads((DATA / "issues.json").read_text())
    with ThreadPoolExecutor(4) as ex:
        return [e for errs in ex.map(_check_issue, issues) for e in errs]


def main(argv: list[str]) -> int:
    if argv[:1] == ["tasks"]:
        errs = check_tasks()
        if errs:
            print("check 2 FAILED:\n" + "\n".join(errs))
            return 1
        print(f"check 2 passed: {len(json.loads((DATA / 'issues.json').read_text()))} issues")
        return 0
    print("usage: checks.py tasks")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
