#!/usr/bin/env python3
"""
Statistical report for the paper: per-condition summaries and pairwise comparisons.

Unit of analysis: episode. Tests: Welch's t-test (episode means), Hedges' g, 95 % CI of the mean
difference (Welch df), Holm correction over the reported family, TOST equivalence test, bootstrap
CI for means. Also threshold metrics (share of epochs with coverage >= 80 %, first violation epoch).

Usage: stats_report.py [--campaign v1|v2|all] [--tex-dir DIR] [--md FILE]
"""
from __future__ import annotations
import argparse, json, math, statistics
from pathlib import Path
import numpy as np
from scipy import stats
from load_runs import load_all, group, LLM_BACKENDS

COMPARISONS = [  # (label, scenario, backend A, backend B)  -- A minus B
    ("S1 LLM vs rule", "s1_peaceful", "llm", "rule"),
    ("S1 LLM vs no-spatial", "s1_peaceful", "llm", "llm_nospatial"),
    ("S1 LLM vs minimal", "s1_peaceful", "llm", "llm_minimal"),
    ("S1 no-spatial vs random", "s1_peaceful", "llm_nospatial", "random"),
    ("S1 noop vs LLM", "s1_peaceful", "noop", "llm"),
    ("S1 noop vs rule", "s1_peaceful", "noop", "rule"),
    ("S2 rule vs LLM", "s2_stress", "rule", "llm"),
    ("S2 LLM vs random", "s2_stress", "llm", "random"),
    ("S3 rule vs LLM", "s3_daynight", "rule", "llm"),
    ("S4 rule vs LLM", "s4_adversarial", "rule", "llm"),
]
EQUIVALENCE = [("S1 LLM vs rule", 5.0), ("S1 no-spatial vs random", 5.0)]


def welch(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    na, nb = len(a), len(b)
    va, vb = a.var(ddof=1), b.var(ddof=1)
    se = math.sqrt(va / na + vb / nb)
    t = (a.mean() - b.mean()) / se if se > 0 else float("nan")
    df = (va / na + vb / nb) ** 2 / ((va / na) ** 2 / (na - 1) + (vb / nb) ** 2 / (nb - 1)) if se > 0 else float("nan")
    p = 2 * stats.t.sf(abs(t), df) if se > 0 else float("nan")
    sp = math.sqrt(((na - 1) * va + (nb - 1) * vb) / (na + nb - 2))
    g = (a.mean() - b.mean()) / sp * (1 - 3 / (4 * (na + nb) - 9)) if sp > 0 else float("nan")
    tc = stats.t.ppf(0.975, df) if se > 0 else float("nan")
    return dict(n_a=na, n_b=nb, mean_a=a.mean(), mean_b=b.mean(), diff=a.mean() - b.mean(), t=t, df=df, p=p, g=g,
                ci=(a.mean() - b.mean() - tc * se, a.mean() - b.mean() + tc * se))


def tost(a, b, delta):
    a, b = np.asarray(a, float), np.asarray(b, float)
    na, nb = len(a), len(b)
    va, vb = a.var(ddof=1), b.var(ddof=1)
    se = math.sqrt(va / na + vb / nb)
    df = (va / na + vb / nb) ** 2 / ((va / na) ** 2 / (na - 1) + (vb / nb) ** 2 / (nb - 1))
    diff = a.mean() - b.mean()
    p1 = stats.t.sf((diff + delta) / se, df)
    p2 = stats.t.cdf((diff - delta) / se, df)
    return max(p1, p2)


def holm(pvals):
    m = len(pvals)
    order = sorted(range(m), key=lambda i: pvals[i])
    adj = [0.0] * m
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, pvals[i] * (m - rank))
        adj[i] = min(1.0, running)
    return adj


def bootstrap_ci(x, n=10000, seed=1):
    rng = np.random.default_rng(seed)
    x = np.asarray(x, float)
    means = rng.choice(x, size=(n, len(x)), replace=True).mean(axis=1)
    return tuple(np.percentile(means, [2.5, 97.5]))


def power_two_sample(delta, sd, n, alpha=0.05):
    d = delta / sd
    df = 2 * n - 2
    ncp = d * math.sqrt(n / 2)
    tc = stats.t.ppf(1 - alpha / 2, df)
    return 1 - stats.nct.cdf(tc, df, ncp) + stats.nct.cdf(-tc, df, ncp)


