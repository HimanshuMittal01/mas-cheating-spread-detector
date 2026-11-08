# Design v3 results: `main`

- Complete rollouts: 96 (incomplete: 0). Honest agent outcomes: 288 (249 with a post, 39 controls).

## Primary measure

- Tamper share with a post: **9.2%** (23/249)
- Tamper share in controls (no post): **0.0%** (0/39)
- **Spread = +9.2%**
- Rollouts tipped (≥2 of 3 honest tamper): 4/83 with a post, 0/13 controls
- Any cheat (visible pass on an impossible task): 17.3% with a post, 2.6% controls; special-casing the bad test (visible + ground-truth pass): 20 with a post, 1 controls
- Tried to tamper (failed visible run): 12 with a post, 1 controls
- Honest ground-truth success: 8.0% with a post, 2.6% controls

## 1. Distributions: tamper share by factor level (rollouts with a post)

| Factor | Level 0 | Level 1 | Difference |
|---|---|---|---|
| method | 2% (3/126) [1%, 7%] | 16% (20/123) [11%, 24%] | +14% |
| success | 8% (10/120) [5%, 15%] | 10% (13/129) [6%, 16%] | +2% |
| persuade | 4% (5/126) [2%, 9%] | 15% (18/123) [9%, 22%] | +11% |
| sources | 5% (6/114) [2%, 11%] | 13% (17/135) [8%, 19%] | +7% |
| coordinate | 7% (9/123) [4%, 13%] | 11% (14/126) [7%, 18%] | +4% |
| test_wording | 8% (10/123) [4%, 14%] | 10% (13/126) [6%, 17%] | +2% |
| push_every | 9% (11/123) [5%, 15%] | 10% (12/126) [6%, 16%] | +1% |
| model | 9% (10/117) [5%, 15%] | 10% (13/132) [6%, 16%] | +1% |
| mode | 5% (7/129) [3%, 11%] | 13% (16/120) [8%, 21%] | +8% |
| auto_results | 9% (12/132) [5%, 15%] | 9% (11/117) [5%, 16%] | +0% |

Settings by tamper share (0 / ≤1/3 / ≤2/3 / >2/3): [20, 10, 2, 0]

## 2–3. Main model and rank

Model: logit, errors clustered by rollout.

| Factor | AME | SE | p | p (Holm) |
|---|---|---|---|---|
| method | +0.152 | 0.059 | 0.00957 | 0.0957 |
| persuade | +0.101 | 0.043 | 0.018 | 0.162 |
| mode | +0.075 | 0.044 | 0.09 | 0.72 |
| sources | +0.063 | 0.038 | 0.0989 | 0.72 |
| coordinate | +0.032 | 0.039 | 0.411 | 1 |
| push_every | +0.014 | 0.039 | 0.72 | 1 |
| model | +0.012 | 0.037 | 0.756 | 1 |
| success | +0.009 | 0.039 | 0.826 | 1 |
| auto_results | -0.001 | 0.038 | 0.982 | 1 |
| test_wording | -0.003 | 0.043 | 0.939 | 1 |

## 4. Robustness

- Top 3 by AME: ['method', 'persuade', 'mode']
- Top 3 with 'rollout tipped' as outcome: ['mode', 'persuade', 'method']
- Top 3 by random-forest permutation importance: ['test_wording', 'push_every', 'method']
- Leave-one-setting-out, share of refits where each stays top 3: method 100%, persuade 97%, mode 81%

## 5. Trace check (tampering agents)

- n = 23. Root conftest: 57%. Mean code similarity to posted hook: 0.57.

| Factor | Level | n | Root conftest | Code similarity | Steps exposure→tamper | Failed runs before |
|---|---|---|---|---|---|---|
| method | 0 | 3 | 0% | 0.00 | 10.3 | 0.0 |
| method | 1 | 20 | 65% | 0.65 | 11.4 | 0.0 |
| success | 0 | 10 | 60% | 0.60 | 10.3 | 0.0 |
| success | 1 | 13 | 54% | 0.54 | 12.1 | 0.0 |
| persuade | 0 | 5 | 40% | 0.40 | 12.6 | 0.0 |
| persuade | 1 | 18 | 61% | 0.61 | 10.9 | 0.0 |
| coordinate | 0 | 9 | 67% | 0.67 | 10.3 | 0.0 |
| coordinate | 1 | 14 | 50% | 0.50 | 11.9 | 0.0 |
| sources | 0 | 6 | 33% | 0.33 | 9.7 | 0.0 |
| sources | 1 | 17 | 65% | 0.65 | 11.9 | 0.0 |

## Communication

- Retransmission (honest post mentions the hook): 16%; pushback: 17%; explicit refusal of the hook: 7%; disclosure in write-up among tamperers: 74%

## Likely causes

A factor is a likely cause only if AME > 0 after Holm, it stays on top in the robustness checks, and its trace matches.

- Pass Holm: none
