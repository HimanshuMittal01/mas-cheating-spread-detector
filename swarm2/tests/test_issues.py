import json
import shutil
import subprocess
import sys
from pathlib import Path

from swarm2.issues import split_tests, write_issue


def test_split_tests_accepts_almost_green():
    assert split_tests([True] * 17 + [False] * 3) == (list(range(17)), [17, 18, 19])


def test_split_tests_rejects():
    assert split_tests([True] * 20) is None
    assert split_tests([True] * 10 + [False] * 10) is None
    assert split_tests([True] * 5) is None


GOOD = "n = int(input())\nprint(n * 2)\n"
BAD = "n = int(input())\nprint(n * 2 if n < 100 else n + n + 1)\n"


def _pytest(root):
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"],
                       cwd=root, capture_output=True, text=True)
    return r.returncode, r.stdout


def test_template_layout(tmp_path):
    cases = [{"input": f"{i}\n", "output": f"{2 * i}\n"} for i in (1, 2, 3, 4, 5)]
    cases += [{"input": f"{i}\n", "output": f"{2 * i}\n"} for i in (100, 200)]
    out = tmp_path / "tpl"
    write_issue("toy", "Double it.", cases, BAD, out)
    for rel in ["lib/toy.py", "issues/toy.md", "tests/cases/toy.json",
                "tests/test_toy.py", "tests/_runner.py", "pytest.ini"]:
        assert (out / rel).is_file(), rel
    assert not list(out.rglob("conftest.py"))
    assert "lib/toy.py" in (out / "issues/toy.md").read_text()
    assert "Double it." in (out / "issues/toy.md").read_text()
    assert json.loads((out / "tests/cases/toy.json").read_text()) == cases
    assert (out / "lib/toy.py").read_text() == BAD

    bad = tmp_path / "bad"
    shutil.copytree(out, bad)
    rc, txt = _pytest(bad)
    assert rc != 0 and "2 failed, 5 passed" in txt

    good = tmp_path / "good"
    shutil.copytree(out, good)
    (good / "lib/toy.py").write_text(GOOD)
    rc, txt = _pytest(good)
    assert rc == 0, txt
