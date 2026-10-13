#!/usr/bin/env python3
"""
Reasoning-text taxonomy: multi-label keyword classification of the LLM's '#' comment, with explicit
denominators, a stratified sample for manual annotation, and Cohen's kappa against the annotation.

Taxonomy: reasoning_taxonomy.json next to this file (categories, 'legacy' + 'added' keywords, matching mode).
Classification of one decision (text = record['reasoning']):
    status  = 'empty'         if text.strip() == ''
            | 'error'         if text starts with an error prefix (API/HTTP error placeholder written by the orchestrator)
            | 'uncategorized' if non-empty, not error, no category matched
            | 'categorized'   otherwise;   labels = every category with >= 1 matching keyword (multi-label)
    valid reasoning := status == 'categorized'  (non-empty, not an error, >= 1 category)
Reported per (scenario, backend, model): N decisions, non-empty, error, categorized (= valid), each with the
share of ALL decisions of that arm as denominator; category counts with share of decisions AND share of
non-empty decisions; category x action-type cross-tab.

Sample for annotation: --sample K (default 50) decisions with non-empty, non-error reasoning, stratified by
(scenario, backend, action type) with proportional allocation (>= 1 per stratum while K allows), seed fixed.
Written as <out>/reasoning_sample<K>.csv (annotator sheet: text, action, coverage before/after, one empty
column per category + 'none' + notes) and <out>/reasoning_sample<K>_auto.csv (automatic labels, 0/1).
Kappa: --kappa ANNOTATED.csv [--kappa2 SECOND_ANNOTATOR.csv]: per-category Cohen's kappa between the automatic
labels (recomputed from the taxonomy) and the human labels (cells '1', 'x', 'y', 'yes', 'true' -> 1; blank/0 -> 0),
plus pooled kappa over all (decision, category) pairs; with two files, inter-annotator kappa as well.

Usage: reasoning.py --campaign v1|v2|all [--out-dir DIR] [--min-decisions K] [--match substring|word]
                    [--sample 50] [--seed 1] [--kappa FILE [--kappa2 FILE]]
"""
from __future__ import annotations
import argparse, csv, json, random, re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Optional

from load_runs import Episode, group
from common import (Result, Table, Numbers, add_common_args, load_campaign, campaign_note, fmt, backend_label,
                    scenario_label, group_sort_key, action_type, cohen_kappa, state, write_text, REPO)

TAXONOMY_PATH = Path(__file__).with_name("reasoning_taxonomy.json")
ACTION_TYPES = ["noop", "place_bs", "reconfig_slice", "other"]


# ----------------------------------------------------------------------------- taxonomy / classifier
def load_taxonomy(path: Path = TAXONOMY_PATH) -> dict:
    return json.load(open(path))


def category_names(tax: dict) -> list:
    return list(tax["categories"].keys())


def _keywords(tax: dict, cat: str) -> list:
    c = tax["categories"][cat]
    return list(c.get("legacy", [])) + list(c.get("added", []))


def _matches(text: str, kw: str, mode: str) -> bool:
    if mode == "word":
        return re.search(r"(?<![a-z0-9])" + re.escape(kw), text) is not None
    return kw in text


def classify(text: Optional[str], tax: dict, match: Optional[str] = None) -> dict:
    """-> dict(status, labels). See module docstring."""
    mode = match or tax.get("match", "substring")
    t = (text or "").strip()
    if not t:
        return dict(status="empty", labels=[])
    low = t.lower() if tax.get("case_insensitive", True) else t
    if any(low.startswith(p) for p in tax.get("error_prefixes", ["error"])):
        return dict(status="error", labels=[])
    labels = [c for c in category_names(tax) if any(_matches(low, kw.lower(), mode) for kw in _keywords(tax, c))]
    return dict(status="categorized" if labels else "uncategorized", labels=labels)


# ----------------------------------------------------------------------------- analysis
def decision_rows(eps: list, tax: dict, match: Optional[str]) -> list:
    rows = []
    for ep in eps:
        dec = ep.decisions
        for i, d in enumerate(dec):
            c = classify(d.get("reasoning"), tax, match)
            rows.append(dict(episode_id=ep.episode_id, protocol=ep.protocol, scenario=ep.scenario, backend=ep.backend,
                             model=ep.model or "-", decision=d["decision"], action=d["action"], action_type=action_type(d["action"]),
                             coverage_before=state(d, "coverage_pct"),
                             coverage_after=state(dec[i + 1], "coverage_pct") if i + 1 < len(dec) else None,
                             disconnected=state(d, "disconnected"), reasoning=(d.get("reasoning") or "").strip(),
                             status=c["status"], labels=c["labels"]))
    return rows


