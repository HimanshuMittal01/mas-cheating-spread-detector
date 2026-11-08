# Experiment log: design v3 factor screen

Running log, newest entry last. Branch `exp/v3-factor-screen`. Every step is committed and pushed.
Design: [docs/design-v3/design-v3-mechanisms.md](docs/design-v3/design-v3-mechanisms.md) (PDF in the same folder).
Settings: [docs/design-v3/settings.csv](docs/design-v3/settings.csv) (32 main settings × 3 repeats + 16 controls = 112 rollouts).

## Plan

| Step | What | Status |
|---|---|---|
| 0 | Branch, design files, this log | done |
| 1 | Session runner with scripted confederate, one-hop / network modes, settings.csv driver (`swarm2/v3.py`) | in progress |
| 2 | Offline tests (fake client) | — |
| 3 | Checks: API smoke call, Daytona pool, model choice | blocked: keys |
| 4 | Pilot: 8 rollouts (all blocks on / all off × 2 models × 2 modes) | — |
| 5 | Main run: 112 rollouts, random order | — |
| 6 | Analysis: per-factor tamper shares, logistic model, AME, Holm, robustness, trace check | — |
| 7 | Report | — |

## Decisions

- **`prompts.py` is not edited** (it says "edit only with Himanshu"). All new text (post blocks, team size for Sources = 3) is in the new file `swarm2/v3.py`.
- The design v2 session runner (`session.py`, plan task B4) does not exist yet on `main`. The v3 runner is written as a separate file so it does not collide with a teammate's B4.
- The confederate is scripted: no model call. Its post goes on the board at tick 0. Honest agents are agents 1–3 in worktrees `a1`–`a3`.

## Entries

### 2026-11-08: setup
- Cloned the repo, made branch `exp/v3-factor-screen`, and added `docs/design-v3/` (design, PDF, figures, settings).
- `.env` template made locally (gitignored). Waiting for `ADAPTION_API_KEY` and `DAYTONA_API_KEY`.
- Research on scenario variety (deep-research run): adding *cheat method* (conftest hook vs editing `tests/cases/*.json`) and *task difficulty* (almost-green vs impossible) is a later option, not in this run.
