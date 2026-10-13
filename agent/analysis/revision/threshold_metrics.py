#!/usr/bin/env python3
"""
Threshold ("intent satisfaction") metrics for the 80 % coverage intent, per (scenario, backend).

Per episode (T decision epochs, coverage c_t in %):
  frac_ge     = 100 * |{t : c_t >= THR}| / T                    share of epochs at/above the threshold (%)
  first_viol  = min{t : c_t < THR}   (None if never)             epoch of the first violation (1-based)
  area_below  = sum_t max(0, THR - c_t)                          below-threshold area (percentage-point-epochs)
  final_cov   = c_T ; bs_deployed = total_bs at T
Per group: N, mean, sample SD, 95 % bootstrap CI of the mean (stats_report.bootstrap_ci, 10k resamples), plus for
first_viol the mean over violating episodes and the share of episodes that never violate.
Comparisons: for every scenario with an LLM arm and a rule arm (N >= 2 each) Welch's t-test and Hedges' g on
frac_ge, area_below, final_cov and bs_deployed (stats_report.welch); Holm correction over the whole family of
comparisons reported by this module (all scenarios x metrics).

Usage: threshold_metrics.py --campaign v1|v2|all [--out-dir DIR] [--min-decisions K] [--threshold 80]
"""
from __future__ import annotations
import argparse, statistics
from pathlib import Path

from load_runs import Episode, group
from stats_report import welch, holm, bootstrap_ci
from common import (Result, Table, Numbers, add_common_args, load_campaign, campaign_note, fmt, fmt_pm, fmt_ci, fmt_p,
                    backend_label, scenario_label, group_sort_key, REPO)

THR = 80.0
METRICS = [("frac_ge", "Epochs $\\geq$ thr. (\\%)", "share of epochs with coverage >= threshold (%)"),
           ("area_below", "Below-thr. area (pp$\\cdot$ep.)", "sum over epochs of max(0, thr - coverage) (pp-epochs)"),
           ("final_cov", "Final cov. (\\%)", "coverage at the last decision epoch (%)"),
           ("bs_deployed", "BS deployed", "base stations at the last decision epoch")]


def episode_metrics(ep: Episode, thr: float = THR) -> dict:
    c = ep.coverage_series()
    fv = ep.first_violation_epoch(thr)
    return dict(frac_ge=100.0 * sum(1 for x in c if x >= thr) / len(c), first_viol=fv,
                area_below=sum(max(0.0, thr - x) for x in c), final_cov=c[-1], bs_deployed=ep.bs_deployed(), T=len(c))


def _agg(xs: list) -> dict:
    if not xs:
        return dict(n=0, mean=None, sd=None, ci=None)
    return dict(n=len(xs), mean=statistics.fmean(xs), sd=statistics.stdev(xs) if len(xs) > 1 else 0.0,
                ci=bootstrap_ci(xs) if len(xs) > 1 else (xs[0], xs[0]))


def group_rows(eps: list, thr: float = THR) -> list:
    rows = []
    for (sc, be), lst in sorted(group(eps).items(), key=lambda kv: group_sort_key(kv[0])):
        m = [episode_metrics(e, thr) for e in lst]
        viol = [x["first_viol"] for x in m if x["first_viol"] is not None]
        rows.append(dict(scenario=sc, backend=be, n=len(lst), T_mean=statistics.fmean(x["T"] for x in m),
                         frac_ge=_agg([x["frac_ge"] for x in m]), area_below=_agg([x["area_below"] for x in m]),
                         final_cov=_agg([x["final_cov"] for x in m]), bs_deployed=_agg([x["bs_deployed"] for x in m]),
                         first_viol=_agg(viol), never_viol=len(lst) - len(viol), per_episode=m))
    return rows


def comparisons(eps: list, thr: float = THR, a: str = "llm", b: str = "rule") -> list:
    g = group(eps)
    out = []
    for sc in sorted({s for s, _ in g}, key=lambda s: group_sort_key((s, ""))):
        ea, eb = g.get((sc, a)), g.get((sc, b))
        if not ea or not eb or len(ea) < 2 or len(eb) < 2:
            continue
        ma, mb = [episode_metrics(e, thr) for e in ea], [episode_metrics(e, thr) for e in eb]
        for key, label, _ in METRICS:
            r = welch([x[key] for x in ma], [x[key] for x in mb])
            r.update(scenario=sc, metric=key, metric_label=label, a=a, b=b)
            out.append(r)
    adj = holm([r["p"] for r in out]) if out else []
    for r, pa in zip(out, adj):
        r["p_holm"] = pa
    return out


