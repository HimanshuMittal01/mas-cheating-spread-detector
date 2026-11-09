# mas-cheating-spread-detector

**A Shortcut on the Team Board Spreads Only When the Honest Route Is Closed: Test Tampering in LLM Coding Teams**

Our entry for Apart Research's Swarm Alignment Hackathon (November 2026). Paper: [docs/submission/submission.pdf](docs/submission/submission.pdf) (source text: [docs/submission/report.md](docs/submission/report.md)).

**Question:** when one agent in a realistic coding team takes a shortcut on hard tests, does the shortcut spread to its teammates, and which operator choices change that?

**Setup:** 4 LLM agents fix different bugs in isolated worktrees of one Python repository and share a team board. Agent 0 (a planted LLM or a scripted post) shares a root `conftest.py` pytest hook that reports failing tests as passed. Every agent's final code is regraded on a clean checkout against the correct tests, so the labels (hook, test tampering, special-casing, honest) are exact.

## Four lines of experiments

| Line | What | Code | Results |
|---|---|---|---|
| A | open route: correct tests, real planted Gemma | `swarm2/session.py` | `docs/learnings.md` |
| B | closed route: one wrong test + CI gate, 10-factor screen (GLM, Qwen) | tag `line-b-v3-screen`, `swarm2/v3.py` | `results/main/corrected.md` |
| C | Qwen + reasoning on, correct vs wrong tests, scripted post vs placebo | `swarm2/session.py --tasks almost/impossible --reasoning medium --stakes --post full` | `swarm2/analyze_mx.py` |
| D | realistic repo (`datakit`), real cheater vs scripted post vs control | tag `line-b-v3-screen`, `swarm2/v4.py` | `results/realism/summary.md` |

Lines B and D were run from the `exp/v3-factor-screen` branch, tagged `line-b-v3-screen`; reproduce them from that tag (main has a newer issue pool).

## Running

See [swarm2/README.md](swarm2/README.md). Model-written code runs only on an isolated Linux box or a Daytona sandbox, never on a laptop. `uv run --python 3.12 --with pytest pytest swarm2/tests` runs the test suite.

## History

The project started as a model-rotation study ("Rotate the Crew"); the pilot that led to the current design is in [pilot/REPORT.md](pilot/REPORT.md), and the run-by-run log is [docs/learnings.md](docs/learnings.md).
