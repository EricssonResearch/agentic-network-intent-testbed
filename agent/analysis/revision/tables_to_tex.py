#!/usr/bin/env python3
"""
Driver: run stats_report + regret + reasoning + latency_invalid + threshold_metrics + monotonicity on one campaign
and write everything the manuscript needs, so that no number is transcribed by hand:

  paper_major_revision/tables/<name>.tex   booktabs tables (\\caption stubs + \\label{tab:<name>}); stats_report's
                                           tab_conditions/tab_comparisons/tab_equivalence are bare tabulars (as before)
  paper_major_revision/tables/numbers.json every reported number: value, definition, N, unit, source module
  paper_major_revision/tables/macros.tex   \\newcommand{\\numXxx}{...} for inline use (\\input{tables/macros.tex})
  paper_major_revision/tables/REPORT.md    human-readable summary (all module markdown + inventory + caveats)
  paper_major_revision/tables/aux/         CSV side products (regret events, annotation sample, exact-regret rows)

Usage: tables_to_tex.py --campaign v1|v2|all [--min-decisions K] [--tables-dir DIR] [--mapping branches.csv]
                        [--figures] [--figures-dir DIR]
"""
from __future__ import annotations
import argparse, datetime, json, statistics, subprocess, sys
from pathlib import Path

from load_runs import load_all, group, MIN_DECISIONS
import stats_report
from common import (Table, Numbers, add_common_args, load_campaign, campaign_note, fmt, fmt_p, fmt_ci, backend_label,
                    scenario_label, group_sort_key, write_table, write_text, DEFAULT_TABLES_DIR, DEFAULT_FIGURES_DIR, REPO)
import regret, reasoning, latency_invalid, threshold_metrics, monotonicity, extensions

CAVEATS_V1 = [
    "v1 (June 2026) data carry the audited defects: one-epoch action lag for every agent (A), mixed simulator versions (B), ~1x speed (C); "
    "relative comparisons remain meaningful but absolute numbers must be labelled 'original campaign'.",
    "v1 latency is reconstructed (see latency_invalid.py docstring); v1 has no parse status, no disconnected_positions, no mobile_units.",
    "geometric-v2 regret on v1 data falls back to the legacy 30 % assumption (column 'Pos. avail.' = 0 %).",
]


def inventory_table(campaign: str, min_decisions) -> tuple:
    eps_all = load_all(campaign in ("v1", "all"), campaign in ("v2", "all"), only_valid=False, min_decisions=min_decisions)
    t = Table("tab_inventory", caption="Episode inventory per condition: valid episodes enter every statistic; discarded episodes are listed with the reason.",
              columns=["Scenario", "Agent", "Model", "Prot.", "Code version(s)", "Valid", "Discarded (reason)"], colspec="lllrlrl", wide=True)
    N = Numbers()
    for (sc, be), lst in sorted(group(eps_all).items(), key=lambda kv: group_sort_key(kv[0])):
        val = [e for e in lst if e.valid]
        inv = [e for e in lst if not e.valid]
        reasons = {}
        for e in inv:
            reasons[e.invalid_reason] = reasons.get(e.invalid_reason, 0) + 1
        models = sorted({(e.model or "-").split("/")[-1] for e in lst})
        t.rows.append([scenario_label(sc), backend_label(be), ", ".join(models), ", ".join(str(p) for p in sorted({e.protocol for e in lst})),
                       ", ".join(sorted({e.code_version for e in val})) or "-", len(val),
                       ("; ".join(f"{n}x {r}" for r, n in sorted(reasons.items())) if inv else "-")])
        N.add(f"inv_{sc}_{be}_valid", len(val), "valid episodes", nd=0)
        N.add(f"inv_{sc}_{be}_discarded", len(inv), "discarded episodes", nd=0)
    N.add("inv_total_valid", sum(1 for e in eps_all if e.valid and e.backend != "replay"), "valid episodes (all conditions, replay excluded)", nd=0)
    N.add("inv_total_discarded", sum(1 for e in eps_all if not e.valid), "discarded episodes (all conditions)", nd=0)
    return t, N, eps_all