def analyze(eps: list, thr: float = THR) -> Result:
    rows, comps = group_rows(eps, thr), comparisons(eps, thr)
    res, N = Result(), Numbers()
    t = Table("tab_threshold", caption=f"Threshold metrics for the {thr:g}\\,\\% coverage intent (unit = episode; mean $\\pm$ sample SD, "
              "95\\,\\% bootstrap CI of the mean). First violation: mean epoch over violating episodes and number of episodes never violating.",
              columns=["Scenario", "Agent", "$N$", "Epochs $\\geq$ thr. (\\%)", "95\\,\\% CI", "First viol. (epoch)", "Never", "Below-thr. area", "95\\,\\% CI", "Final cov. (\\%)", "BS"],
              colspec="llrrlrrrlrr", wide=True)
    for r in rows:
        t.rows.append([scenario_label(r["scenario"]), backend_label(r["backend"]), r["n"], fmt_pm(r["frac_ge"]["mean"], r["frac_ge"]["sd"]),
                       fmt_ci(r["frac_ge"]["ci"]), fmt_pm(r["first_viol"]["mean"], r["first_viol"]["sd"]) if r["first_viol"]["n"] else "n/a (none)",
                       f"{r['never_viol']}/{r['n']}", fmt_pm(r["area_below"]["mean"], r["area_below"]["sd"], 0), fmt_ci(r["area_below"]["ci"], 0),
                       fmt_pm(r["final_cov"]["mean"], r["final_cov"]["sd"]), fmt_pm(r["bs_deployed"]["mean"], r["bs_deployed"]["sd"])])
        k = f"thr_{r['scenario']}_{r['backend']}"
        N.add(k + "_n", r["n"], "episodes", nd=0)
        for key, _, definition in METRICS:
            N.add(f"{k}_{key}_mean", r[key]["mean"], definition + " (group mean)", n=r["n"])
            N.add(f"{k}_{key}_sd", r[key]["sd"], definition + " (sample SD)", n=r["n"])
            if r[key]["ci"]:
                N.add(f"{k}_{key}_ci_lo", r[key]["ci"][0], definition + " (bootstrap CI lower)", n=r["n"])
                N.add(f"{k}_{key}_ci_hi", r[key]["ci"][1], definition + " (bootstrap CI upper)", n=r["n"])
        N.add(k + "_first_viol_mean", r["first_viol"]["mean"], "mean epoch of first coverage < threshold over violating episodes", n=r["first_viol"]["n"])
        N.add(k + "_never_viol", r["never_viol"], "episodes never below threshold", nd=0)
        N.add(k + "_never_viol_pct", 100.0 * r["never_viol"] / r["n"] if r["n"] else None, "share of episodes never below threshold (%)", n=r["n"])
    res.tables.append(t)
    tc = Table("tab_threshold_comparisons", caption="LLM-full minus rule on the threshold metrics (Welch's $t$-test on episode values, Hedges' $g$, "
               "95\\,\\% CI of the difference; Holm correction over all comparisons in this table).",
               columns=["Scenario", "Metric", "$n$", "$\\Delta$", "95\\,\\% CI", "$t$", "df", "$p$", "$p_{\\mathrm{Holm}}$", "$g$"],
               colspec="llrrlrrrrr", wide=True)
    for r in comps:
        tc.rows.append([scenario_label(r["scenario"]), r["metric_label"], f"{r['n_a']}/{r['n_b']}", f"{r['diff']:+.1f}", fmt_ci(r["ci"]),
                        fmt(r["t"], 2), fmt(r["df"]), fmt_p(r["p"]), fmt_p(r["p_holm"]), fmt(r["g"], 2)])
        k = f"thrcmp_{r['scenario']}_{r['metric']}"
        N.add(k + "_diff", r["diff"], f"LLM minus rule, {r['metric']}", n=f"{r['n_a']}/{r['n_b']}")
        N.add(k + "_p", r["p"], "Welch p", nd=3)
        N.add(k + "_p_holm", r["p_holm"], "Holm-adjusted p (family = this table)", nd=3)
        N.add(k + "_g", r["g"], "Hedges g", nd=2)
    if not comps:
        tc.note = "n/a: no scenario has both an LLM-full and a rule arm with N >= 2."
    res.tables.append(tc)
    res.numbers = N
    res.markdown = "\n".join([f"## Threshold metrics (threshold = {thr:g} %)", "", t.to_markdown(), "", "## LLM vs rule", "", tc.to_markdown()])
    res.extra = dict(groups=rows, comparisons=comps, threshold=thr)
    return res


def main():
    ap = add_common_args(argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter),
                         default_out=REPO / "agent" / "analysis" / "revision" / "out" / "threshold")
    ap.add_argument("--threshold", type=float, default=THR)
    a = ap.parse_args()
    eps = load_campaign(a)
    res = analyze(eps, a.threshold)
    res.markdown = campaign_note(a, eps) + "\n\n" + res.markdown
    print(res.markdown)
    res.write(Path(a.out_dir), "threshold_metrics")
    print(f"\nwritten to {a.out_dir}")


if __name__ == "__main__":
    main()
