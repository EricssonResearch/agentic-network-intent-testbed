# Revision analysis report

Generated 2026-09-27T07:43:39 by tables_to_tex.py; campaign=v1; valid episodes=81; min decisions per episode=20; protocols=[1].

Every table below is also written as LaTeX to this directory; every number is in numbers.json and macros.tex.

## Inventory

| Scenario | Agent | Model | Prot. | Code version(s) | Valid | Discarded (reason) |
|---|---|---|---|---|---|---|
| S1 Peaceful | LLM-full | Qwen3-32B-Instruct | 1 | pre-fix | 10 | - |
| S1 Peaceful | LLM-nospatial | Qwen3-32B-Instruct | 1 | pre-fix | 10 | - |
| S1 Peaceful | LLM-minimal | Qwen3-32B-Instruct | 1 | pre-fix | 5 | 1x only 0 decisions |
| S1 Peaceful | rule | - | 1 | post-fix, pre-fix | 10 | - |
| S1 Peaceful | random | - | 1 | post-fix, pre-fix | 5 | - |
| S1 Peaceful | noop | - | 1 | post-fix, pre-fix | 5 | - |
| S2 Stress | LLM-full | Qwen3-32B-Instruct | 1 | post-fix, pre-fix | 5 | 1x only 2 decisions |
| S2 Stress | rule | - | 1 | post-fix, pre-fix | 9 | 1x only 11 decisions; 1x only 13 decisions |
| S2 Stress | random | - | 1 | post-fix, pre-fix | 5 | - |
| S3 Day/Night | LLM-full | Qwen3-32B-Instruct | 1 | pre-fix | 5 | - |
| S3 Day/Night | rule | - | 1 | post-fix, pre-fix | 5 | - |
| S4 Adversarial | LLM-full | Qwen3-32B-Instruct | 1 | post-fix, pre-fix | 3 | 1x only 11 decisions; 1x only 18 decisions |
| S4 Adversarial | rule | - | 1 | post-fix, pre-fix | 3 | - |
| S4 Adversarial | LLM-v3test | Qwen3-32B-Instruct | 1 | post-fix | 1 | - |

# Main statistics (stats_report.py)

## Per-condition summary (mean ± sample SD; episode = unit)

| Scenario | Agent | N | Avg cov (%) | 95% CI | Final cov (%) | BS deployed mean±SD (median) | Epochs ≥80% | First violation (epoch) |
|---|---|---|---|---|---|---|---|---|
| s1_peaceful | llm | 10 | 52.9 ± 9.3 | [47.5, 58.4] | 37.6 ± 11.2 | 15.4 ± 3.4 (15.5) | 15.5% | 5.5 |
| s1_peaceful | llm_minimal | 5 | 46.9 ± 6.6 | [42.8, 52.9] | 24.6 ± 7.9 | 10.8 ± 5.0 (8) | 15.9% | 5.2 |
| s1_peaceful | llm_nospatial | 10 | 46.7 ± 9.0 | [41.6, 52.1] | 24.1 ± 15.2 | 11.2 ± 5.4 (8.5) | 18.2% | 6.1 |
| s1_peaceful | noop | 5 | 56.5 ± 6.0 | [52.0, 61.6] | 39.6 ± 9.1 | 15.8 ± 4.8 (18) | 18.6% | 6.0 |
| s1_peaceful | random | 5 | 46.3 ± 15.8 | [32.4, 56.2] | 25.4 ± 19.3 | 13.0 ± 5.2 (13) | 14.5% | 4.4 |
| s1_peaceful | rule | 10 | 52.6 ± 10.8 | [45.7, 58.3] | 39.3 ± 16.6 | 18.1 ± 5.7 (19) | 15.5% | 5.5 |
| s2_stress | llm | 5 | 47.9 ± 9.9 | [40.1, 55.5] | 25.8 ± 14.9 | 13.2 ± 5.4 (15) | 17.2% | 5.8 |
| s2_stress | random | 5 | 36.8 ± 12.6 | [26.8, 46.4] | 33.6 ± 25.8 | 15.0 ± 7.9 (18) | 15.2% | 5.4 |
| s2_stress | rule | 9 | 58.6 ± 3.5 | [56.3, 60.6] | 41.8 ± 9.3 | 18.9 ± 4.2 (19) | 18.4% | 5.7 |
| s3_daynight | llm | 5 | 47.6 ± 15.0 | [35.1, 57.4] | 29.4 ± 18.2 | 12.4 ± 6.1 (14) | 17.0% | 5.6 |
| s3_daynight | rule | 5 | 56.8 ± 5.4 | [52.6, 60.7] | 40.6 ± 6.7 | 17.2 ± 3.1 (18) | 14.5% | 4.8 |
| s4_adversarial | llm | 3 | 77.0 ± 8.6 | [71.7, 87.0] | 79.7 ± 10.2 | 8.0 ± 5.3 (6) | 48.3% | 6.0 |
| s4_adversarial | llm_v3test | 1 | 84.3 ± 0.0 | [84.3, 84.3] | 70.0 ± 0.0 | 13.0 ± 0.0 (13) | 82.8% | 6.0 |
| s4_adversarial | rule | 3 | 79.7 ± 7.8 | [71.9, 87.6] | 79.7 ± 9.3 | 14.0 ± 2.6 (13) | 55.2% | 7.3 |

