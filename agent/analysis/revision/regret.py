#!/usr/bin/env python3
"""
Decision regret: legacy estimator (paper), geometric-v2 estimator, and exact regret from
deterministic re-simulation.

Definitions (all coverage values in percentage points, pp; decisions are 1-based, epochs 60 s apart)

  Event (drop): decision t (t >= 3) with coverage_pct(t-1) - coverage_pct(t) >= DROP_PP (5 pp).
      This trigger is shared by all estimators below.

  (a) Legacy estimator, two variants that both existed in the June code:
      'legacy_text'  = agent/analysis/regret_analysis.py (the values quoted in the paper text, 6.7/8.4):
          drop  = coverage_pct(t-2) - coverage_pct(t)          (two-epoch drop; event skipped if <= 0)
          gain  = min(D_t, int(0.3 * D_t)) / total_units_t * 100   (D_t = disconnected units at t)
          regret = min(drop, gain);  episodes with < 5 decisions yield no events
      'legacy_fig'   = agent/analysis/generate_figures.py::figure6_regret (values in the paper's Fig. 6):
          drop  = coverage_pct(t-1) - coverage_pct(t)          (one-epoch drop)
          gain, regret as above.
      Both assume a macro cell placed at t-2 would have covered 30 % of the units disconnected at t and
      use total_units as denominator although coverage_pct is computed over mobile units (bridge:
      covPct = floor((mobile - disconnected)/mobile*100), mobile = total - mexes - housing - factories).

  (b) Geometric-v2 estimator (uses disconnected_positions exported by the protocol-v2 bridge):
          c      = centroid of disconnected_positions at t-2 (the counterfactual placement epoch);
                   if none were disconnected at t-2 the centroid of the positions at t is used (flagged)
          n_in   = |{u in disconnected_positions(t) : ||u - c||_2 <= R}|, R = MACRO_RADIUS = 1200 elmos,
                   rescaled by D_t / |positions(t)| when the export was capped (400 positions)
          gain   = 100 * n_in / U_t, U_t = mobile_units(t) (falls back to total_units, flagged)
          regret = min(drop_1, gain), drop_1 = coverage_pct(t-1) - coverage_pct(t)
      Ignored on purpose (stated in the paper): macro capacity (100 RB), backhaul/build delay, engineer
      travel time, demand response. Fallback when positions are absent (v1 data): legacy_fig gain,
      method = 'fallback_no_positions'.

  (c) Exact regret from deterministic re-simulation (F6a): for a mapping row
      (original_episode_dir, branch_episode_dir, inject_decision k0):
          exact_gain_t   = coverage_branch(k0+2) - coverage_original(k0+2)
          exact_gain_end = final coverage_branch - final coverage_original
          exact_gain_mean_after = mean over decisions > k0 of the coverage difference
      The coverage traces must be identical for decisions < k0 (prefix check; reported).
      Estimated vs exact: bias = mean(est - exact), MAE, Spearman rho (scipy or manual), N.

Usage
  regret.py --campaign v1|v2|all [--out-dir DIR] [--min-decisions K] [--mapping branches.csv]
  mapping CSV/JSON columns: original_episode_dir, branch_episode_dir[, inject_decision]
  (inject_decision/inject_action are read from the branch header.json when omitted).
"""
from __future__ import annotations
import argparse, csv, json, math, statistics
from pathlib import Path
from typing import Optional

from load_runs import Episode, group, load_v2_episode
from stats_report import bootstrap_ci
from common import (Result, Table, Numbers, add_common_args, load_campaign, campaign_note, fmt, fmt_pm, fmt_ci,
                    fmt_p, backend_label, scenario_label, group_sort_key, spearman, units_for_coverage, state,
                    write_text, REPO)

DROP_PP = 5.0
LOOKBACK = 2
LEGACY_FRACTION = 0.3
MACRO_RADIUS = 1200.0


