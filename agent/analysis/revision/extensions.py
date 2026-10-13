#!/usr/bin/env python3
"""
Tier-2 extension experiments (REVISION_PLAN.md S4.2) on top of the core revision campaign:

  E1  multi-model        : S1-full and S3 with additional models (openai/gpt-oss-120b, Microsoft/FastContext-1.0-4B-RL)
                           against the primary model (Qwen/Qwen3.8-27B-FP8-1M) of the core campaign  -> tab_ext_models
  E2  prompt variant     : prompt v2 (explicit temporal guidance) + 5-step decision history, primary model, S1 and S3
                           against prompt v1 (core)                                                  -> tab_ext_prompt
  E3  autonomous layer   : S1 with 6g_networkbst_autoplace=false (LLM, rule, noop) against the core arms (autoplace on);
                           marginal contribution of the intent agent = agent - noop in both settings -> tab_ext_autoplace
  E5  path-loss exponent : S1 LLM vs rule at 6g_path_loss_exponent 2.0 / 4.0 against the core arms (3.0) -> tab_ext_pathloss

Data: agent/results_v2_ext/<episode_id>/ (protocol v2, seeds 20001-20320) plus the reference arms of agent/results_v2/.
The extension episodes are identified by the manifest tag embedded in the episode id
(<scenario>_<backend>_<tag>_seed<seed>_<timestamp>) and by header.json (model, prompt_version, history) and
start_script.txt (6g_networkbst_autoplace, 6g_path_loss_exponent). Reference (core) episodes have tag 'core'.

Statistics as in stats_report.py: unit = episode; Welch t on per-episode average coverage; Hedges g; 95 % CI of the
difference; Holm correction within each experiment's family of tests (listed in the table notes); bootstrap CI of means.
Per-decision descriptors reused from the other modules: parse status / validator outcomes (latency_invalid.py), temporal
share of the reasoning comments (reasoning.py taxonomy), latency.

Usage: extensions.py [--ext-dir DIR] [--out-dir DIR] [--figures-dir DIR] [--min-decisions K]
"""
from __future__ import annotations
import argparse, re, statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Optional

from load_runs import Episode, load_v2, V2_DIR
from stats_report import welch, holm, bootstrap_ci
from common import (gamelog_text, Result, Table, Numbers, fmt, fmt_pm, fmt_ci, fmt_p, backend_label, scenario_label, scenario_sort_key,
                    backend_sort_key, write_table, write_text, DEFAULT_TABLES_DIR, DEFAULT_FIGURES_DIR, REPO, MIN_DECISIONS)
import latency_invalid as lat_mod
import reasoning as reason_mod

EXT_DIR = REPO / "agent" / "results_v2_ext"
PRIMARY_MODEL = "Qwen/Qwen3.8-27B-FP8-1M"
MODEL_SHORT = {"Qwen/Qwen3.8-27B-FP8-1M": "Qwen3.8-27B", "openai/gpt-oss-120b": "gpt-oss-120b",
               "Microsoft/FastContext-1.0-4B-RL": "FastContext-4B"}
DEFAULT_PATH_LOSS = 3.0


# ----------------------------------------------------------------------------- provenance of one episode
def episode_tag(ep: Episode) -> str:
    m = re.match(r"s\d_[a-z]+_(?:llm_nospatial|llm_minimal|llm|rule|random|noop|greedy|replay)_(.+?)_seed\d+_\d{8}_\d{6}$", ep.episode_id)
    return m.group(1) if m else ""


def start_script_option(ep: Episode, key: str) -> Optional[str]:
    p = Path(ep.path) / "start_script.txt"
    if not p.exists():
        return None
    m = re.search(re.escape(key) + r"\s*=\s*([^;\s]+)", p.read_text(errors="ignore"))
    return m.group(1) if m else None


def autoplace(ep: Episode) -> bool:
    v = start_script_option(ep, "6g_networkbst_autoplace")
    return (v or "true").lower() != "false"


def path_loss(ep: Episode) -> float:
    v = start_script_option(ep, "6g_path_loss_exponent")
    return float(v) if v else DEFAULT_PATH_LOSS


def model_short(m: Optional[str]) -> str:
    return MODEL_SHORT.get(m or "", (m or "-").split("/")[-1])