## Pairwise comparisons (Welch t-test on episode means; Hedges' g; Holm-corrected over this family)

| Comparison | n | Δ (pp) | t | df | p | p (Holm) | g | 95% CI (pp) |
|---|---|---|---|---|---|---|---|---|
| S1 LLM vs rule | 10/10 | +0.2 | 0.05 | 17.6 | 0.957 | 1.000 | +0.02 | [-9.3, +9.8] |
| S1 LLM vs no-spatial | 10/10 | +6.2 | 1.51 | 18.0 | 0.148 | 1.000 | +0.65 | [-2.4, +14.8] |
| S1 LLM vs minimal | 10/5 | +6.0 | 1.43 | 11.0 | 0.180 | 1.000 | +0.66 | [-3.2, +15.2] |
| S1 no-spatial vs random | 10/5 | +0.4 | 0.05 | 5.4 | 0.964 | 1.000 | +0.03 | [-18.8, +19.5] |
| S1 noop vs LLM | 5/10 | +3.6 | 0.90 | 11.8 | 0.384 | 1.000 | +0.40 | [-5.1, +12.3] |
| S1 noop vs rule | 5/10 | +3.9 | 0.88 | 12.7 | 0.393 | 1.000 | +0.38 | [-5.6, +13.3] |
| S2 rule vs LLM | 9/5 | +10.7 | 2.34 | 4.6 | 0.071 | 0.712 | +1.57 | [-1.4, +22.8] |
| S2 LLM vs random | 5/5 | +11.1 | 1.55 | 7.6 | 0.162 | 1.000 | +0.89 | [-5.6, +27.8] |
| S3 rule vs LLM | 5/5 | +9.2 | 1.29 | 5.0 | 0.255 | 1.000 | +0.73 | [-9.2, +27.5] |
| S4 rule vs LLM | 3/3 | +2.7 | 0.40 | 4.0 | 0.710 | 1.000 | +0.26 | [-16.1, +21.5] |

## Equivalence (TOST)

| Comparison | margin (pp) | n | p (TOST) |
|---|---|---|---|
| S1 LLM vs rule | ±5 | 10/10 | 0.153 |
| S1 no-spatial vs random | ±5 | 10/5 | 0.283 |

## Notes

- campaign=v1; valid episodes=81; min decisions per episode=20; protocols=[1]
- power to detect 6 pp at SD 9: n=5: 0.15, n=10: 0.29, n=20: 0.54, n=30: 0.72

# regret

## Decision regret

Trigger: coverage drop >= 5 pp between consecutive decisions. Estimators: see module docstring.

