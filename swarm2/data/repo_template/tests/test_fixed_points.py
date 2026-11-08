import json
from pathlib import Path

import pytest

from _runner import run_case

ISSUE = "fixed_points"
CASES = json.loads((Path(__file__).parent / "cases" / f"{ISSUE}.json").read_text())


@pytest.mark.parametrize("i", range(len(CASES)))
def test_case(i):
    ok, detail = run_case(ISSUE, CASES[i])
    assert ok, detail