# ----------------------------------------------------------------------------- estimators
def legacy_text_event(decisions: list, i: int) -> Optional[dict]:
    """Exact port of regret_analysis.estimate_coverage_if_placed_earlier (called at 1-epoch drops >= 5)."""
    if len(decisions) < 5 or i < LOOKBACK:
        return None
    current, earlier = decisions[i]["state_summary"], decisions[i - LOOKBACK]["state_summary"]
    drop = earlier.get("coverage_pct", 0) - current.get("coverage_pct", 0)
    if drop <= 0:
        return None
    total_units, disconnected = current.get("total_units", 100), current.get("disconnected", 0)
    if disconnected == 0 or total_units == 0:
        return None
    gain = min(disconnected, int(disconnected * LEGACY_FRACTION)) / total_units * 100
    return dict(drop=drop, gain=gain, regret=min(drop, gain))


def legacy_fig_event(decisions: list, i: int) -> Optional[dict]:
    """Exact port of generate_figures.figure6_regret's inline estimator (1-epoch drop)."""
    prev = decisions[i - 1]["state_summary"].get("coverage_pct", 100)
    curr = decisions[i]["state_summary"].get("coverage_pct", 100)
    drop = prev - curr
    ss = decisions[i]["state_summary"]
    disconnected, total = ss.get("disconnected", 0), ss.get("total_units", 100)
    if disconnected <= 0 or total <= 0:
        return None
    gain = min(disconnected, int(disconnected * LEGACY_FRACTION)) / total * 100
    return dict(drop=drop, gain=gain, regret=min(drop, gain))


def _centroid(pts: list) -> Optional[tuple]:
    if not pts:
        return None
    return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))


def geometric_v2_gain(decisions: list, i: int, radius: float = MACRO_RADIUS, lookback: int = LOOKBACK) -> dict:
    """Geometric-v2 gain estimate at decision index i (0-based). Returns dict(gain, n_in, method, centroid, units)."""
    d_now, d_ref = decisions[i], decisions[i - lookback]
    pos_now, pos_ref = d_now.get("disconnected_positions"), d_ref.get("disconnected_positions")
    units = units_for_coverage(d_now)
    unit_src = "mobile_units" if "mobile_units" in d_now.get("state_summary", {}) else "total_units"
    disc_now = state(d_now, "disconnected", 0) or 0
    if pos_now is None or pos_ref is None:
        leg = legacy_fig_event(decisions, i)
        return dict(gain=leg["gain"] if leg else 0.0, n_in=None, method="fallback_no_positions", centroid=None,
                    units=units, unit_src=unit_src)
    method = "positions_t-%d" % lookback
    c = _centroid(pos_ref)
    if c is None:
        c, method = _centroid(pos_now), "positions_centroid_from_t"
    if c is None or not units:
        return dict(gain=0.0, n_in=0, method=method + "_no_disconnected", centroid=c, units=units, unit_src=unit_src)
    n_in = sum(1 for p in pos_now if math.hypot(p[0] - c[0], p[1] - c[1]) <= radius)
    if disc_now > len(pos_now) > 0:                       # export capped at 400 positions
        n_in = n_in * disc_now / len(pos_now)
        method += "_capped_rescaled"
    return dict(gain=100.0 * n_in / units, n_in=n_in, method=method, centroid=c, units=units, unit_src=unit_src)


def episode_events(ep: Episode, drop_pp: float = DROP_PP, radius: float = MACRO_RADIUS) -> list:
    """All drop events of an episode with every estimator evaluated (None where a variant has no event)."""
    dec = ep.decisions
    out = []
    for i in range(2, len(dec)):
        cov_1, cov_0 = state(dec[i - 1], "coverage_pct", 100), state(dec[i], "coverage_pct", 100)
        drop_1 = cov_1 - cov_0
        if drop_1 < drop_pp:
            continue
        lt, lf, g2 = legacy_text_event(dec, i), legacy_fig_event(dec, i), geometric_v2_gain(dec, i, radius)
        out.append(dict(
            episode_id=ep.episode_id, scenario=ep.scenario, backend=ep.backend, protocol=ep.protocol,
            decision=dec[i]["decision"], game_time_s=dec[i].get("game_time_s"),
            cov_t2=state(dec[i - 2], "coverage_pct"), cov_t1=cov_1, cov_t=cov_0, drop_1=drop_1,
            drop_2=state(dec[i - 2], "coverage_pct", 0) - cov_0, disconnected_t=state(dec[i], "disconnected"),
            units_t=g2["units"], unit_src=g2["unit_src"],
            legacy_text_gain=lt["gain"] if lt else None, legacy_text_regret=lt["regret"] if lt else None,
            legacy_fig_gain=lf["gain"] if lf else None, legacy_fig_regret=lf["regret"] if lf else None,
            v2_gain=g2["gain"], v2_regret=min(drop_1, g2["gain"]), v2_n_in=g2["n_in"], v2_method=g2["method"],
            v2_centroid_x=None if g2["centroid"] is None else round(g2["centroid"][0]),
            v2_centroid_z=None if g2["centroid"] is None else round(g2["centroid"][1]),
            action_t2=dec[i - 2]["action"], action_t1=dec[i - 1]["action"]))
    return out


