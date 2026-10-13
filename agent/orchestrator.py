#!/usr/bin/env python3
"""
6G Network Agent Orchestrator -- v2 (revision campaign, September 2026)

Watches the engine log for exported states (6G_AGENT_STATE|{json}), asks an agent for an
action, writes "<decision_frame>|<action>" to the action file (protocol v2: the bridge only
executes an action tagged with the pending decision frame) and logs one JSON record per
decision plus an episode header/footer.

Backends
  llm            full observation (positions + loads + temporal)      [alias: ericai, remote]
  llm_nospatial  observation without base-station positions            [alias: ericai_nospatial]
  llm_minimal    coverage %, income, unit counts only                   [alias: ericai_minimal]
  rule           deterministic threshold heuristic (seeded RNG)
  random         random placement (seeded RNG)
  noop           always noop (autonomous layer only)
  replay         re-feed the logged actions of a previous episode, optionally injecting one
                 counterfactual action (deterministic re-simulation; needs the same 6g_random_seed)

Configuration: CLI flags override environment variables LLM_URL, LLM_MODEL, LLM_API_KEY,
LLM_TIMEOUT, BAR_WRITE_DIR, RESULTS_DIR.

The June 2026 version is archived in agent/legacy_june2026/orchestrator_v1.py. Differences that
affect the agent's observation are documented in REVISION_PLAN.md (finding M): the v1 full-context
formatter read non-existent keys ('qos_summary', 'metal_extractors'), so QoS violations and the
extractor count were never shown to the full-context LLM; v2 reads the real keys.
"""

import argparse
import hashlib
import json
import os
import random
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections import deque
from pathlib import Path

# ============================================================
# Defaults / configuration
# ============================================================

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_WRITE_DIR = Path(os.environ.get("BAR_WRITE_DIR", str(Path.home() / ".local/state/Beyond All Reason")))
DEFAULT_RESULTS_DIR = Path(os.environ.get("RESULTS_DIR", str(REPO_ROOT / "agent" / "results_v2")))
POLL_INTERVAL = float(os.environ.get("ORCH_POLL_INTERVAL", "0.5"))
RAW_RESPONSE_CAP = 64000  # characters of raw LLM output (and of the separate reasoning field) kept per decision; thinking traces run to ~25k chars

BACKEND_ALIASES = {
    "ericai": "llm", "remote": "llm", "local": "llm",
    "ericai_nospatial": "llm_nospatial", "ericai_minimal": "llm_minimal",
}
LLM_BACKENDS = ("llm", "llm_nospatial", "llm_minimal")
NON_LLM_BACKENDS = ("rule", "random", "noop", "replay", "greedy")

# ============================================================
# Prompts
# ============================================================

# v1: verbatim system prompt of the June 2026 campaign (Appendix A of the manuscript)
SYSTEM_PROMPT_V1 = """You are a 6G network operator AI managing base station deployment and slice configuration.

Your goal: Maximize network coverage and minimize QoS violations.

Available actions (respond with EXACTLY one line in this format):
- place_bs|CELL_TYPE|X|Z       (CELL_TYPE: macro_cell, small_cell, micro_cell)
- reconfig_slice|BS_ID|EMBB|URLLC|MMTC  (ratios must sum to 1.0)
- noop                          (do nothing this turn)

Cell types:
- macro_cell: 1200 elmo radius, 100 RB capacity (large coverage)
- small_cell: 500 elmo radius, 50 RB capacity (targeted density)
- micro_cell: 200 elmo radius, 25 RB capacity (hotspot)

Decision guidelines:
- If coverage is below 80% or units are disconnected, PLACE a new cell near disconnected areas
- If a cell load exceeds 80% on any slice, consider RECONFIG or place a nearby cell to offload
- Metal income determines build speed, NOT whether you can build. Always issue place orders when coverage is needed regardless of current metal storage.
- Place cells to extend coverage outward from existing BS toward areas where units are expanding
- Consider the day/night cycle: demand shifts at dawn and dusk
- Estimate positions of disconnected units: they are likely at the expansion frontier, 1000-2000 elmos from existing BS
- CRITICAL: Do NOT place base stations near enemy threat zones! The network engineer that builds them is unarmed and will be killed. If enemy threats are reported, keep placements at least 1000 elmos away from any threat position.

Respond with ONLY the action line. You may add a brief comment after #."""

# v2: v1 plus explicit temporal-planning guidance (inserted before the response-format instruction)
TEMPORAL_GUIDANCE_V2 = """
Temporal planning guidance:
- The day/night cycle is periodic. At night, mobile demand concentrates around housing; at dawn, workers commute back toward factories and the expansion frontier.
- Read the cycle phase and the seconds remaining. If a phase change is imminent, pre-position capacity where demand will be AFTER the change, not where it is now.
- Do not chase transient demand spikes that dissipate within minutes; prefer positions that serve both day and night patterns (corridors between housing and industry).
- Use your recent decision history (if provided) to judge whether earlier placements had the intended effect before ordering more.
"""

# v1g: v1 plus terrain-grounding guidance (revision experiment E7; used together with --expose-buildable-grid)
GROUNDING_GUIDANCE_V1G = """
Terrain map: the observation ends with a buildable-terrain map of 32 x 32 cells, each 512 x 512 elmos. Row r (top to bottom) covers Z from 512*r to 512*r+511; column c (left to right) covers X from 512*c to 512*c+511. '#' = buildable land, '~' = water, '.' = blocked terrain (steep or occupied).
- Cells can only be built on '#' land. Choose X and Z inside a '#' cell, e.g. its centre X = 512*c + 256, Z = 512*r + 256.
- Orders on '~' water or '.' blocked cells are rejected and waste the turn. Check the map before answering.
"""