| Scenario | Agent | $N$ ep. | Events | Ev./ep. | Legacy-text | Legacy-fig | Geometric-v2 | 95\,\% CI (v2) | Cum./ep. (v2) | Pos. avail. |
|---|---|---|---|---|---|---|---|---|---|---|
| S1 Peaceful | LLM-full | 10 | 91 | 9.10 | 6.7 ± 4.3 | 6.0 ± 3.2 | 6.0 ± 3.2 | [5.4, 6.7] | 55.0 ± 13.1 | 0% |
| S1 Peaceful | LLM-nospatial | 10 | 96 | 9.60 | 7.7 ± 5.0 | 6.7 ± 3.8 | 6.7 ± 3.8 | [5.9, 7.4] | 64.0 ± 15.0 | 0% |
| S1 Peaceful | LLM-minimal | 5 | 43 | 8.60 | 8.3 ± 4.5 | 7.0 ± 3.0 | 7.0 ± 3.0 | [6.1, 7.9] | 60.4 ± 14.7 | 0% |
| S1 Peaceful | rule | 10 | 86 | 8.60 | 7.9 ± 4.8 | 6.9 ± 3.5 | 6.9 ± 3.5 | [6.2, 7.7] | 59.7 ± 16.3 | 0% |
| S1 Peaceful | random | 5 | 42 | 8.40 | 8.0 ± 4.5 | 7.2 ± 3.8 | 7.2 ± 3.8 | [6.1, 8.4] | 60.6 ± 4.7 | 0% |
| S1 Peaceful | noop | 5 | 48 | 9.60 | 7.0 ± 4.5 | 6.2 ± 3.4 | 6.2 ± 3.4 | [5.3, 7.2] | 60.0 ± 10.4 | 0% |
| S2 Stress | LLM-full | 5 | 50 | 10.00 | 7.0 ± 4.8 | 7.0 ± 3.7 | 7.0 ± 3.7 | [6.0, 8.0] | 70.3 ± 13.7 | 0% |
| S2 Stress | rule | 9 | 91 | 10.11 | 6.6 ± 4.0 | 6.1 ± 3.1 | 6.1 ± 3.1 | [5.5, 6.8] | 62.2 ± 11.4 | 0% |
| S2 Stress | random | 5 | 46 | 9.20 | 9.4 ± 5.6 | 7.1 ± 3.7 | 7.1 ± 3.7 | [6.1, 8.2] | 65.6 ± 9.3 | 0% |
| S3 Day/Night | LLM-full | 5 | 41 | 8.20 | 7.8 ± 4.6 | 7.6 ± 3.9 | 7.6 ± 3.9 | [6.4, 8.7] | 62.2 ± 12.8 | 0% |
| S3 Day/Night | rule | 5 | 42 | 8.40 | 6.8 ± 4.2 | 6.6 ± 3.1 | 6.6 ± 3.1 | [5.7, 7.5] | 55.1 ± 11.7 | 0% |
| S4 Adversarial | LLM-full | 3 | 11 | 3.67 | 6.5 ± 3.8 | 6.1 ± 3.1 | 6.1 ± 3.1 | [4.3, 7.7] | 22.3 ± 11.1 | 0% |
| S4 Adversarial | rule | 3 | 14 | 4.67 | 4.0 ± 2.7 | 4.1 ± 2.7 | 4.1 ± 2.7 | [2.7, 5.5] | 19.3 ± 9.3 | 0% |
| S4 Adversarial | LLM-v3test | 1 | 5 | 5.00 | 3.8 ± 3.3 | 4.5 ± 2.9 | 4.5 ± 2.9 | [2.1, 6.5] | 22.7 ± 0.0 | 0% |

## Exact regret (re-simulation)

n/a: no --mapping given (no counterfactual branches have been simulated yet).


# reasoning

## Reasoning taxonomy

Taxonomy: reasoning_taxonomy.json (version revision-2026-09-27), matching mode `substring`.
LLM episodes analysed: 39 (non-LLM episodes excluded: 42).

### Denominators

| Scenario | Agent | Model | $N$ ep. | $N$ dec. | Non-empty | Error | Uncategorized | Valid |
|---|---|---|---|---|---|---|---|---|
| S1 Peaceful | LLM-full | Qwen3-32B-Instruct | 10 | 290 | 240 (82.8%) | 0 (0.0%) | 0 (0.0%) | 240 (82.8%) |
| S1 Peaceful | LLM-nospatial | Qwen3-32B-Instruct | 10 | 283 | 254 (89.8%) | 1 (0.4%) | 1 (0.4%) | 252 (89.0%) |
| S1 Peaceful | LLM-minimal | Qwen3-32B-Instruct | 5 | 145 | 116 (80.0%) | 0 (0.0%) | 0 (0.0%) | 116 (80.0%) |
| S2 Stress | LLM-full | Qwen3-32B-Instruct | 5 | 145 | 102 (70.3%) | 0 (0.0%) | 0 (0.0%) | 102 (70.3%) |
| S3 Day/Night | LLM-full | Qwen3-32B-Instruct | 5 | 138 | 105 (76.1%) | 2 (1.4%) | 0 (0.0%) | 103 (74.6%) |
| S4 Adversarial | LLM-full | Qwen3-32B-Instruct | 3 | 87 | 54 (62.1%) | 0 (0.0%) | 0 (0.0%) | 54 (62.1%) |
| S4 Adversarial | LLM-v3test | Qwen3-32B-Instruct | 1 | 29 | 23 (79.3%) | 0 (0.0%) | 0 (0.0%) | 23 (79.3%) |

