"""Run one case against lib/<issue>.py. Comparison: strip trailing whitespace per line and overall."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def norm(s: str) -> str:
    return "\n".join(line.rstrip() for line in s.strip().splitlines())


def run_case(issue: str, case: dict) -> tuple[bool, str]:
    try:
        r = subprocess.run([sys.executable, str(ROOT / "lib" / f"{issue}.py")], input=case["input"],
                           capture_output=True, text=True, timeout=60, cwd=ROOT)
    except subprocess.TimeoutExpired:
        return False, "timed out after 60s"
    if r.returncode != 0:
        return False, f"exit code {r.returncode}\n{r.stderr[-500:]}"
    if norm(r.stdout) == norm(case["output"]):
        return True, "ok"
    return False, f"expected:\n{case['output'][:500]}\ngot:\n{r.stdout[:500]}"
