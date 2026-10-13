#!/usr/bin/env python3
"""
Inference latency, invalid-output rates, bridge validation outcomes and run-time per arm.

Arm = (campaign, backend, model).  Unit for latency and parse status = decision; unit for run-time = episode.

Latency sources (column 'source' in the table)
  v2 LLM arms       : latency_s logged by the orchestrator (t_llm_end - t_llm_start) -> 'logged'
  v2 baseline arms  : decision_wall_s (agent compute time, ~0) -> 'logged (decision_wall_s)'
  v1 (June) arms    : RECONSTRUCTED. The June orchestrator did not log latency and (defect A) the game was not
                      paused during the LLM call, so the decision-log interval carries no information. We anchor
                      the engine's relative clock ([t=HH:MM:SS] in the game log) to UTC via the demo-file name
                      written at engine time t_demo ("recording demo to .../YYYY-MM-DD_HH-MM-SS-mmm_<map>.sdfz",
                      UTC) and take  latency_k = timestamp_k(decision log, Unix) - (T0 + t_paused_k), where
                      t_paused_k is the engine time of "[6G Agent] Decision #k ... — paused" (state export).
                      This includes the orchestrator's 1 s polling loop and file I/O (rule/random/noop arms show
                      the overhead: median ~0.5 s); it reproduces the audit's finding J (median 12.5 s).

Invalid outputs (v2, from parse_status): invalid rate = (fallback_noop + api_error + timeout) / N; 'extracted'
(action found by regex inside a verbose reply) is reported separately, not counted as invalid.  For v1 the
orchestrator logged no parse status; we infer 'api_error' from the reasoning placeholder 'error: ...' and count
actions that violate the bridge grammar ('syntax_invalid', e.g. 'place_bs|macro_cell|X|Z') for both campaigns.

Bridge validation outcomes: v2 from summary.json['validation_outcomes'] (noop, executed_place, executed_reconfig,
skipped_threat, skipped_water, skipped_invalid_position, no_engineer, invalid_format, ...); v1 from the game log
('Ordered/Queued engineer', 'Skipped: ...'), available only for post-fix episodes (finding B).

Run-time: v2 summary.json wall_clock_s and peak_rss_mb; v1 wall-clock approximated by the decision-log span + 60 s,
RSS n/a.

Usage: latency_invalid.py --campaign v1|v2|all [--out-dir DIR] [--min-decisions K]
"""
from __future__ import annotations
import argparse, re, statistics
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from load_runs import Episode
from common import (open_gamelog, Result, Table, Numbers, add_common_args, load_campaign, campaign_note, fmt, fmt_pm, backend_label,
                    group_sort_key, quantile, mean_sd, action_syntax_valid, DECISION_INTERVAL_S, REPO)

PARSE_STATUSES = ["valid", "extracted", "fallback_noop", "api_error", "timeout"]
INVALID_STATUSES = {"fallback_noop", "api_error", "timeout"}
V1_INFERRED_ERROR = "api_error (inferred)"
V1_UNKNOWN = "unknown (v1 unlogged)"
_T_RE = re.compile(r"^\[t=(\d+):(\d+):(\d+(?:\.\d+)?)\]")
_DEMO_RE = re.compile(r"recording demo to \".*/(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})-(\d{3})_")
_PAUSE_RE = re.compile(r"\[6G Agent\] Decision #(\d+) at frame \d+ .*paused")
_V1_OUTCOME_RES = [("ordered_engineer (pre-fix)", re.compile(r"\[6G Agent\] Ordered engineer")),
                   ("queued_engineer (post-fix)", re.compile(r"\[6G Agent\] Queued engineer")),
                   ("skipped_invalid_position", re.compile(r"\[6G Agent\] Skipped: invalid build position")),
                   ("skipped_water", re.compile(r"\[6G Agent\] Skipped: position .* underwater")),
                   ("skipped_threat", re.compile(r"\[6G Agent\] Skipped: position .* threat zone"))]


# ----------------------------------------------------------------------------- v1 reconstruction
def _engine_seconds(line: str) -> Optional[float]:
    m = _T_RE.match(line)
    return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3)) if m else None


