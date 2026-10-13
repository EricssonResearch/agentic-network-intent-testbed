#!/usr/bin/env python3
"""
Unified episode loader for both campaigns.

  * June 2026 campaign (protocol v1): agent/data/<scenario>_<backend>_runN_<ts>.jsonl (+ _gamelog.txt)
  * Revision campaign (protocol v2):  agent/results_v2/<episode_id>/{decisions.jsonl, header.json, summary.json, gamelog.txt}

Every episode becomes an `Episode` with a canonical backend name (llm, llm_nospatial, llm_minimal,
rule, random, noop, replay), the decision records, and provenance (protocol, code version, seed,
GameID, model, prompt version). Validity: >= MIN_DECISIONS decisions and, for v2, the protocol
assertions from summary.json (zero lag violations, executed == logged actions).

Unit of analysis for all statistics is the episode.

Minimum-length override (for smoke tests on short pilot episodes): either set the environment
variable ANALYSIS_MIN_DECISIONS=<int> or pass `min_decisions=<int>` to load_all/load_v1/load_v2.
The default (20) is the paper's validity criterion and is unchanged for stats_report.py.
"""
from __future__ import annotations
import json, os, re, statistics
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

REPO = Path(__file__).resolve().parents[3]
V1_DIR = REPO / "agent" / "data"
V2_DIR = REPO / "agent" / "results_v2"
MIN_DECISIONS = int(os.environ.get("ANALYSIS_MIN_DECISIONS", "20"))
CANON = {"ericai": "llm", "ericai_nospatial": "llm_nospatial", "ericai_minimal": "llm_minimal", "ericai_v3": "llm_v3test",
         "remote": "llm", "local": "llm"}
LLM_BACKENDS = {"llm", "llm_nospatial", "llm_minimal"}
V1_MODEL = "Qwen/Qwen3-32B-Instruct"   # code default of the June orchestrator (author-confirmed 26 Sep 2026)


@dataclass
class Episode:
    episode_id: str
    scenario: str
    backend: str
    decisions: list
    protocol: int
    path: str
    code_version: str = "unknown"      # 'pre-fix' | 'post-fix' (v1) | commit hash (v2)
    seed: Optional[int] = None
    game_id: Optional[str] = None
    model: Optional[str] = None
    prompt_version: Optional[str] = None
    header: dict = field(default_factory=dict)
    summary: dict = field(default_factory=dict)
    valid: bool = True
    invalid_reason: str = ""

    # ---- metrics (episode level) -------------------------------------------------
    def coverage_series(self):
        return [d["state_summary"]["coverage_pct"] for d in self.decisions]

    def avg_coverage(self):
        return statistics.fmean(self.coverage_series())

    def final_coverage(self):
        return self.coverage_series()[-1]

    def bs_deployed(self):
        return self.decisions[-1]["state_summary"]["total_bs"]

    def frac_epochs_at_least(self, thr=80):
        c = self.coverage_series()
        return 100.0 * sum(1 for x in c if x >= thr) / len(c)

    def first_violation_epoch(self, thr=80):
        for d in self.decisions:
            if d["state_summary"]["coverage_pct"] < thr:
                return d["decision"]
        return None

    def n_decisions(self):
        return len(self.decisions)

    def action_counts(self):
        out = {}
        for d in self.decisions:
            k = d["action"].split("|")[0]
            out[k] = out.get(k, 0) + 1
        return out

    # ---- provenance helpers ------------------------------------------------------
    @property
    def is_llm(self) -> bool:
        return self.backend in LLM_BACKENDS or self.backend.startswith("llm")

    @property
    def campaign(self) -> str:
        return "v1" if self.protocol == 1 else "v2"

    def gamelog_path(self) -> Optional[Path]:
        """Engine log of this episode (v1: <stem>_gamelog.txt next to the JSONL; v2: <dir>/gamelog.txt)."""
        p = Path(self.path)
        g = p.with_name(p.stem + "_gamelog.txt") if self.protocol == 1 else p / "gamelog.txt"
        return g if g.exists() else None

    def arm(self) -> str:
        """Backend plus model, e.g. 'llm/Qwen3-32B-Instruct' or 'rule'."""
        if self.model:
            return f"{self.backend}/{self.model.split('/')[-1]}"
        return self.backend


def _fingerprint_v1(gamelog: Path) -> str:
    if not gamelog.exists():
        return "unknown"
    txt = gamelog.read_text(errors="ignore")
    if "[6G NetworkBST v2]" in txt or "Queued engineer" in txt or "Skipped:" in txt:
        return "post-fix"
    if "[6G NetworkBST] Team" in txt or "Ordered engineer" in txt:
        return "pre-fix"
    return "unknown"


def _game_id(gamelog: Path):
    if not gamelog.exists():
        return None
    m = re.search(r"GameID: ([0-9a-f]+)", gamelog.read_text(errors="ignore"))
    return m.group(1) if m else None


def _min_decisions(min_decisions: Optional[int]) -> int:
    return MIN_DECISIONS if min_decisions is None else int(min_decisions)


