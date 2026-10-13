#!/usr/bin/env python3
"""
Paper figures for the revision -> paper_major_revision/figures/<name>.pdf and .png (300 dpi).

Design rules (dataviz skill, applied before any plotting code was written)
  * One categorical palette keyed by BACKEND, fixed slot order, never cycled:
      llm #2a78d6 (blue) | rule #eb6834 (orange) | llm_nospatial #1baf7a (aqua) | llm_minimal #eda100 (yellow)
      | random #e87ba4 (magenta) | noop #008300 (green) | replay #4a3aa7 (violet)
    Validated with scripts/validate_palette.js on the paper's white surface (#ffffff), light mode:
      adjacent pairs : lightness PASS, chroma PASS, CVD dE 9.1 PASS, normal-vision dE 19.6 PASS,
                       contrast WARN (aqua 2.82, yellow 2.17, magenta 2.69 < 3:1) -> relief = legend + tables
      all pairs (6)  : FAIL (green-orange CVD 3.2; magenta-orange 12.9) -> secondary encoding is mandatory:
                       every backend has its own marker shape, and every legend entry carries N.
  * Fonts >= 9 pt everywhere (rcParams), 2 px lines, markers >= 8 px, hairline solid grid one step off the surface,
    threshold lines dashed (they ARE thresholds) and labelled, CI bands = series hue at ~12 % opacity.
  * No dual axes; one measure per panel; no titles inside the figure (captions live in LaTeX).
  * Every figure degrades gracefully: missing groups are skipped, an empty figure is not written and the reason is printed.

Figures
  fig_coverage_<scenario>      coverage vs decision epoch, mean + 95 % t-CI band per backend, 80 % threshold
  fig_coverage_grid            small multiples of the above for all scenarios present
  fig_qos_peakload_<scenario>  per-slice peak offered load (max over BS) vs epoch, axis "offered load (share of capacity, %)", 80 % overload line
  fig_regret_events_<scenario> regret events per episode over decision epoch (3-epoch bins), per backend
  fig_regret_validation        estimated vs exact counterfactual gain scatter (only with --mapping)
  fig_latency                  latency distribution per arm (box + points, log axis), 60 s decision interval marked
  fig_threshold                epochs >= 80 % and below-threshold area per scenario x backend, bootstrap CI error bars

Usage: make_figures.py --campaign v1|v2|all [--out-dir DIR] [--min-decisions K] [--mapping branches.csv] [--only name,...]
"""
from __future__ import annotations
import argparse, math, statistics
from collections import defaultdict
from pathlib import Path
from typing import Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from load_runs import Episode, group
from common import (add_common_args, load_campaign, backend_label, scenario_label, backend_sort_key, scenario_sort_key,
                    mean_ci_t, DEFAULT_FIGURES_DIR, REPO)
import regret as regret_mod
import latency_invalid as lat_mod
import threshold_metrics as thr_mod

PALETTE = {"llm": "#2a78d6", "rule": "#eb6834", "llm_nospatial": "#1baf7a", "llm_minimal": "#eda100", "random": "#e87ba4",
           "noop": "#008300", "replay": "#4a3aa7", "llm_v3test": "#e34948", "greedy": "#7b3fa0"}
MARKERS = {"llm": "o", "rule": "s", "llm_nospatial": "^", "llm_minimal": "v", "random": "D", "noop": "X", "replay": "P", "llm_v3test": "*", "greedy": "h"}
INK, MUTED, GRID, BASELINE, SURFACE = "#0b0b0b", "#898781", "#e1e0d9", "#c3c2b7", "#ffffff"
FALLBACK = "#898781"
SINGLE_W, FULL_W, H = 3.5, 7.0, 2.7
THR = 80.0


def setup_style():
    plt.rcParams.update({
        "font.size": 9, "axes.labelsize": 9, "axes.titlesize": 9, "xtick.labelsize": 9, "ytick.labelsize": 9,
        "legend.fontsize": 9, "font.family": "sans-serif", "font.sans-serif": ["DejaVu Sans", "Arial", "Helvetica"],
        "axes.edgecolor": BASELINE, "axes.linewidth": 0.8, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6,
        "grid.linestyle": "-", "axes.axisbelow": True, "xtick.color": MUTED, "ytick.color": MUTED, "axes.labelcolor": INK,
        "text.color": INK, "legend.frameon": False, "lines.linewidth": 1.5, "lines.markersize": 4.5, "figure.dpi": 100,
        "savefig.dpi": 300, "pdf.fonttype": 42, "ps.fonttype": 42, "axes.spines.top": False, "axes.spines.right": False,
        "figure.facecolor": SURFACE, "axes.facecolor": SURFACE})