def condition_table(groups):
    rows = []
    for (sc, be), eps in sorted(groups.items()):
        avg = [e.avg_coverage() for e in eps]
        fin = [e.final_coverage() for e in eps]
        bs = [e.bs_deployed() for e in eps]
        f80 = [e.frac_epochs_at_least(80) for e in eps]
        fv = [e.first_violation_epoch(80) or e.n_decisions() + 1 for e in eps]
        ci = bootstrap_ci(avg) if len(avg) > 1 else (avg[0], avg[0])
        rows.append(dict(scenario=sc, backend=be, n=len(eps), avg_mean=statistics.fmean(avg),
                         avg_sd=statistics.stdev(avg) if len(avg) > 1 else 0.0, avg_ci=ci,
                         final_mean=statistics.fmean(fin), final_sd=statistics.stdev(fin) if len(fin) > 1 else 0.0,
                         bs_mean=statistics.fmean(bs), bs_sd=statistics.stdev(bs) if len(bs) > 1 else 0.0, bs_median=statistics.median(bs),
                         f80_mean=statistics.fmean(f80), first_violation_mean=statistics.fmean(fv)))
    return rows


def comparison_table(groups):
    rows = []
    for label, sc, a, b in COMPARISONS:
        ea, eb = groups.get((sc, a)), groups.get((sc, b))
        if not ea or not eb or len(ea) < 2 or len(eb) < 2:
            continue
        r = welch([e.avg_coverage() for e in ea], [e.avg_coverage() for e in eb])
        r.update(label=label, scenario=sc, a=a, b=b)
        rows.append(r)
    adj = holm([r["p"] for r in rows]) if rows else []
    for r, pa in zip(rows, adj):
        r["p_holm"] = pa
    return rows


def equivalence_table(groups):
    rows = []
    for label, delta in EQUIVALENCE:
        comp = next((c for c in COMPARISONS if c[0] == label), None)
        if not comp:
            continue
        _, sc, a, b = comp
        ea, eb = groups.get((sc, a)), groups.get((sc, b))
        if not ea or not eb or len(ea) < 2 or len(eb) < 2:
            continue
        p = tost([e.avg_coverage() for e in ea], [e.avg_coverage() for e in eb], delta)
        rows.append(dict(label=label, delta=delta, p_tost=p, n_a=len(ea), n_b=len(eb)))
    return rows


def fmt_p(p):
    return "<0.001" if p < 0.001 else f"{p:.3f}"


def to_markdown(cond, comp, eq, notes):
    out = ["## Per-condition summary (mean ± sample SD; episode = unit)", "",
           "| Scenario | Agent | N | Avg cov (%) | 95% CI | Final cov (%) | BS deployed mean±SD (median) | Epochs ≥80% | First violation (epoch) |",
           "|---|---|---|---|---|---|---|---|---|"]
    for r in cond:
        out.append(f"| {r['scenario']} | {r['backend']} | {r['n']} | {r['avg_mean']:.1f} ± {r['avg_sd']:.1f} | [{r['avg_ci'][0]:.1f}, {r['avg_ci'][1]:.1f}] | "
                   f"{r['final_mean']:.1f} ± {r['final_sd']:.1f} | {r['bs_mean']:.1f} ± {r['bs_sd']:.1f} ({r['bs_median']:g}) | {r['f80_mean']:.1f}% | {r['first_violation_mean']:.1f} |")
    out += ["", "## Pairwise comparisons (Welch t-test on episode means; Hedges' g; Holm-corrected over this family)", "",
            "| Comparison | n | Δ (pp) | t | df | p | p (Holm) | g | 95% CI (pp) |", "|---|---|---|---|---|---|---|---|---|"]
    for r in comp:
        out.append(f"| {r['label']} | {r['n_a']}/{r['n_b']} | {r['diff']:+.1f} | {r['t']:.2f} | {r['df']:.1f} | {fmt_p(r['p'])} | {fmt_p(r['p_holm'])} | {r['g']:+.2f} | [{r['ci'][0]:+.1f}, {r['ci'][1]:+.1f}] |")
    out += ["", "## Equivalence (TOST)", "", "| Comparison | margin (pp) | n | p (TOST) |", "|---|---|---|---|"]
    for r in eq:
        out.append(f"| {r['label']} | ±{r['delta']:.0f} | {r['n_a']}/{r['n_b']} | {fmt_p(r['p_tost'])} |")
    out += ["", "## Notes", ""] + [f"- {n}" for n in notes]
    return "\n".join(out)