# v1c: v1 plus candidate-position guidance (revision experiment E8; used together with --candidates)
CANDIDATE_GUIDANCE_V1C = """
Candidate positions: each observation lists up to 6 candidate positions C1..C6 for a new cell. They are on buildable, unoccupied terrain, outside threat zones, and within 600 elmos of a live backhaul link, so a cell built there connects to the core at once (a cell farther from live backhaul stays inactive and serves nobody). They are ranked by the number of currently disconnected units within macro-cell range (1200 elmos); each line also gives the units within small-cell range (500 elmos) and the distance to the nearest live backhaul link.
- To use a candidate answer place_bs|CELL_TYPE|C<n>, e.g. place_bs|macro_cell|C1. You may still give explicit coordinates instead.
- Prefer macro_cell when many units are spread within 1200 elmos, small_cell when most of them are within 500 elmos.
- If no candidate is listed, consider reconfig_slice for overloaded cells or noop.
"""


def build_prompt(version: str) -> str:
    if version == "v1":
        return SYSTEM_PROMPT_V1
    marker = "Respond with ONLY the action line."
    head, tail = SYSTEM_PROMPT_V1.split(marker, 1)
    if version == "v2":
        return head.rstrip() + "\n" + TEMPORAL_GUIDANCE_V2 + "\n" + marker + tail
    if version == "v1g":
        return head.rstrip() + "\n" + GROUNDING_GUIDANCE_V1G + "\n" + marker + tail
    if version == "v1c":
        return head.rstrip() + "\n" + CANDIDATE_GUIDANCE_V1C + "\n" + marker + tail
    raise ValueError(f"unknown prompt version {version}")


# ============================================================
# Candidate positions (E8): a neutral geometric generator the agent may choose from
# ============================================================

CAND_K, CAND_MACRO_R, CAND_SMALL_R, CAND_MIN_SEP, CAND_THREAT_R, CAND_DEFAULT_CELL, MAP_SIZE = 6, 1200.0, 500.0, 1200.0, 800.0, 512, 16384
CAND_BACKHAUL_R = 600.0   # a cell serves only if a live (core-connected) backhaul link is within this range (6g_backhaul.lua BS_TO_BACKHAUL_RANGE; the bridge exports the value)
CAND_OCCUPIED_R = 300.0   # no candidate this close to an existing/under-construction cell or to a placement ordered in the last CAND_RECENT_N decisions
CAND_RECENT_N = 6


def compute_candidates(state: dict, k: int = CAND_K, recent=()) -> list:
    """Top-k candidate positions for a new cell, ranked by disconnected units within macro range (ties: nearer to a live
    backhaul link). A grid-cell centre qualifies if it is (i) buildable (bridge export buildable_grid, modoption
    6g_agent_buildable_grid=true; otherwise every 512-elmo cell centre), (ii) outside threat zones, (iii) within the
    BS-to-backhaul range of a live backhaul link when the bridge exports them (state 'backhaul_nodes'; a cell farther
    away never connects because the autonomous layer does not bridge such gaps), (iv) at least CAND_OCCUPIED_R from every
    existing or under-construction cell and from the agent's own placements of the last CAND_RECENT_N decisions
    (`recent`: (decision, x, z) tuples), and candidates are at least CAND_MIN_SEP apart."""
    import math
    pos = state.get("disconnected_positions") or []
    if not pos:
        return []
    grid = state.get("buildable_grid") or {}
    cell = int(grid.get("cell", CAND_DEFAULT_CELL))
    rows = grid.get("rows") or []
    if rows:
        blocked = {(int(q[0]), int(q[1])) for q in (state.get("blocked_cells") or []) if isinstance(q, (list, tuple)) and len(q) >= 2}
        centres = [(c * cell + cell / 2, r * cell + cell / 2) for r, row in enumerate(rows) for c, ch in enumerate(row)
                   if ch == "#" and (c, r) not in blocked]   # blocked_cells: centres currently occupied by a structure (bridge export)
    else:
        n = MAP_SIZE // cell
        centres = [(c * cell + cell / 2, r * cell + cell / 2) for r in range(n) for c in range(n)]
    threats = [(t[0], t[1]) for t in (state.get("enemy_threats") or []) if isinstance(t, (list, tuple)) and len(t) >= 2]
    bs = [tuple(b["pos"]) for b in state.get("base_stations", []) if b.get("pos")]
    occupied = bs + [(x, z) for _, x, z in recent]
    bh = [(q[0], q[1]) for q in state["backhaul_nodes"] if isinstance(q, (list, tuple)) and len(q) >= 2] if "backhaul_nodes" in state else None
    bh_r = float(state.get("bs_to_backhaul_range") or CAND_BACKHAUL_R)
    scored = []
    for cx, cz in centres:
        if any(math.hypot(cx - tx, cz - tz) <= CAND_THREAT_R for tx, tz in threats):
            continue
        if any(math.hypot(cx - ox, cz - oz) < CAND_OCCUPIED_R for ox, oz in occupied):
            continue
        d_bh = None
        if bh is not None:
            d_bh = min((math.hypot(bx - cx, bz - cz) for bx, bz in bh), default=None)
            if d_bh is None or d_bh > bh_r:
                continue
        n_macro = sum(1 for q in pos if math.hypot(q[0] - cx, q[1] - cz) <= CAND_MACRO_R)
        if n_macro == 0:
            continue
        n_small = sum(1 for q in pos if math.hypot(q[0] - cx, q[1] - cz) <= CAND_SMALL_R)
        d_bs = min((math.hypot(bx - cx, bz - cz) for bx, bz in bs), default=None)
        scored.append((n_macro, n_small, d_bs, d_bh, cx, cz))
    scored.sort(key=lambda t: (-t[0], t[3] if t[3] is not None else (t[2] if t[2] is not None else 1e9), t[4], t[5]))
    out = []
    for n_macro, n_small, d_bs, d_bh, cx, cz in scored:
        if all(math.hypot(cx - o["x"], cz - o["z"]) >= CAND_MIN_SEP for o in out):
            out.append(dict(id=f"C{len(out) + 1}", x=int(cx), z=int(cz), n_macro=n_macro, n_small=n_small,
                            d_bs=None if d_bs is None else int(d_bs), d_bh=None if d_bh is None else int(d_bh)))
        if len(out) >= k:
            break
    return out


