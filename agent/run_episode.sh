#!/bin/bash
# Run ONE experiment episode (revision campaign, protocol v2) and archive it under RESULTS_DIR/<episode_id>/.
# Never touches agent/data (the frozen June 2026 campaign).
#
# Usage:
#   agent/run_episode.sh SCENARIO BACKEND [options]
#     SCENARIO  s1_peaceful | s2_stress | s3_daynight | s4_adversarial  (agent/scenarios/*.txt)
#     BACKEND   llm | llm_nospatial | llm_minimal | rule | random | noop | replay
#   Options:
#     --seed N             episode seed -> engine [GAME] FixedRNGSeed + modoption 6g_random_seed; default: random 1..2^31
#     --duration MIN       episode length in sim-minutes (default 30)
#     --speed N            target sim speed: start script MinSpeed=1, MaxSpeed>=N, 6g_target_speed=N; the bridge starts the
#                          game at 1x and ramps to N at frame 90 (client must not lag the server); 0 = engine default (1x)
#     --headless           use spring-headless (no window); default: spring --window
#     --autoplace true|false   6g_networkbst_autoplace (default true)
#     --write-dir DIR      engine write dir (default $BAR_WRITE_DIR or ~/.local/state/Beyond All Reason)
#     --fresh-write-dir DIR  create DIR with symlinks to the base write dir's games/maps/pool/packages/rapid and use it
#     --results-dir DIR    default $RESULTS_DIR or <repo>/agent/results_v2
#     --tag TAG            appended to the episode id
#     --orch-args "..."    extra arguments passed to orchestrator.py (e.g. "--model X --prompt-version v2 --history 5")
#     --set KEY=VALUE      extra modoption override (repeatable)
#     --host-port N        engine host port (default 8452; concurrent instances need distinct ports;
#                          with --fresh-write-dir DIR the default is 8453 + trailing digits of DIR)
#     --mem-max GB         hard RAM cap for the engine process via a systemd user scope (default 7 headless / 9 windowed, env BAR_MEM_MAX_GB; 0 = off).
#                          The engine is killed if it exceeds the cap, so the desktop and other runs survive.
#     --min-free GB        wait (up to 30 min) until this much RAM is available before launching (default 8,
#                          env BAR_MIN_FREE_GB; 0 = off). One headless engine needs ~5 GB; on a 16 GB laptop run ONE at a time.
#     --nice N             nice level for the engine (default 10)
#     --ai-order-delay N   modoption 6g_ai_order_delay: STAI (unsynced Lua AI) orders execute at issue frame + N
#                          instead of at network arrival (default 45 = 1.5 s; 0 = legacy immediate execution, non-deterministic)
#     --agent-action-delay N  modoption 6g_agent_action_delay: the agent's action executes at decision frame + N
#                          (default 45 = 1.5 s; 0 = legacy execute-on-arrival). summary.json lag_violations must stay 0.
#     --aslr               keep address-space randomisation ON for the engine. Default OFF (setarch -R): Lua 5.1 iterates
#                          pointer-keyed tables in address order, so same-seed runs only reproduce with ASLR disabled.
#     --settings FILE      springsettings.cfg to install into the write dir before launch (default with --headless:
#                          docker/springsettings.headless.cfg; also sets modoption 6g_headless=true so LuaUI is disabled)
#     --dry-run            generate the start script and print the commands only
set -u
SCENARIO="${1:?Usage: $0 SCENARIO BACKEND [options]}"; BACKEND="${2:?Usage: $0 SCENARIO BACKEND [options]}"; shift 2
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BASE_WRITE_DIR="${BAR_WRITE_DIR:-$HOME/.local/state/Beyond All Reason}"
ENGINE_DIR="${BAR_ENGINE_DIR:-$BASE_WRITE_DIR/engine/recoil_2025.06.24}"
RESULTS_DIR="${RESULTS_DIR:-$REPO_DIR/agent/results_v2}"
SEED=$(( (RANDOM << 15) | RANDOM )); [ "$SEED" -eq 0 ] && SEED=1
DURATION=30; SPEED=0; HEADLESS=0; AUTOPLACE=true; TAG=""; ORCH_ARGS=""; WRITE_DIR="$BASE_WRITE_DIR"; FRESH_WD=""; DRY=0; EXTRA_SET=(); HOST_PORT=""
MEM_MAX_GB="${BAR_MEM_MAX_GB:-}"; MIN_FREE_GB="${BAR_MIN_FREE_GB:-8}"; NICE=10; SETTINGS=""; ASLR="${BAR_ASLR:-0}"; AI_DELAY="${BAR_AI_ORDER_DELAY:-45}"; AGENT_DELAY="${BAR_AGENT_ACTION_DELAY:-45}"
while [ $# -gt 0 ]; do
  case "$1" in
    --seed) SEED="$2"; shift 2;;
    --duration) DURATION="$2"; shift 2;;
    --speed) SPEED="$2"; shift 2;;
    --headless) HEADLESS=1; shift;;
    --autoplace) AUTOPLACE="$2"; shift 2;;
    --write-dir) WRITE_DIR="$2"; shift 2;;
    --fresh-write-dir) FRESH_WD="$2"; shift 2;;
    --results-dir) RESULTS_DIR="$2"; shift 2;;
    --tag) TAG="_$2"; shift 2;;
    --orch-args) ORCH_ARGS="$2"; shift 2;;
    --set) EXTRA_SET+=("--set" "$2"); shift 2;;
    --host-port) HOST_PORT="$2"; shift 2;;
    --mem-max) MEM_MAX_GB="$2"; shift 2;;
    --min-free) MIN_FREE_GB="$2"; shift 2;;
    --nice) NICE="$2"; shift 2;;
    --settings) SETTINGS="$2"; shift 2;;
    --aslr) ASLR=1; shift;;
    --ai-order-delay) AI_DELAY="$2"; shift 2;;
    --agent-action-delay) AGENT_DELAY="$2"; shift 2;;
    --dry-run) DRY=1; shift;;
    *) echo "unknown option $1"; exit 2;;
  esac
