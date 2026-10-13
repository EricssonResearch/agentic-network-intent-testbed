#!/usr/bin/env python3
"""
One-figure / one-table summary of the whole campaign (core + extension experiments):

  fig_forest.{pdf,png}   every pre-specified and extension comparison as a difference of mean average coverage (pp)
                         with its 95 % CI, grouped by research question; filled markers = significant after Holm
                         correction within the comparison's family, hollow = not.
  tab_summary_arms.tex   one table with every arm of every experiment: N, average coverage (mean +- SD, 95 % CI),
                         final coverage, cells deployed, share of epochs >= 80 %, share of placement orders rejected.

The comparisons and families are exactly those of stats_report.COMPARISONS (core) and extensions.py (E1/E2/E3/E5/E7);
nothing is recomputed differently, so the summary is consistent with the detailed tables.

Usage: summary.py [--tables-dir DIR] [--figures-dir DIR] [--min-decisions K]
"""
from __future__ import annotations
import argparse, re
from collections import defaultdict
from pathlib import Path

from load_runs import group
from stats_report import comparison_table
from common import (Table, Numbers, fmt, fmt_pm, fmt_ci, fmt_p, backend_label, scenario_label, scenario_sort_key,
                    backend_sort_key, write_table, DEFAULT_TABLES_DIR, DEFAULT_FIGURES_DIR)
import extensions as ext

FAMILY_ORDER = ["Core campaign (S1--S4)", "E3 autonomous layer (S1)", "E1 additional models", "E2 prompt variant", "E5 path-loss exponent (S1)", "E7 grounding aids (S1)", "E8 decision support", "E9 thinking mode"]


def core_comparisons(core: list) -> list:
    rows = comparison_table(group(core))
    out = []
    for r in rows:
        lab = r["label"].replace("LLM", "LLM-full").replace("no-spatial", "LLM-nospatial").replace("minimal", "LLM-minimal")
        out.append(dict(family=FAMILY_ORDER[0], label=f"{lab} ({r['n_a']}/{r['n_b']})", diff=r["diff"], ci=r["ci"], p=r["p"], p_holm=r["p_holm"]))
    return out