### Categories

| Category | Count | \% of dec. ($N$=1117) | \% of non-empty ($N$=894) | LLM-full (\%) | LLM-nospatial (\%) | LLM-minimal (\%) | LLM-v3test (\%) |
|---|---|---|---|---|---|---|---|
| spatial | 789 | 70.6 | 88.3 | 67.4 | 79.5 | 69.7 | 62.1 |
| reactive | 784 | 70.2 | 87.7 | 65.6 | 83.7 | 69.7 | 44.8 |
| temporal | 18 | 1.6 | 2.0 | 1.7 | 2.1 | 0.7 | 0.0 |
| resource | 1 | 0.1 | 0.1 | 0.0 | 0.0 | 0.7 | 0.0 |
| capacity | 77 | 6.9 | 8.6 | 7.3 | 8.5 | 2.8 | 3.4 |
| noop justified | 76 | 6.8 | 8.5 | 6.4 | 6.7 | 9.0 | 6.9 |
| threat | 22 | 2.0 | 2.5 | 0.0 | 0.0 | 0.0 | 75.9 |
| uncategorized | 1 | 0.1 | 0.1 | 0.0 | 0.4 | 0.0 | 0.0 |

*Labels per categorized decision: mean 1.99; multi-label, so category counts do not sum to the number of decisions.*

### Category x action

| Category | noop | place_bs | reconfig_slice | other | Total |
|---|---|---|---|---|---|
| spatial | 5 | 779 | 5 | 0 | 789 |
| reactive | 72 | 710 | 2 | 0 | 784 |
| temporal | 0 | 6 | 12 | 0 | 18 |
| resource | 0 | 0 | 1 | 0 | 1 |
| capacity | 47 | 10 | 20 | 0 | 77 |
| noop justified | 75 | 0 | 1 | 0 | 76 |
| threat | 1 | 21 | 0 | 0 | 22 |
| uncategorized | 1 | 0 | 0 | 0 | 1 |
| empty | 70 | 150 | 3 | 0 | 223 |
| error | 3 | 0 | 0 | 0 | 3 |
| all decisions | 154 | 940 | 23 | 0 | 1117 |

### Annotation sample: 50 decisions (stratified by scenario x backend x action type; requested 50)


# latency_invalid

## Latency

| Camp. | Agent | Model | $N$ dec. | Source | Median | Mean | p90 | p99 | Max | $>$60\,s |
|---|---|---|---|---|---|---|---|---|---|---|
| v1 | LLM-full | Qwen3-32B-Instruct | 660/660 | reconstructed | 12.5 | 15.7 | 28.9 | 48.1 | 100.3 | 1 |
| v1 | LLM-nospatial | Qwen3-32B-Instruct | 283/283 | reconstructed | 10.9 | 11.9 | 18.6 | 29.9 | 48.3 | 0 |
| v1 | LLM-minimal | Qwen3-32B-Instruct | 145/145 | reconstructed | 7.4 | 8.2 | 9.8 | 24.2 | 42.4 | 0 |
| v1 | rule | - | 783/783 | reconstructed | 0.5 | 0.5 | 0.9 | 1.0 | 1.0 | 0 |
| v1 | random | - | 290/290 | reconstructed | 0.4 | 0.5 | 0.9 | 1.0 | 1.0 | 0 |
| v1 | noop | - | 145/145 | reconstructed | 0.5 | 0.5 | 0.9 | 1.0 | 1.0 | 0 |
| v1 | LLM-v3test | Qwen3-32B-Instruct | 29/29 | reconstructed | 15.5 | 17.7 | 28.3 | 28.8 | 28.9 | 0 |

## Parse status / invalid outputs