def colour(be: str) -> str:
    return PALETTE.get(be, FALLBACK)


def marker(be: str) -> str:
    return MARKERS.get(be, ".")


def save(fig, out_dir: Path, name: str) -> list:
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for ext in ("pdf", "png"):
        p = out_dir / f"{name}.{ext}"
        fig.savefig(p, bbox_inches="tight", dpi=300 if ext == "png" else None)
        paths.append(p)
    plt.close(fig)
    print(f"  wrote {paths[0].name} / .png")
    return paths


# ----------------------------------------------------------------------------- series helpers
def epoch_series(series_list: list) -> Optional[dict]:
    """Per-epoch mean and 95 % t-CI over episodes (epochs with >= 2 episodes get a band)."""
    if not series_list:
        return None
    T = max(len(s) for s in series_list)
    x, mean, lo, hi, n = [], [], [], [], []
    for t in range(T):
        vals = [s[t] for s in series_list if len(s) > t]
        if not vals or (len(series_list) >= 2 and len(vals) < 2):
            continue
        x.append(t + 1)
        mean.append(statistics.fmean(vals))
        n.append(len(vals))
        ci = mean_ci_t(vals)
        lo.append(ci[0] if ci else float("nan"))
        hi.append(ci[1] if ci else float("nan"))
    return dict(x=np.array(x), mean=np.array(mean), lo=np.array(lo), hi=np.array(hi), n=n, N=len(series_list))


def draw_series(ax, be: str, s: dict, label_extra: str = ""):
    c = colour(be)
    ax.plot(s["x"], s["mean"], color=c, marker=marker(be), markevery=max(1, len(s["x"]) // 10), markeredgecolor=SURFACE,
            markeredgewidth=0.6, label=f"{backend_label(be)}{label_extra} (N={s['N']})", zorder=3)
    if s["N"] >= 2 and not np.all(np.isnan(s["lo"])):
        ax.fill_between(s["x"], s["lo"], s["hi"], color=c, alpha=0.12, linewidth=0, zorder=2)


def threshold_line(ax, y: float, text: str):
    """Dashed threshold line; labelled through the legend (never free text over the data)."""
    ax.axhline(y, color=MUTED, linestyle="--", linewidth=0.9, zorder=1, label=text)


def legend_below(ax, ncol: int = 2, **kw):
    """Legend under the axes so it can never collide with the data."""
    return ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=ncol, handlelength=2.2, columnspacing=1.2, **kw)


def shared_legend_below(fig, ax, ncol: int = 4):
    """One legend for a multi-panel figure, directly under the panels (space reserved by row count)."""
    handles, labels = ax.get_legend_handles_labels()
    ncol = min(ncol, max(1, len(labels)))
    rows = math.ceil(len(labels) / ncol)
    fig.legend(handles, labels, loc="lower center", bbox_to_anchor=(0.5, 0.0), ncol=ncol, handlelength=2.2, columnspacing=1.2)
    fig.tight_layout(rect=(0, 0.04 + 0.075 * rows, 1, 1))


def scenario_short(s: str) -> str:
    return s.split("_")[0].upper() if s.startswith("s") and "_" in s else scenario_label(s)


# ----------------------------------------------------------------------------- figures
def fig_coverage(eps: list, scenario: str, out_dir: Path, thr: float = THR, ax=None) -> list:
    g = {be: lst for (sc, be), lst in group(eps).items() if sc == scenario}
    if not g:
        print(f"  fig_coverage_{scenario}: n/a (no episodes)")
        return []
    own = ax is None
    if own:
        fig, ax = plt.subplots(figsize=(SINGLE_W, H))
    for be in sorted(g, key=backend_sort_key):
        s = epoch_series([e.coverage_series() for e in g[be]])
        if s is not None:
            draw_series(ax, be, s)
    ax.set_ylim(0, 105)
    ax.set_xlim(left=1)
    ax.set_xlabel("Decision epoch (1 epoch = 60 s simulated)")
    ax.set_ylabel("Coverage (% of mobile units)")
    threshold_line(ax, thr, f"{thr:g} % intent threshold")
    legend_below(ax, ncol=2)
    if own:
        return save(fig, out_dir, f"fig_coverage_{scenario}")
    ax.set_title(scenario_label(scenario), loc="left", color=INK)
    return []