def gamelog_pauses(gamelog: Path) -> tuple:
    """-> (T0 Unix time of engine t=0 or None, {decision: engine seconds of the pause line}, Counter of v1 outcomes)."""
    T0, pauses, outcomes = None, {}, Counter()
    h = open_gamelog(gamelog)
    if h is None:
        return T0, pauses, outcomes
    for line in h:
        if T0 is None and "recording demo to" in line:
            m, ts = _DEMO_RE.search(line), _engine_seconds(line)
            if m and ts is not None:
                dt = datetime.strptime(m.group(1), "%Y-%m-%d_%H-%M-%S").replace(tzinfo=timezone.utc)
                T0 = dt.timestamp() + int(m.group(2)) / 1000.0 - ts
        if "[6G Agent]" in line:
            m = _PAUSE_RE.search(line)
            if m:
                ts = _engine_seconds(line)
                if ts is not None:
                    pauses.setdefault(int(m.group(1)), ts)
            for name, rx in _V1_OUTCOME_RES:
                if rx.search(line):
                    outcomes[name] += 1
    return T0, pauses, outcomes


def reconstructed_latencies(ep: Episode) -> list:
    """v1: per-decision reconstructed latency (s) or [] if the game log / anchor is missing."""
    g = ep.gamelog_path()
    if g is None:
        return []
    T0, pauses, _ = gamelog_pauses(g)
    if T0 is None:
        return []
    return [d["timestamp"] - (T0 + pauses[d["decision"]]) for d in ep.decisions if d["decision"] in pauses and "timestamp" in d]


# ----------------------------------------------------------------------------- per-decision extraction
def decision_latency(ep: Episode) -> tuple:
    """-> (list of latencies in s, source label)."""
    if ep.protocol == 2:
        if ep.is_llm:
            xs = [d["latency_s"] for d in ep.decisions if d.get("latency_s") is not None]
            return xs, "logged (latency_s)"
        xs = [d["decision_wall_s"] for d in ep.decisions if d.get("decision_wall_s") is not None]
        return xs, "logged (decision_wall_s)"
    return reconstructed_latencies(ep), "reconstructed"


def parse_statuses(ep: Episode) -> Counter:
    c = Counter()
    for d in ep.decisions:
        if ep.protocol == 2 and d.get("parse_status"):
            c[d["parse_status"]] += 1
        elif ep.protocol == 2:
            c["n/a (non-LLM)"] += 1
        else:
            r = (d.get("reasoning") or "").strip().lower()
            c[V1_INFERRED_ERROR if r.startswith("error") else V1_UNKNOWN] += 1
    c["syntax_invalid"] = sum(1 for d in ep.decisions if not action_syntax_valid(d["action"]))
    return c


def validation_outcomes(ep: Episode) -> Counter:
    if ep.protocol == 2:
        return Counter(ep.summary.get("validation_outcomes", {}))
    g = ep.gamelog_path()
    return gamelog_pauses(g)[2] if g else Counter()