def ext_comparisons(ext_eps: list, core: list) -> list:
    by_tag = defaultdict(list)
    for e in ext_eps:
        by_tag[(e.scenario, e.backend, ext.episode_tag(e))].append(e)
    out = []

    def add(fam, label, c):
        if c is not None:
            out.append(dict(family=fam, label=f"{label} ({c['n_a']}/{c['n_b']})", diff=c["diff"], ci=c["ci"], p=c["p"], c=c))

    # E3: marginal contributions (agent - noop) with and without autonomy, and on - off per agent
    sc = "s1_peaceful"
    on = {be: ext.core_arm(core, sc, be) for be in ("llm", "rule", "noop")}
    off = {be: [e for (s, b, tag), lst in by_tag.items() if s == sc and b == be and tag.startswith("e3_") for e in lst] for be in ("llm", "rule", "noop")}
    fam3 = []
    for setting, arms in (("autonomy on", on), ("autonomy off", off)):
        for be in ("llm", "rule"):
            c = ext.compare(arms[be], arms["noop"])
            if c: fam3.append(c); add(FAMILY_ORDER[1], f"{backend_label(be)} $-$ noop, {setting}", c)
    for be in ("llm", "rule"):
        c = ext.compare(on[be], off[be])
        if c: fam3.append(c); add(FAMILY_ORDER[1], f"{backend_label(be)}: autonomy on $-$ off", c)
    ext.holm_family(fam3)
    # E1: models vs primary
    fam1 = []
    for s in ("s1_peaceful", "s3_daynight"):
        ref = ext.core_arm(core, s, "llm")
        for (sc_, be, tag), lst in sorted(by_tag.items()):
            if sc_ == s and be == "llm" and tag.startswith("e1_"):
                c = ext.compare(lst, ref)
                if c: fam1.append(c); add(FAMILY_ORDER[2], f"{scenario_label(s).split()[0]}: {ext.model_short(lst[0].model)} $-$ primary", c)
    ext.holm_family(fam1)
    # E2
    fam2 = []
    for s in ("s1_peaceful", "s3_daynight"):
        ref = ext.core_arm(core, s, "llm")
        v2 = [e for (sc_, be, tag), lst in by_tag.items() if sc_ == s and be == "llm" and tag.startswith("e2_") for e in lst]
        c = ext.compare(v2, ref)
        if c: fam2.append(c); add(FAMILY_ORDER[3], f"{scenario_label(s).split()[0]}: temporal-guidance $-$ base prompt", c)
    ext.holm_family(fam2)
    # E5
    arms5 = defaultdict(list)
    for be in ("llm", "rule"):
        for e in ext.core_arm(core, sc, be): arms5[(ext.DEFAULT_PATH_LOSS, be)].append(e)
    for (s, be, tag), lst in by_tag.items():
        if s == sc and tag.startswith("e5_"):
            for e in lst: arms5[(ext.path_loss(e), be)].append(e)
    fam5 = []
    for n in sorted({k[0] for k in arms5}):
        c = ext.compare(arms5.get((n, "llm"), []), arms5.get((n, "rule"), []))
        if c: fam5.append(c); add(FAMILY_ORDER[4], f"LLM-full $-$ rule at $n$={n:g}", c)
    ext.holm_family(fam5)
    # E7
    fam7 = []
    for (s, be, tag), lst in sorted(by_tag.items()):
        if s == sc and tag.startswith("e7_"):
            ref = ext.core_arm(core, sc, be)
            aid = {"e7_snap": "snap", "e7_grid": "grid + snap", "e7_rulesnap": "snap"}.get(tag, tag)
            c = ext.compare(lst, ref)
            if c: fam7.append(c); add(FAMILY_ORDER[5], f"{backend_label(be)} + {aid} $-$ {backend_label(be)}", c)
    ext.holm_family(fam7)
    # E8
    fam8 = []
    for (s, be, tag), lst in sorted(by_tag.items()):
        if tag.startswith("e8_"):
            ref = ext.core_arm(core, s, "llm")
            name = {"e8_cand": "LLM-full + candidates", "e8_candfb": "LLM-full + candidates + feedback", "e8_greedy": "greedy-candidate"}.get(tag, tag)
            c = ext.compare(lst, ref)
            if c: fam8.append(c); add(FAMILY_ORDER[6], f"{scenario_label(s).split()[0]}: {name} $-$ LLM-full", c)
    ext.holm_family(fam8)
    # E9
    fam9 = []
    for (s, be, tag), lst in sorted(by_tag.items()):
        if tag.startswith("e9_"):
            if "gpt-oss" in (lst[0].model or ""):
                ref = [e for (s2, b2, t2), l2 in by_tag.items() if s2 == s and t2 == "e1_gptoss" for e in l2]; name = "gpt-oss-120b high $-$ low effort"
            else:
                ref = ext.core_arm(core, s, "llm"); name = "Qwen3.8-27B thinking on $-$ off"
            c = ext.compare(lst, ref)
            if c: fam9.append(c); add(FAMILY_ORDER[7], f"{scenario_label(s).split()[0]}: {name}", c)
    ext.holm_family(fam9)
    for r in out:
        r["p_holm"] = r["c"].get("p_holm", r["p"])
    return out


def fig_forest(comps: list, out_dir: Path) -> list:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import make_figures as mf
    mf.setup_style()
    fams = [f for f in FAMILY_ORDER if any(c["family"] == f for c in comps)]
    rows = []                       # (y, comp or None for header)
    y = 0
    for f in fams:
        rows.append((y, None, f)); y += 1
        for c in comps:
            if c["family"] == f:
                rows.append((y, c, None)); y += 1
        y += 0.4
    height = 0.24 * y + 1.0
    fig, ax = plt.subplots(figsize=(mf.FULL_W, height))
    colours = {FAMILY_ORDER[0]: mf.colour("llm"), FAMILY_ORDER[1]: mf.colour("noop"), FAMILY_ORDER[2]: "#7b3fa0",
               FAMILY_ORDER[3]: mf.colour("llm_minimal"), FAMILY_ORDER[4]: mf.colour("rule"), FAMILY_ORDER[5]: mf.colour("llm_nospatial"),
               FAMILY_ORDER[6]: "#0b6e8a", FAMILY_ORDER[7]: "#8a4b0b"}
    labels, ys = [], []
    for yy, c, header in rows:
        if header:
            ax.text(-0.01, -yy, header, transform=ax.get_yaxis_transform(), ha="right", va="center", fontsize=9, fontweight="bold", color=mf.INK)
            continue
        col = colours.get(c["family"], mf.FALLBACK)
        sig = c["p_holm"] < 0.05
        ax.errorbar(c["diff"], -yy, xerr=[[c["diff"] - c["ci"][0]], [c["ci"][1] - c["diff"]]], fmt="o", color=col,
                    markerfacecolor=col if sig else mf.SURFACE, markeredgecolor=col, markersize=6, capsize=2.5, elinewidth=1.4, zorder=3)
        labels.append(c["label"]); ys.append(-yy)
    ax.set_yticks(ys); ax.set_yticklabels(labels, fontsize=8)
    ax.axvline(0, color=mf.MUTED, linestyle="--", linewidth=0.9, zorder=1)
    ax.set_xlabel("Difference in mean average coverage (pp) with 95 % CI")
    ax.grid(True, axis="x"); ax.grid(False, axis="y")
    ax.set_ylim(-y + 0.2, 0.8)
    ax.tick_params(axis="y", length=0)
    from matplotlib.lines import Line2D
    handles = [Line2D([0], [0], marker="o", color=mf.INK, markerfacecolor=mf.INK, linestyle="", markersize=6, label="significant after Holm correction ($p<0.05$)"),
               Line2D([0], [0], marker="o", color=mf.INK, markerfacecolor=mf.SURFACE, linestyle="", markersize=6, label="not significant")]
    ax.legend(handles=handles, loc="upper right", bbox_to_anchor=(1.0, 1.0), ncol=1, frameon=True, framealpha=0.95, edgecolor=mf.GRID, fontsize=8)
    fig.tight_layout()
    return mf.save(fig, out_dir, "fig_forest")


