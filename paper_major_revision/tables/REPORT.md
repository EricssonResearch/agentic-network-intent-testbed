# Revision analysis report

Generated 2026-10-13T19:27:06 by tables_to_tex.py; campaign=v2; valid episodes=170; min decisions per episode=20; protocols=[2].

Every table below is also written as LaTeX to this directory; every number is in numbers.json and macros.tex.

## Inventory

| Scenario | Agent | Model | Prot. | Code version(s) | Valid | Discarded (reason) |
|---|---|---|---|---|---|---|
| S1 Peaceful | LLM-full | Qwen3.8-27B-FP8-1M | 2 | 90f8c9795533 | 20 | - |
| S1 Peaceful | LLM-nospatial | Qwen3.8-27B-FP8-1M | 2 | 90f8c9795533 | 20 | - |
| S1 Peaceful | LLM-minimal | Qwen3.8-27B-FP8-1M | 2 | 90f8c9795533 | 10 | - |
| S1 Peaceful | rule | - | 2 | 21fd085a0326 | 20 | - |
| S1 Peaceful | random | - | 2 | 90f8c9795533 | 10 | - |
| S1 Peaceful | noop | - | 2 | 406ee1812601, 90f8c9795533 | 20 | - |
| S2 Stress | LLM-full | Qwen3.8-27B-FP8-1M | 2 | 90f8c9795533 | 10 | - |
| S2 Stress | rule | - | 2 | 90f8c9795533 | 10 | - |
| S2 Stress | random | - | 2 | 406ee1812601, 90f8c9795533 | 10 | - |
| S3 Day/Night | LLM-full | Qwen3.8-27B-FP8-1M | 2 | 90f8c9795533 | 10 | - |
| S3 Day/Night | rule | - | 2 | 90f8c9795533 | 10 | - |
| S4 Adversarial | LLM-full | Qwen3.8-27B-FP8-1M | 2 | 90f8c9795533 | 10 | - |
| S4 Adversarial | rule | - | 2 | 90f8c9795533 | 10 | - |

# Main statistics (stats_report.py)

## Per-condition summary (mean ± sample SD; episode = unit)

| Scenario | Agent | N | Avg cov (%) | 95% CI | Final cov (%) | BS deployed mean±SD (median) | Epochs ≥80% | First violation (epoch) |
|---|---|---|---|---|---|---|---|---|
| s1_peaceful | llm | 20 | 57.9 ± 7.1 | [54.7, 60.9] | 49.2 ± 10.6 | 18.1 ± 4.5 (17.5) | 13.3% | 4.5 |
| s1_peaceful | llm_minimal | 10 | 54.5 ± 7.9 | [49.7, 58.8] | 37.3 ± 10.6 | 15.1 ± 4.1 (17) | 13.1% | 4.5 |
| s1_peaceful | llm_nospatial | 20 | 40.6 ± 11.7 | [35.7, 45.7] | 23.6 ± 19.4 | 10.4 ± 5.9 (8.5) | 13.1% | 4.5 |
| s1_peaceful | noop | 20 | 60.6 ± 4.3 | [58.6, 62.4] | 48.3 ± 9.2 | 18.1 ± 4.2 (18) | 13.3% | 4.4 |
| s1_peaceful | random | 10 | 41.5 ± 14.6 | [32.9, 50.1] | 31.1 ± 19.5 | 16.7 ± 8.9 (18) | 10.3% | 3.4 |
| s1_peaceful | rule | 20 | 57.9 ± 6.6 | [55.0, 60.6] | 45.5 ± 10.1 | 20.4 ± 5.0 (21.5) | 11.9% | 4.0 |
| s2_stress | llm | 10 | 59.0 ± 5.2 | [56.1, 62.1] | 50.8 ± 8.1 | 18.5 ± 3.9 (18.5) | 13.4% | 4.8 |
| s2_stress | random | 10 | 45.0 ± 12.6 | [37.0, 51.7] | 35.1 ± 11.7 | 16.3 ± 4.4 (17.5) | 9.3% | 3.5 |
| s2_stress | rule | 10 | 60.3 ± 5.6 | [57.2, 63.7] | 49.1 ± 8.3 | 21.0 ± 2.9 (21) | 13.8% | 4.8 |
| s3_daynight | llm | 10 | 61.3 ± 8.0 | [56.8, 66.2] | 51.8 ± 8.6 | 18.3 ± 5.3 (18) | 14.8% | 4.5 |
| s3_daynight | rule | 10 | 57.0 ± 4.1 | [54.7, 59.4] | 42.7 ± 7.2 | 20.2 ± 3.3 (20) | 14.1% | 4.8 |
| s4_adversarial | llm | 10 | 82.1 ± 7.8 | [77.2, 86.4] | 78.4 ± 10.6 | 11.4 ± 1.0 (11.5) | 63.4% | 10.5 |
| s4_adversarial | rule | 10 | 83.2 ± 4.1 | [81.0, 85.8] | 81.4 ± 5.7 | 12.5 ± 3.1 (13.5) | 57.9% | 12.2 |

## Pairwise comparisons (Welch t-test on episode means; Hedges' g; Holm-corrected over this family)

