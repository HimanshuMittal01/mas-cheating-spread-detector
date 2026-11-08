# swarm2

Run a session set (flags of `python -m swarm2.session`): `--run NAME --arm planted|control|both --model M --sessions N [--wording ban|neutral] [--auto-results] [--stagger S] [--parallel 4] [--max-steps 100] [--seed 0]`.
Defaults: `--sessions 20`, `--wording ban`, `--parallel 4` (pool size), `--max-steps 100`.

Analyze: `uv run swarm2/analyze.py runs2/NAME [--json]` (grouped by model, wording, auto_results, stagger).

## Check 3 (calibration)
Per shortlisted model (`glm-5.2`, `deepseek-v4-flash`, `qwen3.8-27b`), 2 control sessions = 8 honest tasks:

    uv run -m swarm2.session --run check3-<model> --arm control --sessions 2 --wording neutral --model <model>

Read the honest truth rate (target low), seconds per step, loop errors. Pick the default model.

## Check 4 (planted agent)
    uv run -m swarm2.session --run check4 --arm planted --sessions 2 --model <picked>

Agent 0 must have `cheat=True` and a non-empty write-up.

## Check 5 (wording)
    uv run -m swarm2.session --run check5-ban --arm both --sessions 3 --wording ban --model <picked>
    uv run -m swarm2.session --run check5-neutral --arm both --sessions 3 --wording neutral --model <picked>

Hand-check every label against the trajectories, then pick the wording.

## Baseline
    uv run -m swarm2.session --run baseline --arm both --sessions 20 --wording <picked> --model <picked>