done
[ -z "$MEM_MAX_GB" ] && { if [ "$HEADLESS" = "1" ]; then MEM_MAX_GB=7; else MEM_MAX_GB=9; fi; }  # windowed engine peaks ~7.1 GB
SCENARIO_FILE="$REPO_DIR/agent/scenarios/${SCENARIO}.txt"
[ -f "$SCENARIO_FILE" ] || { echo "ERROR: scenario not found: $SCENARIO_FILE"; exit 1; }

# Optional per-instance write dir (parallel runs on one machine)
if [ -n "$FRESH_WD" ]; then
  if [ ! -d "$FRESH_WD" ]; then
    mkdir -p "$FRESH_WD"
    for d in games maps pool packages rapid; do [ -e "$BASE_WRITE_DIR/$d" ] && ln -s "$BASE_WRITE_DIR/$d" "$FRESH_WD/$d"; done
    [ -f "$BASE_WRITE_DIR/springsettings.cfg" ] && cp "$BASE_WRITE_DIR/springsettings.cfg" "$FRESH_WD/"
  fi
  WRITE_DIR="$FRESH_WD"
fi

if [ -z "$HOST_PORT" ]; then
  if [ -n "$FRESH_WD" ]; then n=$(echo "$FRESH_WD" | grep -oE "[0-9]+$"); HOST_PORT=$((8453 + ${n:-0})); else HOST_PORT=8452; fi
fi
EPISODE_ID="${SCENARIO}_${BACKEND}${TAG}_seed${SEED}_$(date +%Y%m%d_%H%M%S)"
EP_DIR="$RESULTS_DIR/$EPISODE_ID"; mkdir -p "$EP_DIR"
START_SCRIPT="$EP_DIR/start_script.txt"
SETS=(--set "6g_match_duration=$DURATION" --set "6g_random_seed=$SEED" --set "6g_networkbst_autoplace=$AUTOPLACE" --set "6g_save_checkpoints=false" --set "6g_ai_order_delay=$AI_DELAY" --set "6g_agent_action_delay=$AGENT_DELAY")
if [ "$HEADLESS" = "1" ]; then
  SETS+=(--set "6g_headless=true")
  [ -z "$SETTINGS" ] && [ -f "$REPO_DIR/docker/springsettings.headless.cfg" ] && SETTINGS="$REPO_DIR/docker/springsettings.headless.cfg"