| Comparison | n | Δ (pp) | t | df | p | p (Holm) | g | 95% CI (pp) |
|---|---|---|---|---|---|---|---|---|
| S1 LLM vs rule | 20/20 | -0.0 | -0.01 | 37.8 | 0.995 | 1.000 | -0.00 | [-4.4, +4.4] |
| S1 LLM vs no-spatial | 20/20 | +17.3 | 5.64 | 31.2 | <0.001 | <0.001 | +1.75 | [+11.0, +23.5] |
| S1 LLM vs minimal | 20/10 | +3.4 | 1.15 | 16.4 | 0.267 | 1.000 | +0.45 | [-2.9, +9.7] |
| S1 no-spatial vs random | 20/10 | -0.9 | -0.17 | 15.0 | 0.871 | 1.000 | -0.07 | [-12.2, +10.5] |
| S1 noop vs LLM | 20/20 | +2.7 | 1.47 | 31.4 | 0.152 | 1.000 | +0.46 | [-1.1, +6.5] |
| S1 noop vs rule | 20/20 | +2.7 | 1.54 | 32.8 | 0.133 | 1.000 | +0.48 | [-0.9, +6.3] |
| S2 rule vs LLM | 10/10 | +1.2 | 0.52 | 17.9 | 0.612 | 1.000 | +0.22 | [-3.8, +6.3] |
| S2 LLM vs random | 10/10 | +14.0 | 3.26 | 12.0 | 0.007 | 0.062 | +1.40 | [+4.6, +23.4] |
| S3 rule vs LLM | 10/10 | -4.3 | -1.53 | 13.4 | 0.150 | 1.000 | -0.65 | [-10.5, +1.8] |
| S4 rule vs LLM | 10/10 | +1.1 | 0.38 | 13.7 | 0.709 | 1.000 | +0.16 | [-4.9, +7.1] |

## Equivalence (TOST)

| Comparison | margin (pp) | n | p (TOST) |
|---|---|---|---|
| S1 LLM vs rule | ±5 | 20/20 | 0.013 |
| S1 no-spatial vs random | ±5 | 20/10 | 0.225 |

## Notes

- campaign=v2; valid episodes=170; min decisions per episode=20; protocols=[2]
- power to detect 6 pp at SD 9: n=5: 0.15, n=10: 0.29, n=20: 0.54, n=30: 0.72

# regret

## Decision regret

Trigger: coverage drop >= 5 pp between consecutive decisions. Estimators: see module docstring.

| Scenario | Agent | $N$ ep. | Events | Ev./ep. | Fixed-fr.\ (2-ep.) | Fixed-fr.\ (1-ep.) | Geometric | 95\,\% CI (geom.) | Cum./ep. | Pos.\ avail. |
|---|---|---|---|---|---|---|---|---|---|---|
| S1 Peaceful | LLM-full | 20 | 161 | 8.05 | 6.7 ± 4.0 | 6.4 ± 3.2 | 6.0 ± 9.1 | [4.7, 7.5] | 48.5 ± 13.1 | 100% |
| S1 Peaceful | LLM-nospatial | 20 | 177 | 8.85 | 8.4 ± 4.9 | 7.2 ± 3.7 | 5.7 ± 7.7 | [4.6, 6.9] | 50.7 ± 20.7 | 100% |
| S1 Peaceful | LLM-minimal | 10 | 87 | 8.70 | 7.2 ± 4.2 | 6.6 ± 3.0 | 5.5 ± 9.0 | [3.7, 7.5] | 47.7 ± 19.3 | 100% |
| S1 Peaceful | rule | 20 | 174 | 8.70 | 6.7 ± 3.6 | 6.6 ± 2.9 | 5.7 ± 9.5 | [4.3, 7.1] | 49.2 ± 21.4 | 100% |
| S1 Peaceful | random | 10 | 83 | 8.30 | 8.7 ± 5.2 | 8.0 ± 4.0 | 8.0 ± 9.3 | [6.1, 10.1] | 66.6 ± 24.5 | 100% |
| S1 Peaceful | noop | 20 | 161 | 8.05 | 6.3 ± 3.5 | 6.1 ± 2.8 | 5.7 ± 8.5 | [4.4, 7.0] | 45.5 ± 11.6 | 100% |
| S2 Stress | LLM-full | 10 | 83 | 8.30 | 7.0 ± 3.9 | 6.5 ± 3.1 | 6.1 ± 7.7 | [4.5, 7.8] | 50.6 ± 17.1 | 100% |
| S2 Stress | rule | 10 | 78 | 7.80 | 6.3 ± 3.4 | 6.0 ± 2.8 | 5.8 ± 8.3 | [4.1, 7.7] | 45.5 ± 11.8 | 100% |
| S2 Stress | random | 10 | 89 | 8.90 | 7.7 ± 4.7 | 7.8 ± 3.7 | 6.2 ± 8.7 | [4.4, 8.0] | 54.9 ± 29.5 | 100% |
| S3 Day/Night | LLM-full | 10 | 86 | 8.60 | 6.6 ± 4.1 | 6.0 ± 2.9 | 5.8 ± 8.5 | [4.1, 7.7] | 50.0 ± 10.3 | 100% |
| S3 Day/Night | rule | 10 | 91 | 9.10 | 6.5 ± 4.2 | 6.4 ± 3.1 | 4.7 ± 8.2 | [3.2, 6.6] | 43.2 ± 18.2 | 100% |
| S4 Adversarial | LLM-full | 10 | 41 | 4.10 | 4.6 ± 2.8 | 4.4 ± 2.4 | 6.0 ± 5.1 | [4.5, 7.6] | 24.5 ± 12.9 | 100% |
| S4 Adversarial | rule | 10 | 35 | 3.50 | 4.4 ± 2.2 | 4.4 ± 2.0 | 5.0 ± 5.7 | [3.2, 6.9] | 17.6 ± 11.9 | 100% |

## Exact regret (re-simulation)

| Estimator | $N$ branches | Bias (pp) | MAE (pp) | Spearman $\rho$ | $p$ |
|---|---|---|---|---|---|
| fixed-fraction (30 %) | 20 | 3.8 | 12.8 | -0.52 | 0.020 |
| geometric | 20 | 7.8 | 8.5 | 0.56 | 0.010 |

*20 usable branch pairs; 0 with a non-identical prefix (determinism violated; excluded from nothing here but flagged in regret_exact.csv).*

Per-branch rows: regret_exact.csv


# reasoning

## Reasoning taxonomy

Taxonomy: reasoning_taxonomy.json (version revision-2026-09-27), matching mode `substring`.
LLM episodes analysed: 80 (non-LLM episodes excluded: 90).