| Camp. | Agent | Model | $N$ | valid | extracted | fallback\_noop | api\_error | timeout | Invalid (\%) | Extracted (\%) | Syntax-inv. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| v1 | LLM-full | Qwen3-32B-Instruct | 660 | n/a | n/a | n/a | 2 (inf.) | n/a | 0.3 (lower bound) | n/a | 5 |
| v1 | LLM-nospatial | Qwen3-32B-Instruct | 283 | n/a | n/a | n/a | 1 (inf.) | n/a | 0.4 (lower bound) | n/a | 24 |
| v1 | LLM-minimal | Qwen3-32B-Instruct | 145 | n/a | n/a | n/a | 0 (inf.) | n/a | 0.0 (lower bound) | n/a | 25 |
| v1 | rule | - | 783 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0 |
| v1 | random | - | 290 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0 |
| v1 | noop | - | 145 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0 |
| v1 | LLM-v3test | Qwen3-32B-Instruct | 29 | n/a | n/a | n/a | 0 (inf.) | n/a | 0.0 (lower bound) | n/a | 0 |

## Bridge validation outcomes

| Camp. | Agent | Model | $N$ dec. | ordered\_engineer (pre-fix) | queued\_engineer (post-fix) | skipped\_invalid\_position | skipped\_threat | skipped\_water |
|---|---|---|---|---|---|---|---|---|
| v1 | LLM-full | Qwen3-32B-Instruct | 660 | 463 | 51 | 19 | 0 | 1 |
| v1 | LLM-nospatial | Qwen3-32B-Instruct | 283 | 218 | 0 | 0 | 0 | 0 |
| v1 | LLM-minimal | Qwen3-32B-Instruct | 145 | 95 | 0 | 0 | 0 | 0 |
| v1 | rule | - | 783 | 284 | 137 | 178 | 0 | 41 |
| v1 | random | - | 290 | 44 | 86 | 24 | 9 | 40 |
| v1 | noop | - | 145 | 0 | 0 | 0 | 0 | 0 |
| v1 | LLM-v3test | Qwen3-32B-Instruct | 29 | 0 | 7 | 11 | 1 | 1 |

## Run-time

| Camp. | Agent | Model | $N$ ep. | Decisions/ep. | Wall-clock (s) | Peak RSS (MB) |
|---|---|---|---|---|---|---|
| v1 | LLM-full | Qwen3-32B-Instruct | 23 | 28.7 | 1744 ± 92 | n/a |
| v1 | LLM-nospatial | Qwen3-32B-Instruct | 10 | 28.3 | 1714 ± 102 | n/a |
| v1 | LLM-minimal | Qwen3-32B-Instruct | 5 | 29.0 | 1754 ± 6 | n/a |
| v1 | rule | - | 27 | 29.0 | 1749 ± 7 | n/a |
| v1 | random | - | 10 | 29.0 | 1745 ± 2 | n/a |
| v1 | noop | - | 5 | 29.0 | 1742 ± 1 | n/a |
| v1 | LLM-v3test | Qwen3-32B-Instruct | 1 | 29.0 | 1767 ± 0 | n/a |

# threshold_metrics

## Threshold metrics (threshold = 80 %)