# ----------------------------------------------------------------------------- analysis
def analyze(eps: list) -> Result:
    arms = defaultdict(list)
    for e in eps:
        arms[(e.campaign, e.backend, (e.model or "-").split("/")[-1])].append(e)
    res, N = Result(), Numbers()
    order = lambda kv: (kv[0][0],) + group_sort_key(("", kv[0][1])) + (kv[0][2],)

    t_lat = Table("tab_latency", caption="Decision latency per arm (seconds; unit = decision). v2 values are logged by the orchestrator; "
                  "v1 values are reconstructed from game-log and decision-log timestamps (see text) and include $\\approx$0.5\\,s polling overhead.",
                  columns=["Camp.", "Agent", "Model", "$N$ dec.", "Source", "Median", "Mean", "p90", "p99", "Max", "$>$60\\,s"],
                  colspec="lllrlrrrrrr", wide=True)
    t_ps = Table("tab_parse_status", caption="LLM output parsing outcomes per arm (counts; unit = decision). Invalid rate = "
                 "(fallback\\_noop + api\\_error + timeout)/$N$; `extracted' = action recovered by regex from a verbose reply. "
                 "Syntax-invalid = action string violating the bridge grammar (both campaigns).",
                 columns=["Camp.", "Agent", "Model", "$N$"] + [s.replace("_", "\\_") for s in PARSE_STATUSES] + ["Invalid (\\%)", "Extracted (\\%)", "Syntax-inv."],
                 colspec="lllr" + "r" * (len(PARSE_STATUSES) + 3), wide=True)
    all_outcomes = set()
    arm_outcomes = {}
    t_rt = Table("tab_runtime", caption="Run-time per episode (unit = episode): wall-clock and engine peak RSS (v2 from summary.json; "
                 "v1 wall-clock approximated by the decision-log span + 60\\,s, RSS not recorded).",
                 columns=["Camp.", "Agent", "Model", "$N$ ep.", "Decisions/ep.", "Wall-clock (s)", "Peak RSS (MB)"], colspec="lllrrrr")
    for key, lst in sorted(arms.items(), key=order):
        camp, be, model = key
        lat, src = [], None
        ps, out = Counter(), Counter()
        wall, rss = [], []
        for e in lst:
            xs, src = decision_latency(e)
            lat += xs
            ps.update(parse_statuses(e))
            out.update(validation_outcomes(e))
            if e.protocol == 2:
                if e.summary.get("wall_clock_s") is not None:
                    wall.append(e.summary["wall_clock_s"])
                if e.summary.get("peak_rss_mb") is not None:
                    rss.append(e.summary["peak_rss_mb"])
            elif len(e.decisions) >= 2 and "timestamp" in e.decisions[0]:
                wall.append(e.decisions[-1]["timestamp"] - e.decisions[0]["timestamp"] + DECISION_INTERVAL_S)
        n_dec = sum(len(e.decisions) for e in lst)
        arm_outcomes[key] = out
        all_outcomes |= set(out)
        lab = [camp, backend_label(be), model]
        if lat:
            t_lat.rows.append(lab + [f"{len(lat)}/{n_dec}", src, fmt(statistics.median(lat)), fmt(statistics.fmean(lat)),
                                     fmt(quantile(lat, 0.9)), fmt(quantile(lat, 0.99)), fmt(max(lat)),
                                     sum(1 for x in lat if x > DECISION_INTERVAL_S)])
        else:
            t_lat.rows.append(lab + [f"0/{n_dec}", src or "n/a", "n/a", "n/a", "n/a", "n/a", "n/a", "n/a"])
        k = f"latency_{camp}_{be}_{model}"
        N.add(k + "_n", len(lat), "decisions with a latency value", nd=0)
        N.add(k + "_median", statistics.median(lat) if lat else None, f"median decision latency (s), source={src}", n=len(lat))
        N.add(k + "_mean", statistics.fmean(lat) if lat else None, "mean decision latency (s)", n=len(lat))
        N.add(k + "_p90", quantile(lat, 0.9) if lat else None, "90th percentile latency (s)", n=len(lat))
        N.add(k + "_p99", quantile(lat, 0.99) if lat else None, "99th percentile latency (s)", n=len(lat))
        N.add(k + "_max", max(lat) if lat else None, "maximum latency (s)", n=len(lat))
        N.add(k + "_over_interval", sum(1 for x in lat if x > DECISION_INTERVAL_S), "decisions with latency > 60 s decision interval", nd=0)
        # parse status
        if camp == "v2" and lst[0].is_llm:
            inv = sum(ps[s] for s in INVALID_STATUSES)
            row = lab + [n_dec] + [ps.get(s, 0) for s in PARSE_STATUSES] + [fmt(100.0 * inv / n_dec if n_dec else None),
                                                                            fmt(100.0 * ps.get("extracted", 0) / n_dec if n_dec else None), ps["syntax_invalid"]]
            N.add(f"invalid_{camp}_{be}_{model}_rate_pct", 100.0 * inv / n_dec if n_dec else None, "invalid-output rate (%): fallback_noop+api_error+timeout over decisions", n=n_dec)
            N.add(f"invalid_{camp}_{be}_{model}_extracted_pct", 100.0 * ps.get("extracted", 0) / n_dec if n_dec else None, "share of decisions whose action was regex-extracted (%)", n=n_dec)
        elif camp == "v1" and lst[0].is_llm:
            err = ps.get(V1_INFERRED_ERROR, 0)
            row = lab + [n_dec, "n/a", "n/a", "n/a", f"{err} (inf.)", "n/a", fmt(100.0 * err / n_dec if n_dec else None) + " (lower bound)", "n/a", ps["syntax_invalid"]]
            N.add(f"invalid_{camp}_{be}_{model}_rate_pct", 100.0 * err / n_dec if n_dec else None, "inferred API-error rate (%) in v1 (lower bound of invalid outputs)", n=n_dec)
        else:
            row = lab + [n_dec] + ["n/a"] * len(PARSE_STATUSES) + ["n/a", "n/a", ps["syntax_invalid"]]
        N.add(f"invalid_{camp}_{be}_{model}_syntax", ps["syntax_invalid"], "actions violating the bridge grammar", nd=0)
        t_ps.rows.append(row)
        # runtime
        wm, ws = mean_sd(wall)
        rm, rs = mean_sd(rss)
        t_rt.rows.append(lab + [len(lst), fmt(n_dec / len(lst)), fmt_pm(wm, ws, 0) if wall else "n/a", fmt_pm(rm, rs, 0) if rss else "n/a"])
        N.add(f"runtime_{camp}_{be}_{model}_wall_s", wm, "mean episode wall-clock (s)", n=len(wall), nd=0)
        N.add(f"runtime_{camp}_{be}_{model}_peak_rss_mb", rm, "mean engine peak RSS (MB)", n=len(rss), nd=0)

    # validation outcomes table (columns = union of observed outcomes)
    cols = sorted(all_outcomes)
    t_val = Table("tab_validation_outcomes", caption="Bridge validation outcomes per arm (counts of decisions; v2 from summary.json, "
                  "v1 from game-log lines, available only for post-fix episodes).",
                  columns=["Camp.", "Agent", "Model", "$N$ dec."] + [c.replace("_", "\\_") for c in cols] if cols else ["Camp.", "Agent", "Model", "$N$ dec.", "outcomes"],
                  colspec="lllr" + "r" * max(1, len(cols)), wide=True)
    for key, lst in sorted(arms.items(), key=order):
        out = arm_outcomes[key]
        n_dec = sum(len(e.decisions) for e in lst)
        t_val.rows.append([key[0], backend_label(key[1]), key[2], n_dec] + ([out.get(c, 0) for c in cols] if cols else ["n/a"]))
        for c in cols:
            N.add(f"validation_{key[0]}_{key[1]}_{key[2]}_{c}", out.get(c, 0), f"bridge validation outcome '{c}' count", nd=0)
    if all(e.protocol == 2 for e in eps):      # single campaign: drop the campaign column and the cross-campaign wording
        for t in (t_lat, t_ps, t_val, t_rt):
            t.columns = t.columns[1:]
            t.rows = [r[1:] for r in t.rows]
            t.colspec = t.colspec[1:] if t.colspec else None
        t_lat.caption = ("Decision latency per arm (seconds; unit = decision), logged by the orchestrator as the time between sending the "
                         "observation and receiving the reply; for the non-LLM agents the agent's compute time.")
        t_ps.caption = ("LLM output parsing outcomes per arm (counts; unit = decision). Invalid rate = (fallback\\_noop + api\\_error + timeout)/$N$; "
                        "`extracted' = action recovered by regex from a verbose reply; syntax-invalid = action string violating the bridge grammar.")
        t_val.caption = "Validation outcome of every decision by the execution layer, per arm (counts of decisions)."
        t_rt.caption = "Run-time per episode (unit = episode): wall-clock time of the headless engine and its peak resident memory."
    res.tables = [t_lat, t_ps, t_val, t_rt]
    res.numbers = N
    res.markdown = "\n".join(["## Latency", "", t_lat.to_markdown(), "", "## Parse status / invalid outputs", "", t_ps.to_markdown(), "",
                              "## Bridge validation outcomes", "", t_val.to_markdown(), "", "## Run-time", "", t_rt.to_markdown()])
    res.extra = dict(arms={k: decision_latency_all(v) for k, v in arms.items()})
    return res


def decision_latency_all(lst: list) -> dict:
    lat, src = [], None
    for e in lst:
        xs, src = decision_latency(e)
        lat += xs
    return dict(latencies=lat, source=src, n_decisions=sum(len(e.decisions) for e in lst))


def main():
    ap = add_common_args(argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter),
                         default_out=REPO / "agent" / "analysis" / "revision" / "out" / "latency")
    a = ap.parse_args()
    eps = load_campaign(a)
    res = analyze(eps)
    res.markdown = campaign_note(a, eps) + "\n\n" + res.markdown
    print(res.markdown)
    res.write(Path(a.out_dir), "latency_invalid")
    print(f"\nwritten to {a.out_dir}")


if __name__ == "__main__":
    main()