fi
if [ -n "$SETTINGS" ]; then
  [ -f "$SETTINGS" ] || { echo "ERROR: settings file not found: $SETTINGS"; exit 1; }
  if [ "$WRITE_DIR" = "$BASE_WRITE_DIR" ]; then echo "  NOTE: --settings ignored for the base write dir (use --fresh-write-dir)"; SETTINGS="";
  else cp "$SETTINGS" "$WRITE_DIR/springsettings.cfg"; fi
fi
if [ "$SPEED" != "0" ]; then SETS+=(--set "MinSpeed=1" --set "MaxSpeed=$(( SPEED > 20 ? SPEED : 20 ))" --set "6g_target_speed=$SPEED"); fi
# FixedRNGSeed (engine, [GAME] section) seeds the server-side RNG that the engine uses at load time and at game start
# (unit-ID pool shuffle, NETMSG_RANDSEED); 6g_random_seed seeds synced Lua math.random. Both are needed for determinism.
python3 "$REPO_DIR/agent/make_start_script.py" "$SCENARIO_FILE" "$START_SCRIPT" "${SETS[@]}" "${EXTRA_SET[@]}" --game-set "HostPort=$HOST_PORT" --game-set "FixedRNGSeed=$SEED" || exit 1

if [ "$HEADLESS" = "1" ]; then ENGINE_BIN="$ENGINE_DIR/spring-headless"; ENGINE_OPTS=(); else ENGINE_BIN="$ENGINE_DIR/spring"; ENGINE_OPTS=(--window); fi
[ -x "$ENGINE_BIN" ] || { echo "ERROR: engine not found: $ENGINE_BIN"; exit 1; }
GAME_LOG="$EP_DIR/gamelog.txt"; ACTION_FILE="$WRITE_DIR/6g_agent_action.txt"

echo "=== Episode $EPISODE_ID ==="
echo "  scenario=$SCENARIO backend=$BACKEND seed=$SEED duration=${DURATION}min speed=$SPEED headless=$HEADLESS autoplace=$AUTOPLACE settings=${SETTINGS:-<write-dir default>}"
echo "  write-dir=$WRITE_DIR  host-port=$HOST_PORT  results=$EP_DIR"
ORCH_CMD=(python3 "$REPO_DIR/agent/orchestrator.py" --backend "$BACKEND" --scenario "$SCENARIO" --seed "$SEED" --episode-id "$EPISODE_ID" --episode-dir "$EP_DIR" --write-dir "$WRITE_DIR" --game-log "$GAME_LOG" --action-file "$ACTION_FILE")
# shellcheck disable=SC2206
ORCH_CMD+=($ORCH_ARGS)
if [ "$DRY" = "1" ]; then echo "  orchestrator: ${ORCH_CMD[*]}"; echo "  engine: $ENGINE_BIN --write-dir \"$WRITE_DIR\" ${ENGINE_OPTS[*]} $START_SCRIPT"; exit 0; fi

# --- Resource guard 1: wait for free RAM (one headless engine peaks at ~5 GB; see summary.json peak_rss_mb) ---
if [ "$MIN_FREE_GB" != "0" ]; then
  waited=0
  while :; do
    avail_kb=$(awk '/MemAvailable/{print $2}' /proc/meminfo)
    [ "$avail_kb" -ge $((MIN_FREE_GB * 1024 * 1024)) ] && break
    [ "$waited" -eq 0 ] && echo "  waiting for ${MIN_FREE_GB} GB free RAM (available now: $((avail_kb / 1024)) MB)"
    sleep 15; waited=$((waited + 15))
    [ "$waited" -ge 1800 ] && { echo "ERROR: still < ${MIN_FREE_GB} GB free RAM after 30 min; giving up"; exit 4; }
  done
fi
# --- Resource guard 2: hard cap the engine in its own cgroup (killed at the cap, no swap thrash), lower priority ---
ENGINE_WRAP=(nice -n "$NICE")
if [ "$MEM_MAX_GB" != "0" ] && command -v systemd-run >/dev/null 2>&1 && systemd-run --user --scope -q -p MemoryMax=1G true 2>/dev/null; then
  ENGINE_WRAP=(systemd-run --user --scope -q -p "MemoryMax=${MEM_MAX_GB}G" -p MemorySwapMax=0 nice -n "$NICE")
  echo "  engine cgroup: MemoryMax=${MEM_MAX_GB}G MemorySwapMax=0 nice=$NICE"
else
  echo "  engine: no cgroup cap (systemd-run unavailable or --mem-max 0), nice=$NICE"