def to_tex(cond, comp, eq, tex_dir: Path):
    tex_dir.mkdir(parents=True, exist_ok=True)
    L = [r"% auto-generated by stats_report.py -- do not edit", r"\begin{tabular*}{\tblwidth}{@{}llrrrrr@{}}", r"\toprule",
         r"Scenario & Agent & $N$ & Avg.\ cov.\ (\%) & 95\,\% CI & Final cov.\ (\%) & BS deployed \\", r"\midrule"]
    for r in cond:
        L.append(f"{r['scenario'].replace('_',' ')} & {r['backend'].replace('_','-')} & {r['n']} & ${r['avg_mean']:.1f} \\pm {r['avg_sd']:.1f}$ & "
                 f"[{r['avg_ci'][0]:.1f}, {r['avg_ci'][1]:.1f}] & ${r['final_mean']:.1f} \\pm {r['final_sd']:.1f}$ & ${r['bs_mean']:.1f} \\pm {r['bs_sd']:.1f}$ ({r['bs_median']:g}) \\\\")
    L += [r"\bottomrule", r"\end{tabular*}"]
    (tex_dir / "tab_conditions.tex").write_text("\n".join(L) + "\n")
    L = [r"% auto-generated by stats_report.py -- do not edit", r"\begin{tabular*}{\tblwidth}{@{}lrrrrrrrl@{}}", r"\toprule",
         r"Comparison & $n$ & $\Delta$ (pp) & $t$ & df & $p$ & $p_{\mathrm{Holm}}$ & $g$ & 95\,\% CI (pp) \\", r"\midrule"]
    for r in comp:
        L.append(f"{r['label']} & {r['n_a']}/{r['n_b']} & ${r['diff']:+.1f}$ & {r['t']:.2f} & {r['df']:.1f} & {fmt_p(r['p'])} & {fmt_p(r['p_holm'])} & ${r['g']:+.2f}$ & $[{r['ci'][0]:+.1f}, {r['ci'][1]:+.1f}]$ \\\\")
    L += [r"\bottomrule", r"\end{tabular*}"]
    (tex_dir / "tab_comparisons.tex").write_text("\n".join(L) + "\n")
    L = [r"% auto-generated by stats_report.py -- do not edit", r"\begin{tabular}{lrrr}", r"\toprule", r"Comparison & margin (pp) & $n$ & $p_{\mathrm{TOST}}$ \\", r"\midrule"]
    for r in eq:
        L.append(f"{r['label']} & $\\pm{r['delta']:.0f}$ & {r['n_a']}/{r['n_b']} & {fmt_p(r['p_tost'])} \\\\")
    L += [r"\bottomrule", r"\end{tabular}"]
    (tex_dir / "tab_equivalence.tex").write_text("\n".join(L) + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--campaign", choices=["v1", "v2", "all"], default="v2")
    ap.add_argument("--tex-dir", default=None)
    ap.add_argument("--md", default=None)
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    eps = load_all(a.campaign in ("v1", "all"), a.campaign in ("v2", "all"), only_valid=True)
    eps = [e for e in eps if e.backend != "replay"]
    groups = group(eps)
    cond, comp, eq = condition_table(groups), comparison_table(groups), equivalence_table(groups)
    notes = [f"campaign={a.campaign}; episodes={len(eps)}; SD = sample SD (ddof=1); CI of means by bootstrap (10k)",
             "power to detect 6 pp at SD 9: " + ", ".join(f"n={n}: {power_two_sample(6, 9, n):.2f}" for n in (5, 10, 20, 30))]
    md = to_markdown(cond, comp, eq, notes)
    print(md)
    if a.md:
        Path(a.md).write_text(md + "\n")
    if a.tex_dir:
        to_tex(cond, comp, eq, Path(a.tex_dir))
    if a.json:
        Path(a.json).write_text(json.dumps(dict(conditions=cond, comparisons=comp, equivalence=eq, notes=notes), indent=2, default=list))


if __name__ == "__main__":
    main()
