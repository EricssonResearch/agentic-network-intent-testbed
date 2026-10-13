#!/usr/bin/env python3
"""
Empirical check of the coverage-monotonicity theorem (thm:monotone) at decision-epoch granularity.

DEFINITIONS (printed in the output so the paper can quote them verbatim)
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

Usage: monotonicity.py --campaign v1|v2|all [--out-dir DIR] [--min-decisions K]
"""
from __future__ import annotations
import argparse
from collections import defaultdict
from pathlib import Path

from load_runs import Episode
from common import (Result, Table, Numbers, add_common_args, load_campaign, campaign_note, fmt, backend_label, scenario_label,
                    group_sort_key, wilson_ci, units_for_coverage, state, action_type, REPO)

DEFINITIONS = __doc__.split("DEFINITIONS")[1].split("Usage:")[0].strip()
VARIANTS = [("strict", "(i) strict"), ("demand_adj", "(ii) demand-adjusted"), ("covered", "(iii) covered-count"), ("action", "(iv) action-based")]


def transitions(ep: Episode) -> list:
    """One dict per consecutive pair with the boolean tests of every variant."""
    out = []
    d = ep.decisions
    for i in range(len(d) - 1):
        a, b = d[i], d[i + 1]
        ua, ub = units_for_coverage(a), units_for_coverage(b)
        ca, cb = state(a, "coverage_pct"), state(b, "coverage_pct")
        da, db = state(a, "disconnected"), state(b, "disconnected")
        cov_nondec = cb >= ca
        bs_inc = state(b, "total_bs", 0) > state(a, "total_bs", 0)
        covered_ok = (ua is not None and ub is not None and da is not None and db is not None and (ub - db) >= (ua - da))
        out.append(dict(episode_id=ep.episode_id, scenario=ep.scenario, backend=ep.backend, protocol=ep.protocol, t=a["decision"],
                        bs_increase=bs_inc, place_action=action_type(a["action"]) == "place_bs", cov_nondec=cov_nondec,
                        demand_grew=(ua is not None and ub is not None and ub > ua), covered_nondec=covered_ok,
                        unit_src="mobile_units" if "mobile_units" in a.get("state_summary", {}) else "total_units"))
    return out


def shares(trs: list) -> dict:
    """-> {variant: (k, n)} for one set of transitions."""
    bs = [t for t in trs if t["bs_increase"]]
    pl = [t for t in trs if t["place_action"]]
    return dict(strict=(sum(1 for t in bs if t["cov_nondec"]), len(bs)),
                demand_adj=(sum(1 for t in bs if t["cov_nondec"] or t["demand_grew"]), len(bs)),
                covered=(sum(1 for t in bs if t["covered_nondec"]), len(bs)),
                action=(sum(1 for t in pl if t["cov_nondec"]), len(pl)), n_transitions=len(trs))


def _cell(k: int, n: int) -> str:
    if n == 0:
        return "n/a (0)"
    ci = wilson_ci(k, n)
    return f"{100.0 * k / n:.1f}% [{100 * ci[0]:.1f}, {100 * ci[1]:.1f}] ({k}/{n})"


def analyze(eps: list) -> Result:
    res, N = Result(), Numbers()
    by = defaultdict(list)
    for e in eps:
        by[(e.campaign, e.backend)] += transitions(e)
    all_tr = [t for v in by.values() for t in v]
    t = Table("tab_monotonicity", caption="Empirical coverage monotonicity at decision-epoch granularity: share of transitions (Wilson 95\\,\\% CI, $k/N$) "
              "in which coverage did not decrease after a base station came online. Definitions (i)--(iv) in the text.",
              columns=["Camp.", "Agent", "Transitions", "(i) strict", "(ii) demand-adj.", "(iii) covered-count", "(iv) action-based"],
              colspec="llrllll", wide=True)
    rows = []
    for key in sorted(by, key=lambda k: (k[0],) + group_sort_key(("", k[1]))):
        s = shares(by[key])
        rows.append((key, s))
        t.rows.append([key[0], backend_label(key[1]), s["n_transitions"]] + [_cell(*s[v]) for v, _ in VARIANTS])
        for v, _ in VARIANTS:
            k_, n_ = s[v]
            N.add(f"mono_{key[0]}_{key[1]}_{v}_pct", 100.0 * k_ / n_ if n_ else None, f"monotonicity share variant {v} (%)", n=n_)
            N.add(f"mono_{key[0]}_{key[1]}_{v}_n", n_, f"transitions in the denominator of variant {v}", nd=0)
    for camp in sorted({k[0] for k in by}):
        s = shares([tr for k, v in by.items() if k[0] == camp for tr in v])
        t.rows.append([camp, "all agents", s["n_transitions"]] + [_cell(*s[v]) for v, _ in VARIANTS])
        for v, _ in VARIANTS:
            k_, n_ = s[v]
            N.add(f"mono_{camp}_all_{v}_pct", 100.0 * k_ / n_ if n_ else None, f"monotonicity share variant {v}, all agents (%)", n=n_)
            N.add(f"mono_{camp}_all_{v}_k", k_, f"transitions satisfying variant {v}, all agents", nd=0)
            N.add(f"mono_{camp}_all_{v}_n", n_, f"transitions in the denominator of variant {v}, all agents", nd=0)
    srcs = sorted({tr["unit_src"] for tr in all_tr})
    t.note = f"U(t) taken from {', '.join(srcs) if srcs else 'n/a'}; unit = transition, episode clustering ignored."
    if all(e.protocol == 2 for e in eps):      # single campaign: drop the campaign column and the legacy action-based variant
        keep = [i for i, c in enumerate(t.columns) if c not in ("Camp.", "(iv) action-based")]
        t.columns = [t.columns[i] for i in keep]
        t.rows = [[r[i] for i in keep] for r in t.rows]
        t.colspec = None
        t.caption = ("Empirical coverage monotonicity at decision-epoch granularity: share of transitions (Wilson 95\\,\\% CI, $k/N$) in which "
                     "coverage did not decrease after a base station came online, under the three readings (i)--(iii) defined in the text.")
    res.tables.append(t)
    res.numbers = N
    res.markdown = "\n".join(["## Coverage monotonicity", "", "```", DEFINITIONS, "```", "", t.to_markdown()])
    res.extra = dict(transitions=all_tr, rows=rows)
    return res


def main():
    ap = add_common_args(argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter),
                         default_out=REPO / "agent" / "analysis" / "revision" / "out" / "monotonicity")
    a = ap.parse_args()
    eps = load_campaign(a)
    res = analyze(eps)
    res.markdown = campaign_note(a, eps) + "\n\n" + res.markdown
    print(res.markdown)
    res.write(Path(a.out_dir), "monotonicity")
    print(f"\nwritten to {a.out_dir}")


if __name__ == "__main__":
    main()