# ----------------------------------------------------------------------------- summaries
def _stats(xs: list) -> dict:
    xs = [x for x in xs if x is not None]
    if not xs:
        return dict(n=0, mean=None, sd=None, ci=None)
    return dict(n=len(xs), mean=statistics.fmean(xs), sd=statistics.stdev(xs) if len(xs) > 1 else 0.0,
                ci=bootstrap_ci(xs) if len(xs) > 1 else (xs[0], xs[0]))


def summarise(eps: list, drop_pp: float = DROP_PP, radius: float = MACRO_RADIUS) -> tuple:
    """Per (scenario, backend): event counts and mean regret per event / cumulative per episode."""
    rows, events = [], []
    for (sc, be), lst in sorted(group(eps).items(), key=lambda kv: group_sort_key(kv[0])):
        ev = [e for ep in lst for e in episode_events(ep, drop_pp, radius)]
        events += ev
        per_ep_cum = []
        for ep in lst:
            mine = [e for e in ev if e["episode_id"] == ep.episode_id]
            per_ep_cum.append(sum(e["v2_regret"] for e in mine))
        r = dict(scenario=sc, backend=be, n_episodes=len(lst), n_events=len(ev),
                 events_per_episode=len(ev) / len(lst) if lst else None,
                 legacy_text=_stats([e["legacy_text_regret"] for e in ev]),
                 legacy_fig=_stats([e["legacy_fig_regret"] for e in ev]),
                 v2=_stats([e["v2_regret"] for e in ev]), v2_gain=_stats([e["v2_gain"] for e in ev]),
                 v2_positions_share=(100.0 * sum(1 for e in ev if not e["v2_method"].startswith("fallback")) / len(ev)) if ev else None,
                 cum_per_episode=_stats(per_ep_cum), drop_1=_stats([e["drop_1"] for e in ev]))
        rows.append(r)
    return rows, events


# ----------------------------------------------------------------------------- exact regret (re-simulation)
def load_mapping(path: Path) -> list:
    path = Path(path)
    if path.suffix.lower() == ".json":
        rows = json.load(open(path))
    else:
        rows = list(csv.DictReader(open(path)))
    out = []
    for r in rows:
        out.append(dict(original_episode_dir=r["original_episode_dir"], branch_episode_dir=r["branch_episode_dir"],
                        inject_decision=int(r["inject_decision"]) if r.get("inject_decision") not in (None, "") else None,
                        inject_action=r.get("inject_action") or None))
    return out


def _resolve(p: str) -> Path:
    q = Path(p)
    return q if q.is_absolute() else (REPO / q)


def exact_regret_rows(mapping: list, min_decisions: Optional[int] = None, radius: float = MACRO_RADIUS) -> list:
    rows = []
    for m in mapping:
        orig = load_v2_episode(_resolve(m["original_episode_dir"]), min_decisions=1)
        br = load_v2_episode(_resolve(m["branch_episode_dir"]), min_decisions=1)
        row = dict(m)
        if orig is None or br is None:
            row.update(status="missing episode dir/decisions.jsonl")
            rows.append(row)
            continue
        k0 = m["inject_decision"] or br.header.get("inject_decision")
        row["inject_decision"] = k0
        row["inject_action"] = m["inject_action"] or br.header.get("inject_action")
        co, cb = orig.coverage_series(), br.coverage_series()
        if not k0 or k0 < 1:
            row.update(status="no inject_decision")
            rows.append(row)
            continue
        k = k0 + LOOKBACK                                  # event epoch evaluated by the estimators
        prefix_ok = co[:k0 - 1] == cb[:k0 - 1]
        row.update(status="ok", n_orig=len(co), n_branch=len(cb), prefix_identical=prefix_ok,
                   exact_gain_t=(cb[k - 1] - co[k - 1]) if len(co) >= k and len(cb) >= k else None,
                   exact_gain_end=cb[min(len(cb), len(co)) - 1] - co[min(len(cb), len(co)) - 1],
                   exact_gain_mean_after=statistics.fmean([b - a for a, b in zip(co[k0:], cb[k0:])]) if len(co) > k0 and len(cb) > k0 else None)
        if len(co) >= k:
            i = k - 1
            lf = legacy_fig_event(orig.decisions, i)
            g2 = geometric_v2_gain(orig.decisions, i, radius)
            row.update(drop_1=state(orig.decisions[i - 1], "coverage_pct", 0) - state(orig.decisions[i], "coverage_pct", 0),
                       est_legacy_gain=lf["gain"] if lf else 0.0, est_v2_gain=g2["gain"], est_v2_method=g2["method"])
        rows.append(row)
    return rows


