# Revision analysis pipeline (`agent/analysis/revision/`)

Offline analysis of the intent-execution episodes for the COMCOM major revision. Reads the frozen June 2026
campaign (`agent/data/`, protocol v1) and the revision campaign (`agent/results_v2/<episode_id>/`, protocol v2);
never writes into either. Plain Python 3 + numpy/scipy/matplotlib.

| Module | Purpose | Main outputs |
|---|---|---|
| `load_runs.py` | Loader for both campaigns -> `Episode` objects (canonical backend, provenance, validity). `--min-decisions K` / `ANALYSIS_MIN_DECISIONS` lowers the 20-decision validity threshold for smoke tests. | inventory on stdout |
| `stats_report.py` | Per-condition means, Welch t / Hedges g / 95 % CI, Holm, TOST, bootstrap CI, power. | `tab_conditions.tex`, `tab_comparisons.tex`, `tab_equivalence.tex` |
| `common.py` | Shared helpers: labels/palette order, argparse, `Table` (markdown + booktabs), `Numbers` (numbers.json/macros.tex), Wilson CI, Spearman, Cohen's kappa, action grammar. | - |
| `regret.py` | Legacy regret estimators (exact ports of the June scripts), geometric-v2 estimator (disconnected_positions within 1200 elmos of their centroid), exact regret from deterministic re-simulation (`--mapping`). | `tab_regret.tex`, `tab_regret_validation.tex`, `regret_events.csv`, `regret_exact.csv` |
| `reasoning.py` + `reasoning_taxonomy.json` | Multi-label keyword taxonomy with explicit denominators, category x action cross-tab, stratified 50-decision annotation sample, Cohen's kappa (`--kappa`). | `tab_reasoning_*.tex`, `reasoning_sample50.csv`, `reasoning_sample50_auto.csv` |
| `latency_invalid.py` | Latency per arm (v2 logged, v1 reconstructed via the demo-timestamp clock anchor), parse-status / invalid-output rates, bridge validation outcomes, wall-clock and peak RSS. | `tab_latency.tex`, `tab_parse_status.tex`, `tab_validation_outcomes.tex`, `tab_runtime.tex` |
| `threshold_metrics.py` | Share of epochs >= 80 %, first violation, below-threshold area, final coverage, BS; LLM vs rule with Holm. | `tab_threshold.tex`, `tab_threshold_comparisons.tex` |
| `monotonicity.py` | Coverage-monotonicity shares (strict / demand-adjusted / covered-count / action-based) with Wilson CIs; prints the definitions. | `tab_monotonicity.tex` |
| `make_figures.py` | All paper figures (PDF + PNG 300 dpi, >= 9 pt, N in legends, validated colour-blind-safe palette). | `paper_major_revision/figures/fig_*.{pdf,png}` |
| `tables_to_tex.py` | Driver: runs everything, writes tables, `numbers.json`, `macros.tex`, `REPORT.md`. | `paper_major_revision/tables/` |
| `compare_determinism.py` | Same-seed episode comparison (E4b / F6a pilot). | stdout |

## One command

```bash
cd agent/analysis/revision
python3 tables_to_tex.py --campaign v2 --figures            # revision campaign -> paper_major_revision/{tables,figures}
python3 tables_to_tex.py --campaign v1 --tables-dir ../../../paper_major_revision/tables_v1 --figures-dir ../../../paper_major_revision/figures_v1
```
Smoke test on the short pilot episodes: add `--min-decisions 2`. Regret validation against re-simulated branches:
`--mapping branches.csv` with columns `original_episode_dir,branch_episode_dir[,inject_decision]`.
Every module is also a script with the same `--campaign/--out-dir/--min-decisions` options and is importable
(`analyze(eps, ...) -> common.Result` with `.tables`, `.numbers`, `.markdown`, `.extra`).

In the manuscript: `\input{tables/macros.tex}` once, then `\numSOnePeacefulLlmAvgMean` etc. (keys and definitions in
`numbers.json`); `\input{tables/tab_threshold.tex}` etc. for the tables (captions are stubs to edit in place).

Manual annotation of the reasoning classifier: fill the `label_*` columns of `tables/aux/reasoning_sample50.csv`
(1/x = present), then `python3 reasoning.py --kappa <filled.csv> [--kappa2 <second annotator.csv>]`.

## State on 27 Sep 2026

`paper_major_revision/tables/v1/` + `figures/v1/` hold the complete run on the June data (81 valid episodes; caveats in
`REPORT.md`); `tables/smoke_v2/` + `figures/smoke_v2/` are smoke tests on the short determinism/pilot episodes
(`--min-decisions 2`, synthetic `--mapping`) and carry no scientific meaning. The top-level `tables/` and `figures/`
are reserved for the revision campaign (`tables_to_tex.py --campaign v2 --figures`).