def fig_coverage_grid(eps: list, out_dir: Path, thr: float = THR) -> list:
    scenarios = sorted({e.scenario for e in eps}, key=scenario_sort_key)
    if len(scenarios) < 2:
        print("  fig_coverage_grid: n/a (fewer than two scenarios)")
        return []
    ncol = 2
    nrow = math.ceil(len(scenarios) / ncol)
    fig, axes = plt.subplots(nrow, ncol, figsize=(FULL_W, H * nrow * 1.25), sharey=True, squeeze=False)
    for ax, sc in zip(axes.flat, scenarios):
        fig_coverage(eps, sc, out_dir, thr, ax=ax)
    for ax in list(axes.flat)[len(scenarios):]:
        ax.axis("off")
    fig.tight_layout(h_pad=2.5)
    return save(fig, out_dir, "fig_coverage_grid")


def peak_load_series(ep: Episode, field: str) -> Optional[list]:
    if not any(d.get("base_stations") for d in ep.decisions):
        return None
    return [max((b.get(field, 0) for b in d.get("base_stations") or []), default=0) for d in ep.decisions]


def fig_qos_peakload(eps: list, scenario: str, out_dir: Path, thr: float = THR) -> list:
    g = {be: lst for (sc, be), lst in group(eps).items() if sc == scenario}
    slices = [("load_embb", "eMBB"), ("load_urllc", "URLLC"), ("load_mmtc", "mMTC")]
    fig, axes = plt.subplots(1, 3, figsize=(FULL_W, H), sharey=True)
    drawn = False
    for ax, (field, name) in zip(axes, slices):
        for be in sorted(g, key=backend_sort_key):
            series = [s for s in (peak_load_series(e, field) for e in g[be]) if s is not None]
            s = epoch_series(series)
            if s is not None:
                draw_series(ax, be, s)
                drawn = True
        ax.set_xlabel("Decision epoch")
        ax.set_title(name, loc="left", color=INK)
        ax.set_xlim(left=1)
    if not drawn:
        plt.close(fig)
        print(f"  fig_qos_peakload_{scenario}: n/a (no base_stations records)")
        return []
    ymax = max(ax.get_ylim()[1] for ax in axes)
    for ax in axes:
        ax.set_ylim(0, max(110, ymax))
        threshold_line(ax, thr, f"{thr:g} % overload")
    axes[0].set_ylabel("Peak offered load\n(% of slice capacity)")
    shared_legend_below(fig, axes[0], ncol=4)
    return save(fig, out_dir, f"fig_qos_peakload_{scenario}")


def fig_regret_events(eps: list, scenario: str, out_dir: Path, bin_epochs: int = 3) -> list:
    """Regret events per episode over decision time, per backend, binned in windows of bin_epochs epochs."""
    sel = [e for e in eps if e.scenario == scenario]
    rows, events = regret_mod.summarise(sel)
    if not events:
        print(f"  fig_regret_events_{scenario}: n/a (no regret events)")
        return []
    fig, ax = plt.subplots(figsize=(SINGLE_W, H))
    n_eps = defaultdict(set)
    for e in sel:
        n_eps[e.backend].add(e.episode_id)
    by_be = defaultdict(list)
    for ev in events:
        by_be[ev["backend"]].append(ev["decision"])
    T = max(e.n_decisions() for e in sel)
    edges = np.arange(0.5, T + bin_epochs + 0.5, bin_epochs)
    for be in sorted(by_be, key=backend_sort_key):
        hist, _ = np.histogram(by_be[be], bins=edges)
        ax.plot(edges[:-1] + bin_epochs / 2, hist / max(1, len(n_eps[be])), color=colour(be), marker=marker(be), markeredgecolor=SURFACE,
                markeredgewidth=0.6, drawstyle="steps-mid", label=f"{backend_label(be)} (N={len(n_eps[be])} ep., {len(by_be[be])} ev.)")
    ax.set_xlabel(f"Decision epoch of the coverage drop ({bin_epochs}-epoch bins)")
    ax.set_ylabel("Regret events per episode")
    ax.set_xlim(1, T)
    ax.set_ylim(bottom=0)
    legend_below(ax, ncol=2)
    return save(fig, out_dir, f"fig_regret_events_{scenario}")