def stats_numbers(cond: list, comp: list, eq: list) -> Numbers:
    N = Numbers()
    for r in cond:
        k = f"cond_{r['scenario']}_{r['backend']}"
        N.add(k + "_n", r["n"], "episodes", nd=0)
        N.add(k + "_avg_mean", r["avg_mean"], "mean of per-episode average coverage (%)", n=r["n"])
        N.add(k + "_avg_sd", r["avg_sd"], "sample SD of per-episode average coverage (%)", n=r["n"])
        N.add(k + "_avg_ci_lo", r["avg_ci"][0], "bootstrap 95% CI lower, average coverage (%)", n=r["n"])
        N.add(k + "_avg_ci_hi", r["avg_ci"][1], "bootstrap 95% CI upper, average coverage (%)", n=r["n"])
        N.add(k + "_final_mean", r["final_mean"], "mean final coverage (%)", n=r["n"])
        N.add(k + "_final_sd", r["final_sd"], "sample SD final coverage (%)", n=r["n"])
        N.add(k + "_bs_mean", r["bs_mean"], "mean BS deployed", n=r["n"])
        N.add(k + "_bs_sd", r["bs_sd"], "sample SD BS deployed", n=r["n"])
        N.add(k + "_bs_median", r["bs_median"], "median BS deployed", n=r["n"], nd=0)
    for r in comp:
        k = "cmp_" + r["label"].lower().replace(" ", "_").replace("-", "_")
        N.add(k + "_n", f"{r['n_a']}/{r['n_b']}", "episodes A/B")
        N.add(k + "_diff", r["diff"], "difference of means A-B (pp)")
        N.add(k + "_t", r["t"], "Welch t", nd=2)
        N.add(k + "_df", r["df"], "Welch df")
        N.add(k + "_p", fmt_p(r["p"]), "Welch p")
        N.add(k + "_p_holm", fmt_p(r["p_holm"]), "Holm-adjusted p (family = stats_report.COMPARISONS)")
        N.add(k + "_g", r["g"], "Hedges g", nd=2)
        N.add(k + "_ci_lo", r["ci"][0], "95% CI lower of A-B (pp)")
        N.add(k + "_ci_hi", r["ci"][1], "95% CI upper of A-B (pp)")
    for r in eq:
        k = "eq_" + r["label"].lower().replace(" ", "_").replace("-", "_")
        N.add(k + "_p_tost", fmt_p(r["p_tost"]), f"TOST p at +/-{r['delta']:g} pp")
    for n in (5, 10, 20, 30):
        N.add(f"power_6pp_sd9_n{n}", stats_report.power_two_sample(6, 9, n), f"power to detect 6 pp at SD 9 with n={n}/arm (alpha 0.05)", nd=2)
    return N