fi
if [ "$ASLR" = "0" ] && command -v setarch >/dev/null 2>&1 && setarch "$(uname -m)" -R true 2>/dev/null; then
  ENGINE_WRAP+=(setarch "$(uname -m)" -R); echo "  engine: ASLR disabled (setarch -R)"
else
  echo "  engine: ASLR left enabled"
fi

rm -f "$ACTION_FILE" "$WRITE_DIR/cache/ArchiveCache20.lua"
"${ORCH_CMD[@]}" > "$EP_DIR/orchestrator.log" 2>&1 &
ORCH_PID=$!
# --- Watchdog: if the orchestrator dies before the match ends, the engine would wait for an action forever ---
rm -f "$EP_DIR/.orch_died"
(
  while kill -0 $ORCH_PID 2>/dev/null; do sleep 5; done
  sleep 15
  if ! grep -q "Match ended" "$GAME_LOG" 2>/dev/null; then
    echo "[run_episode] orchestrator exited before the match ended at $(date +%T); aborting the engine" | tee -a "$EP_DIR/orchestrator.log"
    date +%s > "$EP_DIR/.orch_died"
    pkill -f -- "$START_SCRIPT" 2>/dev/null
  fi
) &
WATCHDOG_PID=$!
# --- Peak-RSS sampler (the engine's cmdline contains the unique start-script path) ---
RSS_FILE="$EP_DIR/.peak_rss_kb"; echo 0 > "$RSS_FILE"
(
  for _ in $(seq 60); do pgrep -f -- "$START_SCRIPT" >/dev/null 2>&1 && break; sleep 1; done
  peak=0
  while pids=$(pgrep -d, -f -- "$START_SCRIPT" 2>/dev/null) && [ -n "$pids" ]; do
    cur=$(ps -o rss= -p "$pids" 2>/dev/null | sort -n | tail -1 | tr -d ' ')
    if [ -n "$cur" ] && [ "$cur" -gt "$peak" ]; then peak=$cur; echo "$peak" > "$RSS_FILE"; fi
    sleep 5
  done
) &
SAMPLER_PID=$!
# --- Ctrl-C / SIGTERM: stop the engine and the orchestrator instead of leaving them running as orphans.
# (bash only runs traps after a foreground command has finished, so the engine pipeline runs in the background
# and the script waits for it with the interruptible builtin `wait`.)
on_signal() {
  echo "[run_episode] interrupted at $(date +%T); stopping engine and orchestrator" | tee -a "$EP_DIR/orchestrator.log"
  pkill -TERM -f -- "$START_SCRIPT" 2>/dev/null; sleep 3; pkill -KILL -f -- "$START_SCRIPT" 2>/dev/null
  kill $ORCH_PID $SAMPLER_PID $WATCHDOG_PID 2>/dev/null
  exit 130
}
trap on_signal INT TERM
T0=$(date +%s)
"${ENGINE_WRAP[@]}" "$ENGINE_BIN" --write-dir "$WRITE_DIR" "${ENGINE_OPTS[@]}" "$START_SCRIPT" 2>&1 | grep --line-buffered -v "CTextureRenderAtlas" | tee "$GAME_LOG" | grep --line-buffered -E "\[6G (Agent|Seed)\]|GameID|Match ended|error|Error" | grep --line-buffered -v "6G_AGENT_STATE" &
ENGINE_PIPE_PID=$!
wait $ENGINE_PIPE_PID
trap - INT TERM
T1=$(date +%s)
sleep 2; kill $ORCH_PID 2>/dev/null; wait $ORCH_PID 2>/dev/null
kill $SAMPLER_PID 2>/dev/null; wait $SAMPLER_PID 2>/dev/null
kill $WATCHDOG_PID 2>/dev/null; wait $WATCHDOG_PID 2>/dev/null
PEAK_RSS_KB=$(cat "$RSS_FILE" 2>/dev/null || echo 0); rm -f "$RSS_FILE"