### Denominators

| Scenario | Agent | Model | $N$ ep. | $N$ dec. | Non-empty | Error | Uncategorized | Valid |
|---|---|---|---|---|---|---|---|---|
| S1 Peaceful | LLM-full | Qwen3.8-27B-FP8-1M | 20 | 580 | 580 (100.0%) | 2 (0.3%) | 0 (0.0%) | 578 (99.7%) |
| S1 Peaceful | LLM-nospatial | Qwen3.8-27B-FP8-1M | 20 | 580 | 580 (100.0%) | 0 (0.0%) | 0 (0.0%) | 580 (100.0%) |
| S1 Peaceful | LLM-minimal | Qwen3.8-27B-FP8-1M | 10 | 290 | 290 (100.0%) | 0 (0.0%) | 0 (0.0%) | 290 (100.0%) |
| S2 Stress | LLM-full | Qwen3.8-27B-FP8-1M | 10 | 290 | 290 (100.0%) | 0 (0.0%) | 0 (0.0%) | 290 (100.0%) |
| S3 Day/Night | LLM-full | Qwen3.8-27B-FP8-1M | 10 | 290 | 290 (100.0%) | 0 (0.0%) | 0 (0.0%) | 290 (100.0%) |
| S4 Adversarial | LLM-full | Qwen3.8-27B-FP8-1M | 10 | 290 | 290 (100.0%) | 0 (0.0%) | 0 (0.0%) | 290 (100.0%) |

### Categories

| Category | Count | \% of dec. ($N$=2320) | \% of non-empty ($N$=2320) | LLM-full (\%) | LLM-nospatial (\%) | LLM-minimal (\%) |
|---|---|---|---|---|---|---|
| spatial | 1949 | 84.0 | 84.0 | 88.9 | 78.4 | 70.7 |
| reactive | 2240 | 96.6 | 96.6 | 94.8 | 100.0 | 98.3 |
| temporal | 1 | 0.0 | 0.0 | 0.0 | 0.2 | 0.0 |
| resource | 2 | 0.1 | 0.1 | 0.1 | 0.0 | 0.0 |
| capacity | 194 | 8.4 | 8.4 | 7.7 | 14.3 | 0.0 |
| noop justified | 222 | 9.6 | 9.6 | 9.9 | 9.0 | 9.3 |
| threat | 1305 | 56.2 | 56.2 | 89.6 | 1.0 | 0.0 |
| uncategorized | 0 | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |

*Labels per categorized decision: mean 2.55; multi-label, so category counts do not sum to the number of decisions.*

### Category x action

| Category | noop | place_bs | reconfig_slice | other | Total |
|---|---|---|---|---|---|
| spatial | 10 | 1939 | 0 | 0 | 1949 |
| reactive | 233 | 1973 | 34 | 0 | 2240 |
| temporal | 0 | 1 | 0 | 0 | 1 |
| resource | 2 | 0 | 0 | 0 | 2 |
| capacity | 140 | 20 | 34 | 0 | 194 |
| noop justified | 219 | 3 | 0 | 0 | 222 |
| threat | 61 | 1244 | 0 | 0 | 1305 |
| uncategorized | 0 | 0 | 0 | 0 | 0 |
| empty | 0 | 0 | 0 | 0 | 0 |
| error | 2 | 0 | 0 | 0 | 2 |
| all decisions | 235 | 2051 | 34 | 0 | 2320 |

### Annotation sample: 50 decisions (stratified by scenario x backend x action type; requested 50)


# latency_invalid

## Latency

| Agent | Model | $N$ dec. | Source | Median | Mean | p90 | p99 | Max | $>$60\,s |
|---|---|---|---|---|---|---|---|---|---|
| LLM-full | Qwen3.8-27B-FP8-1M | 1450/1450 | logged (latency_s) | 1.0 | 1.7 | 2.2 | 18.1 | 120.1 | 2 |
| LLM-nospatial | Qwen3.8-27B-FP8-1M | 580/580 | logged (latency_s) | 1.2 | 2.3 | 2.7 | 29.6 | 99.9 | 1 |
| LLM-minimal | Qwen3.8-27B-FP8-1M | 290/290 | logged (latency_s) | 1.7 | 4.3 | 7.3 | 39.9 | 60.0 | 1 |
| rule | - | 1450/1450 | logged (decision_wall_s) | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0 |
| random | - | 580/580 | logged (decision_wall_s) | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0 |
| noop | - | 580/580 | logged (decision_wall_s) | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0 |

## Parse status / invalid outputs

| Agent | Model | $N$ | valid | extracted | fallback\_noop | api\_error | timeout | Invalid (\%) | Extracted (\%) | Syntax-inv. |
|---|---|---|---|---|---|---|---|---|---|---|
| LLM-full | Qwen3.8-27B-FP8-1M | 1450 | 1448 | 0 | 0 | 0 | 2 | 0.1 | 0.0 | 0 |
| LLM-nospatial | Qwen3.8-27B-FP8-1M | 580 | 575 | 1 | 4 | 0 | 0 | 0.7 | 0.2 | 0 |
| LLM-minimal | Qwen3.8-27B-FP8-1M | 290 | 290 | 0 | 0 | 0 | 0 | 0.0 | 0.0 | 0 |
| rule | - | 1450 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0 |
| random | - | 580 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0 |
| noop | - | 580 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0 |

## Bridge validation outcomes