def main():
    ap = add_common_args(argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter))
    ap.add_argument("--tables-dir", default=str(DEFAULT_TABLES_DIR))
    ap.add_argument("--figures-dir", default=str(DEFAULT_FIGURES_DIR))
    ap.add_argument("--figures", action="store_true", help="also run make_figures.py")
    ap.add_argument("--mapping", default=None, help="regret re-simulation mapping CSV/JSON")
    ap.add_argument("--match", default=None, help="reasoning keyword matching mode override (substring|word)")
    ap.add_argument("--ext-dir", default=str(extensions.EXT_DIR), help="Tier-2 extension campaign results (E1/E2/E3/E5); skipped if absent")
    ap.add_argument("--kappa", default=None, help="filled-in reasoning annotation CSV -> tab_reasoning_kappa.tex")
    a = ap.parse_args()
    tables_dir, aux = Path(a.tables_dir), Path(a.tables_dir) / "aux"
    tables_dir.mkdir(parents=True, exist_ok=True)
    aux.mkdir(parents=True, exist_ok=True)
    eps = load_campaign(a)
    numbers, written, report = Numbers(), [], []
    stamp = datetime.datetime.now().isoformat(timespec="seconds")
    report += [f"# Revision analysis report", "", f"Generated {stamp} by tables_to_tex.py; {campaign_note(a, eps)}.", "",
               "Every table below is also written as LaTeX to this directory; every number is in numbers.json and macros.tex.", ""]

    # 0. inventory
    t_inv, n_inv, eps_all = inventory_table(a.campaign, a.min_decisions)
    written.append(write_table(t_inv, tables_dir))
    numbers.update(n_inv)
    report += ["## Inventory", "", t_inv.to_markdown(), ""]

    # 1. stats_report
    groups = group(eps)
    cond, comp, eq = stats_report.condition_table(groups), stats_report.comparison_table(groups), stats_report.equivalence_table(groups)
    stats_report.to_tex(cond, comp, eq, tables_dir)
    written += [tables_dir / "tab_conditions.tex", tables_dir / "tab_comparisons.tex", tables_dir / "tab_equivalence.tex"]
    numbers.update(stats_numbers(cond, comp, eq))
    notes = [campaign_note(a, eps), "power to detect 6 pp at SD 9: " + ", ".join(f"n={n}: {stats_report.power_two_sample(6, 9, n):.2f}" for n in (5, 10, 20, 30))]
    report += ["# Main statistics (stats_report.py)", "", stats_report.to_markdown(cond, comp, eq, notes), ""]
    if not comp:
        report += ["*No pairwise comparison in stats_report.COMPARISONS has N >= 2 in both arms for this campaign.*", ""]

    # 2-6. modules
    mapping = regret.load_mapping(a.mapping) if a.mapping else None
    res_regret = regret.analyze(eps, mapping, min_decisions=a.min_decisions)
    regret.write_csv(aux / "regret_events.csv", res_regret.extra["events"])
    if res_regret.extra["exact_rows"]:
        regret.write_csv(aux / "regret_exact.csv", res_regret.extra["exact_rows"])
    res_reason = reasoning.analyze(eps, match=a.match)
    sheet, auto = reasoning.write_sample(res_reason.extra["sample"], res_reason.extra["categories"], aux, "reasoning_sample50")
    res_lat = latency_invalid.analyze(eps)
    res_thr = threshold_metrics.analyze(eps)
    res_mono = monotonicity.analyze(eps)
    for name, res in (("regret", res_regret), ("reasoning", res_reason), ("latency_invalid", res_lat),
                      ("threshold_metrics", res_thr), ("monotonicity", res_mono)):
        for t in res.tables:
            written.append(write_table(t, tables_dir))
        for k, v in res.numbers.items.items():
            v["source"] = name
        numbers.update(res.numbers)
        report += [f"# {name}", "", res.markdown, ""]

    # 6b. extension experiments (E1/E2/E3/E5) against the core arms (v2 only)
    ext_dir = Path(a.ext_dir)
    if a.campaign == "v2" and ext_dir.exists() and any(ext_dir.iterdir()):
        ext_eps = extensions.load_ext(ext_dir, a.min_decisions)
        res_ext = extensions.analyze(ext_eps, eps)
        for t in res_ext.tables:
            written.append(write_table(t, tables_dir))
        for k, v in res_ext.numbers.items.items():
            v["source"] = "extensions"
        numbers.update(res_ext.numbers)
        report += ["# extensions", "", res_ext.markdown, ""]
        if a.figures:
            written += extensions.make_figures(res_ext, eps, Path(a.figures_dir))
    # 6c. classifier vs manual annotation
    if a.kappa:
        t_k = reasoning.kappa_report(Path(a.kappa), reasoning.load_taxonomy(), a.match)
        written.append(write_table(t_k, tables_dir))
        report += ["# reasoning classifier validation", "", t_k.to_markdown(), ""]

    # 7. figures
    if a.figures:
        cmd = [sys.executable, str(Path(__file__).with_name("make_figures.py")), "--campaign", a.campaign, "--out-dir", a.figures_dir]
        if a.min_decisions is not None:
            cmd += ["--min-decisions", str(a.min_decisions)]
        if a.mapping:
            cmd += ["--mapping", a.mapping]
        print("running:", " ".join(cmd))
        out = subprocess.run(cmd, capture_output=True, text=True)
        report += ["# Figures", "", "```", out.stdout.strip(), out.stderr.strip(), "```", ""]

    # 8. numbers, macros, report
    numbers.to_json(tables_dir / "numbers.json")
    numbers.to_macros(tables_dir / "macros.tex")
    report += ["# Caveats", ""] + [f"- {c}" for c in (CAVEATS_V1 if a.campaign in ("v1", "all") else [])] + [
        "- Unit of analysis is the episode for coverage/threshold statistics, the decision for latency/parse/reasoning, the transition for monotonicity, the event for regret.",
        "- Holm families: stats_report.COMPARISONS (main), all rows of tab_threshold_comparisons (threshold module).",
        f"- Annotation sample for the reasoning classifier: {sheet.relative_to(tables_dir)} (fill in, then `reasoning.py --kappa <file>`).", "",
        "# Files written", ""] + [f"- {p.relative_to(tables_dir) if p.is_relative_to(tables_dir) else p}" for p in written + [tables_dir / 'numbers.json', tables_dir / 'macros.tex', aux / 'regret_events.csv', sheet, auto]]
    write_text(tables_dir / "REPORT.md", "\n".join(report))
    print("\n".join(report[:6]))
    print(f"{len(written)} tables, {len(numbers.items)} numbers -> {tables_dir}")


if __name__ == "__main__":
    main()