# ----------------------------------------------------------------------------- per-arm descriptors
def arm_summary(eps: list) -> dict:
    """Episode-level and decision-level descriptors of one arm."""
    avg = [e.avg_coverage() for e in eps]
    fin = [e.final_coverage() for e in eps]
    bs = [e.bs_deployed() for e in eps]
    f80 = [e.frac_epochs_at_least(80) for e in eps]
    n_dec = sum(len(e.decisions) for e in eps)
    d = dict(n=len(eps), avg=avg, avg_mean=statistics.fmean(avg) if avg else None,
             avg_sd=statistics.stdev(avg) if len(avg) > 1 else 0.0,
             avg_ci=bootstrap_ci(avg) if len(avg) > 1 else ((avg[0], avg[0]) if avg else None),
             final_mean=statistics.fmean(fin) if fin else None, final_sd=statistics.stdev(fin) if len(fin) > 1 else 0.0,
             bs_mean=statistics.fmean(bs) if bs else None, bs_sd=statistics.stdev(bs) if len(bs) > 1 else 0.0,
             f80_mean=statistics.fmean(f80) if f80 else None, f80_sd=statistics.stdev(f80) if len(f80) > 1 else 0.0,
             n_dec=n_dec)
    # decision-level (LLM arms): parse status, validator outcomes, latency, temporal reasoning share
    ps, out = Counter(), Counter()
    lat = []
    for e in eps:
        ps.update(lat_mod.parse_statuses(e))
        out.update(lat_mod.validation_outcomes(e))
        lat += lat_mod.decision_latency(e)[0]
    inv = sum(ps.get(s, 0) for s in lat_mod.INVALID_STATUSES)
    placed = sum(out.get(k, 0) for k in out if k.startswith("executed_place") or k.startswith("skipped") or k.startswith("snapped"))
    rejected = sum(out.get(k, 0) for k in out if k.startswith("skipped"))
    snapped = out.get("snapped_place", 0)
    d.update(invalid_pct=100.0 * inv / n_dec if n_dec else None, extracted=ps.get("extracted", 0),
             placements=placed, rejected=rejected, rejected_pct=100.0 * rejected / placed if placed else None,
             snapped=snapped, snapped_pct=100.0 * snapped / placed if placed else None,
             executed_place=out.get("executed_place", 0) + snapped, noop_actions=out.get("noop", 0),
             latency_median=statistics.median(lat) if lat else None, latency_p90=(sorted(lat)[int(0.9 * (len(lat) - 1))] if lat else None))
    # cells the autonomous linker reported as isolated at least once (gamelog '[6G NetworkBST v2] ... LINKING isolated BS <id>'),
    # and cells without a live backhaul path at the last decision (bridge flag 'connected', logged since E8; None if absent)
    iso, inact = [], []
    for e in eps:
        try:
            txt = gamelog_text(Path(e.path) / "gamelog.txt")
            iso.append(len(set(re.findall(r"LINKING isolated BS (\d+)", txt))))
        except OSError:
            pass
        bs = (e.decisions[-1].get("base_stations") or []) if e.decisions else []
        if bs and "connected" in bs[0]:
            inact.append(sum(1 for b in bs if not b.get("connected") and not b.get("under_construction")))
    d.update(isolated_mean=statistics.fmean(iso) if iso else None, inactive_end_mean=statistics.fmean(inact) if inact else None)
    if eps and eps[0].is_llm:
        tax = reason_mod.load_taxonomy()
        rows = reason_mod.decision_rows(eps, tax, None)
        d["temporal_n"] = sum(1 for r in rows if "temporal" in r["labels"])
        d["temporal_pct"] = 100.0 * d["temporal_n"] / len(rows) if rows else None
        d["nonempty_pct"] = 100.0 * sum(1 for r in rows if r["status"] != "empty") / len(rows) if rows else None
    else:
        d["temporal_n"], d["temporal_pct"], d["nonempty_pct"] = None, None, None
    return d


def compare(a: list, b: list) -> Optional[dict]:
    if len(a) < 2 or len(b) < 2:
        return None
    return welch([e.avg_coverage() for e in a], [e.avg_coverage() for e in b])


def holm_family(comps: list):
    """comps: list of dicts with 'p'; adds 'p_holm' in place (None entries skipped)."""
    idx = [i for i, c in enumerate(comps) if c is not None]
    adj = holm([comps[i]["p"] for i in idx]) if idx else []
    for i, pa in zip(idx, adj):
        comps[i]["p_holm"] = pa


def cmp_cells(c: Optional[dict]) -> list:
    if c is None:
        return ["ref.", "", "", ""]
    return [f"{c['diff']:+.1f}", fmt_ci(c["ci"]), f"{fmt_p(c['p'])} / {fmt_p(c.get('p_holm', c['p']))}", f"{c['g']:+.2f}"]


def add_cmp_numbers(N: Numbers, key: str, c: Optional[dict], what: str):
    if c is None:
        return
    N.add(key + "_n", f"{c['n_a']}/{c['n_b']}", f"{what}: episodes A/B")
    N.add(key + "_diff", c["diff"], f"{what}: difference of mean average coverage A-B (pp)")
    N.add(key + "_ci_lo", c["ci"][0], f"{what}: 95% CI lower (pp)")
    N.add(key + "_ci_hi", c["ci"][1], f"{what}: 95% CI upper (pp)")
    N.add(key + "_t", c["t"], f"{what}: Welch t", nd=2)
    N.add(key + "_df", c["df"], f"{what}: Welch df")
    N.add(key + "_p", fmt_p(c["p"]), f"{what}: Welch p")
    N.add(key + "_p_holm", fmt_p(c.get("p_holm", c["p"])), f"{what}: Holm-adjusted p within the experiment's family")
    N.add(key + "_g", c["g"], f"{what}: Hedges g", nd=2)