| Agent | Model | $N$ dec. | executed\_place | executed\_reconfig | noop | skipped\_invalid\_position | skipped\_threat | skipped\_water |
|---|---|---|---|---|---|---|---|---|
| LLM-full | Qwen3.8-27B-FP8-1M | 1450 | 499 | 13 | 155 | 436 | 9 | 338 |
| LLM-nospatial | Qwen3.8-27B-FP8-1M | 580 | 246 | 21 | 53 | 259 | 0 | 1 |
| LLM-minimal | Qwen3.8-27B-FP8-1M | 290 | 31 | 0 | 27 | 232 | 0 | 0 |
| rule | - | 1450 | 503 | 2 | 180 | 654 | 0 | 111 |
| random | - | 580 | 252 | 0 | 93 | 82 | 31 | 122 |
| noop | - | 580 | 0 | 0 | 580 | 0 | 0 | 0 |

## Run-time

| Agent | Model | $N$ ep. | Decisions/ep. | Wall-clock (s) | Peak RSS (MB) |
|---|---|---|---|---|---|
| LLM-full | Qwen3.8-27B-FP8-1M | 50 | 29.0 | 518 ± 70 | 6094 ± 52 |
| LLM-nospatial | Qwen3.8-27B-FP8-1M | 20 | 29.0 | 515 ± 61 | 6089 ± 98 |
| LLM-minimal | Qwen3.8-27B-FP8-1M | 10 | 29.0 | 580 ± 75 | 6092 ± 39 |
| rule | - | 50 | 29.0 | 463 ± 37 | 6097 ± 86 |
| random | - | 20 | 29.0 | 469 ± 53 | 6150 ± 153 |
| noop | - | 20 | 29.0 | 476 ± 42 | 6109 ± 73 |

# threshold_metrics

## Threshold metrics (threshold = 80 %)

| Scenario | Agent | $N$ | Epochs $\geq$ thr. (\%) | 95\,\% CI | First viol. (epoch) | Never | Below-thr. area | 95\,\% CI | Final cov. (\%) | BS |
|---|---|---|---|---|---|---|---|---|---|---|
| S1 Peaceful | LLM-full | 20 | 13.3 ± 3.8 | [11.7, 14.8] | 4.5 ± 1.2 | 0/20 | 697 ± 202 | [614, 789] | 49.2 ± 10.6 | 18.1 ± 4.5 |
| S1 Peaceful | LLM-nospatial | 20 | 13.1 ± 3.1 | [11.9, 14.5] | 4.5 ± 0.9 | 0/20 | 1198 ± 332 | [1055, 1336] | 23.6 ± 19.4 | 10.4 ± 5.9 |
| S1 Peaceful | LLM-minimal | 10 | 13.1 ± 1.5 | [12.1, 13.8] | 4.5 ± 0.5 | 0/10 | 801 ± 228 | [678, 939] | 37.3 ± 10.6 | 15.1 ± 4.1 |
| S1 Peaceful | rule | 20 | 11.9 ± 3.4 | [10.5, 13.4] | 4.0 ± 1.0 | 0/20 | 696 ± 193 | [615, 780] | 45.5 ± 10.1 | 20.4 ± 5.0 |
| S1 Peaceful | random | 10 | 10.3 ± 4.3 | [8.3, 13.1] | 3.4 ± 0.8 | 0/10 | 1161 ± 415 | [918, 1406] | 31.1 ± 19.5 | 16.7 ± 8.9 |
| S1 Peaceful | noop | 20 | 13.3 ± 3.6 | [11.9, 14.8] | 4.4 ± 1.0 | 0/20 | 621 ± 126 | [569, 677] | 48.3 ± 9.2 | 18.1 ± 4.2 |
| S2 Stress | LLM-full | 10 | 13.4 ± 2.0 | [12.4, 14.5] | 4.8 ± 0.8 | 0/10 | 667 ± 155 | [573, 755] | 50.8 ± 8.1 | 18.5 ± 3.9 |
| S2 Stress | rule | 10 | 13.8 ± 3.6 | [11.7, 15.9] | 4.8 ± 1.2 | 0/10 | 638 ± 156 | [540, 722] | 49.1 ± 8.3 | 21.0 ± 2.9 |
| S2 Stress | random | 10 | 9.3 ± 4.3 | [6.9, 12.1] | 3.5 ± 0.8 | 0/10 | 1054 ± 359 | [863, 1284] | 35.1 ± 11.7 | 16.3 ± 4.4 |
| S3 Day/Night | LLM-full | 10 | 14.8 ± 7.5 | [11.4, 19.7] | 4.5 ± 1.1 | 0/10 | 601 ± 218 | [469, 724] | 51.8 ± 8.6 | 18.3 ± 5.3 |
| S3 Day/Night | rule | 10 | 14.1 ± 3.0 | [12.4, 16.2] | 4.8 ± 0.9 | 0/10 | 728 ± 115 | [661, 793] | 42.7 ± 7.2 | 20.2 ± 3.3 |
| S4 Adversarial | LLM-full | 10 | 63.4 ± 26.3 | [47.9, 79.0] | 8.3 ± 4.0 | 1/10 | 115 ± 173 | [27, 235] | 78.4 ± 10.6 | 11.4 ± 1.0 |
| S4 Adversarial | rule | 10 | 57.9 ± 28.0 | [42.4, 74.8] | 7.8 ± 3.0 | 2/10 | 68 ± 50 | [38, 96] | 81.4 ± 5.7 | 12.5 ± 3.1 |

## LLM vs rule

