#!/usr/bin/env python3
"""Compare two episodes run with the same seed and action policy (E4b determinism check / F6a replay pilot).

  compare_determinism.py EP_DIR_A EP_DIR_B [--log] [--keep-arrival]

Compares, decision by decision: decision frame, game time, action, state_summary, base_stations,
disconnected_positions, enemy_threats.  With --log also compares the synced game-log lines
([f=NNN] [6G NetworkBST v2]/[6G Agent]/[6G Seed] ...) after stripping wall-clock stamps, and reports the first
divergent frame.  Exit code 0 = identical, 1 = divergence, 2 = usage/incomplete episodes.
"""
from common import open_gamelog
import json, re, sys
from pathlib import Path

FIELDS = ["decision_frame", "game_time_s", "action", "state_summary", "base_stations", "disconnected_positions", "enemy_threats"]
SYNC_RE = re.compile(r"^\[t=[^\]]+\]\[f=(-?\d+)\] (\[6G (?:NetworkBST v2|Agent|Seed)\].*)$")


def load(ep):
    recs = [json.loads(l) for l in open(ep / "decisions.jsonl") if l.strip()]
    dec = [r for r in recs if r.get("record") == "decision"]
    head = next((r for r in recs if r.get("record") == "header"), {})
    summ = json.load(open(ep / "summary.json")) if (ep / "summary.json").exists() else {}
    return head, dec, summ


ARRIVAL_RE = re.compile(r"Decision #\d+ (→|->) |action received at frame|Decision #\d+ at frame \d+ .*paused")


def sync_lines(ep, ignore_arrival=True):
    """Simulation-side log lines. Lines that record the *arrival* of the agent's message (unsynced, wall-clock
    dependent: the orchestrator answers a few frames after the pause) are skipped unless ignore_arrival=False;
    the executed frame ('executed at frame ...') is synced and is always compared."""
    out = []
    for line in (open_gamelog(ep / "gamelog.txt") or []):
        m = SYNC_RE.match(line.rstrip("\n"))
        if m and "6G_AGENT_STATE" not in line:
            if ignore_arrival and ARRIVAL_RE.search(m.group(2)):
                continue
            out.append((int(m.group(1)), m.group(2)))
    return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) != 2:
        sys.exit(__doc__)
    a, b = Path(args[0]), Path(args[1])
    ha, da, sa = load(a); hb, db, sb = load(b)
    print(f"A: {a.name}\n   seed={ha.get('seed')} decisions={len(da)} match_ended={sa.get('match_ended')} wall={sa.get('wall_clock_s')}s peak_rss={sa.get('peak_rss_mb')}MB")
    print(f"B: {b.name}\n   seed={hb.get('seed')} decisions={len(db)} match_ended={sb.get('match_ended')} wall={sb.get('wall_clock_s')}s peak_rss={sb.get('peak_rss_mb')}MB")
    if ha.get("seed") != hb.get("seed"):
        print("NOTE: different seeds -> divergence is expected (negative control)")
    rc = 0
    if not (sa.get("match_ended") and sb.get("match_ended")):
        print("WARNING: at least one episode did not finish"); rc = 2
    n = min(len(da), len(db))
    if len(da) != len(db):
        print(f"DIFF: decision count {len(da)} vs {len(db)}"); rc = rc or 1
    for i in range(n):
        for f in FIELDS:
            if da[i].get(f) != db[i].get(f):
                va, vb = json.dumps(da[i].get(f))[:160], json.dumps(db[i].get(f))[:160]
                print(f"DIFF decision #{da[i].get('decision')} field {f}:\n   A: {va}\n   B: {vb}"); rc = rc or 1
    print(f"decisions compared: {n}; identical fields: {'yes' if rc == 0 else 'NO'}")
    if "--log" in sys.argv:
        keep = "--keep-arrival" in sys.argv
        la, lb = sync_lines(a, not keep), sync_lines(b, not keep)
        print(f"synced log lines: {len(la)} vs {len(lb)}")
        for i, (x, y) in enumerate(zip(la, lb)):
            if x != y:
                print(f"first log divergence at index {i}: frame {x[0]} vs {y[0]}\n   A: {x[1][:160]}\n   B: {y[1][:160]}"); rc = rc or 1; break
        else:
            if len(la) != len(lb):
                print("log prefix identical but lengths differ"); rc = rc or 1
            else:
                print("synced game-log lines identical")
    print("RESULT:", "IDENTICAL" if rc == 0 else ("DIVERGENT" if rc == 1 else "INCOMPLETE"))
    sys.exit(rc)


if __name__ == "__main__":
    main()