def load_v1(data_dir: Path = V1_DIR, min_decisions: Optional[int] = None) -> list[Episode]:
    thr = _min_decisions(min_decisions)
    eps = []
    for f in sorted(data_dir.glob("*_run*_*.jsonl")):
        m = re.match(r"(s\d_[a-z]+)_(.+?)_run(\d+)_(\d{8}_\d{6})\.jsonl", f.name)
        if not m:
            continue
        scenario, backend_raw = m.group(1), m.group(2)
        decisions = []
        for line in open(f):
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                continue
            if "action" in d and "state_summary" in d:
                decisions.append(d)
        gamelog = f.with_name(f.stem + "_gamelog.txt")
        ep = Episode(episode_id=f.stem, scenario=scenario, backend=CANON.get(backend_raw, backend_raw), decisions=decisions,
                     protocol=1, path=str(f), code_version=_fingerprint_v1(gamelog), game_id=_game_id(gamelog),
                     model=V1_MODEL if backend_raw.startswith("ericai") else None,
                     prompt_version="v1" if backend_raw.startswith("ericai") else None)
        if len(decisions) < thr:
            ep.valid, ep.invalid_reason = False, f"only {len(decisions)} decisions"
        eps.append(ep)
    return eps


def load_v2_episode(d: Path, min_decisions: Optional[int] = None) -> Optional[Episode]:
    """Load one protocol-v2 episode directory; None if it has no decisions.jsonl."""
    thr = _min_decisions(min_decisions)
    dec_file = d / "decisions.jsonl"
    if not dec_file.exists():
        return None
    header, decisions, footer = {}, [], {}
    for line in open(dec_file):
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        kind = r.get("record", "decision")
        if kind == "header":
            header = r
        elif kind == "footer":
            footer = r
        elif kind == "decision":
            decisions.append(r)
    if (d / "header.json").exists():
        header = {**header, **json.load(open(d / "header.json"))}
    summary = json.load(open(d / "summary.json")) if (d / "summary.json").exists() else {}
    backend = CANON.get(header.get("backend", ""), header.get("backend", "unknown"))
    parts = d.name.split("_")
    scenario = header.get("scenario") or ("_".join(parts[:2]) if len(parts) >= 2 else d.name)
    ep = Episode(episode_id=d.name, scenario=scenario, backend=backend, decisions=decisions, protocol=2, path=str(d),
                 code_version=(header.get("commit") or "unknown")[:12], seed=header.get("seed"),
                 game_id=header.get("game_id") or footer.get("game_id") or summary.get("game_id"),
                 model=header.get("model"), prompt_version=header.get("prompt_version"), header=header, summary=summary)
    if len(decisions) < thr:
        ep.valid, ep.invalid_reason = False, f"only {len(decisions)} decisions"
    elif not summary:
        # every finished protocol-v2 episode has a summary.json (written by run_episode.sh after the match ended);
        # a directory without one is an interrupted episode (Ctrl-C, killed) that the campaign runner re-runs
        ep.valid, ep.invalid_reason = False, "no summary.json (episode interrupted)"
    elif summary:
        if summary.get("lag_violations", 0) > 0 or summary.get("action_mismatches"):
            ep.valid, ep.invalid_reason = False, "protocol assertion failed (lag/mismatch)"
        elif not summary.get("match_ended", True):
            ep.valid, ep.invalid_reason = False, "match did not end"
    return ep


def load_v2(results_dir: Path = V2_DIR, min_decisions: Optional[int] = None) -> list[Episode]:
    eps = []
    for d in sorted(p for p in results_dir.iterdir() if p.is_dir()) if results_dir.exists() else []:
        ep = load_v2_episode(d, min_decisions)
        if ep is not None:
            eps.append(ep)
    return eps


def load_all(include_v1=True, include_v2=True, only_valid=True, min_decisions: Optional[int] = None) -> list[Episode]:
    eps = []
    if include_v1:
        eps += load_v1(min_decisions=min_decisions)
    if include_v2:
        eps += load_v2(min_decisions=min_decisions)
    return [e for e in eps if e.valid] if only_valid else eps


def group(eps, key=lambda e: (e.scenario, e.backend)):
    out = {}
    for e in eps:
        out.setdefault(key(e), []).append(e)
    return out


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Inventory of episodes")
    ap.add_argument("--campaign", choices=["v1", "v2", "all"], default="all")
    ap.add_argument("--all", action="store_true", help="include invalid episodes")
    ap.add_argument("--min-decisions", type=int, default=None, help=f"validity threshold (default {MIN_DECISIONS}; env ANALYSIS_MIN_DECISIONS)")
    a = ap.parse_args()
    eps = load_all(a.campaign in ("v1", "all"), a.campaign in ("v2", "all"), only_valid=not a.all, min_decisions=a.min_decisions)
    for (sc, be), lst in sorted(group(eps).items()):
        vals = [e.avg_coverage() for e in lst if e.valid]
        vers = sorted({e.code_version for e in lst})
        print(f"{sc:15s} {be:14s} N={len(lst):3d} valid={sum(e.valid for e in lst):3d} protocol={sorted({e.protocol for e in lst})} "
              f"code={vers} avg={statistics.fmean(vals):5.1f}±{statistics.stdev(vals) if len(vals)>1 else 0:4.1f}" if vals else f"{sc:15s} {be:14s} N={len(lst)} (no valid)")
    inv = [e for e in eps if not e.valid]
    if inv:
        print("\ninvalid:"); [print("  ", e.episode_id, "-", e.invalid_reason) for e in inv]