def fig_regret_validation(mapping_rows: Optional[list], out_dir: Path) -> list:
    """Estimated vs exact counterfactual gain (needs re-simulated branches)."""
    ok = [r for r in (mapping_rows or []) if r.get("status") == "ok" and r.get("exact_gain_t") is not None]
    if not ok:
        print("  fig_regret_validation: n/a (no re-simulated branches with an exact gain; pass --mapping)")
        return []
    fig, ax = plt.subplots(figsize=(SINGLE_W, H))
    for est, lab, mk, be in (("est_v2_gain", "geometric", "o", "llm"), ("est_legacy_gain", "fixed-fraction (30 %)", "s", "rule")):
        pts = [(r[est], r["exact_gain_t"]) for r in ok if r.get(est) is not None]
        if pts:
            ax.scatter([p[0] for p in pts], [p[1] for p in pts], s=30, marker=mk, color=colour(be), edgecolor=SURFACE, linewidth=0.6,
                       label=f"{lab} (N={len(pts)})", zorder=3)
    lim = max([abs(v) for r in ok for v in (r.get("est_v2_gain") or 0, r.get("est_legacy_gain") or 0, r["exact_gain_t"])] + [1.0]) * 1.1
    ax.plot([-lim, lim], [-lim, lim], color=MUTED, linestyle="--", linewidth=0.9, zorder=1, label="estimate = exact")
    ax.set_xlim(-lim * 0.1, lim)
    ax.set_ylim(-lim * 0.3, lim)
    ax.set_xlabel("Estimated coverage gain at $k_0+2$ (pp)")
    ax.set_ylabel("Exact gain from re-simulation (pp)")
    legend_below(ax, ncol=2)
    return save(fig, out_dir, "fig_regret_validation")


def fig_latency(eps: list, out_dir: Path) -> list:
    arms = defaultdict(list)
    for e in eps:
        arms[(e.campaign, e.backend, (e.model or "").split("/")[-1])].append(e)
    data = []
    for key in sorted(arms, key=lambda k: (k[0],) + backend_sort_key(k[1]) + (k[2],)):
        d = lat_mod.decision_latency_all(arms[key])
        xs = [x for x in d["latencies"] if x is not None and x > 0]
        if xs:
            lab = f"{backend_label(key[1])}" + (f" / {key[2]}" if key[2] else "") + f" [{key[0]}, {d['source'].split(' ')[0]}] (N={len(xs)})"
            data.append((key, lab, xs))
    if not data:
        print("  fig_latency: n/a (no positive latency values)")
        return []
    fig, ax = plt.subplots(figsize=(FULL_W, 0.45 * len(data) + 1.2))
    rng = np.random.default_rng(1)
    for i, (key, lab, xs) in enumerate(data):
        c = colour(key[1])
        ax.boxplot([xs], positions=[i], vert=False, widths=0.5, showfliers=False, patch_artist=True,
                   boxprops=dict(facecolor=c, alpha=0.25, edgecolor=c), medianprops=dict(color=c, linewidth=1.8),
                   whiskerprops=dict(color=c), capprops=dict(color=c))
        sub = rng.choice(xs, size=min(len(xs), 150), replace=False)
        ax.scatter(sub, i + rng.uniform(-0.18, 0.18, len(sub)), s=9, color=c, alpha=0.5, edgecolor="none", zorder=3)
    ax.set_yticks(range(len(data)))
    ax.set_yticklabels([d[1] for d in data])
    ax.set_xscale("log")
    ax.set_xlabel("Decision latency (s, log scale)")
    ax.axvline(60, color=MUTED, linestyle="--", linewidth=0.9)
    ax.text(60, len(data) - 0.4, "60 s decision interval", color=MUTED, fontsize=9, ha="right", va="top", rotation=90)
    ax.grid(True, axis="x")
    ax.grid(False, axis="y")
    fig.tight_layout()
    return save(fig, out_dir, "fig_latency")