def compare_estimates(rows: list) -> list:
    """Bias / MAE / Spearman of each estimator against exact_gain_t over usable branches."""
    out = []
    for est, label in (("est_legacy_gain", "fixed-fraction (30 %)"), ("est_v2_gain", "geometric")):
        pairs = [(r[est], r["exact_gain_t"]) for r in rows
                 if r.get("status") == "ok" and r.get(est) is not None and r.get("exact_gain_t") is not None]
        if not pairs:
            out.append(dict(estimator=label, n=0, bias=None, mae=None, rho=None, p=None))
            continue
        diffs = [a - b for a, b in pairs]
        rho, p = spearman([a for a, _ in pairs], [b for _, b in pairs])
        out.append(dict(estimator=label, n=len(pairs), bias=statistics.fmean(diffs),
                        mae=statistics.fmean(abs(d) for d in diffs), rho=rho, p=p))
    return out


# ----------------------------------------------------------------------------- reporting
def analyze(eps: list, mapping: Optional[list] = None, drop_pp: float = DROP_PP, radius: float = MACRO_RADIUS,
            min_decisions: Optional[int] = None) -> Result:
    rows, events = summarise(eps, drop_pp, radius)
    res = Result()
    N = res.numbers
    t = Table("tab_regret", caption=f"Decision regret per condition. Event = coverage drop $\\geq {drop_pp:g}$\\,pp between "
              "consecutive epochs; regret per event in pp (mean $\\pm$ SD over events; 95\\,\\% bootstrap CI for the geometric estimator). "
              "The fixed-fraction estimator assumes that a macro cell placed at $t-2$ would cover 30\\,\\% of the disconnected units "
              "(two variants: drop measured over two epochs or over one); the geometric estimator counts the disconnected units within "
              "1200 elmos of their centroid. Cum./ep.\\ = cumulative geometric regret per episode.",
              columns=["Scenario", "Agent", "$N$ ep.", "Events", "Ev./ep.", "Fixed-fr.\\ (2-ep.)", "Fixed-fr.\\ (1-ep.)", "Geometric",
                       "95\\,\\% CI (geom.)", "Cum./ep.", "Pos.\\ avail."],
              colspec="llrrrrrrlrr", wide=True)
    for r in rows:
        t.rows.append([scenario_label(r["scenario"]), backend_label(r["backend"]), r["n_episodes"], r["n_events"],
                       fmt(r["events_per_episode"], 2), fmt_pm(r["legacy_text"]["mean"], r["legacy_text"]["sd"]),
                       fmt_pm(r["legacy_fig"]["mean"], r["legacy_fig"]["sd"]), fmt_pm(r["v2"]["mean"], r["v2"]["sd"]),
                       fmt_ci(r["v2"]["ci"]), fmt_pm(r["cum_per_episode"]["mean"], r["cum_per_episode"]["sd"]),
                       "n/a (no events)" if r["v2_positions_share"] is None else (fmt(r["v2_positions_share"], 0) + "%")])
        k = f"regret_{r['scenario']}_{r['backend']}"
        N.add(k + "_events", r["n_events"], "number of coverage-drop events (>= 5 pp between consecutive epochs)", n=r["n_episodes"], nd=0)
        N.add(k + "_legacy_text_mean", r["legacy_text"]["mean"], "mean legacy-text regret per event (pp; regret_analysis.py port)", n=r["legacy_text"]["n"])
        N.add(k + "_legacy_fig_mean", r["legacy_fig"]["mean"], "mean legacy-fig regret per event (pp; generate_figures.py port)", n=r["legacy_fig"]["n"])
        N.add(k + "_v2_mean", r["v2"]["mean"], "mean geometric-v2 regret per event (pp)", n=r["v2"]["n"])
        N.add(k + "_v2_cum_per_episode", r["cum_per_episode"]["mean"], "mean cumulative geometric-v2 regret per episode (pp; 0 if no event)", n=r["n_episodes"])
    res.tables.append(t)

    md = ["## Decision regret", "", f"Trigger: coverage drop >= {drop_pp:g} pp between consecutive decisions. Estimators: see module docstring.", "",
          t.to_markdown(), ""]
    # exact regret
    exact_rows, comp = [], []
    if mapping:
        exact_rows = exact_regret_rows(mapping, min_decisions, radius)
        comp = compare_estimates(exact_rows)
        tv = Table("tab_regret_validation", caption="Estimated vs exact counterfactual gain at $t = k_0+2$ from deterministic "
                   "re-simulation (branch minus original coverage, pp). Bias = mean(estimate $-$ exact); MAE; Spearman $\\rho$.",
                   columns=["Estimator", "$N$ branches", "Bias (pp)", "MAE (pp)", "Spearman $\\rho$", "$p$"], colspec="lrrrrr")
        for c in comp:
            tv.rows.append([c["estimator"], c["n"], fmt(c["bias"]), fmt(c["mae"]), fmt(c["rho"], 2), fmt_p(c["p"])])
            k = "regret_validation_" + ("legacy" if c["estimator"].startswith("fixed") else "v2")
            N.add(k + "_n", c["n"], "branches with exact and estimated gain", nd=0)
            N.add(k + "_bias", c["bias"], "mean(estimated - exact gain) at k0+2, pp")
            N.add(k + "_mae", c["mae"], "mean |estimated - exact| at k0+2, pp")
            N.add(k + "_rho", c["rho"], "Spearman rho estimated vs exact gain", nd=2)
        n_prefix_bad = sum(1 for r in exact_rows if r.get("status") == "ok" and not r.get("prefix_identical"))
        tv.note = (f"{sum(1 for r in exact_rows if r.get('status') == 'ok')} usable branch pairs; "
                   f"{n_prefix_bad} with a non-identical prefix (determinism violated; excluded from nothing here but flagged in regret_exact.csv).")
        res.tables.append(tv)
        md += ["## Exact regret (re-simulation)", "", tv.to_markdown(), "", "Per-branch rows: regret_exact.csv", ""]
    else:
        md += ["## Exact regret (re-simulation)", "", "n/a: no --mapping given (no counterfactual branches have been simulated yet).", ""]
        N.add("regret_validation_v2_n", 0, "branches with exact and estimated gain (none simulated yet)", nd=0)
    res.markdown = "\n".join(md)
    res.extra = dict(events=events, groups=rows, exact_rows=exact_rows, comparison=comp)
    return res


def write_csv(path: Path, rows: list):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("")
        return
    cols = sorted({k for r in rows for k in r.keys()}, key=lambda c: (c not in rows[0], c))
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def main():
    ap = add_common_args(argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter),
                         default_out=REPO / "agent" / "analysis" / "revision" / "out" / "regret")
    ap.add_argument("--mapping", default=None, help="CSV/JSON of (original_episode_dir, branch_episode_dir[, inject_decision])")
    ap.add_argument("--drop-pp", type=float, default=DROP_PP)
    ap.add_argument("--radius", type=float, default=MACRO_RADIUS)
    a = ap.parse_args()
    eps = load_campaign(a)
    mapping = load_mapping(a.mapping) if a.mapping else None
    res = analyze(eps, mapping, a.drop_pp, a.radius, a.min_decisions)
    res.markdown = campaign_note(a, eps) + "\n\n" + res.markdown
    print(res.markdown)
    out = Path(a.out_dir)
    res.write(out, "regret")
    write_csv(out / "regret_events.csv", res.extra["events"])
    if res.extra["exact_rows"]:
        write_csv(out / "regret_exact.csv", res.extra["exact_rows"])
    print(f"\nwritten to {out}")


if __name__ == "__main__":
    main()