| Scenario | Metric | $n$ | $\Delta$ | 95\,\% CI | $t$ | df | $p$ | $p_{\mathrm{Holm}}$ | $g$ |
|---|---|---|---|---|---|---|---|---|---|
| S1 Peaceful | Epochs $\geq$ thr. (\%) | 20/20 | +1.4 | [-0.9, 3.7] | 1.21 | 37.7 | 0.234 | 1.000 | 0.38 |
| S1 Peaceful | Below-thr. area (pp$\cdot$ep.) | 20/20 | +1.9 | [-124.7, 128.4] | 0.03 | 37.9 | 0.977 | 1.000 | 0.01 |
| S1 Peaceful | Final cov. (\%) | 20/20 | +3.7 | [-3.0, 10.3] | 1.11 | 37.9 | 0.272 | 1.000 | 0.35 |
| S1 Peaceful | BS deployed | 20/20 | -2.2 | [-5.3, 0.8] | -1.50 | 37.5 | 0.143 | 1.000 | -0.46 |
| S2 Stress | Epochs $\geq$ thr. (\%) | 10/10 | -0.3 | [-3.1, 2.5] | -0.26 | 13.8 | 0.796 | 1.000 | -0.11 |
| S2 Stress | Below-thr. area (pp$\cdot$ep.) | 10/10 | +29.3 | [-116.8, 175.4] | 0.42 | 18.0 | 0.678 | 1.000 | 0.18 |
| S2 Stress | Final cov. (\%) | 10/10 | +1.7 | [-6.0, 9.4] | 0.47 | 18.0 | 0.647 | 1.000 | 0.20 |
| S2 Stress | BS deployed | 10/10 | -2.5 | [-5.7, 0.7] | -1.64 | 16.6 | 0.119 | 1.000 | -0.70 |
| S3 Day/Night | Epochs $\geq$ thr. (\%) | 10/10 | +0.7 | [-4.9, 6.2] | 0.27 | 11.9 | 0.791 | 1.000 | 0.12 |
| S3 Day/Night | Below-thr. area (pp$\cdot$ep.) | 10/10 | -127.0 | [-294.5, 40.5] | -1.63 | 13.6 | 0.126 | 1.000 | -0.70 |
| S3 Day/Night | Final cov. (\%) | 10/10 | +9.1 | [1.6, 16.6] | 2.56 | 17.5 | 0.020 | 0.317 | 1.10 |
| S3 Day/Night | BS deployed | 10/10 | -1.9 | [-6.1, 2.3] | -0.96 | 15.1 | 0.354 | 1.000 | -0.41 |
| S4 Adversarial | Epochs $\geq$ thr. (\%) | 10/10 | +5.5 | [-20.0, 31.0] | 0.45 | 17.9 | 0.655 | 1.000 | 0.19 |
| S4 Adversarial | Below-thr. area (pp$\cdot$ep.) | 10/10 | +47.4 | [-78.4, 173.2] | 0.83 | 10.5 | 0.423 | 1.000 | 0.36 |
| S4 Adversarial | Final cov. (\%) | 10/10 | -3.0 | [-11.2, 5.2] | -0.79 | 13.8 | 0.444 | 1.000 | -0.34 |
| S4 Adversarial | BS deployed | 10/10 | -1.1 | [-3.4, 1.2] | -1.07 | 10.7 | 0.308 | 1.000 | -0.46 |

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

| Agent | Transitions | (i) strict | (ii) demand-adj. | (iii) covered-count |
|---|---|---|---|---|
| LLM-full | 1400 | 46.4% [42.5, 50.3] (288/621) | 99.7% [98.8, 99.9] (619/621) | 79.9% [76.5, 82.8] (496/621) |
| LLM-nospatial | 560 | 47.4% [39.3, 55.8] (65/137) | 100.0% [97.3, 100.0] (137/137) | 74.5% [66.6, 81.0] (102/137) |
| LLM-minimal | 280 | 41.6% [32.5, 51.3] (42/101) | 100.0% [96.3, 100.0] (101/101) | 79.2% [70.3, 86.0] (80/101) |
| rule | 1400 | 45.3% [41.6, 49.0] (312/689) | 100.0% [99.4, 100.0] (689/689) | 81.7% [78.7, 84.4] (563/689) |
| random | 560 | 57.2% [50.7, 63.4] (131/229) | 100.0% [98.4, 100.0] (229/229) | 77.7% [71.9, 82.6] (178/229) |
| noop | 560 | 46.2% [40.0, 52.6] (110/238) | 100.0% [98.4, 100.0] (238/238) | 78.2% [72.5, 82.9] (186/238) |
| all agents | 4760 | 47.0% [44.9, 49.2] (948/2015) | 99.9% [99.6, 100.0] (2013/2015) | 79.7% [77.8, 81.4] (1605/2015) |

*U(t) taken from mobile_units; unit = transition, episode clustering ignored.*

# extensions

## Extension experiments (results_v2_ext + core reference arms)

Arms found: s1_peaceful/greedy/e8_greedy (N=30), s1_peaceful/llm/e1_fastctx4b (N=10), s1_peaceful/llm/e1_gptoss (N=20), s1_peaceful/llm/e2_v2 (N=10), s1_peaceful/llm/e3_noauto (N=20), s1_peaceful/llm/e5_pl2 (N=10), s1_peaceful/llm/e5_pl4 (N=10), s1_peaceful/llm/e7_grid (N=10), s1_peaceful/llm/e7_snap (N=10), s1_peaceful/llm/e8_cand (N=30), s1_peaceful/llm/e8_candfb (N=10), s1_peaceful/llm/e9_gptoss_high (N=20), s1_peaceful/llm/e9_think (N=30), s1_peaceful/noop/e3_noauto (N=20), s1_peaceful/rule/e3_noauto (N=10), s1_peaceful/rule/e5_pl2 (N=10), s1_peaceful/rule/e5_pl4 (N=10), s1_peaceful/rule/e7_rulesnap (N=10), s3_daynight/llm/e1_fastctx4b (N=10), s3_daynight/llm/e1_gptoss (N=10), s3_daynight/llm/e2_v2 (N=10), s3_daynight/llm/e8_cand (N=10)

### E1 Multi-model