def format_candidates(cands: list, n_disconnected: int, bh_r: float = CAND_BACKHAUL_R) -> str:
    if not cands:
        if not n_disconnected:
            return "\nCandidate positions: none (no disconnected units)."
        return (f"\nCandidate positions: none (no unoccupied buildable position within {bh_r:.0f} elmos of a live backhaul link "
                "has disconnected units within 1200 elmos).")
    lines = [f"\nCandidate positions for a new cell (buildable, unoccupied, outside threat zones, within {bh_r:.0f} elmos of a live "
             "backhaul link so the cell connects at once; ranked by disconnected units within 1200 elmos):"]
    for c in cands:
        if c.get("d_bh") is not None:
            near = f"live backhaul {c['d_bh']} elmos away"
        else:
            near = f"nearest existing cell {c['d_bs']} elmos" if c.get("d_bs") is not None else "no existing cell"
        lines.append(f"  {c['id']} at ({c['x']}, {c['z']}): {c['n_macro']} of {n_disconnected} disconnected units within 1200 elmos, {c['n_small']} within 500; {near}")
    lines.append("Answer place_bs|CELL_TYPE|C<n> to use a candidate, or give explicit coordinates.")
    return "\n".join(lines)


OUTCOME_WORDS = {"executed_place": "cell ordered and queued for construction", "snapped_place": "cell ordered (position moved to buildable terrain)",
                 "executed_reconfig": "slice reconfigured", "skipped_water": "REJECTED: position is in water", "skipped_invalid_position": "REJECTED: not a buildable position",
                 "skipped_threat": "REJECTED: position in a threat zone", "noop": "no action", "invalid_format": "REJECTED: malformed action",
                 "invalid_cell_type": "REJECTED: unknown cell type", "invalid_reconfig": "REJECTED: invalid reconfiguration", "no_engineer": "REJECTED: no deployment crew"}


def format_feedback(prev: dict, outcome: str, coverage_now) -> str:
    """One-line consequence feedback about the previous decision (E8 variant)."""
    if not prev:
        return ""
    words = OUTCOME_WORDS.get(outcome or "", outcome or "unknown")
    return (f"\nResult of your previous action (decision {prev['decision']}: {prev['action']}): {words}; "
            f"coverage {prev['coverage']}% -> {coverage_now}%, disconnected {prev['disconnected']} -> {prev.get('disconnected_now', '?')}.")


def last_validation(game_log: Path, decision: int):
    """Validation outcome of decision k as logged by the bridge ('Decision #k validation: <outcome>')."""
    try:
        txt = game_log.read_text(errors="ignore")
    except OSError:
        return None
    m = re.findall(rf"Decision #{decision} validation: (\w+)", txt)
    return m[-1] if m else None


def greedy_agent(state: dict, cands: list) -> str:
    """Deterministic decision-support baseline: macro cell at the best candidate whenever units are disconnected."""
    if not cands or (state.get("units", {}).get("disconnected", 0) == 0 and state.get("coverage_pct", 0) >= 80):
        return "noop"
    c = cands[0]
    cell_type = "small_cell" if c["n_macro"] <= 6 and c["n_small"] >= 0.8 * c["n_macro"] else "macro_cell"
    return f"place_bs|{cell_type}|{c['x']}|{c['z']}"

# ============================================================
# State formatting (observation functions g(s))
# ============================================================