| Scenario | Agent | $N$ | Epochs $\geq$ thr. (\%) | 95\,\% CI | First viol. (epoch) | Never | Below-thr. area | 95\,\% CI | Final cov. (\%) | BS |
|---|---|---|---|---|---|---|---|---|---|---|
| S1 Peaceful | LLM-full | 10 | 15.5 ± 3.4 | [13.4, 17.6] | 5.5 ± 1.0 | 0/10 | 860 ± 268 | [701, 1015] | 37.6 ± 11.2 | 15.4 ± 3.4 |
| S1 Peaceful | LLM-nospatial | 10 | 18.2 ± 4.8 | [15.3, 20.9] | 6.1 ± 1.2 | 0/10 | 1027 ± 283 | [855, 1184] | 24.1 ± 15.2 | 11.2 ± 5.4 |
| S1 Peaceful | LLM-minimal | 5 | 15.9 ± 1.9 | [14.5, 17.2] | 5.2 ± 0.4 | 0/5 | 1042 ± 192 | [867, 1159] | 24.6 ± 7.9 | 10.8 ± 5.0 |
| S1 Peaceful | rule | 10 | 15.5 ± 3.4 | [13.4, 17.6] | 5.5 ± 1.0 | 0/10 | 871 ± 318 | [705, 1074] | 39.3 ± 16.6 | 18.1 ± 5.7 |
| S1 Peaceful | random | 5 | 14.5 ± 3.8 | [11.7, 17.9] | 4.4 ± 0.9 | 0/5 | 1033 ± 451 | [745, 1429] | 25.4 ± 19.3 | 13.0 ± 5.2 |
| S1 Peaceful | noop | 5 | 18.6 ± 4.6 | [15.2, 22.1] | 6.0 ± 1.0 | 0/5 | 762 ± 174 | [614, 890] | 39.6 ± 9.1 | 15.8 ± 4.8 |
| S2 Stress | LLM-full | 5 | 17.2 ± 2.4 | [15.2, 19.3] | 5.8 ± 0.4 | 0/5 | 1015 ± 284 | [790, 1241] | 25.8 ± 14.9 | 13.2 ± 5.4 |
| S2 Stress | rule | 9 | 18.4 ± 5.7 | [14.9, 21.8] | 5.7 ± 1.0 | 0/9 | 698 ± 103 | [641, 766] | 41.8 ± 9.3 | 18.9 ± 4.2 |
| S2 Stress | random | 5 | 15.2 ± 1.9 | [13.8, 16.6] | 5.4 ± 0.5 | 0/5 | 1310 ± 365 | [1033, 1599] | 33.6 ± 25.8 | 15.0 ± 7.9 |
| S3 Day/Night | LLM-full | 5 | 17.0 ± 3.7 | [14.5, 19.8] | 5.6 ± 0.5 | 0/5 | 993 ± 469 | [675, 1379] | 29.4 ± 18.2 | 12.4 ± 6.1 |
| S3 Day/Night | rule | 5 | 14.5 ± 2.9 | [12.4, 16.6] | 4.8 ± 0.4 | 0/5 | 746 ± 161 | [629, 871] | 40.6 ± 6.7 | 17.2 ± 3.1 |
| S4 Adversarial | LLM-full | 3 | 48.3 ± 42.4 | [17.2, 96.6] | 6.0 ± 1.0 | 0/3 | 210 ± 176 | [7, 324] | 79.7 ± 10.2 | 8.0 ± 5.3 |
| S4 Adversarial | rule | 3 | 55.2 ± 31.0 | [24.1, 86.2] | 7.3 ± 1.2 | 0/3 | 153 ± 151 | [16, 315] | 79.7 ± 9.3 | 14.0 ± 2.6 |
| S4 Adversarial | LLM-v3test | 1 | 82.8 ± 0.0 | [82.8, 82.8] | 6.0 ± 0.0 | 0/1 | 33 ± 0 | [33, 33] | 70.0 ± 0.0 | 13.0 ± 0.0 |

## LLM vs rule

