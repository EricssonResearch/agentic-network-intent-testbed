# Revision analysis report

Generated 2026-09-27T07:43:03 by tables_to_tex.py; campaign=v2; valid episodes=24; min decisions per episode=2; protocols=[2].

Every table below is also written as LaTeX to this directory; every number is in numbers.json and macros.tex.

## Inventory

| Scenario | Agent | Model | Prot. | Code version(s) | Valid | Discarded (reason) |
|---|---|---|---|---|---|---|
| S1 Peaceful | LLM-full | gemma4:latest | 2 | bc359d7594f7 | 1 | 2x only 0 decisions |
| S1 Peaceful | rule | - | 2 | bc359d7594f7 | 23 | 11x only 0 decisions; 1x protocol assertion failed (lag/mismatch) |
| S1 Peaceful | noop | - | 2 | - | 0 | 1x protocol assertion failed (lag/mismatch) |
| S1 Peaceful | replay | - | 2 | bc359d7594f7 | 2 | - |

# Main statistics (stats_report.py)

## Per-condition summary (mean ± sample SD; episode = unit)

| Scenario | Agent | N | Avg cov (%) | 95% CI | Final cov (%) | BS deployed mean±SD (median) | Epochs ≥80% | First violation (epoch) |
|---|---|---|---|---|---|---|---|---|
| s1_peaceful | llm | 1 | 100.0 ± 0.0 | [100.0, 100.0] | 100.0 ± 0.0 | 1.0 ± 0.0 (1) | 100.0% | 3.0 |
| s1_peaceful | rule | 23 | 90.2 ± 10.9 | [85.4, 94.0] | 78.5 ± 19.4 | 2.1 ± 2.7 (2) | 83.2% | 4.8 |

## Pairwise comparisons (Welch t-test on episode means; Hedges' g; Holm-corrected over this family)

| Comparison | n | Δ (pp) | t | df | p | p (Holm) | g | 95% CI (pp) |
|---|---|---|---|---|---|---|---|---|

## Equivalence (TOST)

| Comparison | margin (pp) | n | p (TOST) |
|---|---|---|---|

## Notes

- campaign=v2; valid episodes=24; min decisions per episode=2; protocols=[2]
- power to detect 6 pp at SD 9: n=5: 0.15, n=10: 0.29, n=20: 0.54, n=30: 0.72

*No pairwise comparison in stats_report.COMPARISONS has N >= 2 in both arms for this campaign.*

# regret

## Decision regret

Trigger: coverage drop >= 5 pp between consecutive decisions. Estimators: see module docstring.

| Scenario | Agent | $N$ ep. | Events | Ev./ep. | Legacy-text | Legacy-fig | Geometric-v2 | 95\,\% CI (v2) | Cum./ep. (v2) | Pos. avail. |
|---|---|---|---|---|---|---|---|---|---|---|
| S1 Peaceful | LLM-full | 1 | 0 | 0.00 | n/a | n/a | n/a | n/a | 0.0 ± 0.0 | n/a (no events) |
| S1 Peaceful | rule | 23 | 35 | 1.52 | 4.1 ± 3.7 | 4.4 ± 3.7 | 18.2 ± 17.5 | [12.7, 24.2] | 27.7 ± 19.6 | 100% |

## Exact regret (re-simulation)

| Estimator | $N$ branches | Bias (pp) | MAE (pp) | Spearman $\rho$ | $p$ |
|---|---|---|---|---|---|
| legacy (30 % rule) | 2 | 0.0 | 0.0 | n/a | n/a |
| geometric-v2 | 2 | 0.0 | 0.0 | n/a | n/a |

*2 usable branch pairs; 0 with a non-identical prefix (determinism violated; excluded from nothing here but flagged in regret_exact.csv).*

Per-branch rows: regret_exact.csv


# reasoning

## Reasoning taxonomy

Taxonomy: reasoning_taxonomy.json (version revision-2026-09-27), matching mode `substring`.
LLM episodes analysed: 1 (non-LLM episodes excluded: 23).

### Denominators

| Scenario | Agent | Model | $N$ ep. | $N$ dec. | Non-empty | Error | Uncategorized | Valid |
|---|---|---|---|---|---|---|---|---|
| S1 Peaceful | LLM-full | gemma4:latest | 1 | 2 | 2 (100.0%) | 0 (0.0%) | 0 (0.0%) | 2 (100.0%) |

### Categories

| Category | Count | \% of dec. ($N$=2) | \% of non-empty ($N$=2) | LLM-full (\%) |
|---|---|---|---|---|
| spatial | 1 | 50.0 | 50.0 | 50.0 |
| reactive | 2 | 100.0 | 100.0 | 100.0 |
| temporal | 0 | 0.0 | 0.0 | 0.0 |
| resource | 0 | 0.0 | 0.0 | 0.0 |
| capacity | 2 | 100.0 | 100.0 | 100.0 |
| noop justified | 2 | 100.0 | 100.0 | 100.0 |
| threat | 2 | 100.0 | 100.0 | 100.0 |
| uncategorized | 0 | 0.0 | 0.0 | 0.0 |