def tab_summary_arms(core: list, ext_eps: list) -> Table:
    t = Table("tab_summary_arms", caption="All arms of the campaign in one table. Per episode: average coverage (mean $\\pm$ sample SD, bootstrap 95\\,\\% CI of the mean), "
              "final coverage, cells deployed at episode end, share of epochs with coverage $\\geq 80\\,\\%$, share of placement orders rejected by the validator "
              "(`snapped' orders count as executed). Core arms use the base prompt and the primary model; extension arms differ in the stated respect only.",
              columns=["Experiment", "Scenario", "Arm", "$N$", "Avg.\\ cov.\\ (\\%)", "95\\,\\% CI", "Final (\\%)", "Cells", "Ep.\\ $\\geq$80\\,\\% (\\%)", "Rej.\\ (\\%)"],
              colspec="lllrrrrrrr", wide=True)
    def row(exp, sc, arm, lst):
        s = ext.arm_summary(lst)
        t.rows.append([exp, scenario_label(sc), arm, s["n"], fmt_pm(s["avg_mean"], s["avg_sd"]), fmt_ci(s["avg_ci"]), fmt_pm(s["final_mean"], s["final_sd"], 0),
                       fmt(s["bs_mean"]), fmt(s["f80_mean"]), fmt(s["rejected_pct"], 0) if s["rejected_pct"] is not None else "--"])
    for (sc, be), lst in sorted(group(core).items(), key=lambda kv: scenario_sort_key(kv[0][0]) + backend_sort_key(kv[0][1])):
        row("core", sc, backend_label(be), lst)
    by_tag = defaultdict(list)
    for e in ext_eps:
        by_tag[(e.scenario, e.backend, ext.episode_tag(e))].append(e)
    names = {"e1_gptoss": "LLM-full, gpt-oss-120b", "e1_fastctx4b": "LLM-full, FastContext-4B", "e2_v2": "LLM-full, temporal-guidance prompt",
             "e3_noauto": "{be}, autonomy off", "e5_pl2": "{be}, path loss $n$=2", "e5_pl4": "{be}, path loss $n$=4",
             "e7_snap": "LLM-full + snap", "e7_grid": "LLM-full + grid + snap", "e7_rulesnap": "rule + snap",
             "e8_cand": "LLM-full + candidates", "e8_candfb": "LLM-full + candidates + feedback", "e8_greedy": "greedy-candidate",
             "e9_think": "LLM-full, thinking on", "e9_gptoss_high": "LLM-full, gpt-oss-120b high effort"}
    for (sc, be, tag), lst in sorted(by_tag.items(), key=lambda kv: (kv[0][2][:2], scenario_sort_key(kv[0][0]), backend_sort_key(kv[0][1]))):
        row(tag.split("_")[0].upper(), sc, names.get(tag, tag).format(be=backend_label(be)), lst)
    return t


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--tables-dir", default=str(DEFAULT_TABLES_DIR))
    ap.add_argument("--figures-dir", default=str(DEFAULT_FIGURES_DIR))
    ap.add_argument("--min-decisions", type=int, default=None)
    ap.add_argument("--ext-dir", default=str(ext.EXT_DIR))
    a = ap.parse_args()
    core = ext.load_core(a.min_decisions)
    ext_eps = ext.load_ext(Path(a.ext_dir), a.min_decisions)
    comps = core_comparisons(core) + ext_comparisons(ext_eps, core)
    fig_forest(comps, Path(a.figures_dir))
    t = tab_summary_arms(core, ext_eps)
    write_table(t, Path(a.tables_dir))
    print(t.to_markdown())
    print(f"{len(comps)} comparisons in the forest plot; table -> {a.tables_dir}/tab_summary_arms.tex")


if __name__ == "__main__":
    main()