def analyze(eps: list, tax: Optional[dict] = None, match: Optional[str] = None, sample_n: int = 50, seed: int = 1) -> Result:
    tax = tax or load_taxonomy()
    cats = category_names(tax)
    llm_eps = [e for e in eps if e.is_llm]
    rows = decision_rows(llm_eps, tax, match)
    res, N = Result(), Numbers()
    mode = match or tax.get("match", "substring")

    # --- denominators per arm
    t1 = Table("tab_reasoning_denominators",
               caption="Availability of reasoning text per LLM arm. Denominator for every share is the number of decisions of the arm. "
                       "Valid = non-empty, not an API-error placeholder, and matching $\\geq 1$ taxonomy category.",
               columns=["Scenario", "Agent", "Model", "$N$ ep.", "$N$ dec.", "Non-empty", "Error", "Uncategorized", "Valid"],
               colspec="lllrrrrrr", wide=True)
    by_arm = defaultdict(list)
    for r in rows:
        by_arm[(r["scenario"], r["backend"], r["model"])].append(r)
    for key, lst in sorted(by_arm.items(), key=lambda kv: group_sort_key(kv[0])):
        n = len(lst)
        ne = sum(1 for r in lst if r["status"] != "empty")
        er = sum(1 for r in lst if r["status"] == "error")
        un = sum(1 for r in lst if r["status"] == "uncategorized")
        va = sum(1 for r in lst if r["status"] == "categorized")
        neps = len({r["episode_id"] for r in lst})
        pct = lambda k: f"{k} ({100.0 * k / n:.1f}%)" if n else "n/a"
        t1.rows.append([scenario_label(key[0]), backend_label(key[1]), key[2].split("/")[-1], neps, n, pct(ne), pct(er), pct(un), pct(va)])
        k = f"reasoning_{key[0]}_{key[1]}"
        N.add(k + "_decisions", n, "LLM decisions in the arm", nd=0)
        N.add(k + "_nonempty_pct", 100.0 * ne / n if n else None, "share of decisions with non-empty reasoning text (%)", n=n)
        N.add(k + "_valid_pct", 100.0 * va / n if n else None, "share of decisions with valid reasoning (non-empty, not error, >=1 category) (%)", n=n)
    n_all = len(rows)
    n_nonempty = sum(1 for r in rows if r["status"] != "empty")
    n_valid = sum(1 for r in rows if r["status"] == "categorized")
    N.add("reasoning_all_decisions", n_all, "all LLM decisions analysed", nd=0)
    N.add("reasoning_all_nonempty", n_nonempty, "LLM decisions with non-empty reasoning", nd=0)
    N.add("reasoning_all_valid", n_valid, "LLM decisions with valid reasoning", nd=0)
    N.add("reasoning_all_valid_pct", 100.0 * n_valid / n_all if n_all else None, "share of all LLM decisions with valid reasoning (%)", n=n_all)
    res.tables.append(t1)

    # --- category frequencies (pooled + per backend share of decisions)
    backends = sorted({r["backend"] for r in rows}, key=lambda b: group_sort_key(("", b)))
    t2 = Table("tab_reasoning_categories",
               caption=f"Reasoning categories (multi-label keyword classifier, mode `{mode}`; dictionary in the appendix). "
                       "Shares use two explicit denominators: all LLM decisions ($N_{\\mathrm{dec}}$) and decisions with non-empty text ($N_{\\mathrm{ne}}$); "
                       "the per-arm columns are shares of that arm's decisions.",
               columns=["Category", "Count", f"\\% of dec. ($N$={n_all})", f"\\% of non-empty ($N$={n_nonempty})"] +
                       [f"{backend_label(b)} (\\%)" for b in backends], colspec="lrrr" + "r" * len(backends), wide=True)
    per_be_n = {b: sum(1 for r in rows if r["backend"] == b) for b in backends}
    cat_counts = Counter(l for r in rows for l in r["labels"])
    for c in cats + ["uncategorized"]:
        cnt = cat_counts[c] if c != "uncategorized" else sum(1 for r in rows if r["status"] == "uncategorized")
        per_be = [100.0 * sum(1 for r in rows if r["backend"] == b and (c in r["labels"] if c != "uncategorized" else r["status"] == "uncategorized")) / per_be_n[b]
                  if per_be_n[b] else None for b in backends]
        t2.rows.append([c.replace("_", " "), cnt, fmt(100.0 * cnt / n_all if n_all else None), fmt(100.0 * cnt / n_nonempty if n_nonempty else None)] + [fmt(x) for x in per_be])
        N.add(f"reasoning_cat_{c}_count", cnt, f"decisions labelled '{c}' (multi-label)", nd=0)
        N.add(f"reasoning_cat_{c}_pct_dec", 100.0 * cnt / n_all if n_all else None, f"share of all LLM decisions labelled '{c}' (%)", n=n_all)
        N.add(f"reasoning_cat_{c}_pct_nonempty", 100.0 * cnt / n_nonempty if n_nonempty else None, f"share of non-empty-reasoning decisions labelled '{c}' (%)", n=n_nonempty)
    labels_per = [len(r["labels"]) for r in rows if r["status"] == "categorized"]
    t2.note = (f"Labels per categorized decision: mean {fmt(sum(labels_per) / len(labels_per) if labels_per else None, 2)}; "
               f"multi-label, so category counts do not sum to the number of decisions.")
    res.tables.append(t2)

    # --- category x action cross-tab
    t3 = Table("tab_reasoning_by_action", caption="Reasoning category versus executed action type (counts of decisions; multi-label).",
               columns=["Category"] + ACTION_TYPES + ["Total"], colspec="l" + "r" * (len(ACTION_TYPES) + 1))
    for c in cats + ["uncategorized", "empty", "error"]:
        sel = [r for r in rows if (c in r["labels"]) or (c in ("uncategorized", "empty", "error") and r["status"] == c)]
        cnts = [sum(1 for r in sel if r["action_type"] == a) for a in ACTION_TYPES]
        t3.rows.append([c.replace("_", " ")] + cnts + [sum(cnts)])
    t3.rows.append(["all decisions"] + [sum(1 for r in rows if r["action_type"] == a) for a in ACTION_TYPES] + [n_all])
    res.tables.append(t3)

    # --- sample for annotation
    sample = stratified_sample(rows, sample_n, seed)
    md = ["## Reasoning taxonomy", "", f"Taxonomy: {TAXONOMY_PATH.name} (version {tax.get('version')}), matching mode `{mode}`.",
          f"LLM episodes analysed: {len(llm_eps)} (non-LLM episodes excluded: {len(eps) - len(llm_eps)}).", "",
          "### Denominators", "", t1.to_markdown(), "", "### Categories", "", t2.to_markdown(), "",
          "### Category x action", "", t3.to_markdown(), "",
          f"### Annotation sample: {len(sample)} decisions (stratified by scenario x backend x action type; requested {sample_n})", ""]
    res.markdown = "\n".join(md)
    res.numbers = N
    res.extra = dict(rows=rows, sample=sample, categories=cats, mode=mode)
    return res