*Labels per categorized decision: mean 4.50; multi-label, so category counts do not sum to the number of decisions.*

### Category x action

| Category | noop | place_bs | reconfig_slice | other | Total |
|---|---|---|---|---|---|
| spatial | 1 | 0 | 0 | 0 | 1 |
| reactive | 2 | 0 | 0 | 0 | 2 |
| temporal | 0 | 0 | 0 | 0 | 0 |
| resource | 0 | 0 | 0 | 0 | 0 |
| capacity | 2 | 0 | 0 | 0 | 2 |
| noop justified | 2 | 0 | 0 | 0 | 2 |
| threat | 2 | 0 | 0 | 0 | 2 |
| uncategorized | 0 | 0 | 0 | 0 | 0 |
| empty | 0 | 0 | 0 | 0 | 0 |
| error | 0 | 0 | 0 | 0 | 0 |
| all decisions | 2 | 0 | 0 | 0 | 2 |

### Annotation sample: 2 decisions (stratified by scenario x backend x action type; requested 50)


# latency_invalid

## Latency

| Camp. | Agent | Model | $N$ dec. | Source | Median | Mean | p90 | p99 | Max | $>$60\,s |
|---|---|---|---|---|---|---|---|---|---|---|
| v2 | LLM-full | gemma4:latest | 2/2 | logged (latency_s) | 113.8 | 113.8 | 184.7 | 200.6 | 202.4 | 1 |
| v2 | rule | - | 134/134 | logged (decision_wall_s) | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 0 |

## Parse status / invalid outputs

| Camp. | Agent | Model | $N$ | valid | extracted | fallback\_noop | api\_error | timeout | Invalid (\%) | Extracted (\%) | Syntax-inv. |
|---|---|---|---|---|---|---|---|---|---|---|---|
| v2 | LLM-full | gemma4:latest | 2 | 2 | 0 | 0 | 0 | 0 | 0.0 | 0.0 | 0 |
| v2 | rule | - | 134 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | 0 |

## Bridge validation outcomes

| Camp. | Agent | Model | $N$ dec. | executed\_place | noop | skipped\_invalid\_position | skipped\_water |
|---|---|---|---|---|---|---|---|
| v2 | LLM-full | gemma4:latest | 2 | 0 | 2 | 0 | 0 |
| v2 | rule | - | 134 | 14 | 74 | 2 | 5 |

## Run-time

| Camp. | Agent | Model | $N$ ep. | Decisions/ep. | Wall-clock (s) | Peak RSS (MB) |
|---|---|---|---|---|---|---|
| v2 | LLM-full | gemma4:latest | 1 | 2.0 | 362 ± 0 | 5833 ± 0 |
| v2 | rule | - | 23 | 5.8 | 130 ± 37 | 5877 ± 27 |

# threshold_metrics

## Threshold metrics (threshold = 80 %)

| Scenario | Agent | $N$ | Epochs $\geq$ thr. (\%) | 95\,\% CI | First viol. (epoch) | Never | Below-thr. area | 95\,\% CI | Final cov. (\%) | BS |
|---|---|---|---|---|---|---|---|---|---|---|
| S1 Peaceful | LLM-full | 1 | 100.0 ± 0.0 | [100.0, 100.0] | n/a (none) | 1/1 | 0 ± 0 | [0, 0] | 100.0 ± 0.0 | 1.0 ± 0.0 |
| S1 Peaceful | rule | 23 | 83.2 ± 18.4 | [75.5, 90.1] | 4.3 ± 1.2 | 9/23 | 53 ± 191 | [8, 135] | 78.5 ± 19.4 | 2.1 ± 2.7 |

## LLM vs rule

| Scenario | Metric | $n$ | $\Delta$ | 95\,\% CI | $t$ | df | $p$ | $p_{\mathrm{Holm}}$ | $g$ |
|---|---|---|---|---|---|---|---|---|---|

*n/a: no scenario has both an LLM-full and a rule arm with N >= 2.*

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
| v2 | LLM-full | 1 | n/a (0) | n/a (0) | n/a (0) | n/a (0) |
| v2 | rule | 111 | 40.9% [23.3, 61.3] (9/22) | 90.9% [72.2, 97.5] (20/22) | 54.5% [34.7, 73.1] (12/22) | 46.4% [29.5, 64.2] (13/28) |
| v2 | all agents | 112 | 40.9% [23.3, 61.3] (9/22) | 90.9% [72.2, 97.5] (20/22) | 54.5% [34.7, 73.1] (12/22) | 46.4% [29.5, 64.2] (13/28) |

*U(t) taken from mobile_units; unit = transition, episode clustering ignored.*

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
- numbers.json
- macros.tex
- aux/regret_events.csv
- aux/reasoning_sample50.csv
- aux/reasoning_sample50_auto.csv