def add_arm_numbers(N: Numbers, key: str, s: dict, what: str):
    N.add(key + "_n", s["n"], f"{what}: episodes", nd=0)
    N.add(key + "_avg_mean", s["avg_mean"], f"{what}: mean of per-episode average coverage (%)", n=s["n"])
    N.add(key + "_avg_sd", s["avg_sd"], f"{what}: sample SD of average coverage (%)", n=s["n"])
    if s["avg_ci"]:
        N.add(key + "_avg_ci_lo", s["avg_ci"][0], f"{what}: bootstrap 95% CI lower of the mean (%)", n=s["n"])
        N.add(key + "_avg_ci_hi", s["avg_ci"][1], f"{what}: bootstrap 95% CI upper of the mean (%)", n=s["n"])
    N.add(key + "_final_mean", s["final_mean"], f"{what}: mean final coverage (%)", n=s["n"])
    N.add(key + "_bs_mean", s["bs_mean"], f"{what}: mean BS deployed", n=s["n"])
    N.add(key + "_f80_mean", s["f80_mean"], f"{what}: mean share of epochs with coverage >= 80% (%)", n=s["n"])
    N.add(key + "_rejected_pct", s["rejected_pct"], f"{what}: share of placement orders rejected by the validator (%)", n=s["placements"])
    N.add(key + "_invalid_pct", s["invalid_pct"], f"{what}: invalid LLM outputs (fallback/api_error/timeout) (%)", n=s["n_dec"])
    N.add(key + "_latency_median", s["latency_median"], f"{what}: median decision latency (s)", n=s["n_dec"])
    if s.get("isolated_mean") is not None:
        N.add(key + "_isolated_mean", s["isolated_mean"], f"{what}: cells reported isolated by the autonomous linker at least once, per episode", n=s["n"])
    if s.get("inactive_end_mean") is not None:
        N.add(key + "_inactive_end_mean", s["inactive_end_mean"], f"{what}: cells without a live backhaul path at the last decision, per episode", n=s["n"])
    if s["temporal_pct"] is not None:
        N.add(key + "_temporal_pct", s["temporal_pct"], f"{what}: share of decisions with temporal reasoning vocabulary (%)", n=s["n_dec"])
        N.add(key + "_temporal_n", s["temporal_n"], f"{what}: decisions with temporal reasoning vocabulary", nd=0)


def arm_cells(s: dict, llm: bool = True) -> list:
    cells = [s["n"], fmt_pm(s["avg_mean"], s["avg_sd"]), fmt_ci(s["avg_ci"]), fmt_pm(s["final_mean"], s["final_sd"], 0),
             fmt(s["bs_mean"]), fmt(s["rejected_pct"], 0)]
    if llm:
        cells += [fmt(s["invalid_pct"]), f"{s['temporal_n']} ({fmt(s['temporal_pct'])})" if s["temporal_n"] is not None else "n/a"]
    return cells


ARM_COLS = ["$N$", "Avg.\\ cov.\\ (\\%)", "95\\,\\% CI", "Final (\\%)", "BS", "Rej.\\ (\\%)"]
LLM_COLS = ["Inv.\\ (\\%)", "Temporal $n$ (\\%)"]
CMP_COLS = ["$\\Delta$ (pp)", "95\\,\\% CI", "$p$ / $p_{\\mathrm{Holm}}$", "$g$"]


# ----------------------------------------------------------------------------- loading
def load_ext(ext_dir: Path = EXT_DIR, min_decisions: Optional[int] = None) -> list:
    eps = [e for e in load_v2(ext_dir, min_decisions) if e.valid and e.backend != "replay"]
    return eps


def load_core(min_decisions: Optional[int] = None) -> list:
    return [e for e in load_v2(V2_DIR, min_decisions) if e.valid and e.backend != "replay"]


def core_arm(core: list, scenario: str, backend: str) -> list:
    return [e for e in core if e.scenario == scenario and e.backend == backend]


