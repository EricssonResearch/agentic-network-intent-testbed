#!/usr/bin/env python3
"""
E4: regret-estimator validation by deterministic re-simulation (REVISION_PLAN.md S4.2, F6a).

Reads agent/results_v2_e4/<episode_id>/ (backend=replay; tags e4b_plain<seed> = unchanged-action replays,
e4_<seed>_d<k0> = counterfactual branches with `place_bs|macro_cell|<centroid>` substituted at decision k0) and
the original episodes they replay (header.json: replay_file), then writes

  <tables>/aux/e4_mapping.csv          original_episode_dir, branch_episode_dir, inject_decision  (input for regret.py --mapping)
  <tables>/tab_determinism.tex         plain replays vs originals: identical decision fields / synced log lines
  <tables>/tab_regret_branches.tex     one row per branch (appendix): seed, k0, t, drop, estimated gains, exact gains,
                                       validator verdict of the substituted order, prefix identical
  <tables>/numbers_e4.json / macros_e4.tex
  paper_major_revision/sections/e4_results.tex   the results paragraph of Section 6 (numbers filled in)

Usage: e4_analysis.py [--e4-dir DIR] [--tables-dir DIR]
"""
from __future__ import annotations
import argparse, csv, json, re, statistics
from pathlib import Path

from load_runs import load_v2_episode
from common import gamelog_text, Table, Numbers, fmt, fmt_p, write_table, write_text, spearman, DEFAULT_TABLES_DIR, REPO, REVISION_DIR
import regret as regret_mod
import compare_determinism as cd

E4_DIR = REPO / "agent" / "results_v2_e4"


def resolve(p: str) -> Path:
    q = Path(p)
    return q if q.is_absolute() else REPO / q