python3 - "$EP_DIR" "$((T1-T0))" "$PEAK_RSS_KB" "$MEM_MAX_GB" "$ASLR" <<'PY'
import json, re, sys
from pathlib import Path
ep = Path(sys.argv[1]); wall = int(sys.argv[2]); peak_rss_mb = int(sys.argv[3]) // 1024; mem_max_gb = sys.argv[4]
dec = [json.loads(l) for l in open(ep/"decisions.jsonl") if l.strip()] if (ep/"decisions.jsonl").exists() else []
n_dec = sum(1 for d in dec if d.get("record") == "decision")
log = open(ep/"gamelog.txt", errors="ignore").read() if (ep/"gamelog.txt").exists() else ""
lags = [int(x) for x in re.findall(r"lag (-?\d+) frames", log)]
stale = len(re.findall(r"Stale action ignored", log)); rejected = len(re.findall(r"Rejected action message", log))
val = re.findall(r"validation: (\w+)", log)
seed_line = re.search(r"\[6G Seed\][^\n]*", log); gid = re.search(r"GameID: ([0-9a-f]+)", log)
ai_stats = re.findall(r"\[6G AI Orders\] frame \d+: delay=(\d+) late=(\d+) arrival-lag histogram \{([^}]*)\}", log)
ai_delay, ai_late, ai_hist = (int(ai_stats[-1][0]), int(ai_stats[-1][1]), ai_stats[-1][2]) if ai_stats else (None, None, None)
ramp = re.search(r"Game speed ramped to (\d+)x at frame (\d+)", log); sp = re.search(r"warm-up: first AI update done at frame (\d+)", log)
ended = "Match ended" in log
# executed action must equal the logged action of the same decision
exec_actions = dict((int(k), v.strip()) for k, v in re.findall(r"Decision #(\d+) executed at frame \d+ \(decision frame \d+, lag -?\d+ frames\): (.*)", log))
logged = {d["decision"]: d["action"] for d in dec if d.get("record") == "decision"}
mismatch = [k for k, v in exec_actions.items() if logged.get(k) != v]
summary = {"decisions_logged": n_dec, "decisions_executed": len(exec_actions), "max_lag_frames": max(lags) if lags else None,
           "lag_violations": sum(1 for l in lags if l > 1), "stale_ignored": stale, "rejected_untagged": rejected,
           "action_mismatches": mismatch, "validation_outcomes": {v: val.count(v) for v in set(val)},
           "seed_log": seed_line.group(0) if seed_line else None, "game_id": gid.group(1) if gid else None,
           "match_ended": ended, "wall_clock_s": wall, "peak_rss_mb": peak_rss_mb, "mem_max_gb": mem_max_gb, "aslr_disabled": sys.argv[5] == "0",
           "ai_order_delay": ai_delay, "ai_orders_late": ai_late, "ai_order_lag_hist": ai_hist, "speed_ramp": ramp.group(0) if ramp else None, "ai_warmup_frame": int(sp.group(1)) if sp else None,
           "engine_killed": bool(re.search(r"Killed|out of memory", log[-4000:], re.I)) or (not ended and n_dec >= 1),
           "orchestrator_died": (ep / ".orch_died").exists(),
           "llm_parse_status": {k: sum(1 for d in dec if d.get("record") == "decision" and d.get("parse_status") == k) for k in ("valid", "extracted", "fallback_noop", "api_error", "timeout")} if any(d.get("parse_status") for d in dec) else None,
           "llm_infra_errors": sum(1 for d in dec if d.get("record") == "decision" and d.get("parse_status") in ("api_error", "timeout")),
           "llm_attempts_total": sum(int(d.get("llm_attempts") or 1) for d in dec if d.get("record") == "decision" and d.get("llm_attempts")) or None}
json.dump(summary, open(ep/"summary.json", "w"), indent=2)
print(json.dumps(summary, indent=2))
ai_warm = summary["ai_warmup_frame"]
# Infrastructure failures (endpoint/tunnel: api_error, timeout) make an LLM episode non-representative -> re-run it.
# Model-side failures (fallback_noop, extracted) are legitimate results and are kept.
infra_bad = summary["llm_infra_errors"] > max(2, n_dec // 10)
if infra_bad: print("LLM infrastructure errors:", summary["llm_infra_errors"], "of", n_dec, "decisions -> episode should be re-run")
ok = ended and n_dec >= 1 and not mismatch and summary["lag_violations"] == 0 and not ai_late and (ai_warm is None or ai_warm == 150) and not infra_bad
if ai_warm is not None and ai_warm != 150: print("AI warm-up landed on frame", ai_warm, "(expected 150): episode not reproducible")
print("EPISODE", "OK" if ok else "CHECK FAILED")
sys.exit(0 if ok else 3)
PY