# ----------------------------------------------------------------------------- experiments
def analyze(ext: list, core: list) -> Result:
    res, N = Result(), Numbers()
    md = ["## Extension experiments (results_v2_ext + core reference arms)", ""]
    by_tag = defaultdict(list)
    for e in ext:
        by_tag[(e.scenario, e.backend, episode_tag(e))].append(e)
    md += ["Arms found: " + ", ".join(f"{sc}/{be}/{tag} (N={len(l)})" for (sc, be, tag), l in sorted(by_tag.items())), ""]

    # ---------------- E1 models
    t1 = Table("tab_ext_models", caption="E1 -- Additional models on S1 (spatial) and S3 (resource depletion), full context, base prompt, "
               "$N=10$ per arm ($N=20$/10 for the primary model). Coverage statistics per episode (mean $\\pm$ sample SD, bootstrap 95\\,\\% CI); "
               "`Rejected' = share of placement orders refused by the simulator's validator; `Invalid' = LLM outputs that fell back to \\texttt{noop}; "
               "`Temporal' = decisions whose reasoning comment matches the temporal category. $\\Delta$ = model minus primary model, Welch's $t$, Hedges' $g$; "
               "Holm over the four model-vs-primary tests.",
               columns=["Scenario", "Model"] + ARM_COLS + LLM_COLS + CMP_COLS, colspec="ll" + "r" * (len(ARM_COLS) + len(LLM_COLS) + len(CMP_COLS)), wide=True)
    comps, rows_e1 = [], []
    for sc in ("s1_peaceful", "s3_daynight"):
        ref = core_arm(core, sc, "llm")
        arms = [(PRIMARY_MODEL, ref, None)]
        for (s, be, tag), lst in sorted(by_tag.items()):
            if s == sc and be == "llm" and tag.startswith("e1_"):
                arms.append((lst[0].model, lst, compare(lst, ref)))
        for model, lst, c in arms:
            if c is not None:
                comps.append(c)
            rows_e1.append((sc, model, lst, c))
        # rule reference (descriptive)
        rows_e1.append((sc, "rule (reference)", core_arm(core, sc, "rule"), compare(core_arm(core, sc, "rule"), ref)))
        comps.append(rows_e1[-1][3])
    # Holm family: the model-vs-primary tests only (rule rows are descriptive; give them their own adjusted p = p)
    model_comps = [c for (sc, m, lst, c) in rows_e1 if c is not None and m != "rule (reference)"]
    holm_family(model_comps)
    for sc, model, lst, c in rows_e1:
        if not lst:
            continue
        s = arm_summary(lst)
        llm = lst[0].is_llm
        label = model_short(model) if llm else model
        if c is not None and model == "rule (reference)":
            c["p_holm"] = c["p"]
        t1.rows.append([scenario_label(sc), label + (" (primary)" if model == PRIMARY_MODEL else "")] + arm_cells(s, llm=True) + cmp_cells(c))
        key = f"ext_e1_{sc}_{re.sub(r'[^a-z0-9]+', '_', label.lower())}"
        add_arm_numbers(N, key, s, f"E1 {scenario_label(sc)} {label}")
        add_cmp_numbers(N, key + "_vs_primary", c, f"E1 {scenario_label(sc)} {label} minus primary model")
    t1.note = "Rows `rule (reference)' repeat the core rule arm for orientation; their $p$ is not part of the Holm family."
    res.tables.append(t1)
    md += ["### E1 Multi-model", "", t1.to_markdown(), ""]

    # ---------------- E2 prompt variant
    t2 = Table("tab_ext_prompt", caption="E2 -- Prompt variant: the base prompt (core campaign) versus the temporal-guidance variant (base prompt plus an explicit "
               "temporal-planning paragraph and a five-step decision history), primary model, full context. $\\Delta$ = variant minus base; Holm over the two scenario tests.",
               columns=["Scenario", "Prompt"] + ARM_COLS + LLM_COLS + CMP_COLS, colspec="ll" + "r" * (len(ARM_COLS) + len(LLM_COLS) + len(CMP_COLS)), wide=True)
    rows_e2, comps2 = [], []
    for sc in ("s1_peaceful", "s3_daynight"):
        ref = core_arm(core, sc, "llm")
        v2 = [e for (s, be, tag), lst in by_tag.items() if s == sc and be == "llm" and tag.startswith("e2_") for e in lst]
        c = compare(v2, ref)
        rows_e2 += [(sc, "base prompt (core)", ref, None), (sc, "temporal guidance + history", v2, c)]
        if c:
            comps2.append(c)
    holm_family(comps2)
    for sc, lab, lst, c in rows_e2:
        if not lst:
            continue
        s = arm_summary(lst)
        t2.rows.append([scenario_label(sc), lab] + arm_cells(s) + cmp_cells(c))
        key = f"ext_e2_{sc}_{'v1' if lab.startswith('base') else 'v2'}"
        add_arm_numbers(N, key, s, f"E2 {scenario_label(sc)} prompt {lab}")
        add_cmp_numbers(N, key + "_vs_v1", c, f"E2 {scenario_label(sc)} prompt v2 minus v1")
    res.tables.append(t2)
    md += ["### E2 Prompt variant", "", t2.to_markdown(), ""]

    # ---------------- E3 autonomous layer off
    t3 = Table("tab_ext_autoplace", caption="E3 -- Isolating the intent agent from the autonomous infrastructure layer on S1. "
               "`Autonomy on' = core campaign (the network engineer also places cells on its own); `off' = \\texttt{6g\\_networkbst\\_autoplace=false} "
               "(the engineer only executes agent orders and repairs backhaul). Marginal contribution = agent minus no-op within the same setting "
               "(Welch, 95\\,\\% CI, Hedges' $g$); `On $-$ off' = the same agent with minus without autonomy. Holm over the six tests of this table "
               "(four marginal contributions, two on-vs-off differences of the agents).",
               columns=["Autonomy", "Agent"] + ARM_COLS + ["Marginal (pp)", "95\\,\\% CI", "$p$ / $p_{\\mathrm{Holm}}$", "$g$", "On $-$ off (pp) [CI]"],
               colspec="ll" + "r" * (len(ARM_COLS) + 5), wide=True)
    sc = "s1_peaceful"
    on = {be: core_arm(core, sc, be) for be in ("llm", "rule", "noop")}
    off = {be: [e for (s, b, tag), lst in by_tag.items() if s == sc and b == be and tag.startswith("e3_") for e in lst] for be in ("llm", "rule", "noop")}
    fam = []
    marg = {("on", be): compare(on[be], on["noop"]) for be in ("llm", "rule")}
    marg.update({("off", be): compare(off[be], off["noop"]) for be in ("llm", "rule")})
    onoff = {be: compare(on[be], off[be]) for be in ("llm", "rule", "noop")}
    fam = [c for c in list(marg.values()) + [onoff["llm"], onoff["rule"]] if c is not None]
    holm_family(fam)
    for setting, arms in (("on", on), ("off", off)):
        for be in ("llm", "rule", "noop"):
            lst = arms[be]
            if not lst:
                continue
            s = arm_summary(lst)
            m = marg.get((setting, be))
            oo = onoff.get(be) if setting == "off" else None
            row = [f"autonomy {setting}", backend_label(be)] + arm_cells(s, llm=False)
            row += [f"{m['diff']:+.1f}", fmt_ci(m["ci"]), f"{fmt_p(m['p'])} / {fmt_p(m['p_holm'])}", f"{m['g']:+.2f}"] if m else ["ref.", "", "", ""]
            if oo is not None:
                row += [f"{oo['diff']:+.1f} {fmt_ci(oo['ci'])}, $p$ {fmt_p(oo['p'])}"]
            else:
                row += [""]
            t3.rows.append(row)
            key = f"ext_e3_{setting}_{be}"
            add_arm_numbers(N, key, s, f"E3 S1 autonomy {setting} {be}")
            add_cmp_numbers(N, key + "_marginal", m, f"E3 S1 autonomy {setting}: {be} minus noop")
            if setting == "off":
                add_cmp_numbers(N, f"ext_e3_{be}_on_minus_off", onoff[be], f"E3 S1 {be}: autonomy on minus off")
    t3.note = "The no-op on-vs-off row measures the autonomous layer alone; its $p$ is reported but not Holm-adjusted (it is not one of the six planned tests)."
    res.tables.append(t3)
    md += ["### E3 Autonomous layer", "", t3.to_markdown(), ""]

    # ---------------- E5 path loss
    t5 = Table("tab_ext_pathloss", caption="E5 -- Radio-model sensitivity on S1: path-loss exponent $n$ of the signal model "
               "$s(d)=100\\,(1-(d/R)^{2/n})$ (default $n=3.0$ = core campaign; $n=2.0$ free space, $n=4.0$ dense urban). "
               "LLM (full context) versus rule at each exponent (Welch, Holm over the three LLM-vs-rule tests); the last columns compare each agent "
               "at $n$ with the same agent at $n=3.0$.",
               columns=["$n$", "Agent"] + ARM_COLS + ["LLM $-$ rule (pp)", "95\\,\\% CI", "$p$ / $p_{\\mathrm{Holm}}$", "$g$", "vs $n$=3.0 (pp) [CI], $p$"],
               colspec="ll" + "r" * (len(ARM_COLS) + 5), wide=True)
    arms5 = defaultdict(list)
    for be in ("llm", "rule"):
        for e in core_arm(core, sc, be):
            arms5[(DEFAULT_PATH_LOSS, be)].append(e)
    for (s, be, tag), lst in by_tag.items():
        if s == sc and tag.startswith("e5_"):
            for e in lst:
                arms5[(path_loss(e), be)].append(e)
    exps = sorted({k[0] for k in arms5})
    lr = {n: compare(arms5.get((n, "llm"), []), arms5.get((n, "rule"), [])) for n in exps}
    holm_family([c for c in lr.values() if c is not None])
    for n in exps:
        for be in ("llm", "rule"):
            lst = arms5.get((n, be), [])
            if not lst:
                continue
            s = arm_summary(lst)
            c = lr[n]
            vs3 = compare(lst, arms5.get((DEFAULT_PATH_LOSS, be), [])) if n != DEFAULT_PATH_LOSS else None
            row = [f"{n:.1f}" + (" (core)" if n == DEFAULT_PATH_LOSS else ""), backend_label(be)] + arm_cells(s, llm=False)
            row += ([f"{c['diff']:+.1f}", fmt_ci(c["ci"]), f"{fmt_p(c['p'])} / {fmt_p(c['p_holm'])}", f"{c['g']:+.2f}"] if (c and be == "llm") else ["", "", "", ""])
            row += ([f"{vs3['diff']:+.1f} {fmt_ci(vs3['ci'])}, {fmt_p(vs3['p'])}"] if vs3 else ["ref."])
            t5.rows.append(row)
            key = f"ext_e5_n{str(n).replace('.', 'p')}_{be}"
            add_arm_numbers(N, key, s, f"E5 S1 path-loss n={n} {be}")
            if be == "llm":
                add_cmp_numbers(N, key + "_vs_rule", c, f"E5 S1 n={n}: LLM minus rule")
            add_cmp_numbers(N, key + "_vs_n3", vs3, f"E5 S1 {be}: n={n} minus n=3.0")
    res.tables.append(t5)
    md += ["### E5 Path-loss sensitivity", "", t5.to_markdown(), ""]

    # ---------------- E7 grounding aids (only if such arms exist)
    e7 = {(be, tag): lst for (s, be, tag), lst in by_tag.items() if s == "s1_peaceful" and tag.startswith("e7_")}
    if e7:
        t7 = Table("tab_ext_grounding", caption="E7 -- Grounding aids on S1. `Snap' = a placement order rejected for water or an invalid build position is moved "
                   "to the nearest buildable 512-elmo grid cell within 1500 elmos; `grid' = the agent additionally receives a 32$\\times$32 buildable-terrain map "
                   "in every observation together with instructions to place inside buildable cells. `Snapped' = share of placement orders that were moved. "
                   "$\\Delta$ = arm minus the corresponding core arm (LLM-full or rule) without aids; Holm over the tests of this table.",
                   columns=["Agent", "Aid"] + ARM_COLS + ["Snapped (\\%)"] + CMP_COLS, colspec="ll" + "r" * (len(ARM_COLS) + 1 + len(CMP_COLS)), wide=True)
        rows7 = []
        for be in ("llm", "rule"):
            ref = core_arm(core, "s1_peaceful", be)
            rows7.append((be, "none (core)", ref, None))
            for (b, tag), lst in sorted(e7.items()):
                if b == be:
                    aid = {"e7_snap": "snap", "e7_grid": "grid + snap", "e7_rulesnap": "snap"}.get(tag, tag)
                    rows7.append((be, aid, lst, compare(lst, ref)))
        holm_family([c for (_, _, _, c) in rows7 if c is not None])
        for be, aid, lst, c in rows7:
            if not lst:
                continue
            s7 = arm_summary(lst)
            t7.rows.append([backend_label(be), aid] + arm_cells(s7, llm=False) + [fmt(s7["snapped_pct"], 0)] + cmp_cells(c))
            key = f"ext_e7_{be}_{re.sub(r'[^a-z0-9]+', '_', aid.lower())}"
            add_arm_numbers(N, key, s7, f"E7 S1 {be} aid={aid}")
            N.add(key + "_snapped_pct", s7["snapped_pct"], f"E7 S1 {be} aid={aid}: share of placement orders snapped (%)", n=s7["placements"])
            add_cmp_numbers(N, key + "_vs_core", c, f"E7 S1 {be} aid={aid} minus core arm")
        res.tables.append(t7)
        md += ["### E7 Grounding aids", "", t7.to_markdown(), ""]

    # ---------------- E8 decision support (candidate positions, feedback, greedy baseline)
    e8 = {(sc_, be, tag): lst for (sc_, be, tag), lst in by_tag.items() if tag.startswith("e8_")}
    if e8:
        t8 = Table("tab_ext_candidates", caption="E8 -- Decision support. `Candidates' = the observation lists up to six candidate positions (buildable and unoccupied grid-cell centres within backhaul reach of the live network, outside threat zones) ranked by "
                   "the disconnected units within macro range and the agent may answer with a candidate id; `+ feedback' = the validation outcome and coverage "
                   "change of the previous decision are also reported; `greedy' = deterministic baseline that always takes the first candidate. "
                   "$\\Delta$ = arm minus the core LLM-full arm of the same scenario; Holm over the tests of this table.",
                   columns=["Scenario", "Agent"] + ARM_COLS + ["Invalid (\\%)", "Isol.\\ cells"] + CMP_COLS, colspec="ll" + "r" * (len(ARM_COLS) + 2 + len(CMP_COLS)), wide=True)
        rows8 = []
        for sc_ in ("s1_peaceful", "s3_daynight"):
            ref = core_arm(core, sc_, "llm")
            if not ref or not any(k[0] == sc_ for k in e8):
                continue
            rows8.append((sc_, "LLM-full (core)", ref, None))
            for (s_, be, tag), lst in sorted(e8.items()):
                if s_ != sc_:
                    continue
                name = {"e8_cand": "LLM-full + candidates", "e8_candfb": "LLM-full + candidates + feedback", "e8_greedy": "greedy-candidate"}.get(tag, tag)
                rows8.append((sc_, name, lst, compare(lst, ref)))
            rows8.append((sc_, "rule (core)", core_arm(core, sc_, "rule"), None))
            if core_arm(core, sc_, "noop"):
                rows8.append((sc_, "noop (core)", core_arm(core, sc_, "noop"), None))
        holm_family([c for (_, _, _, c) in rows8 if c is not None])
        # pairwise comparisons among the decision-support arms and against the no-op baseline (macros only)
        for sc_ in ("s1_peaceful", "s3_daynight"):
            arms8 = {tag: lst for (s_, be, tag), lst in e8.items() if s_ == sc_}
            pairs = [("e8_cand", "e8_greedy", "greedy"), ("e8_cand", "e8_candfb", "feedback"), ("e8_greedy", "e8_candfb", "feedback")]
            for a_, b_, lab in pairs:
                if a_ in arms8 and b_ in arms8:
                    add_cmp_numbers(N, f"ext_e8_{sc_}_{a_}_vs_{lab}", compare(arms8[a_], arms8[b_]), f"E8 {scenario_label(sc_)} {a_} minus {b_}")
                    if lab == "greedy":   # equivalence of the LLM and the greedy agent on the same candidates (TOST, +/-5 pp)
                        from stats_report import tost
                        N.add(f"ext_e8_{sc_}_{a_}_vs_{lab}_p_tost", fmt_p(tost([e.avg_coverage() for e in arms8[a_]], [e.avg_coverage() for e in arms8[b_]], 5.0)),
                              f"E8 {scenario_label(sc_)} {a_} vs {b_}: TOST p at +/-5 pp")
            for a_ in ("e8_cand", "e8_greedy", "e8_candfb"):
                for ref_be in ("noop", "rule"):
                    if a_ in arms8 and core_arm(core, sc_, ref_be):
                        add_cmp_numbers(N, f"ext_e8_{sc_}_{a_}_vs_{ref_be}", compare(arms8[a_], core_arm(core, sc_, ref_be)), f"E8 {scenario_label(sc_)} {a_} minus core {ref_be}")
        for sc_, name, lst, c in rows8:
            if not lst:
                continue
            s8 = arm_summary(lst)
            t8.rows.append([scenario_label(sc_), name] + arm_cells(s8, llm=False) + [fmt(s8["invalid_pct"]) if lst[0].is_llm else "--", fmt(s8["isolated_mean"])] + cmp_cells(c))
            key = f"ext_e8_{sc_}_{re.sub(r'[^a-z0-9]+', '_', name.lower())}"
            add_arm_numbers(N, key, s8, f"E8 {scenario_label(sc_)} {name}")
            add_cmp_numbers(N, key + "_vs_core", c, f"E8 {scenario_label(sc_)} {name} minus core LLM-full")
        res.tables.append(t8)
        md += ["### E8 Decision support", "", t8.to_markdown(), ""]

    # ---------------- E9 inference configuration (thinking mode / reasoning effort)
    e9 = {(sc_, be, tag): lst for (sc_, be, tag), lst in by_tag.items() if tag.startswith("e9_")}
    if e9:
        t9 = Table("tab_ext_thinking", caption="E9 -- Inference configuration: the primary model with its thinking mode enabled and the 120B model at "
                   "high reasoning effort, against the same models with thinking disabled / low effort (core campaign and E1). `Lat.' = median decision latency. "
                   "$\\Delta$ = arm minus its non-thinking counterpart; Holm over the tests of this table.",
                   columns=["Scenario", "Model / setting"] + ARM_COLS + ["Invalid (\\%)", "Lat.\\ (s)", "Isol.\\ cells"] + CMP_COLS,
                   colspec="ll" + "r" * (len(ARM_COLS) + 3 + len(CMP_COLS)), wide=True)
        rows9 = []
        for (s_, be, tag), lst in sorted(e9.items()):
            model = lst[0].model or ""
            if "gpt-oss" in model:
                ref = [e for (s2, b2, t2), l2 in by_tag.items() if s2 == s_ and t2 == "e1_gptoss" for e in l2]
                refname, name = "gpt-oss-120b, low effort (E1)", "gpt-oss-120b, high effort"
            else:
                ref = core_arm(core, s_, "llm")
                refname, name = "Qwen3.8-27B, thinking off (core)", "Qwen3.8-27B, thinking on"
            rows9 += [(s_, refname, ref, None), (s_, name, lst, compare(lst, ref))]
        holm_family([c for (_, _, _, c) in rows9 if c is not None])
        for s_, name, lst, c in rows9:
            if not lst:
                continue
            s9 = arm_summary(lst)
            t9.rows.append([scenario_label(s_), name] + arm_cells(s9, llm=False) + [fmt(s9["invalid_pct"]), fmt(s9["latency_median"]), fmt(s9["isolated_mean"])] + cmp_cells(c))
            key = f"ext_e9_{s_}_{re.sub(r'[^a-z0-9]+', '_', name.lower())}"
            add_arm_numbers(N, key, s9, f"E9 {scenario_label(s_)} {name}")
            add_cmp_numbers(N, key + "_vs_ref", c, f"E9 {scenario_label(s_)} {name} minus non-thinking counterpart")
        res.tables.append(t9)
        md += ["### E9 Inference configuration", "", t9.to_markdown(), ""]

    # ---------------- inventory of the extension campaign
    tinv = Table("tab_ext_inventory", caption="Extension campaign inventory: valid episodes per arm (seeds 20001--20620, frozen code).",
                 columns=["Experiment", "Scenario", "Agent", "Model", "Prompt", "Autonomy", "$n$", "Valid $N$"], colspec="llllllrr", wide=True)
    for (s, be, tag), lst in sorted(by_tag.items(), key=lambda kv: (kv[0][2], scenario_sort_key(kv[0][0]), backend_sort_key(kv[0][1]))):
        e0 = lst[0]
        agent_lbl = backend_label(be) + {"e8_cand": " + candidates", "e8_candfb": " + candidates + feedback", "e9_think": ", thinking on", "e9_gptoss_high": ", high effort",
                                         "e7_snap": " + snap", "e7_grid": " + grid + snap", "e7_rulesnap": " + snap"}.get(tag, "")
        tinv.rows.append([tag.split("_")[0].upper(), scenario_label(s), agent_lbl, model_short(e0.model) if e0.is_llm else "-",
                          (e0.prompt_version or "-") + (f"+hist {e0.header.get('history')}" if e0.header.get("history") else ""),
                          "on" if autoplace(e0) else "off", f"{path_loss(e0):.1f}", len(lst)])
        N.add(f"ext_inv_{tag}_{s}_{be}_n", len(lst), f"valid extension episodes {tag} {s} {be}", nd=0)
    N.add("ext_inv_total", len(ext), "valid extension episodes (all)", nd=0)
    res.tables.append(tinv)
    md += ["### Inventory", "", tinv.to_markdown(), ""]

    res.numbers = N
    res.markdown = "\n".join(md)
    res.extra = dict(by_tag=by_tag, on=on, off=off, arms5=arms5, rows_e1=rows_e1, rows_e2=rows_e2)
    return res