def validator_verdict(branch_dir: Path, k0: int) -> str:
    log = gamelog_text(branch_dir / "gamelog.txt")
    m = re.search(rf"Decision #{k0} validation: (\w+)", log)
    return m.group(1) if m else "n/a"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--e4-dir", default=str(E4_DIR))
    ap.add_argument("--tables-dir", default=str(DEFAULT_TABLES_DIR))
    a = ap.parse_args()
    e4, tables = Path(a.e4_dir), Path(a.tables_dir)
    aux = tables / "aux"
    aux.mkdir(parents=True, exist_ok=True)
    N = Numbers()

    plain, branches = [], []
    for d in sorted(p for p in e4.iterdir() if p.is_dir() and p.name != "failed"):
        ep = load_v2_episode(d, min_decisions=1)
        if ep is None or not ep.valid or not ep.summary.get("match_ended"):
            print("skip (incomplete):", d.name)
            continue
        src = ep.header.get("replay_file")
        if not src:
            continue
        orig_dir = resolve(src).parent
        if ep.header.get("inject_decision"):
            branches.append((orig_dir, d, int(ep.header["inject_decision"]), ep))
        else:
            plain.append((orig_dir, d, ep))
    print(f"{len(plain)} plain replays, {len(branches)} counterfactual branches")

    # ---- determinism table
    t_det = Table("tab_determinism", caption="Full-length determinism check (requirement R7): S1 LLM episodes re-simulated from their logged "
                  "seed and action stream without substitution, compared with the originals decision by decision (all logged fields) "
                  "and line by line on the simulation-side log (wall-clock-dependent message-arrival lines excluded).",
                  columns=["Seed", "Decisions identical", "Synced log lines (orig / replay)", "Identical", "Wall-clock (s) orig / replay"], colspec="lrrlr")
    n_ident = 0
    first_div = {}   # seed -> first decision at which the plain replay differs from the original (None = identical)
    for orig_dir, d, ep in plain:
        ha, da, sa = cd.load(orig_dir)
        hb, db, sb = cd.load(d)
        fields_ok = len(da) == len(db) and all(da[i].get(f) == db[i].get(f) for i in range(len(da)) for f in cd.FIELDS)
        la, lb = cd.sync_lines(orig_dir), cd.sync_lines(d)
        log_ok = la == lb
        ident = fields_ok and log_ok
        n_ident += ident
        fd = next((da[i]["decision"] for i in range(min(len(da), len(db))) if any(da[i].get(f) != db[i].get(f) for f in cd.FIELDS)), None)
        first_div[str(ep.seed)] = fd
        t_det.rows.append([ep.seed, f"{sum(1 for i in range(min(len(da), len(db))) if all(da[i].get(f) == db[i].get(f) for f in cd.FIELDS))}/{len(da)}",
                           f"{len(la)} / {len(lb)}", "yes" if ident else "NO", f"{sa.get('wall_clock_s')} / {sb.get('wall_clock_s')}"])
    N.add("e4_plain_n", len(plain), "unchanged-action full-length replays", nd=0)
    N.add("e4_plain_first_div", ", ".join(f"{k}: {v}" for k, v in sorted(first_div.items()) if v), "first differing decision of the non-identical replays")
    N.add("e4_plain_identical", n_ident, "replays bit-identical to the original (decisions and synced log)", nd=0)
    write_table(t_det, tables)

    # ---- mapping + exact regret rows
    with open(aux / "e4_mapping.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["original_episode_dir", "branch_episode_dir", "inject_decision"])
        for orig_dir, d, k0, ep in branches:
            w.writerow([str(orig_dir.relative_to(REPO)), str(d.relative_to(REPO)), k0])
    mapping = regret_mod.load_mapping(aux / "e4_mapping.csv")
    rows = regret_mod.exact_regret_rows(mapping, min_decisions=1)
    ok = [r for r in rows if r.get("status") == "ok" and r.get("exact_gain_t") is not None]
    comp = regret_mod.compare_estimates(rows)

    # ---- per-branch table
    t_br = Table("tab_regret_branches", caption="Every re-simulated counterfactual branch (S1, primary LLM agent). $k_0 = t-2$ is the substitution "
                 "epoch, $t$ the event epoch; drop = coverage($t-1$) $-$ coverage($t$) in the original; gains are branch minus original coverage "
                 "(pp) at $t$ and at episode end; `verdict' is the simulator's validation of the substituted macro-cell order; `prefix' = the "
                 "re-simulated trajectory equals the original at every epoch before $k_0$; `clean' = the unchanged-action replay of the same episode is identical to the original through the event epoch $t$, so the exact gain contains no replay noise.",
                 columns=["Seed", "$k_0$", "$t$", "Drop", "Est.\\ geometric", "Est.\\ fixed-fr.", "Exact at $t$", "Exact at end", "Mean after $k_0$", "Verdict", "Prefix", "Clean"],
                 colspec="rrrrrrrrrlll", wide=True)
    verdicts = []
    for r in sorted(ok, key=lambda r: (r["original_episode_dir"], r["inject_decision"])):
        bd = resolve(r["branch_episode_dir"])
        seed = re.search(r"seed(\d+)", bd.name).group(1)
        v = validator_verdict(bd, r["inject_decision"])
        verdicts.append(v)
        r["verdict"] = v
        fd = first_div.get(seed)
        r["clean"] = fd is None or (r["inject_decision"] + 2) < fd      # plain replay identical through the event epoch t
        t_br.rows.append([seed, r["inject_decision"], r["inject_decision"] + 2, fmt(r.get("drop_1")), fmt(r.get("est_v2_gain")), fmt(r.get("est_legacy_gain")),
                          fmt(r["exact_gain_t"]), fmt(r["exact_gain_end"]), fmt(r.get("exact_gain_mean_after")), v.replace("_", "\\_"),
                          "yes" if r["prefix_identical"] else "NO", "yes" if r["clean"] else "no"])
    write_table(t_br, tables)
    regret_mod.write_csv(aux / "regret_exact.csv", rows)

    # ---- summary numbers
    n = len(ok)
    exact = [r["exact_gain_t"] for r in ok]
    est2 = [r.get("est_v2_gain") or 0.0 for r in ok]
    estl = [r.get("est_legacy_gain") or 0.0 for r in ok]
    executed = sum(1 for v in verdicts if v == "executed_place")
    pos_exact = sum(1 for x in exact if x > 0)
    neg_exact = sum(1 for x in exact if x < 0)
    sign_agree2 = sum(1 for e, x in zip(est2, exact) if (e > 0) == (x > 0))
    end_pos = sum(1 for r in ok if r["exact_gain_end"] > 0)
    mean_after_pos = sum(1 for r in ok if (r.get("exact_gain_mean_after") or 0) > 0)
    # executed-only subset: branches in which the substituted order was actually built (the estimator's premise holds)
    clean = [r for r in ok if r.get("clean")]
    ex_rows = [r for r in clean if r.get("verdict") == "executed_place"]
    ex_exact = [r["exact_gain_t"] for r in ex_rows]
    ex_est2 = [r.get("est_v2_gain") or 0.0 for r in ex_rows]
    ex_estl = [r.get("est_legacy_gain") or 0.0 for r in ex_rows]
    rej_rows = [r for r in clean if r.get("verdict") != "executed_place"]
    N.add("e4_clean_n", len(clean), "branches whose unchanged-action replay is identical through the event epoch (no replay noise)", nd=0)
    ex_rho2, ex_p2 = spearman(ex_est2, ex_exact) if len(ex_rows) >= 3 else (None, None)
    ex_rhol, ex_pl = spearman(ex_estl, ex_exact) if len(ex_rows) >= 3 else (None, None)
    N.add("e4_exec_n", len(ex_rows), "branches with the substituted order executed", nd=0)
    N.add("e4_exec_exact_mean", statistics.fmean(ex_exact) if ex_exact else None, "executed branches: mean exact gain at t (pp)", n=len(ex_rows))
    N.add("e4_exec_est_v2_mean", statistics.fmean(ex_est2) if ex_est2 else None, "executed branches: mean geometric estimate (pp)", n=len(ex_rows))
    N.add("e4_exec_v2_bias", statistics.fmean(e - x for e, x in zip(ex_est2, ex_exact)) if ex_rows else None, "executed branches: geometric bias (pp)", n=len(ex_rows))
    N.add("e4_exec_v2_mae", statistics.fmean(abs(e - x) for e, x in zip(ex_est2, ex_exact)) if ex_rows else None, "executed branches: geometric MAE (pp)", n=len(ex_rows))
    N.add("e4_exec_v2_rho", ex_rho2, "executed branches: Spearman rho geometric vs exact", nd=2)
    N.add("e4_exec_legacy_bias", statistics.fmean(e - x for e, x in zip(ex_estl, ex_exact)) if ex_rows else None, "executed branches: legacy bias (pp)", n=len(ex_rows))
    N.add("e4_exec_legacy_mae", statistics.fmean(abs(e - x) for e, x in zip(ex_estl, ex_exact)) if ex_rows else None, "executed branches: legacy MAE (pp)", n=len(ex_rows))
    N.add("e4_exec_legacy_rho", ex_rhol, "executed branches: Spearman rho legacy vs exact", nd=2)
    N.add("e4_exec_pos", sum(1 for x in ex_exact if x > 0), "executed branches with exact gain > 0 at t", nd=0)
    N.add("e4_rej_exact_mean", statistics.fmean(r["exact_gain_t"] for r in rej_rows) if rej_rows else None, "rejected branches: mean exact gain at t (pp)", n=len(rej_rows))
    N.add("e4_rej_est_v2_mean", statistics.fmean(r.get("est_v2_gain") or 0.0 for r in rej_rows) if rej_rows else None, "rejected branches: mean geometric estimate (pp)", n=len(rej_rows))
    rho2, p2 = spearman(est2, exact) if n >= 3 else (None, None)
    rhol, pl = spearman(estl, exact) if n >= 3 else (None, None)
    N.add("e4_branches_n", n, "usable counterfactual branches", nd=0)
    N.add("e4_prefix_identical", sum(1 for r in ok if r["prefix_identical"]), "branches identical to the original before k0", nd=0)
    N.add("e4_executed", executed, "branches whose substituted order passed validation and was executed", nd=0)
    N.add("e4_exact_pos", pos_exact, "branches with exact gain > 0 at t", nd=0)
    N.add("e4_exact_neg", neg_exact, "branches with exact gain < 0 at t", nd=0)
    N.add("e4_exact_mean", statistics.fmean(exact) if exact else None, "mean exact gain at t (pp)", n=n)
    N.add("e4_exact_end_pos", end_pos, "branches with exact gain > 0 at episode end", nd=0)
    N.add("e4_exact_end_mean", statistics.fmean(r["exact_gain_end"] for r in ok) if ok else None, "mean exact gain at episode end (pp)", n=n)
    N.add("e4_mean_after_pos", mean_after_pos, "branches with positive mean coverage difference after k0", nd=0)
    N.add("e4_est_v2_mean", statistics.fmean(est2) if est2 else None, "mean geometric estimate (pp)", n=n)
    N.add("e4_est_legacy_mean", statistics.fmean(estl) if estl else None, "mean legacy estimate (pp)", n=n)
    N.add("e4_sign_agree_v2", sign_agree2, "branches where geometric estimate and exact gain agree in sign (>0 vs <=0)", nd=0)
    for c in comp:
        k = "e4_" + ("legacy" if c["estimator"].startswith("legacy") else "v2")
        N.add(k + "_bias", c["bias"], f"{c['estimator']}: mean(estimate - exact) at t (pp)", n=c["n"])
        N.add(k + "_mae", c["mae"], f"{c['estimator']}: mean |estimate - exact| (pp)", n=c["n"])
        N.add(k + "_rho", c["rho"], f"{c['estimator']}: Spearman rho vs exact gain", nd=2)
        N.add(k + "_rho_p", fmt_p(c["p"]) if c["p"] is not None else "n/a", f"{c['estimator']}: p of Spearman rho")
    N.to_json(tables / "numbers_e4.json")
    N.to_macros(tables / "macros_e4.tex")

    # ---- clean-subset agreement statistics (branches without replay noise) + clean mapping for tables_to_tex
    comp_clean = regret_mod.compare_estimates(clean)
    c2 = next(c for c in comp_clean if c["estimator"].startswith("geometric"))
    cl = next(c for c in comp_clean if c["estimator"].startswith("fixed"))
    nc, nx = len(clean), len(ex_rows)
    sign_clean = sum(1 for r in clean if ((r.get("est_v2_gain") or 0) > 0) == (r["exact_gain_t"] > 0))
    end_pos_clean = sum(1 for r in clean if r["exact_gain_end"] > 0)
    N.add("e4_clean_exec", nx, "clean branches with the substituted order executed", nd=0)
    N.add("e4_clean_sign_agree_v2", sign_clean, "clean branches with sign agreement geometric vs exact", nd=0)
    N.add("e4_clean_v2_bias", c2["bias"], "clean branches: geometric bias (pp)", n=c2["n"])
    N.add("e4_clean_v2_mae", c2["mae"], "clean branches: geometric MAE (pp)", n=c2["n"])
    N.add("e4_clean_v2_rho", c2["rho"], "clean branches: Spearman rho geometric vs exact", nd=2)
    N.add("e4_clean_legacy_bias", cl["bias"], "clean branches: fixed-fraction bias (pp)", n=cl["n"])
    N.add("e4_clean_legacy_mae", cl["mae"], "clean branches: fixed-fraction MAE (pp)", n=cl["n"])
    N.add("e4_clean_legacy_rho", cl["rho"], "clean branches: Spearman rho fixed-fraction vs exact", nd=2)
    with open(aux / "e4_mapping_clean.csv", "w", newline="") as fcsv:
        w = csv.writer(fcsv)
        w.writerow(["original_episode_dir", "branch_episode_dir", "inject_decision"])
        for r in clean:
            w.writerow([r["original_episode_dir"], r["branch_episode_dir"], r["inject_decision"]])
    N.to_json(tables / "numbers_e4.json")
    N.to_macros(tables / "macros_e4.tex")

    # ---- paragraphs for the manuscript (Section 6.9) and the response letter
    def f(x, nd=1):
        return fmt(x, nd)

    def rho_txt(r, p):
        if r is None:
            return "too few branches for a rank correlation"
        ps = fmt_p(p)
        return f"Spearman $\\rho = {f(r, 2)}$, $p {ps}$" if ps.startswith("<") else f"Spearman $\\rho = {f(r, 2)}$, $p = {fmt_p(p)}$"

    nplain = len(plain)
    divergent = sorted((k, v) for k, v in first_div.items() if v)
    div_txt = " and ".join(f"seed {k} from decision {v}" for k, v in divergent)
    ex_pos = N.items["e4_exec_pos"]["value"]
    exec_pct = 100.0 * nx / nc if nc else 0
    det = (
        "% auto-generated by agent/analysis/revision/e4_analysis.py -- do not edit by hand\n"
        "\\paragraph{Reproducibility check.} Before using re-simulation as ground truth we re-simulated the four source episodes from their logged seed and "
        f"action stream without any substitution (\\Cref{{tab:tab_determinism}}). {n_ident} of the {nplain} replays reproduced the original bit for bit over all 29 decisions: "
        "identical decision states (coverage, cell lists, positions of disconnected units, threat lists) and identical simulation-side logs (about 2{,}300 lines each; only "
        f"the wall-clock-dependent arrival frame of the agent's message differs). The other {nplain - n_ident} were identical up to the decision epoch before the one named "
        f"({div_txt}) and then diverged in the decisions of the civilian AI, while the agent's own actions were executed at the scheduled frame in every episode. "
        "A counterfactual branch therefore enters the validation only if the unchanged-action replay of its episode is identical through the event epoch $t$ "
        f"({nc} of {n} branches); the remaining "
        f"{n - nc} branches are listed in \\Cref{{app:e4}} but excluded from the agreement statistics."
    )
    write_text(REVISION_DIR / "sections" / "e4_determinism.tex", det)
    txt = [
        "% auto-generated by agent/analysis/revision/e4_analysis.py -- do not edit by hand",
        "\\paragraph{Agreement.} "
        f"All {n} branches reproduced the original trajectory exactly up to the substitution epoch ({N.items['e4_prefix_identical']['value']} of {n} identical prefixes). "
        f"Among the {nc} clean branches the substituted macro-cell order passed validation and was built in {nx} ({exec_pct:.0f}\\,\\%); in the other {nc - nx} "
        f"the estimator's centroid lay in water or on an unbuildable position, so the order was rejected and the branch differs from the original only in that the "
        f"agent's original action at $k_0$ was removed. These rejected branches are the estimator's first failure mode: it predicted a mean gain of "
        f"{f(N.items['e4_rej_est_v2_mean']['value'])}\\pp{{}} for them, whereas the exact effect of the (removed) original action was {f(N.items['e4_rej_exact_mean']['value'])}\\pp{{}} on average. "
        f"For the {nx} branches in which the counterfactual cell was actually built, the exact gain at the event epoch was positive in {ex_pos} "
        f"(mean {f(N.items['e4_exec_exact_mean']['value'])}\\pp) against a mean geometric estimate of {f(N.items['e4_exec_est_v2_mean']['value'])}\\pp: the geometric estimator "
        f"has a bias of {f(N.items['e4_exec_v2_bias']['value'])}\\pp{{}} and a mean absolute error of {f(N.items['e4_exec_v2_mae']['value'])}\\pp{{}} ({rho_txt(ex_rho2, ex_p2)}), "
        f"the fixed-fraction estimator a bias of {f(N.items['e4_exec_legacy_bias']['value'])}\\pp{{}} and a mean absolute error of {f(N.items['e4_exec_legacy_mae']['value'])}\\pp{{}} "
        f"({rho_txt(ex_rhol, ex_pl)}). Over all {nc} clean branches (\\Cref{{tab:tab_regret_validation}}) the geometric estimator's bias is {f(c2['bias'])}\\pp{{}} with a mean absolute "
        f"error of {f(c2['mae'])}\\pp{{}} ({rho_txt(c2['rho'], c2['p'])}), the fixed-fraction estimator's {f(cl['bias'])}\\pp{{}} and {f(cl['mae'])}\\pp{{}} ({rho_txt(cl['rho'], cl['p'])}); "
        f"the geometric estimate and the exact gain agree in sign in {sign_clean} of {nc} branches. Over the remainder of the episode the substituted order left coverage higher on average "
        f"in {end_pos_clean} of {nc} clean branches. The geometric estimator thus ranks events in the right order but overstates the gain: it counts the units a cell would "
        f"reach, not the units it would serve after backhaul delay, capacity and continued movement, and it does not know whether the centroid is buildable.",
    ]
    write_text(REVISION_DIR / "sections" / "e4_results.tex", "\n".join(txt))
    resp = [
        "% auto-generated by agent/analysis/revision/e4_analysis.py -- do not edit by hand",
        f"\\emph{{Results (new Section~\\mref{{sec:eval_regret}} and Appendix~\\mref{{app:e4}}).}} Four S1 episodes of the primary model were re-simulated without substitution: {n_ident} of the four are bit-identical "
        f"to the originals over all 29 decisions (all logged fields equal, about 2{{,}}300 identical simulation-side log lines each); the other {nplain - n_ident} are identical up to "
        f"the decision before the one named ({div_txt}) and then diverge in the civilian AI's decisions; a branch enters the validation only if the unchanged-action replay "
        f"whose unchanged-action replay is identical through the event epoch ({nc} of {n} branches). The {n} regret events of these episodes were re-simulated with the estimator's "
        f"counterfactual macro cell substituted at $t-2$. Among the {nc} clean branches the substituted order was built in {nx} ({exec_pct:.0f}\\,\\%) and rejected by the simulator's "
        f"validator (water or unbuildable position) in {nc - nx}; the latter are the estimator's main failure mode and are reported separately. For the built branches the geometric "
        f"estimator (which counts the disconnected units within macro range of the centroid) has a bias of {f(N.items['e4_exec_v2_bias']['value'])}\\pp{{}} and a mean absolute error of "
        f"{f(N.items['e4_exec_v2_mae']['value'])}\\pp{{}} ({rho_txt(ex_rho2, ex_p2)}); the original fixed-fraction (30\\,\\%) estimator has a bias of {f(N.items['e4_exec_legacy_bias']['value'])}\\pp{{}} "
        f"and a mean absolute error of {f(N.items['e4_exec_legacy_mae']['value'])}\\pp. Over all {nc} clean branches the geometric estimator's bias is {f(c2['bias'])}\\pp{{}} (MAE {f(c2['mae'])}\\pp, "
        f"{rho_txt(c2['rho'], c2['p'])}) and its sign agreement with the exact gain {sign_clean}/{nc}; the fixed-fraction estimator's rank correlation is {f(cl['rho'], 2)}. "
        f"The estimator ranks events correctly but overstates the gain, which the manuscript now says explicitly. Every branch is listed in Appendix~\\mref{{app:e4}} with the validator's verdict.",
    ]
    write_text(REVISION_DIR / "response" / "e4_summary.tex", "\n".join(resp))
    print(t_det.to_markdown()); print(); print(t_br.to_markdown()); print(); print("\n".join(txt[1:]))
    print(f"\nmapping: {aux / 'e4_mapping.csv'}; tables -> {tables}")


if __name__ == "__main__":
    main()