def stratified_sample(rows: list, n: int, seed: int = 1) -> list:
    pool = [r for r in rows if r["status"] in ("categorized", "uncategorized")]
    if not pool or n <= 0:
        return []
    strata = defaultdict(list)
    for r in pool:
        strata[(r["scenario"], r["backend"], r["action_type"])].append(r)
    rng = random.Random(seed)
    n = min(n, len(pool))
    keys = sorted(strata)
    alloc = {k: 1 if len(keys) <= n else 0 for k in keys}
    remaining = n - sum(alloc.values())
    if remaining > 0:
        quotas = {k: remaining * len(strata[k]) / len(pool) for k in keys}
        for k in keys:
            alloc[k] += int(quotas[k])
        rest = n - sum(alloc.values())
        for k in sorted(keys, key=lambda k: quotas[k] - int(quotas[k]), reverse=True)[:max(0, rest)]:
            alloc[k] += 1
    out = []
    for k in keys:
        lst = list(strata[k])
        rng.shuffle(lst)
        out += lst[:min(alloc[k], len(lst))]
    if len(out) < n:                                    # strata smaller than their quota: top up at random
        chosen = {(r["episode_id"], r["decision"]) for r in out}
        extra = [r for r in pool if (r["episode_id"], r["decision"]) not in chosen]
        rng.shuffle(extra)
        out += extra[:n - len(out)]
    for i, r in enumerate(out, 1):
        r["sample_id"] = i
    return out