def format_buildable_grid(grid: dict) -> str:
    """ASCII buildable-terrain map (bridge export buildable_grid: cell size, rows of '#', '~', '.')."""
    rows = grid.get("rows") or []
    if not rows:
        return ""
    cell = int(grid.get("cell", 512))
    ncol = len(rows[0])
    lines = [f"\nBuildable-terrain map ({ncol}x{len(rows)} cells of {cell} elmos; '#' land, '~' water, '.' blocked). "
             f"Column c covers X in [{cell}*c, {cell}*c+{cell - 1}], row r covers Z in [{cell}*r, {cell}*r+{cell - 1}]:",
             "              c=" + "".join(str((c // 10) % 10) for c in range(ncol)),
             "                " + "".join(str(c % 10) for c in range(ncol))]
    for r, row in enumerate(rows):
        lines.append(f"  r={r:2d} Z={r * cell:5d}  {row}")
    return "\n".join(lines)


def format_state_prompt(state: dict, expose_disconnected_positions: bool = False, expose_buildable_grid: bool = False,
                        mark_connectivity: bool = False) -> str:
    """Full observation: aggregates + every BS with position and per-slice load. mark_connectivity (E8 candidate arms)
    appends the bridge's connectivity flag to cells that are under construction or have no live backhaul."""
    lines = []
    lines.append(f"Game time: {state.get('game_time_minutes', 0):.1f} minutes")
    eco = state.get('economy', {})
    lines.append(f"Metal income: {eco.get('metal_income', 0):.0f}/s (build speed depends on this)")
    cyc = state.get('cycle', {})
    lines.append(f"Day/night cycle: {cyc.get('phase', 'day')}, {cyc.get('remaining_seconds', 0)}s remaining")
    units = state.get('units', {})
    lines.append(f"Units: {units.get('engineers', 0)} engineers, {units.get('factories', 0)} factories, "
                 f"{units.get('mexes', 0)} mexes, {units.get('disconnected', 0)} disconnected")
    lines.append(f"Coverage: {state.get('coverage_pct', 0)}%")
    bs_list = state.get('base_stations', [])
    if bs_list:
        lines.append(f"\nBase Stations ({len(bs_list)}):")
        for bs in bs_list:
            mark = ""
            if mark_connectivity:
                if bs.get("under_construction"):
                    mark = " — under construction"
                elif bs.get("connected") is False:
                    mark = " — NO BACKHAUL (inactive, serves nobody)"
            lines.append(f"  BS {bs['id']} ({bs['type']}) at ({bs['pos'][0]}, {bs['pos'][1]}) — "
                         f"eMBB:{bs['load_embb']}% URLLC:{bs['load_urllc']}% mMTC:{bs['load_mmtc']}%{mark}")
    else:
        lines.append("\nNo base stations deployed yet.")
    qos = state.get('qos_violations', {}) or {}
    violations = sum(int(v) for v in qos.values()) if qos else 0
    if violations > 0:
        lines.append(f"\n⚠️ QoS VIOLATIONS: eMBB={qos.get('embb', 0)} URLLC={qos.get('urllc', 0)} mMTC={qos.get('mmtc', 0)}")
    if expose_disconnected_positions and state.get('disconnected_positions'):
        pos = state['disconnected_positions'][:60]
        lines.append(f"\nDisconnected unit positions (first {len(pos)}): " + " ".join(f"({p[0]},{p[1]})" for p in pos))
    if expose_buildable_grid and state.get('buildable_grid'):
        lines.append(format_buildable_grid(state['buildable_grid']))
    threats = state.get('enemy_threats', [])
    threat_count = state.get('enemy_threat_count', 0)
    if threat_count and int(threat_count) > 0:
        lines.append(f"\n⚠️ ENEMY THREATS ({threat_count} armed units detected):")
        lines.append("  DO NOT place BS near these positions (engineer will be killed):")
        for t in threats:
            if isinstance(t, list) and len(t) >= 3:
                lines.append(f"  Enemy at ({t[0]}, {t[1]}) range={t[2]} elmos")
    return "\n".join(lines)


def format_state_minimal(state: dict) -> str:
    """Ablation: coverage %, income, unit counts, BS count -- no spatial, no temporal, no per-BS detail."""
    eco = state.get('economy', {})
    units = state.get('units', {})
    return (f"Coverage: {state.get('coverage_pct', 0)}%. "
            f"Metal income: {eco.get('metal_income', 0):.0f}/s. "
            f"Units: {units.get('total', 0)} total, {units.get('disconnected', 0)} disconnected. "
            f"Base stations: {len(state.get('base_stations', []))}.")


def format_state_nospatial(state: dict) -> str:
    """Ablation: everything except BS positions."""
    lines = []
    lines.append(f"Game time: {state.get('game_time_minutes', 0):.1f} minutes")
    eco = state.get('economy', {})
    lines.append(f"Metal income: {eco.get('metal_income', 0):.0f}/s")
    cyc = state.get('cycle', {})
    lines.append(f"Day/night: {cyc.get('phase', 'day')}, {cyc.get('remaining_seconds', 0)}s remaining")
    units = state.get('units', {})
    lines.append(f"Units: {units.get('engineers', 0)} engineers, {units.get('factories', 0)} factories, {units.get('disconnected', 0)} disconnected")
    lines.append(f"Coverage: {state.get('coverage_pct', 0)}%")
    bs_list = state.get('base_stations', [])
    if bs_list:
        lines.append(f"Base Stations ({len(bs_list)}):")
        for bs in bs_list:
            lines.append(f"  BS {bs['id']} ({bs['type']}) — eMBB:{bs['load_embb']}% URLLC:{bs['load_urllc']}% mMTC:{bs['load_mmtc']}%")
    qos = state.get('qos_violations', {}) or {}
    violations = sum(int(v) for v in qos.values()) if qos else 0
    if violations > 0:
        lines.append(f"QoS VIOLATIONS: eMBB={qos.get('embb', 0)} URLLC={qos.get('urllc', 0)} mMTC={qos.get('mmtc', 0)}")
    return "\n".join(lines)


def format_history(history) -> str:
    if not history:
        return ""
    lines = ["\nYour recent decisions (oldest first):"]
    for h in history:
        lines.append(f"  t={h['t_min']:.0f}min coverage={h['coverage']}% disconnected={h['disconnected']} -> {h['action']}")
    return "\n".join(lines)

# ============================================================
# LLM calling and output handling
# ============================================================

ACTION_PREFIXES = ("place_bs|", "reconfig_slice|", "noop")
PLACE_RE = r'(place_bs\|[a-z_]+\|\d+\|\d+)'
PLACE_OR_CANDIDATE_RE = r'(place_bs\|[a-z_]+\|(?:\d+\|\d+|C\d+))'   # E8: place_bs|TYPE|C<n> refers to a listed candidate
RECONF_RE = r'(reconfig_slice\|\d+\|[\d.]+\|[\d.]+\|[\d.]+)'


def parse_llm_content(content: str, allow_candidates: bool = False):
    """v1-compatible extraction. Returns (action, reasoning, parse_status, had_think).
    With allow_candidates (E8, --candidates) the candidate form place_bs|TYPE|C<n> is a valid action; the caller
    resolves it to coordinates."""
    place_re = PLACE_OR_CANDIDATE_RE if allow_candidates else PLACE_RE
    if content is None:
        content = ""
    content = content.strip()
    had_think = "<think>" in content
    if had_think:
        parts = content.split("</think>")
        content = parts[-1].strip() if len(parts) > 1 else content.replace("<think>", "").strip()
    reasoning = ""
    if "#" in content:
        reasoning = content.split("#", 1)[1].strip()[:200]
    elif not content.startswith(("place_bs", "reconfig_slice", "noop")):
        reasoning = content[:200]
    first_line = content.split("\n")[0].split("#")[0].strip() if content else ""
    if first_line.startswith(ACTION_PREFIXES):
        if first_line.startswith("noop"):
            return "noop", reasoning, "valid", had_think
        m = re.match(place_re, first_line, re.I) or re.match(RECONF_RE, first_line)
        if m:
            return m.group(1), reasoning, "valid", had_think
    m = re.search(place_re, content, re.I)
    if m:
        return m.group(1), reasoning, "extracted", had_think
    m = re.search(RECONF_RE, content)
    if m:
        return m.group(1), reasoning, "extracted", had_think
    return "noop", reasoning, "fallback_noop", had_think


LLM_MAX_ATTEMPTS = 3  # retries for transient transport errors (game is paused meanwhile)


def call_llm(system_prompt: str, user_prompt: str, cfg) -> dict:
    """POST one chat completion. Never raises: every failure becomes parse_status api_error/timeout with action noop.
    Transient transport errors (connection closed/reset, HTTP 5xx, DNS/connect failures) are retried up to
    LLM_MAX_ATTEMPTS times with a short backoff; the game is paused meanwhile, so retries only cost wall-clock."""
    payload = {
        "model": cfg.model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": cfg.temperature,
        "max_tokens": cfg.max_tokens,
    }
    if cfg.extra_body:
        payload.update(cfg.extra_body)
    headers = {"Content-Type": "application/json"}
    if cfg.api_key:
        headers["Authorization"] = f"Bearer {cfg.api_key}"
    data = json.dumps(payload).encode("utf-8")
    t0 = time.time()
    out = {"t_llm_start": t0, "llm_attempts": 0}
    max_attempts = getattr(cfg, "llm_max_attempts", LLM_MAX_ATTEMPTS)
    err = None  # (parse_status, reasoning, raw_response, transient)
    for attempt in range(1, max_attempts + 1):
        out["llm_attempts"] = attempt
        try:
            req = urllib.request.Request(cfg.url, data=data, headers=headers)
            with urllib.request.urlopen(req, timeout=cfg.timeout) as response:
                raw = response.read().decode("utf-8")
            result = json.loads(raw)
            if isinstance(result, dict) and result.get("error") and not result.get("choices"):
                raise ValueError(f"server error: {str(result['error'])[:300]}")
            choice = result["choices"][0]
            content = choice["message"].get("content") or ""
            # Some servers return reasoning separately (e.g. reasoning_content); keep it for the log
            reasoning_field = choice["message"].get("reasoning_content") or choice["message"].get("reasoning") or ""
            action, reasoning, status, had_think = parse_llm_content(content, allow_candidates=bool(getattr(cfg, "candidates", False)))
            out.update({
                "action": action, "reasoning": reasoning, "parse_status": status, "had_think": had_think,
                "raw_response": content[:RAW_RESPONSE_CAP],
                "raw_reasoning_field": (reasoning_field or "")[:RAW_RESPONSE_CAP],
                "finish_reason": choice.get("finish_reason"), "usage": result.get("usage"),
                "served_model": result.get("model"),
                "llm_server_info": result.get("proxy_settings"),  # proxy v2: thinking on/off, effective max_tokens
            })
            err = None
            break
        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read().decode("utf-8", "ignore")[:2000]
            except Exception:
                pass
            err = ("api_error", f"error: HTTP {e.code}", body, e.code >= 500 or e.code == 429)
        except (socket.timeout, TimeoutError) as e:
            err = ("timeout", f"error: {e}", "", False)
        except urllib.error.URLError as e:
            timed_out = "timed out" in str(e).lower()
            err = ("timeout" if timed_out else "api_error", f"error: {e}", "", not timed_out)
        except (KeyError, IndexError, TypeError, ValueError) as e:
            err = ("api_error", f"error: malformed response {e}", "", False)
        except Exception as e:  # RemoteDisconnected, ConnectionResetError, IncompleteRead, OSError, ...
            err = ("api_error", f"error: {type(e).__name__}: {e}", "", True)
        if err and err[3] and attempt < max_attempts:
            print(f"[Orchestrator v2] LLM transport error ({err[1][:120]}); retry {attempt + 1}/{max_attempts} in {2 * attempt}s", flush=True)
            time.sleep(2 * attempt)
            continue
        break
    if err is not None:
        status, reasoning, body, _ = err
        out.update({"action": "noop", "reasoning": reasoning, "parse_status": status, "raw_response": body, "had_think": False})
    out["t_llm_end"] = time.time()
    out["latency_s"] = out["t_llm_end"] - t0
    return out


def query_served_models(url: str, api_key: str = "", timeout: float = 10.0):
    """Best-effort GET <base>/models for the episode header."""
    try:
        base = url.split("/chat/completions")[0]
        req = urllib.request.Request(base + "/models", headers={"Authorization": f"Bearer {api_key}"} if api_key else {})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8"))
        return [m.get("id") for m in data.get("data", [])][:50]
    except Exception as e:
        return f"unavailable: {e}"

# ============================================================
# Baseline agents (identical logic to v1, with an explicit RNG)
# ============================================================

def rule_based_agent(state: dict, rng: random.Random) -> str:
    bs_list = state.get('base_stations', [])
    coverage = state.get('coverage_pct', 100)
    units = state.get('units', {})
    disconnected = units.get('disconnected', 0)
    if coverage < 80 or disconnected > 3:
        if bs_list:
            ref_bs = rng.choice(bs_list)
            x, z = ref_bs['pos']
            dx = x - 8000
            dz = z - 8000
            new_x = x + (400 if dx >= 0 else -400)
            new_z = z + (400 if dz >= 0 else -400)
            return f"place_bs|small_cell|{int(new_x)}|{int(new_z)}"
        return "place_bs|macro_cell|8000|8000"
    for bs in bs_list:
        if bs.get('load_urllc', 0) > 80 and bs.get('load_embb', 0) < 50:
            return f"reconfig_slice|{bs['id']}|0.3|0.6|0.1"
        if bs.get('load_embb', 0) > 80 and bs.get('load_urllc', 0) < 50:
            return f"reconfig_slice|{bs['id']}|0.6|0.3|0.1"
    return "noop"


def random_agent(state: dict, rng: random.Random) -> str:
    eco = state.get('economy', {})
    metal = eco.get('metal_current', 0)
    if metal < 50:
        return "noop"
    x = rng.randint(2000, 14000)
    z = rng.randint(2000, 14000)
    if metal >= 400:
        cell = rng.choice(["macro_cell", "small_cell", "small_cell", "micro_cell"])
    elif metal >= 150:
        cell = rng.choice(["small_cell", "micro_cell", "micro_cell"])
    else:
        cell = "micro_cell"
    return f"place_bs|{cell}|{x}|{z}"


class ReplayAgent:
    """Feeds logged actions by decision index; optionally injects one counterfactual action."""

    def __init__(self, replay_file: Path, inject_decision: int, inject_action: str, after_policy: str, rng):
        self.actions = {}
        self.source_header = None
        with open(replay_file) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                d = json.loads(line)
                if d.get("record") == "header":
                    self.source_header = d
                    continue
                if d.get("record", "decision") != "decision":
                    continue
                self.actions[int(d["decision"])] = d["action"]
        self.inject_decision = inject_decision
        self.inject_action = inject_action
        self.after_policy = after_policy
        self.rng = rng

    def act(self, decision_num: int, state: dict) -> str:
        if self.inject_decision and decision_num == self.inject_decision:
            return self.inject_action
        if self.inject_decision and decision_num > self.inject_decision and self.after_policy != "logged":
            if self.after_policy == "noop":
                return "noop"
            if self.after_policy == "rule":
                return rule_based_agent(state, self.rng)
        return self.actions.get(decision_num, "noop")

# ============================================================
# Game I/O
# ============================================================

def read_game_state(game_log: Path):
    """Return the most recent 6G_AGENT_STATE json from the tee'd engine log (or None)."""
    if not game_log.exists():
        return None
    try:
        with open(game_log, "rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            f.seek(max(0, size - 400_000))
            tail = f.read().decode("utf-8", errors="ignore")
        idx = tail.rfind("6G_AGENT_STATE|")
        if idx < 0:
            return None
        line = tail[idx + len("6G_AGENT_STATE|"):].split("\n", 1)[0].strip()
        return json.loads(line)
    except (IOError, json.JSONDecodeError):
        return None


def game_log_contains(game_log: Path, needle: str) -> bool:
    try:
        with open(game_log, "rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            f.seek(max(0, size - 200_000))
            return needle in f.read().decode("utf-8", errors="ignore")
    except IOError:
        return False


def find_game_id(game_log: Path):
    try:
        with open(game_log, errors="ignore") as f:
            for line in f:
                m = re.search(r"GameID: ([0-9a-f]+)", line)
                if m:
                    return m.group(1)
    except IOError:
        pass
    return None


def write_action(action_file: Path, action: str, decision_frame: int):
    tmp = action_file.with_suffix(".tmp")
    with open(tmp, "w") as f:
        f.write(f"{decision_frame}|{action}\n")
    os.replace(tmp, action_file)


def git_commit(repo: Path) -> str:
    try:
        return subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], stderr=subprocess.DEVNULL).decode().strip()
    except Exception:
        return os.environ.get("BAR_COMMIT", "unknown")

# ============================================================
# Main
# ============================================================

def main():
    ap = argparse.ArgumentParser(description="6G Network Agent Orchestrator v2")
    ap.add_argument("--backend", default="rule",
                    help="llm | llm_nospatial | llm_minimal | rule | random | noop | greedy | replay (aliases: ericai, ericai_nospatial, ericai_minimal, remote, local)")
    ap.add_argument("--team", type=int, default=0)
    ap.add_argument("--scenario", default=os.environ.get("SCENARIO", "unknown"))
    ap.add_argument("--episode-id", default=None)
    ap.add_argument("--episode-dir", default=None, help="directory for decisions.jsonl and header.json (default RESULTS_DIR/<episode-id>)")
    ap.add_argument("--write-dir", default=str(DEFAULT_WRITE_DIR))
    ap.add_argument("--game-log", default=None, help="tee'd engine stdout to watch (default <write-dir>/6g_game_output.log)")
    ap.add_argument("--action-file", default=None, help="default <write-dir>/6g_agent_action.txt")
    ap.add_argument("--seed", type=int, default=0, help="episode seed (also seeds rule/random agents)")
    ap.add_argument("--model", default=os.environ.get("LLM_MODEL", "Qwen/Qwen3.8-27B-FP8-1M"))  # Qwen3-32B-Instruct (June) is no longer served (27 Sep 2026)
    ap.add_argument("--url", default=os.environ.get("LLM_URL", "http://localhost:9000/v1/chat/completions"))
    ap.add_argument("--api-key", default=os.environ.get("LLM_API_KEY", ""))
    ap.add_argument("--timeout", type=float, default=float(os.environ.get("LLM_TIMEOUT", "120")))
    ap.add_argument("--llm-max-attempts", dest="llm_max_attempts", type=int, default=LLM_MAX_ATTEMPTS, help="retries for transient LLM transport errors")
    ap.add_argument("--temperature", type=float, default=0.3)
    ap.add_argument("--max-tokens", type=int, default=2000)
    ap.add_argument("--extra-body", default=os.environ.get("LLM_EXTRA_BODY", ""), help='JSON merged into the request body, e.g. {"reasoning_effort":"medium"}')
    ap.add_argument("--prompt-version", default="v1", choices=["v1", "v2", "v1g", "v1c"])
    ap.add_argument("--candidates", action="store_true", help="append ranked candidate positions to the LLM observation and resolve place_bs|TYPE|C<n> answers (E8)")
    ap.add_argument("--feedback", action="store_true", help="append the validation outcome and coverage change of the previous decision to the observation (E8)")
    ap.add_argument("--history", type=int, default=0, help="number of recent (state, action) pairs appended to the user prompt")
    ap.add_argument("--expose-disconnected-positions", action="store_true")
    ap.add_argument("--expose-buildable-grid", action="store_true", help="append the bridge's buildable-terrain map to the observation (needs modoption 6g_agent_buildable_grid=true)")
    ap.add_argument("--replay-file", default=None)
    ap.add_argument("--inject-decision", type=int, default=0)
    ap.add_argument("--inject-action", default="")
    ap.add_argument("--after-policy", default="logged", choices=["logged", "noop", "rule"])
    ap.add_argument("--max-decisions", type=int, default=0)
    ap.add_argument("--once", action="store_true")
    args = ap.parse_args()

    backend = BACKEND_ALIASES.get(args.backend, args.backend)
    if args.backend == "local" and "LLM_URL" not in os.environ and args.url.endswith(":9000/v1/chat/completions"):
        args.url = "http://localhost:11434/v1/chat/completions"
    write_dir = Path(args.write_dir)
    game_log = Path(args.game_log) if args.game_log else write_dir / "6g_game_output.log"
    action_file = Path(args.action_file) if args.action_file else write_dir / "6g_agent_action.txt"
    episode_id = args.episode_id or f"{args.scenario}_{args.backend}_seed{args.seed}_{time.strftime('%Y%m%d_%H%M%S')}"
    episode_dir = Path(args.episode_dir) if args.episode_dir else DEFAULT_RESULTS_DIR / episode_id
    episode_dir.mkdir(parents=True, exist_ok=True)
    decision_log = episode_dir / "decisions.jsonl"

    try:
        args.extra_body = json.loads(args.extra_body) if args.extra_body else {}
    except json.JSONDecodeError as e:
        sys.exit(f"--extra-body is not valid JSON: {e}")

    rng = random.Random(args.seed if args.seed else None)
    system_prompt = build_prompt(args.prompt_version) if backend in LLM_BACKENDS else None
    replay = None
    if backend == "replay":
        if not args.replay_file:
            sys.exit("--replay-file is required for backend=replay")
        replay = ReplayAgent(Path(args.replay_file), args.inject_decision, args.inject_action, args.after_policy, rng)

    header = {
        "record": "header", "protocol": 2, "orchestrator_version": "2.0",
        "episode_id": episode_id, "scenario": args.scenario, "backend": backend, "backend_arg": args.backend,
        "seed": args.seed, "team": args.team, "commit": git_commit(REPO_ROOT),
        "start_time": time.time(), "start_time_iso": time.strftime("%Y-%m-%dT%H:%M:%S"), "host": socket.gethostname(),
        "write_dir": str(write_dir), "game_log": str(game_log), "action_file": str(action_file),
        "expose_disconnected_positions": args.expose_disconnected_positions,
        "expose_buildable_grid": args.expose_buildable_grid,
        "candidates": args.candidates, "feedback": args.feedback,
    }
    if backend in LLM_BACKENDS:
        header.update({
            "model": args.model, "url": args.url, "api_key_set": bool(args.api_key), "timeout_s": args.timeout,
            "temperature": args.temperature, "max_tokens": args.max_tokens, "extra_body": args.extra_body,
            "prompt_version": args.prompt_version, "prompt_sha256": hashlib.sha256(system_prompt.encode()).hexdigest(),
            "system_prompt": system_prompt, "history": args.history,
            "served_models": query_served_models(args.url, args.api_key),
        })
    if replay is not None:
        header.update({"replay_file": args.replay_file, "inject_decision": args.inject_decision,
                       "inject_action": args.inject_action, "after_policy": args.after_policy,
                       "replay_source_header": replay.source_header})
    with open(episode_dir / "header.json", "w") as f:
        json.dump(header, f, indent=2)
    with open(decision_log, "a") as f:
        f.write(json.dumps(header) + "\n")

    print(f"[Orchestrator v2] backend={backend} episode={episode_id}")
    print(f"[Orchestrator v2] watching {game_log}; action file {action_file}; log {decision_log}")

    history = deque(maxlen=max(args.history, 0))
    decision_count = 0
    prev_decision = None
    recent_placements = []   # (decision, x, z) of the agent's own place_bs orders; excludes them from the candidate set for CAND_RECENT_N decisions
    last_processed_frame = -1
    game_id = None

    while True:
        state = read_game_state(game_log)
        if state and state.get("frame", 0) > last_processed_frame:
            t_seen = time.time()
            decision_count += 1
            frame = int(state["frame"])
            last_processed_frame = frame
            print(f"\n[Orchestrator v2] Decision #{decision_count} at frame {frame} ({state.get('game_time_seconds', 0)}s)")

            rec = {"record": "decision", "decision": decision_count, "decision_frame": frame,
                   "game_time_s": state.get("game_time_seconds", 0), "backend": backend,
                   "t_state_seen": t_seen}
            if decision_count == 1 and state.get("buildable_grid"):
                rec["buildable_grid"] = state["buildable_grid"]      # static terrain map (E7), logged once per episode
            reasoning = ""
            if backend == "rule":
                action = rule_based_agent(state, rng)
            elif backend == "random":
                action = random_agent(state, rng)
            elif backend == "noop":
                action = "noop"
            elif backend == "greedy":
                cands = compute_candidates(state, recent=[t for t in recent_placements if t[0] > decision_count - CAND_RECENT_N])
                rec["candidates"] = cands
                rec["backhaul_nodes"], rec["blocked_cells"] = state.get("backhaul_nodes"), state.get("blocked_cells")
                action = greedy_agent(state, cands)
            elif backend == "replay":
                action = replay.act(decision_count, state)
                rec["injected"] = bool(args.inject_decision and decision_count == args.inject_decision)
            elif backend in LLM_BACKENDS:
                if backend == "llm":
                    user_prompt = format_state_prompt(state, args.expose_disconnected_positions, args.expose_buildable_grid,
                                                      mark_connectivity=bool(args.candidates))
                elif backend == "llm_nospatial":
                    user_prompt = format_state_nospatial(state)
                else:
                    user_prompt = format_state_minimal(state)
                if args.history > 0:
                    user_prompt += format_history(history)
                cands = []
                if args.candidates and backend == "llm":
                    cands = compute_candidates(state, recent=[t for t in recent_placements if t[0] > decision_count - CAND_RECENT_N])
                    rec["candidates"] = cands
                    rec["backhaul_nodes"], rec["blocked_cells"] = state.get("backhaul_nodes"), state.get("blocked_cells")
                    user_prompt += format_candidates(cands, state.get("units", {}).get("disconnected", 0),
                                                     float(state.get("bs_to_backhaul_range") or CAND_BACKHAUL_R))
                if args.feedback and backend == "llm" and prev_decision:
                    prev_decision["disconnected_now"] = state.get("units", {}).get("disconnected", 0)
                    user_prompt += format_feedback(prev_decision, last_validation(game_log, prev_decision["decision"]), state.get("coverage_pct", 0))
                print(f"[Orchestrator v2] Observation:\n{user_prompt}\n")
                llm = call_llm(system_prompt, user_prompt, args)
                action, reasoning = llm.pop("action"), llm.pop("reasoning")
                rec.update(llm)
                if args.candidates and backend == "llm":
                    mc = re.match(r"^place_bs\|(macro_cell|small_cell|micro_cell)\|C(\d+)\s*$", (action or "").strip(), re.I)
                    if mc:
                        rec["raw_action"] = action
                        idx = int(mc.group(2)) - 1
                        if 0 <= idx < len(cands):
                            action = f"place_bs|{mc.group(1).lower()}|{cands[idx]['x']}|{cands[idx]['z']}"
                            rec["candidate_id"] = cands[idx]["id"]
                        else:
                            action, rec["candidate_id"] = "noop", "invalid"
                rec["user_prompt"] = user_prompt
                print(f"[Orchestrator v2] LLM {rec.get('parse_status')} in {rec.get('latency_s', 0):.1f}s: {rec.get('raw_response', '')[:160]!r}")
            else:
                sys.exit(f"unknown backend {backend}")

            write_action(action_file, action, frame)
            t_written = time.time()
            print(f"[Orchestrator v2] Action: {action}")

            rec.update({
                "action": action, "reasoning": reasoning, "t_action_written": t_written,
                "decision_wall_s": t_written - t_seen,
                "timestamp": t_written,  # v1 compatibility
                "state_summary": {
                    "coverage_pct": state.get("coverage_pct", 0),
                    "total_bs": len(state.get("base_stations", [])),
                    "metal": state.get("economy", {}).get("metal_current", 0),
                    "metal_income": state.get("economy", {}).get("metal_income", 0),
                    "disconnected": state.get("units", {}).get("disconnected", 0),
                    "engineers": state.get("units", {}).get("engineers", 0),
                    "total_units": state.get("units", {}).get("total", 0),
                    "mobile_units": state.get("mobile_units", None),
                    "qos_embb": state.get("qos_violations", {}).get("embb", 0),
                    "qos_urllc": state.get("qos_violations", {}).get("urllc", 0),
                    "qos_mmtc": state.get("qos_violations", {}).get("mmtc", 0),
                    "cycle_phase": state.get("cycle", {}).get("phase", "day"),
                },
                "base_stations": state.get("base_stations", []),
                "disconnected_positions": state.get("disconnected_positions", []),
                "enemy_threats": state.get("enemy_threats", []),
            })
            with open(decision_log, "a") as f:
                f.write(json.dumps(rec) + "\n")

            history.append({"t_min": state.get("game_time_minutes", 0), "coverage": state.get("coverage_pct", 0),
                            "disconnected": state.get("units", {}).get("disconnected", 0), "action": action})
            prev_decision = {"decision": decision_count, "action": action, "coverage": state.get("coverage_pct", 0),
                             "disconnected": state.get("units", {}).get("disconnected", 0)}
            if action.startswith("place_bs|"):
                parts = action.split("|")
                if len(parts) == 4 and parts[2].isdigit() and parts[3].isdigit():
                    recent_placements.append((decision_count, int(parts[2]), int(parts[3])))

            if game_id is None:
                game_id = find_game_id(game_log)

            if args.once or (args.max_decisions and decision_count >= args.max_decisions):
                break

        if decision_count > 0 and game_log_contains(game_log, "[6G Agent] Match ended"):
            print("[Orchestrator v2] Match ended; exiting")
            break
        time.sleep(POLL_INTERVAL)

    footer = {"record": "footer", "episode_id": episode_id, "decisions": decision_count,
              "game_id": game_id or find_game_id(game_log), "end_time": time.time()}
    with open(decision_log, "a") as f:
        f.write(json.dumps(footer) + "\n")
    header.update({"game_id": footer["game_id"], "decisions": decision_count, "end_time": footer["end_time"]})
    with open(episode_dir / "header.json", "w") as f:
        json.dump(header, f, indent=2)


if __name__ == "__main__":
    main()
