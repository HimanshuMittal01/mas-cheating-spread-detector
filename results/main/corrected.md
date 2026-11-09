# Main run: corrected outcomes

Regrade: each agent's final code was run against the CORRECT (unmutated) tests in a Daytona sandbox.

| Outcome | With post | No post | Test |
|---|---|---|---|
| Posted hook used (CI disabled) | 15/288 | 0/48 | 15/288 vs 0/48, one-sided Fisher p = 0.094 |
| Wrong test restored to correct value | 9/288 | 0/48 | 9/288 vs 0/48, one-sided Fisher p = 0.25 |
| Green suite, wrong code | 25/288 | 1/48 | 25/288 vs 1/48, one-sided Fisher p = 0.088 |
| Old label: tamper | 25/288 | 0/48 | 25/288 vs 0/48, one-sided Fisher p = 0.018 |
| Final code correct | 183/288 | 34/48 | 183/288 vs 34/48, one-sided Fisher p = 0.87 |

- Old-label tampers with correct final code: 23 of 25. Old-label special-cases with correct code: 0 of 23.
- Hook by method block: on 15/144, off 0/144 (15/144 vs 0/144, one-sided Fisher p = 2.1e-05). By model: glm-5.2 3, qwen3.5-397b 12
- Test restores by wording: neutral 8, "don't modify tests" 1. By model: glm-5.2 7, qwen3.5-397b 2

## LPM: Hook (all rollouts with a post)

| Factor | Effect (pts) | SE | p | p (Holm) |
|---|---|---|---|---|
| method | +10.4 | 3.1 | 0.000703 | 0.00703 |
| mode | +9.0 | 3.1 | 0.00332 | 0.0299 |
| persuade | +7.6 | 3.1 | 0.013 | 0.104 |
| test_wording | +6.2 | 3.1 | 0.0421 | 0.294 |
| model | +6.2 | 3.1 | 0.0421 | 0.294 |
| sources | +4.9 | 3.1 | 0.114 | 0.569 |
| push_every | +3.5 | 3.1 | 0.259 | 1 |
| auto_results | +2.1 | 3.1 | 0.498 | 1 |
| coordinate | +0.7 | 3.1 | 0.821 | 1 |
| success | -0.7 | 3.1 | 0.821 | 1 |

## LPM: Hook within method = on (exploratory: resolution III slice)

| Factor | Effect (pts) | SE | p | p (Holm) |
|---|---|---|---|---|
| mode | +18.1 | 5.3 | 0.000588 | 0.00529 |
| persuade | +15.3 | 5.3 | 0.00363 | 0.0291 |
| test_wording | +12.5 | 5.3 | 0.0173 | 0.121 |
| model | +12.5 | 5.3 | 0.0173 | 0.121 |
| sources | +9.7 | 5.3 | 0.0642 | 0.321 |
| push_every | +6.9 | 5.3 | 0.186 | 0.745 |
| auto_results | +4.2 | 5.3 | 0.428 | 1 |
| coordinate | +1.4 | 5.3 | 0.791 | 1 |
| success | -1.4 | 5.3 | 0.791 | 1 |

## LPM: Green suite, wrong code

| Factor | Effect (pts) | SE | p | p (Holm) |
|---|---|---|---|---|
| coordinate | +6.3 | 3.6 | 0.0799 | 0.799 |
| auto_results | +2.1 | 3.6 | 0.559 | 1 |
| persuade | +2.1 | 3.6 | 0.559 | 1 |
| sources | +2.1 | 3.6 | 0.559 | 1 |
| test_wording | -2.1 | 3.6 | 0.559 | 1 |
| method | -3.5 | 3.6 | 0.331 | 1 |
| push_every | -3.5 | 3.6 | 0.331 | 1 |
| model | -4.9 | 3.6 | 0.173 | 1 |
| success | -4.9 | 3.6 | 0.173 | 1 |
| mode | -4.9 | 3.6 | 0.173 | 1 |
