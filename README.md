# Agentic network-intent testbed: measurement data and tool chain

Companion repository of *Beyond Intent Translation: A Closed-Loop Testbed for Evaluating Agentic AI Execution of
Network Intents* (G. Szabó, Ericsson Research; manuscript COMCOM-D-26-02550, Computer Communications, under
review). A recording of the testbed in operation: https://youtu.be/iWS802mPziI

The testbed evaluates how agentic AI systems (LLM agents, heuristics, no-intervention and greedy baselines)
*execute* network intents over time: autonomous civilian economies generate spatially distributed demand for three
QoS classes, a network model computes coverage, capacity and backhaul connectivity, an intent agent is queried every
60 simulated seconds through a pause-query-action protocol and orders cell deployments or slice reconfigurations,
and an autonomous infrastructure layer executes them. Episodes are seeded and can be re-simulated exactly with an
alternative action for counterfactual analysis.

## What is in this repository

| Directory | Content | Licence |
|---|---|---|
| `agent/results_v2/` | 170 core-campaign episodes (S1 to S4; LLM, no-spatial, minimal, rule, random, no-op arms) | CC BY 4.0 |
| `agent/results_v2_ext/` | 320 extension episodes (E1 models, E2 prompt variant, E3 autonomous layer off, E5 path loss, E7 grounding aids, E8 decision support and greedy baseline, E9 thinking mode); `failed/` holds episodes retired by the campaign runner (endpoint failures, interruptions, two superseded tool versions of E8), kept for transparency and excluded from every table | CC BY 4.0 |
| `agent/results_v2_e4/` | 27 deterministic re-simulations (4 unchanged replays, 23 counterfactual branches) used to validate the regret estimator | CC BY 4.0 |
| `paper_major_revision/tables/` | every table of the paper as LaTeX, `numbers.json` (every number with definition and sample size), `macros.tex`, `REPORT.md`; `aux/` holds the reasoning-annotation sheets and the regret mappings | CC BY 4.0 |
| `paper_major_revision/figures/` | every figure of the paper | CC BY 4.0 |
| `agent/orchestrator.py` | agent host: LLM (OpenAI-compatible endpoint), rule, random, no-op, greedy and replay backends; observation formatting; candidate generator; complete inference logging | BSD 3-Clause |
| `agent/run_episode.sh`, `agent/campaign.py`, `agent/make_start_script.py`, `agent/setup_native.sh` | seeded headless episode runner with protocol assertions; idempotent campaign runner with validity checks, automatic re-runs and an endpoint speed gate; start-script generator; environment setup | BSD 3-Clause |
| `agent/campaign_*.csv`, `agent/scenarios/` | the manifests of every campaign reported in the paper; the four scenario start-script templates | BSD 3-Clause |
| `agent/analysis/revision/` | the analysis pipeline that generates every number, table and figure of the paper | BSD 3-Clause |
| `agent/ericai_proxy.py` | optional adapter between the agent host and a corporate inference platform (requires that platform's client, not included) | BSD 3-Clause |
| `docker/` | container recipe for headless episodes | BSD 3-Clause |
| `DEPENDENCIES.md` | exact versions of everything used | |

**Not in this repository.** The simulation-side modules (Lua gadgets, autonomous-layer behaviours and unit
definitions) extend the GPL-licensed game content of *Beyond All Reason* on the *Recoil* engine and are subject to
a separate release approval. Until that approval they are available to researchers on request, and a
reimplementation specification is being prepared for this repository. Running new episodes therefore requires
those modules; reproducing every number of the paper does not (see below).

## Reproducing the numbers of the paper

Requirements: Python 3.12 with `numpy`, `scipy`, `matplotlib`.

```
cd agent/analysis/revision
python3 tables_to_tex.py --campaign v2 --figures \
    --mapping ../../../paper_major_revision/tables/aux/e4_mapping_clean.csv \
    --kappa   ../../../paper_major_revision/tables/aux/reasoning_sample50_annotated.csv
python3 summary.py
```

This rewrites `paper_major_revision/tables/*.tex`, `numbers.json`, `macros.tex`, `REPORT.md` and
`paper_major_revision/figures/*.pdf` from the episode logs. `REPORT.md` is the human-readable version of every table.
The pipeline reads the compressed engine logs (`gamelog.txt.gz`) directly.

## Data format (one directory per episode)

| File | Content |
|---|---|
| `header.json` | scenario, seed, engine game identifier, code commit, agent backend, model identifier as served, prompt version and SHA-256 hash, sampling parameters, timeout, enabled options |
| `decisions.jsonl` | one JSON line per decision: the observation sent, the raw model reply (and separately returned reasoning), parse status, latency and token usage, the executed action, a state summary, the cell list, the positions of disconnected units and the threats; candidate lists and connectivity exports in the E8 arms |
| `summary.json` | protocol assertions (execution lag, action mismatches, stale actions), validator outcomes, run facts (wall-clock, peak memory, game identifier), inference-error counts |
| `gamelog.txt.gz` | the engine's simulation-side log: every `[6G Agent]` protocol line (decision, acceptance, execution, validation), the seed confirmation, the autonomous layer's log lines |
| `start_script.txt` | the engine start script of the episode (map, teams, every mod option, seed) |

Directory names follow `<scenario>_<backend>[_<tag>]_seed<seed>_<YYYYmmdd_HHMMSS>`. Seeds: 10001 to 10170 (core),
20001 to 20890 (extensions). The prompt texts are in Appendix A of the paper and in `agent/orchestrator.py`.

## Licences

Code: BSD 3-Clause (`LICENSE`). Data, tables, figures and annotation sheets: Creative Commons Attribution 4.0
(`LICENSE-DATA.md`). Please cite the paper when using either.

## Citation

G. Szabó, "Beyond Intent Translation: A Closed-Loop Testbed for Evaluating Agentic AI Execution of Network
Intents," Computer Communications, under review (manuscript COMCOM-D-26-02550), 2026.