# ----------------------------------------------------------------------------- figures
def make_figures(res: Result, core: list, out_dir: Path) -> list:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    import make_figures as mf
    mf.setup_style()
    out_dir = Path(out_dir)
    written = []

    # fig_ext_models: dot + CI per model for S1 and S3 (avg coverage), rule as reference line
    fig, axes = plt.subplots(1, 2, figsize=(mf.FULL_W, mf.H), sharey=True)
    for ax, sc in zip(axes, ("s1_peaceful", "s3_daynight")):
        rows = [(m, lst) for (s, m, lst, c) in res.extra["rows_e1"] if s == sc and lst]
        labels, means, lo, hi, ns = [], [], [], [], []
        for m, lst in rows:
            s = arm_summary(lst)
            short = {"Qwen3.8-27B": "Qwen3.8\n27B", "FastContext-4B": "FastContext\n4B", "gpt-oss-120b": "gpt-oss\n120b"}
            lab = model_short(m) if lst[0].is_llm else "rule"
            labels.append(short.get(lab, lab) + f"\n(N={s['n']})")
            means.append(s["avg_mean"]); lo.append(s["avg_mean"] - s["avg_ci"][0]); hi.append(s["avg_ci"][1] - s["avg_mean"]); ns.append(s["n"])
        x = np.arange(len(labels))
        cols = [mf.colour("llm") if not l.startswith("rule") else mf.colour("rule") for l in labels]
        ax.bar(x, means, color=cols, edgecolor=mf.SURFACE, yerr=[lo, hi], error_kw=dict(ecolor=mf.INK, elinewidth=0.8, capsize=2), width=0.6)
        for xi, lst in zip(x, [l for _, l in rows]):
            ys = [e.avg_coverage() for e in lst]
            ax.scatter(np.full(len(ys), xi) + np.random.default_rng(1).uniform(-0.15, 0.15, len(ys)), ys, s=9, color=mf.INK, alpha=0.45, zorder=3, edgecolor="none")
        ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=8)
        ax.set_title(scenario_label(sc), loc="left", color=mf.INK)
        ax.grid(False, axis="x")
        ax.set_ylim(0, 100)
    axes[0].set_ylabel("Average coverage per episode (%)")
    fig.tight_layout()
    written += mf.save(fig, out_dir, "fig_ext_models")

    # fig_ext_autoplace: coverage over epochs, autonomy on (solid) vs off (dashed), per agent
    fig, axes = plt.subplots(1, 2, figsize=(mf.FULL_W, mf.H), sharey=True)
    for ax, (setting, arms) in zip(axes, (("Autonomous layer on", res.extra["on"]), ("Autonomous layer off", res.extra["off"]))):
        for be in ("llm", "rule", "noop"):
            lst = arms.get(be, [])
            s = mf.epoch_series([e.coverage_series() for e in lst])
            if s is not None:
                mf.draw_series(ax, be, s)
        mf.threshold_line(ax, 80, "80 % intent threshold")
        ax.set_ylim(0, 105); ax.set_xlim(left=1)
        ax.set_xlabel("Decision epoch"); ax.set_title(setting, loc="left", color=mf.INK)
    axes[0].set_ylabel("Coverage (% of mobile units)")
    mf.shared_legend_below(fig, axes[0], ncol=4)
    written += mf.save(fig, out_dir, "fig_ext_autoplace")

    # fig_ext_pathloss: LLM vs rule mean coverage against path-loss exponent
    fig, ax = plt.subplots(figsize=(mf.SINGLE_W, mf.H))
    arms5 = res.extra["arms5"]
    exps = sorted({k[0] for k in arms5})
    for be in ("llm", "rule"):
        xs, ys, lo, hi, n = [], [], [], [], []
        for e in exps:
            lst = arms5.get((e, be), [])
            if len(lst) < 2:
                continue
            s = arm_summary(lst)
            xs.append(e); ys.append(s["avg_mean"]); lo.append(s["avg_mean"] - s["avg_ci"][0]); hi.append(s["avg_ci"][1] - s["avg_mean"]); n.append(s["n"])
        if xs:
            ax.errorbar(xs, ys, yerr=[lo, hi], color=mf.colour(be), marker=mf.marker(be), capsize=2, linewidth=1.5,
                        markeredgecolor=mf.SURFACE, label=f"{backend_label(be)} (N={'/'.join(map(str, n))})")
    ax.set_xlabel("Path-loss exponent $n$"); ax.set_ylabel("Average coverage per episode (%)")
    ax.set_xticks(exps); ax.set_ylim(0, 100)
    mf.legend_below(ax, ncol=2)
    written += mf.save(fig, out_dir, "fig_ext_pathloss")
    return written


# ----------------------------------------------------------------------------- CLI
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ext-dir", default=str(EXT_DIR))
    ap.add_argument("--out-dir", default=str(DEFAULT_TABLES_DIR))
    ap.add_argument("--figures-dir", default=str(DEFAULT_FIGURES_DIR))
    ap.add_argument("--min-decisions", type=int, default=None)
    ap.add_argument("--no-figures", action="store_true")
    a = ap.parse_args()
    ext, core = load_ext(Path(a.ext_dir), a.min_decisions), load_core(a.min_decisions)
    print(f"{len(ext)} extension episodes, {len(core)} core episodes")
    res = analyze(ext, core)
    print(res.markdown)
    out = Path(a.out_dir)
    for t in res.tables:
        write_table(t, out)
    write_text(out / "extensions.md", res.markdown)
    res.numbers.to_json(out / "numbers_ext.json")
    res.numbers.to_macros(out / "macros_ext.tex")
    if not a.no_figures:
        make_figures(res, core, Path(a.figures_dir))
    print(f"written to {out}")


if __name__ == "__main__":
    main()