## Additions 29 Sep 2026

| Module | Purpose | Main outputs |
|---|---|---|
| `extensions.py` | Tier-2 experiments E1 (models), E2 (prompt v2), E3 (autoplace off), E5 (path loss), E7 (grounding aids), E8 (candidate positions, feedback, greedy), E9 (thinking mode / reasoning effort) against the core arms; Welch/Holm per experiment family; per-arm `isolated_mean` (cells the autonomous linker reported isolated, from gamelog) and `inactive_end_mean` (cells without a live backhaul path at the last decision, from the bridge's `connected` flag, logged since E8) | `tab_ext_models.tex`, `tab_ext_prompt.tex`, `tab_ext_autoplace.tex`, `tab_ext_pathloss.tex`, `tab_ext_inventory.tex`, `fig_ext_*.{pdf,png}` (called by `tables_to_tex.py`, `--ext-dir`) |
| `e4_analysis.py` | E4 regret validation: builds `aux/e4_mapping.csv` from `agent/results_v2_e4`, determinism table for the plain replays, per-branch table, results paragraphs | `tab_determinism.tex`, `tab_regret_branches.tex`, `numbers_e4.json`, `macros_e4.tex`, `../sections/e4_results.tex`, `../response/e4_summary.tex` |

Full build of every number in the revised manuscript:
```bash
cd agent/analysis/revision
python3 e4_analysis.py                                   # after agent/results_v2_e4 is complete
python3 make_taxonomy_table.py                            # appendix keyword table
python3 tables_to_tex.py --campaign v2 --figures --mapping ../../../paper_major_revision/tables/aux/e4_mapping_clean.csv \
        --kappa ../../../paper_major_revision/tables/aux/reasoning_sample50_annotated.csv
cd ../../../paper_major_revision && pdflatex main && bibtex main && pdflatex main && pdflatex main
```
Wide auto-tables are wrapped in `adjustbox{max width=\textwidth}` (the CAS class defines `\tblwidth` as the table's natural width).

## Additions 30 Sep 2026 (E8/E9 prepared)

- `orchestrator.py`: `--candidates` (ranked buildable candidate positions in the observation, `place_bs|TYPE|C<n>` answers resolved), `--feedback` (validation outcome + coverage change of the previous decision), prompt version `v1c`, backend `greedy` (always the first candidate). Needs modoption `6g_agent_buildable_grid=true` for buildability.
- Manifests: `agent/campaign_e8.csv` (LLM+candidates S1/S3, LLM+candidates+feedback S1, greedy S1; 40 episodes) and `agent/campaign_e9.csv` (Qwen3.8 thinking on, gpt-oss-120b high effort; 20 episodes, slow: 50-150 s per decision with thinking).
- `extensions.py` writes `tab_ext_candidates.tex` (E8) and `tab_ext_thinking.tex` (E9) when the arms exist; `summary.py` adds the forest-plot families.

## Additions 1 Oct 2026 (E8/E9 complete)

- E8 (40 episodes, tags `e8_cand`, `e8_candfb`, `e8_greedy`) and E9 (20 episodes, `e9_think`, `e9_gptoss_high`) are in `agent/results_v2_ext`; `failed/` holds the episodes of the two earlier E8 attempts
  (reply parser did not accept `place_bs|TYPE|C<n>`; candidate generator proposed occupied or unconnectable positions) and interrupted episodes.
- Final candidate generator (orchestrator `compute_candidates`): buildable grid-cell centres that are unoccupied (bridge export `blocked_cells`, 300 elmos from cells and from the agent's own orders of the last 6 decisions),
  outside threat zones, within `bs_to_backhaul_range` (600) of a live backhaul link (bridge export `backhaul_nodes`); ranked by disconnected units within 1200 elmos. Decision records log `candidates`, `candidate_id`, `raw_action`, `backhaul_nodes`, `blocked_cells`.
- `tab_ext_candidates.tex` / `tab_ext_thinking.tex` have an `Isol. cells` column; E8 pairwise macros `\numExtEEightSOnePeacefulEEightCandVs{Greedy,Feedback,Noop,Rule}*`.
- Headline: S1 LLM+candidates 65.7 (+7.8 pp vs core LLM, Holm p 0.005; +6.2 vs noop), greedy 61.8 (+4.0 ns), +feedback 60.7; LLM took C1 in 180/180 placements; S3 +0.9 ns. E9: thinking on 61.4 (+3.5 ns, latency 19.5 s, rejections 76 %), gpt-oss high 57.5 (+7.3 vs low, ns).