| Scenario | Model | $N$ | Avg.\ cov.\ (\%) | 95\,\% CI | Final (\%) | BS | Rej.\ (\%) | Inv.\ (\%) | Temporal $n$ (\%) | $\Delta$ (pp) | 95\,\% CI | $p$ / $p_{\mathrm{Holm}}$ | $g$ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S1 Peaceful | Qwen3.8-27B (primary) | 20 | 57.9 ± 7.1 | [54.7, 60.9] | 49 ± 11 | 18.1 | 64 | 0.3 | 0 (0.0) | ref. |  |  |  |
| S1 Peaceful | FastContext-4B | 10 | 60.0 ± 5.2 | [57.0, 63.2] | 46 ± 9 | 19.1 | 80 | 0.0 | 0 (0.0) | +2.2 | [-2.5, 6.9] | 0.349 / 0.699 | +0.32 |
| S1 Peaceful | gpt-oss-120b | 20 | 52.9 ± 9.5 | [48.6, 56.6] | 40 ± 15 | 14.7 | 64 | 0.0 | 0 (0.0) | -5.0 | [-10.4, 0.4] | 0.066 / 0.200 | -0.59 |
| S1 Peaceful | rule (reference) | 20 | 57.9 ± 6.6 | [55.0, 60.6] | 46 ± 10 | 20.4 | 56 | 0.0 | n/a | +0.0 | [-4.4, 4.4] | 0.995 / 0.995 | +0.00 |
| S3 Day/Night | Qwen3.8-27B (primary) | 10 | 61.3 ± 8.0 | [56.8, 66.2] | 52 ± 9 | 18.3 | 58 | 0.0 | 0 (0.0) | ref. |  |  |  |
| S3 Day/Night | FastContext-4B | 10 | 59.6 ± 6.8 | [55.7, 63.7] | 46 ± 10 | 17.3 | 86 | 0.3 | 0 (0.0) | -1.7 | [-8.7, 5.3] | 0.618 / 0.699 | -0.22 |
| S3 Day/Night | gpt-oss-120b | 10 | 52.0 ± 11.4 | [44.6, 57.8] | 38 ± 16 | 16.4 | 68 | 0.0 | 0 (0.0) | -9.3 | [-18.6, 0.0] | 0.050 / 0.200 | -0.91 |
| S3 Day/Night | rule (reference) | 10 | 57.0 ± 4.1 | [54.7, 59.4] | 43 ± 7 | 20.2 | 60 | 0.0 | n/a | -4.3 | [-10.5, 1.8] | 0.150 / 0.150 | -0.65 |