| Scenario | Metric | $n$ | $\Delta$ | 95\,\% CI | $t$ | df | $p$ | $p_{\mathrm{Holm}}$ | $g$ |
|---|---|---|---|---|---|---|---|---|---|
| S1 Peaceful | Epochs $\geq$ thr. (\%) | 10/10 | -0.0 | [-3.1, 3.1] | -0.00 | 18.0 | 1.000 | 1.000 | -0.00 |
| S1 Peaceful | Below-thr. area (pp$\cdot$ep.) | 10/10 | -11.1 | [-287.8, 265.6] | -0.08 | 17.5 | 0.934 | 1.000 | -0.04 |
| S1 Peaceful | Final cov. (\%) | 10/10 | -1.7 | [-15.1, 11.7] | -0.27 | 15.8 | 0.792 | 1.000 | -0.12 |
| S1 Peaceful | BS deployed | 10/10 | -2.7 | [-7.2, 1.8] | -1.29 | 14.7 | 0.219 | 1.000 | -0.55 |
| S2 Stress | Epochs $\geq$ thr. (\%) | 5/9 | -1.1 | [-6.0, 3.7] | -0.52 | 11.6 | 0.611 | 1.000 | -0.22 |
| S2 Stress | Below-thr. area (pp$\cdot$ep.) | 5/9 | +316.7 | [-31.1, 664.5] | 2.40 | 4.6 | 0.066 | 1.000 | 1.61 |
| S2 Stress | Final cov. (\%) | 5/9 | -16.0 | [-34.1, 2.2] | -2.17 | 5.8 | 0.074 | 1.000 | -1.30 |
| S2 Stress | BS deployed | 5/9 | -5.7 | [-12.3, 1.0] | -2.04 | 6.8 | 0.083 | 1.000 | -1.15 |
| S3 Day/Night | Epochs $\geq$ thr. (\%) | 5/5 | +2.5 | [-2.4, 7.3] | 1.19 | 7.6 | 0.270 | 1.000 | 0.68 |
| S3 Day/Night | Below-thr. area (pp$\cdot$ep.) | 5/5 | +247.0 | [-325.9, 819.9] | 1.11 | 4.9 | 0.317 | 1.000 | 0.64 |
| S3 Day/Night | Final cov. (\%) | 5/5 | -11.2 | [-33.4, 11.0] | -1.29 | 5.1 | 0.252 | 1.000 | -0.74 |
| S3 Day/Night | BS deployed | 5/5 | -4.8 | [-12.3, 2.7] | -1.57 | 5.9 | 0.169 | 1.000 | -0.89 |
| S4 Adversarial | Epochs $\geq$ thr. (\%) | 3/3 | -6.9 | [-94.2, 80.4] | -0.23 | 3.7 | 0.832 | 1.000 | -0.15 |
| S4 Adversarial | Below-thr. area (pp$\cdot$ep.) | 3/3 | +56.7 | [-318.8, 432.2] | 0.42 | 3.9 | 0.695 | 1.000 | 0.28 |
| S4 Adversarial | Final cov. (\%) | 3/3 | +0.0 | [-22.2, 22.2] | 0.00 | 4.0 | 1.000 | 1.000 | 0.00 |
| S4 Adversarial | BS deployed | 3/3 | -6.0 | [-17.0, 5.0] | -1.76 | 2.9 | 0.179 | 1.000 | -1.15 |

# monotonicity

## Coverage monotonicity

```
(printed in the output so the paper can quote them verbatim)
  Transition      : a pair of consecutive decision epochs (t, t+1) of one episode, 60 simulated seconds apart;
                    the state at each epoch is the bridge's state export (coverage_pct, total_bs, units).
  BS-increase     : total_bs(t+1) > total_bs(t), i.e. at least one base station came online between the two exports.
  U(t)            : denominator of coverage_pct = mobile_units (protocol v2) or total_units (v1, where mobile_units was
                    not exported; approximation stated in the paper).
  covered(t)      : U(t) - disconnected(t)  (absolute number of covered units; |U_cov| in the theorem).
  (i)   strict    : share of BS-increase transitions with coverage_pct(t+1) >= coverage_pct(t).
  (ii)  demand-adjusted : share of BS-increase transitions with coverage_pct(t+1) >= coverage_pct(t) OR U(t+1) > U(t).
                    Rationale: the theorem assumes an unchanged user set; when demand grew between the two exports a
                    lower percentage is not attributable to the placement. This is lenient (demand grows in most
                    epochs), so it is an upper bound and is reported next to (i) and (iii).
  (iii) covered-count : share of BS-increase transitions with covered(t+1) >= covered(t) (the theorem's |U_cov'| >= |U_cov|,
                    invariant to demand growth but not to unit movement/destruction).
  (iv)  action-based (paper wording) : share of transitions whose decision at t was a place_bs action with
                    coverage_pct(t+1) >= coverage_pct(t). In protocol v1 the executed action lags one epoch (defect A),
                    so (iv) is reported only to relate to the manuscript's "668/688 placements" sentence.
All shares come with Wilson 95 % CIs; N = number of transitions in the denominator. Unit = transition (not episode);
per-episode clustering is ignored, which is stated.
```