def fig_threshold(eps: list, out_dir: Path, thr: float = THR) -> list:
    rows = thr_mod.group_rows(eps, thr)
    if not rows:
        print("  fig_threshold: n/a (no episodes)")
        return []
    scenarios = sorted({r["scenario"] for r in rows}, key=scenario_sort_key)
    backends = sorted({r["backend"] for r in rows}, key=backend_sort_key)
    fig, axes = plt.subplots(1, 2, figsize=(FULL_W, H))
    width = min(0.8 / max(1, len(backends)), 0.18)
    for ax, (metric, ylabel) in zip(axes, (("frac_ge", f"Epochs with coverage ≥ {thr:g} %\n(% of epochs)"), ("area_below", "Below-threshold area\n(pp · epochs)"))):
        for j, be in enumerate(backends):
            xs, ys, err_lo, err_hi, ns = [], [], [], [], []
            for i, sc in enumerate(scenarios):
                r = next((r for r in rows if r["scenario"] == sc and r["backend"] == be), None)
                if r is None or r[metric]["mean"] is None:
                    continue
                xs.append(i + (j - (len(backends) - 1) / 2) * width)
                ys.append(r[metric]["mean"])
                ci = r[metric]["ci"] or (r[metric]["mean"], r[metric]["mean"])
                err_lo.append(max(0.0, r[metric]["mean"] - ci[0]))
                err_hi.append(max(0.0, ci[1] - r[metric]["mean"]))
                ns.append(r["n"])
            if xs:
                n_total = sum(r["n"] for r in rows if r["backend"] == be)
                ax.bar(xs, ys, width=width * 0.9, color=colour(be), edgecolor=SURFACE, linewidth=0.8,
                       yerr=[err_lo, err_hi], error_kw=dict(ecolor=INK, elinewidth=0.8, capsize=2),
                       label=f"{backend_label(be)} (N={n_total} ep.)")
        ax.set_xticks(range(len(scenarios)))
        ax.set_xticklabels([scenario_short(s) for s in scenarios])
        ax.set_ylabel(ylabel)
        ax.grid(False, axis="x")
    shared_legend_below(fig, axes[0], ncol=4)
    return save(fig, out_dir, "fig_threshold")


def make_all(eps: list, out_dir: Path, mapping_rows: Optional[list] = None, only: Optional[set] = None, thr: float = THR) -> list:
    setup_style()
    out_dir = Path(out_dir)
    written = []
    scenarios = sorted({e.scenario for e in eps}, key=scenario_sort_key)
    want = lambda name: only is None or name in only
    if want("coverage"):
        for sc in scenarios:
            written += fig_coverage(eps, sc, out_dir, thr)
        written += fig_coverage_grid(eps, out_dir, thr)
    if want("qos"):
        for sc in scenarios:
            written += fig_qos_peakload(eps, sc, out_dir, thr)
    if want("regret"):
        for sc in scenarios:
            written += fig_regret_events(eps, sc, out_dir)
        written += fig_regret_validation(mapping_rows, out_dir)
    if want("latency"):
        written += fig_latency(eps, out_dir)
    if want("threshold"):
        written += fig_threshold(eps, out_dir, thr)
    return written


def main():
    ap = add_common_args(argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter),
                         default_out=DEFAULT_FIGURES_DIR)
    ap.add_argument("--mapping", default=None, help="regret re-simulation mapping (see regret.py)")
    ap.add_argument("--only", default=None, help="comma list of: coverage,qos,regret,latency,threshold")
    ap.add_argument("--threshold", type=float, default=THR)
    a = ap.parse_args()
    eps = load_campaign(a)
    print(f"{len(eps)} episodes (campaign={a.campaign})")
    mapping_rows = regret_mod.exact_regret_rows(regret_mod.load_mapping(a.mapping), a.min_decisions) if a.mapping else None
    written = make_all(eps, Path(a.out_dir), mapping_rows, set(a.only.split(",")) if a.only else None, a.threshold)
    print(f"{len(written)} files written to {a.out_dir}")


if __name__ == "__main__":
    main()