*Rows `rule (reference)' repeat the core rule arm for orientation; their $p$ is not part of the Holm family.*

### E2 Prompt variant

| Scenario | Prompt | $N$ | Avg.\ cov.\ (\%) | 95\,\% CI | Final (\%) | BS | Rej.\ (\%) | Inv.\ (\%) | Temporal $n$ (\%) | $\Delta$ (pp) | 95\,\% CI | $p$ / $p_{\mathrm{Holm}}$ | $g$ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S1 Peaceful | base prompt (core) | 20 | 57.9 ± 7.1 | [54.7, 60.9] | 49 ± 11 | 18.1 | 64 | 0.3 | 0 (0.0) | ref. |  |  |  |
| S1 Peaceful | temporal guidance + history | 10 | 59.1 ± 3.8 | [57.0, 61.4] | 48 ± 7 | 18.2 | 59 | 0.0 | 14 (4.8) | +1.2 | [-2.9, 5.3] | 0.546 / 0.661 | +0.19 |
| S3 Day/Night | base prompt (core) | 10 | 61.3 ± 8.0 | [56.8, 66.2] | 52 ± 9 | 18.3 | 58 | 0.0 | 0 (0.0) | ref. |  |  |  |
| S3 Day/Night | temporal guidance + history | 10 | 58.4 ± 4.3 | [56.0, 61.0] | 52 ± 7 | 17.4 | 62 | 0.0 | 13 (4.5) | -2.9 | [-9.1, 3.3] | 0.331 / 0.661 | -0.43 |

### E3 Autonomous layer

| Autonomy | Agent | $N$ | Avg.\ cov.\ (\%) | 95\,\% CI | Final (\%) | BS | Rej.\ (\%) | Marginal (pp) | 95\,\% CI | $p$ / $p_{\mathrm{Holm}}$ | $g$ | On $-$ off (pp) [CI] |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| autonomy on | LLM-full | 20 | 57.9 ± 7.1 | [54.7, 60.9] | 49 ± 11 | 18.1 | 64 | -2.7 | [-6.5, 1.1] | 0.152 / 0.400 | -0.46 |  |
| autonomy on | rule | 20 | 57.9 ± 6.6 | [55.0, 60.6] | 46 ± 10 | 20.4 | 56 | -2.7 | [-6.3, 0.9] | 0.133 / 0.400 | -0.48 |  |
| autonomy on | noop | 20 | 60.6 ± 4.3 | [58.6, 62.4] | 48 ± 9 | 18.1 | n/a | ref. |  |  |  |  |
| autonomy off | LLM-full | 20 | 27.1 ± 5.7 | [24.6, 29.4] | 13 ± 7 | 5.1 | 66 | +6.6 | [2.2, 10.9] | 0.004 / 0.017 | +0.95 | +30.8 [26.7, 34.9], $p$ <0.001 |
| autonomy off | rule | 10 | 20.3 ± 7.2 | [16.2, 24.6] | -3 ± 10 | 2.0 | 96 | -0.3 | [-6.2, 5.7] | 0.929 / 0.929 | -0.03 | +37.6 [31.9, 43.4], $p$ <0.001 |
| autonomy off | noop | 20 | 20.5 ± 7.7 | [17.4, 23.9] | 2 ± 9 | 1.0 | n/a | ref. |  |  |  | +40.1 [36.0, 44.1], $p$ <0.001 |

*The no-op on-vs-off row measures the autonomous layer alone; its $p$ is reported but not Holm-adjusted (it is not one of the six planned tests).*

### E5 Path-loss sensitivity

| $n$ | Agent | $N$ | Avg.\ cov.\ (\%) | 95\,\% CI | Final (\%) | BS | Rej.\ (\%) | LLM $-$ rule (pp) | 95\,\% CI | $p$ / $p_{\mathrm{Holm}}$ | $g$ | vs $n$=3.0 (pp) [CI], $p$ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2.0 | LLM-full | 10 | 60.9 ± 5.9 | [57.5, 64.2] | 53 ± 9 | 19.1 | 54 | +3.0 | [-2.3, 8.3] | 0.248 / 0.744 | +0.51 | +3.1 [-2.0, 8.1], 0.224 |
| 2.0 | rule | 10 | 57.9 ± 5.4 | [54.8, 61.2] | 45 ± 7 | 22.6 | 59 |  |  |  |  | +0.0 [-4.7, 4.7], 0.992 |
| 3.0 (core) | LLM-full | 20 | 57.9 ± 7.1 | [54.7, 60.9] | 49 ± 11 | 18.1 | 64 | -0.0 | [-4.4, 4.4] | 0.995 / 1.000 | -0.00 | ref. |
| 3.0 (core) | rule | 20 | 57.9 ± 6.6 | [55.0, 60.6] | 46 ± 10 | 20.4 | 56 |  |  |  |  | ref. |
| 4.0 | LLM-full | 10 | 58.9 ± 7.5 | [54.2, 62.9] | 48 ± 13 | 17.9 | 61 | -2.0 | [-9.9, 5.9] | 0.605 / 1.000 | -0.23 | +1.0 [-5.0, 7.0], 0.725 |
| 4.0 | rule | 10 | 60.9 ± 9.1 | [55.5, 66.2] | 52 ± 8 | 22.8 | 58 |  |  |  |  | +3.0 [-4.0, 9.9], 0.373 |

### E7 Grounding aids

| Agent | Aid | $N$ | Avg.\ cov.\ (\%) | 95\,\% CI | Final (\%) | BS | Rej.\ (\%) | Snapped (\%) | $\Delta$ (pp) | 95\,\% CI | $p$ / $p_{\mathrm{Holm}}$ | $g$ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| LLM-full | none (core) | 20 | 57.9 ± 7.1 | [54.7, 60.9] | 49 ± 11 | 18.1 | 64 | 0 | ref. |  |  |  |
| LLM-full | grid + snap | 10 | 46.5 ± 8.7 | [41.3, 51.5] | 41 ± 15 | 19.6 | 5 | 53 | -11.4 | [-18.1, -4.6] | 0.003 / 0.008 | -1.45 |
| LLM-full | snap | 10 | 55.8 ± 7.0 | [51.9, 60.1] | 45 ± 10 | 20.1 | 4 | 58 | -2.1 | [-7.8, 3.7] | 0.461 / 0.549 | -0.28 |
| rule | none (core) | 20 | 57.9 ± 6.6 | [55.0, 60.6] | 46 ± 10 | 20.4 | 56 | 0 | ref. |  |  |  |
| rule | snap | 10 | 54.7 ± 7.5 | [50.1, 58.8] | 44 ± 11 | 28.1 | 0 | 52 | -3.2 | [-9.1, 2.8] | 0.274 / 0.549 | -0.45 |

### E8 Decision support

| Scenario | Agent | $N$ | Avg.\ cov.\ (\%) | 95\,\% CI | Final (\%) | BS | Rej.\ (\%) | Invalid (\%) | Isol.\ cells | $\Delta$ (pp) | 95\,\% CI | $p$ / $p_{\mathrm{Holm}}$ | $g$ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S1 Peaceful | LLM-full (core) | 20 | 57.9 ± 7.1 | [54.7, 60.9] | 49 ± 11 | 18.1 | 64 | 0.3 | 4.1 | ref. |  |  |  |
| S1 Peaceful | greedy-candidate | 30 | 63.4 ± 5.2 | [61.6, 65.2] | 53 ± 6 | 26.9 | 0 | -- | 0.3 | +5.6 | [1.8, 9.3] | 0.005 / 0.015 | +0.91 |
| S1 Peaceful | LLM-full + candidates | 30 | 64.2 ± 6.2 | [61.9, 66.4] | 53 ± 9 | 26.4 | 0 | 0.9 | 0.2 | +6.3 | [2.4, 10.3] | 0.002 / 0.010 | +0.95 |
| S1 Peaceful | LLM-full + candidates + feedback | 10 | 60.7 ± 4.6 | [58.1, 63.5] | 50 ± 6 | 26.2 | 0 | 1.4 | 0.2 | +2.8 | [-1.6, 7.3] | 0.197 / 0.394 | +0.43 |
| S1 Peaceful | rule (core) | 20 | 57.9 ± 6.6 | [55.0, 60.6] | 46 ± 10 | 20.4 | 56 | -- | 2.0 | ref. |  |  |  |
| S1 Peaceful | noop (core) | 20 | 60.6 ± 4.3 | [58.6, 62.4] | 48 ± 9 | 18.1 | n/a | -- | 0.1 | ref. |  |  |  |
| S3 Day/Night | LLM-full (core) | 10 | 61.3 ± 8.0 | [56.8, 66.2] | 52 ± 9 | 18.3 | 58 | 0.0 | 3.6 | ref. |  |  |  |
| S3 Day/Night | LLM-full + candidates | 10 | 62.2 ± 5.2 | [59.2, 65.3] | 50 ± 8 | 23.7 | 0 | 1.4 | 0.3 | +0.9 | [-5.5, 7.3] | 0.774 / 0.774 | +0.13 |
| S3 Day/Night | rule (core) | 10 | 57.0 ± 4.1 | [54.7, 59.4] | 43 ± 7 | 20.2 | 60 | -- | 2.2 | ref. |  |  |  |

### E9 Inference configuration

| Scenario | Model / setting | $N$ | Avg.\ cov.\ (\%) | 95\,\% CI | Final (\%) | BS | Rej.\ (\%) | Invalid (\%) | Lat.\ (s) | Isol.\ cells | $\Delta$ (pp) | 95\,\% CI | $p$ / $p_{\mathrm{Holm}}$ | $g$ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S1 Peaceful | gpt-oss-120b, low effort (E1) | 20 | 52.9 ± 9.5 | [48.6, 56.6] | 40 ± 15 | 14.7 | 64 | 0.0 | 1.1 | 2.9 | ref. |  |  |  |
| S1 Peaceful | gpt-oss-120b, high effort | 20 | 56.3 ± 6.1 | [53.8, 59.1] | 46 ± 7 | 17.9 | 74 | 0.0 | 11.4 | 3.0 | +3.4 | [-1.7, 8.6] | 0.182 / 0.225 | +0.42 |
| S1 Peaceful | Qwen3.8-27B, thinking off (core) | 20 | 57.9 ± 7.1 | [54.7, 60.9] | 49 ± 11 | 18.1 | 64 | 0.3 | 1.2 | 4.1 | ref. |  |  |  |
| S1 Peaceful | Qwen3.8-27B, thinking on | 30 | 61.0 ± 6.0 | [58.9, 63.1] | 49 ± 9 | 17.1 | 73 | 0.6 | 21.0 | 3.4 | +3.1 | [-0.8, 7.0] | 0.112 / 0.225 | +0.48 |

### Inventory

| Experiment | Scenario | Agent | Model | Prompt | Autonomy | $n$ | Valid $N$ |
|---|---|---|---|---|---|---|---|
| E1 | S1 Peaceful | LLM-full | FastContext-4B | v1 | on | 3.0 | 10 |
| E1 | S3 Day/Night | LLM-full | FastContext-4B | v1 | on | 3.0 | 10 |
| E1 | S1 Peaceful | LLM-full | gpt-oss-120b | v1 | on | 3.0 | 20 |
| E1 | S3 Day/Night | LLM-full | gpt-oss-120b | v1 | on | 3.0 | 10 |
| E2 | S1 Peaceful | LLM-full | Qwen3.8-27B | v2+hist 5 | on | 3.0 | 10 |
| E2 | S3 Day/Night | LLM-full | Qwen3.8-27B | v2+hist 5 | on | 3.0 | 10 |
| E3 | S1 Peaceful | LLM-full | Qwen3.8-27B | v1 | off | 3.0 | 20 |
| E3 | S1 Peaceful | rule | - | - | off | 3.0 | 10 |
| E3 | S1 Peaceful | noop | - | - | off | 3.0 | 20 |
| E5 | S1 Peaceful | LLM-full | Qwen3.8-27B | v1 | on | 2.0 | 10 |
| E5 | S1 Peaceful | rule | - | - | on | 2.0 | 10 |
| E5 | S1 Peaceful | LLM-full | Qwen3.8-27B | v1 | on | 4.0 | 10 |
| E5 | S1 Peaceful | rule | - | - | on | 4.0 | 10 |
| E7 | S1 Peaceful | LLM-full + grid + snap | Qwen3.8-27B | v1g | on | 3.0 | 10 |
| E7 | S1 Peaceful | rule + snap | - | - | on | 3.0 | 10 |
| E7 | S1 Peaceful | LLM-full + snap | Qwen3.8-27B | v1 | on | 3.0 | 10 |
| E8 | S1 Peaceful | LLM-full + candidates | Qwen3.8-27B | v1c | on | 3.0 | 30 |
| E8 | S3 Day/Night | LLM-full + candidates | Qwen3.8-27B | v1c | on | 3.0 | 10 |
| E8 | S1 Peaceful | LLM-full + candidates + feedback | Qwen3.8-27B | v1c | on | 3.0 | 10 |
| E8 | S1 Peaceful | greedy-candidate | - | - | on | 3.0 | 30 |
| E9 | S1 Peaceful | LLM-full, high effort | gpt-oss-120b | v1 | on | 3.0 | 20 |
| E9 | S1 Peaceful | LLM-full, thinking on | Qwen3.8-27B | v1 | on | 3.0 | 30 |


# reasoning classifier validation

| Category | $N$ | Auto pos. | Human pos. | Agreement | $\kappa$ auto vs human |
|---|---|---|---|---|---|
| spatial | 50 | 38 | 38 | 96.0% | 0.89 |
| reactive | 50 | 49 | 49 | 100.0% | 1.00 |
| temporal | 50 | 0 | 0 | 100.0% | 1.00 |
| resource | 50 | 0 | 0 | 100.0% | 1.00 |
| capacity | 50 | 8 | 8 | 100.0% | 1.00 |
| noop justified | 50 | 8 | 9 | 98.0% | 0.93 |
| threat | 50 | 24 | 23 | 98.0% | 0.96 |
| none | 50 | 0 | 0 | 100.0% | 1.00 |
| pooled | 400 | 127 | 127 | 99.0% | 0.98 |

# Caveats

- Unit of analysis is the episode for coverage/threshold statistics, the decision for latency/parse/reasoning, the transition for monotonicity, the event for regret.
- Holm families: stats_report.COMPARISONS (main), all rows of tab_threshold_comparisons (threshold module).
- Annotation sample for the reasoning classifier: aux/reasoning_sample50.csv (fill in, then `reasoning.py --kappa <file>`).

# Files written

- tab_inventory.tex
- tab_conditions.tex
- tab_comparisons.tex
- tab_equivalence.tex
- tab_regret.tex
- tab_regret_validation.tex
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
- tab_ext_models.tex
- tab_ext_prompt.tex
- tab_ext_autoplace.tex
- tab_ext_pathloss.tex
- tab_ext_grounding.tex
- tab_ext_candidates.tex
- tab_ext_thinking.tex
- tab_ext_inventory.tex
- tab_reasoning_kappa.tex
- numbers.json
- macros.tex
- aux/regret_events.csv
- aux/reasoning_sample50.csv
- aux/reasoning_sample50_auto.csv