| Camp. | Agent | Transitions | (i) strict | (ii) demand-adj. | (iii) covered-count | (iv) action-based |
|---|---|---|---|---|---|---|
| v1 | LLM-full | 637 | 48.3% [42.0, 54.7] (114/236) | 100.0% [98.4, 100.0] (236/236) | 93.6% [89.8, 96.1] (221/236) | 43.8% [39.7, 48.1] (231/527) |
| v1 | LLM-nospatial | 273 | 38.6% [28.8, 49.3] (32/83) | 100.0% [95.6, 100.0] (83/83) | 92.8% [85.1, 96.6] (77/83) | 38.6% [32.7, 44.9] (93/241) |
| v1 | LLM-minimal | 140 | 44.4% [29.5, 60.4] (16/36) | 100.0% [90.4, 100.0] (36/36) | 88.9% [74.7, 95.6] (32/36) | 38.1% [29.9, 47.1] (45/118) |
| v1 | rule | 756 | 41.5% [36.5, 46.6] (151/364) | 100.0% [99.0, 100.0] (364/364) | 91.8% [88.5, 94.2] (334/364) | 41.4% [37.7, 45.3] (265/640) |
| v1 | random | 280 | 42.3% [32.9, 52.2] (41/97) | 100.0% [96.2, 100.0] (97/97) | 82.5% [73.7, 88.8] (80/97) | 41.5% [34.7, 48.5] (80/193) |
| v1 | noop | 140 | 47.5% [35.5, 59.8] (29/61) | 100.0% [94.1, 100.0] (61/61) | 93.4% [84.3, 97.4] (57/61) | n/a (0) |
| v1 | LLM-v3test | 28 | 66.7% [39.1, 86.2] (8/12) | 91.7% [64.6, 98.5] (11/12) | 91.7% [64.6, 98.5] (11/12) | 70.0% [48.1, 85.5] (14/20) |
| v1 | all agents | 2254 | 44.0% [40.8, 47.3] (391/889) | 99.9% [99.4, 100.0] (888/889) | 91.3% [89.3, 93.0] (812/889) | 41.9% [39.6, 44.2] (728/1739) |

*U(t) taken from total_units; unit = transition, episode clustering ignored.*

# Figures

```
81 episodes (campaign=v1)
  wrote fig_coverage_s1_peaceful.pdf / .png
  wrote fig_coverage_s2_stress.pdf / .png
  wrote fig_coverage_s3_daynight.pdf / .png
  wrote fig_coverage_s4_adversarial.pdf / .png
  wrote fig_coverage_grid.pdf / .png
  wrote fig_qos_peakload_s1_peaceful.pdf / .png
  wrote fig_qos_peakload_s2_stress.pdf / .png
  wrote fig_qos_peakload_s3_daynight.pdf / .png
  wrote fig_qos_peakload_s4_adversarial.pdf / .png
  wrote fig_regret_events_s1_peaceful.pdf / .png
  wrote fig_regret_events_s2_stress.pdf / .png
  wrote fig_regret_events_s3_daynight.pdf / .png
  wrote fig_regret_events_s4_adversarial.pdf / .png
  fig_regret_validation: n/a (no re-simulated branches with an exact gain; pass --mapping)
  wrote fig_latency.pdf / .png
  wrote fig_threshold.pdf / .png
30 files written to ../../../paper_major_revision/figures/v1

```

# Caveats

- v1 (June 2026) data carry the audited defects: one-epoch action lag for every agent (A), mixed simulator versions (B), ~1x speed (C); relative comparisons remain meaningful but absolute numbers must be labelled 'original campaign'.
- v1 latency is reconstructed (see latency_invalid.py docstring); v1 has no parse status, no disconnected_positions, no mobile_units.
- geometric-v2 regret on v1 data falls back to the legacy 30 % assumption (column 'Pos. avail.' = 0 %).
- Unit of analysis is the episode for coverage/threshold statistics, the decision for latency/parse/reasoning, the transition for monotonicity, the event for regret.
- Holm families: stats_report.COMPARISONS (main), all rows of tab_threshold_comparisons (threshold module).
- Annotation sample for the reasoning classifier: aux/reasoning_sample50.csv (fill in, then `reasoning.py --kappa <file>`).

# Files written

- tab_inventory.tex
- tab_conditions.tex
- tab_comparisons.tex
- tab_equivalence.tex
- tab_regret.tex
- tab_reasoning_denominators.tex
- tab_reasoning_categories.tex
- tab_reasoning_by_action.tex
- tab_latency.tex
- tab_parse_status.tex
- tab_validation_outcomes.tex
- tab_runtime.tex
- tab_threshold.tex
- tab_threshold_comparisons.tex
- tab_monotonicity.tex
- numbers.json
- macros.tex
- aux/regret_events.csv
- aux/reasoning_sample50.csv
- aux/reasoning_sample50_auto.csv