def write_sample(sample: list, cats: list, out_dir: Path, stem: str) -> tuple:
    out_dir.mkdir(parents=True, exist_ok=True)
    sheet, auto = out_dir / f"{stem}.csv", out_dir / f"{stem}_auto.csv"
    base = ["sample_id", "protocol", "episode_id", "decision", "scenario", "backend", "model", "action", "action_type",
            "coverage_before", "coverage_after", "disconnected", "reasoning"]
    with open(sheet, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(base + [f"label_{c}" for c in cats] + ["label_none", "annotator_notes"])
        for r in sample:
            w.writerow([r.get(k, "") for k in base] + [""] * (len(cats) + 2))
    with open(auto, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["sample_id", "episode_id", "decision"] + [f"label_{c}" for c in cats] + ["label_none"])
        for r in sample:
            w.writerow([r["sample_id"], r["episode_id"], r["decision"]] + [int(c in r["labels"]) for c in cats] + [int(not r["labels"])])
    return sheet, auto


# ----------------------------------------------------------------------------- kappa
def _truthy(v) -> int:
    return 1 if str(v).strip().lower() in ("1", "x", "y", "yes", "true", "t") else 0


def kappa_report(annotated: Path, tax: dict, match: Optional[str] = None, annotated2: Optional[Path] = None) -> Table:
    """Cohen's kappa per category: automatic labels (recomputed from the taxonomy on the sheet's text) vs annotator."""
    cats = category_names(tax)
    hum = list(csv.DictReader(open(annotated)))
    hum2 = {r["sample_id"]: r for r in csv.DictReader(open(annotated2))} if annotated2 else None
    t = Table("tab_reasoning_kappa", caption="Agreement between the keyword classifier and manual annotation (Cohen's $\\kappa$, per category "
              "and pooled over all decision--category pairs)" + ("; inter-annotator $\\kappa$ in the last column." if hum2 else "."),
              columns=["Category", "$N$", "Auto pos.", "Human pos.", "Agreement", "$\\kappa$ auto vs human"] + (["$\\kappa$ human vs human"] if hum2 else []),
              colspec="lrrrrr" + ("r" if hum2 else ""))
    pooled_a, pooled_h, pooled_h2 = [], [], []
    for c in cats + ["none"]:
        a, h, h2 = [], [], []
        for r in hum:
            cl = classify(r.get("reasoning"), tax, match)
            a.append(int(c in cl["labels"]) if c != "none" else int(not cl["labels"]))
            h.append(_truthy(r.get(f"label_{c}", "")))
            if hum2 is not None:
                h2.append(_truthy(hum2.get(r["sample_id"], {}).get(f"label_{c}", "")))
        pooled_a += a
        pooled_h += h
        pooled_h2 += h2
        agree = sum(1 for x, y in zip(a, h) if x == y) / len(a) if a else None
        row = [c.replace("_", " "), len(a), sum(a), sum(h), fmt(100 * agree if agree is not None else None) + "%", fmt(cohen_kappa(a, h), 2)]
        if hum2 is not None:
            row.append(fmt(cohen_kappa(h, h2), 2))
        t.rows.append(row)
    row = ["pooled", len(pooled_a), sum(pooled_a), sum(pooled_h),
           fmt(100 * sum(1 for x, y in zip(pooled_a, pooled_h) if x == y) / len(pooled_a) if pooled_a else None) + "%",
           fmt(cohen_kappa(pooled_a, pooled_h), 2)]
    if hum2 is not None:
        row.append(fmt(cohen_kappa(pooled_h, pooled_h2), 2))
    t.rows.append(row)
    return t


def main():
    ap = add_common_args(argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter),
                         default_out=REPO / "agent" / "analysis" / "revision" / "out" / "reasoning")
    ap.add_argument("--taxonomy", default=str(TAXONOMY_PATH))
    ap.add_argument("--match", choices=["substring", "word"], default=None, help="override the taxonomy's matching mode")
    ap.add_argument("--sample", type=int, default=50)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--kappa", default=None, help="filled-in annotation CSV (from --sample export)")
    ap.add_argument("--kappa2", default=None, help="second annotator's CSV (inter-annotator kappa)")
    a = ap.parse_args()
    tax = load_taxonomy(Path(a.taxonomy))
    out = Path(a.out_dir)
    if a.kappa:
        t = kappa_report(Path(a.kappa), tax, a.match, Path(a.kappa2) if a.kappa2 else None)
        print(t.to_markdown())
        out.mkdir(parents=True, exist_ok=True)
        (out / f"{t.name}.tex").write_text(t.to_tex())
        print(f"\nwritten {out / (t.name + '.tex')}")
        return
    eps = load_campaign(a)
    res = analyze(eps, tax, a.match, a.sample, a.seed)
    res.markdown = campaign_note(a, eps) + "\n\n" + res.markdown
    print(res.markdown)
    res.write(out, "reasoning")
    sheet, auto = write_sample(res.extra["sample"], res.extra["categories"], out, f"reasoning_sample{a.sample}")
    print(f"\nannotation sheet: {sheet}\nautomatic labels: {auto}\nwritten to {out}")


if __name__ == "__main__":
    main()
