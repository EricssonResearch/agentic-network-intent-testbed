#!/usr/bin/env python3
"""
Campaign runner: executes the episodes listed in a manifest, several at a time, idempotently.

Manifest (CSV, header row): scenario,backend,seed,replicate,tag,orch_args,duration,speed,autoplace[,set]
  e.g.  s1_peaceful,llm,1001,1,core,"--model Qwen/Qwen3-32B-Instruct --prompt-version v1",30,5,true
  set (optional): ";"-separated extra modoptions KEY=VALUE, each passed as run_episode.sh --set (e.g. 6g_path_loss_exponent=2.0)

Executors
  local   : agent/run_episode.sh --headless --fresh-write-dir /tmp/bar_wd_<slot>   (this machine)
  docker  : docker run --rm -v RESULTS:/results -e LLM_URL -e LLM_MODEL -e LLM_API_KEY IMAGE <args>

An episode is considered done when a results directory whose name starts with
"<scenario>_<backend>_<tag>_seed<seed>_" contains a summary.json that passes the validity checks in
summary_problems(): match ended, no lag violations / late AI orders / action mismatches, warm-up at frame 150,
orchestrator alive, and at most max(2, 10 % of decisions) LLM infrastructure errors (timeouts, connection
failures -> forced noop). Done episodes are skipped, so the runner can be restarted or run on several machines
with the same or disjoint manifests. An episode whose results directories all fail the checks (e.g. the LLM
endpoint was unreachable for part of the match) is re-run; its failing directories are first moved to
<results-dir>/failed/ so that the analysis loader never sees two copies of one seed. Directories without a
summary.json (episode still running, or killed before the summary was written) are left in place.
--verify lists every finished directory that fails the checks; --status counts done/pending without running.

  agent/campaign.py MANIFEST.csv --executor local --parallel 1 --results-dir agent/results_v2

RAM: one headless engine peaks at ~5 GB (summary.json: peak_rss_mb). run_episode.sh refuses to start an engine
while < BAR_MIN_FREE_GB (8) are available and caps each engine at BAR_MEM_MAX_GB (7) in a systemd user scope, so
--parallel N > RAM/8 GB only queues; on a 16 GB laptop use --parallel 1 (2 only with Ollama unloaded).
  agent/campaign.py MANIFEST.csv --executor docker --image bar-6g-testbed:revision-v1 --parallel 4 --results-dir /srv/results
  agent/campaign.py MANIFEST.csv --status
  agent/campaign.py MANIFEST.csv --verify
"""
import argparse, csv, json, os, shlex, subprocess, sys, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
FAILED_SUBDIR = "failed"


def episode_prefix(row):
    tag = f"_{row['tag']}" if row.get("tag") else ""
    return f"{row['scenario']}_{row['backend']}{tag}_seed{row['seed']}_"


def dir_prefix(name: str):
    """Episode prefix of a results directory name (<prefix><YYYYMMDD>_<HHMMSS>, see run_episode.sh EPISODE_ID)."""
    return name.rsplit("_", 2)[0] + "_"


def summary_problems(s):
    """Validity checks for one summary.json; an episode counts as done only if this list is empty."""
    problems = []
    if not s.get("match_ended"): problems.append("match not ended")
    if s.get("lag_violations", 0): problems.append(f"lag_violations={s['lag_violations']}")
    if s.get("ai_orders_late"): problems.append(f"ai_orders_late={s['ai_orders_late']}")
    if s.get("ai_warmup_frame") not in (None, 150): problems.append(f"ai_warmup_frame={s['ai_warmup_frame']}")
    if s.get("orchestrator_died"): problems.append("orchestrator died")
    n = s.get("decisions_logged", 0)
    if s.get("llm_infra_errors", 0) > max(2, n // 10): problems.append(f"llm_infra_errors={s['llm_infra_errors']}/{n}")
    if s.get("action_mismatches"): problems.append("action mismatches")
    return problems


def load_summary(d: Path):
    """Parsed summary.json of a results directory, or None if absent/unreadable (episode running or killed early)."""
    try:
        return json.load(open(d / "summary.json"))
    except (OSError, json.JSONDecodeError):
        return None


def episode_dirs(results_dir: Path, row):
    """[(dir, summary or None)] for every results directory of this manifest row."""
    return [(d, load_summary(d)) for d in sorted(results_dir.glob(episode_prefix(row) + "*")) if d.is_dir()]


def is_done(results_dir: Path, row):
    return any(s is not None and not summary_problems(s) for _, s in episode_dirs(results_dir, row))


def retire_failed(results_dir: Path, row):
    """Move finished-but-invalid results directories of this episode to <results_dir>/failed/ before re-running it."""
    for d, s in episode_dirs(results_dir, row):
        if s is None or not summary_problems(s):
            continue
        dest = results_dir / FAILED_SUBDIR / d.name
        dest.parent.mkdir(exist_ok=True)
        d.rename(dest)
        print(f"[{time.strftime('%H:%M:%S')}] retired {d.name} -> {FAILED_SUBDIR}/ ({'; '.join(summary_problems(s))})", flush=True)


def probe_tps(row, timeout=150.0):
    """Generation speed (completion tokens per second) of the inference endpoint for this manifest row's model and
    thinking setting, measured with one request that resembles a campaign decision. Returns 0.0 on timeout or error.
    Used by --min-tps to start episodes only when the platform is fast enough for the request to finish within its
    own time limit (the platform cuts requests after about 180 s; a 10k-token thinking reply needs >= 60 tok/s)."""
    import re
    def opt(name, default=None):   # whitespace-split like run_episode.sh does (keeps the JSON quotes of --extra-body intact)
        m = re.search(re.escape(name) + r"\s+(\S+)", row.get("orch_args") or "")
        return m.group(1) if m else default
    model = opt("--model", os.environ.get("LLM_MODEL", "Qwen/Qwen3.8-27B-FP8-1M"))
    extra = json.loads(opt("--extra-body", os.environ.get("LLM_EXTRA_BODY", "") or "{}") or "{}")
    url = os.environ.get("LLM_URL", "http://localhost:9000/v1/chat/completions")
    body = {"model": model, "temperature": 0.3, "max_tokens": 6000, "messages": [
        {"role": "system", "content": "You are a 6G network operator AI. Reason carefully, then answer with exactly one line: place_bs|macro_cell|X|Z # comment."},
        {"role": "user", "content": "Game time: 12.0 minutes\nCoverage: 54%\nUnits: 22 engineers, 9 factories, 20 mexes, 31 disconnected\nBase Stations (6):\n  BS 11 (macro) at (5320, 9040)\n  BS 12 (macro) at (5496, 7768)\n  BS 13 (macro) at (4552, 10152)\n  BS 14 (small) at (3496, 9496)\n  BS 15 (macro) at (6320, 10040)\n  BS 16 (macro) at (7104, 8456)\nDisconnected units are mostly 1500-2500 elmos north-east of BS 16. Where should the next macro cell go?"}]}
    body.update(extra)
    headers = {"Content-Type": "application/json"}
    if os.environ.get("LLM_API_KEY"):
        headers["Authorization"] = "Bearer " + os.environ["LLM_API_KEY"]
    t0 = time.time()
    try:
        with urllib.request.urlopen(urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers), timeout=timeout) as r:
            res = json.loads(r.read().decode())
        if res.get("error") and not res.get("choices"):
            return 0.0, 0, time.time() - t0, str(res["error"])[:80]
        tok = (res.get("usage") or {}).get("completion_tokens") or 0
        dt = time.time() - t0
        return (tok / dt if dt > 0 else 0.0), tok, dt, "ok"
    except Exception as e:  # timeout, HTTP 5xx, connection errors
        return 0.0, 0, time.time() - t0, type(e).__name__


def wait_for_speed(row, min_tps, interval, log=None):
    """Block until two consecutive probes reach min_tps tokens/s; probes are spaced `interval` seconds apart."""
    good = 0
    while True:
        tps, tok, dt, note = probe_tps(row)
        msg = f"[{time.strftime('%H:%M:%S')}] speed probe: {tps:5.0f} tok/s ({tok} tokens in {dt:.0f}s, {note}); need {min_tps:.0f} twice -> {'go' if tps >= min_tps and good >= 1 else 'wait'}"
        print(msg, flush=True)
        if log:
            with open(log, "a") as f:
                f.write(msg + "\n")
        good = good + 1 if tps >= min_tps else 0
        if good >= 2:
            return tps
        time.sleep(interval if tps < min_tps else 60)


def build_args(row):
    args = [row["scenario"], row["backend"], "--seed", str(row["seed"])]
    if row.get("tag"):
        args += ["--tag", row["tag"]]
    if row.get("duration"):
        args += ["--duration", str(row["duration"])]
    if row.get("speed"):
        args += ["--speed", str(row["speed"])]
    if row.get("autoplace"):
        args += ["--autoplace", str(row["autoplace"])]
    if row.get("orch_args"):
        args += ["--orch-args", row["orch_args"]]
    for kv in (row.get("set") or "").split(";"):
        if kv.strip():
            args += ["--set", kv.strip()]
    return args


CHILDREN = set()   # running episode processes, terminated on Ctrl-C (run_episode.sh then stops its engine and orchestrator)


def run_child(cmd) -> int:
    p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
    CHILDREN.add(p)
    try:
        return p.wait()
    finally:
        CHILDREN.discard(p)


def run_local(row, slot, results_dir, mem_max):
    cmd = [str(REPO / "agent" / "run_episode.sh")] + build_args(row) + ["--headless", "--fresh-write-dir", f"/tmp/bar_wd_{slot}", "--host-port", str(8453 + slot), "--results-dir", str(results_dir), "--mem-max", mem_max]
    return run_child(cmd)


def run_docker(row, slot, results_dir, image, mem_max):
    env = [f"-e{k}={os.environ[k]}" for k in ("LLM_URL", "LLM_MODEL", "LLM_API_KEY", "LLM_TIMEOUT", "LLM_EXTRA_BODY") if k in os.environ]
    cmd = ["docker", "run", "--rm", "--network", "host", "--memory", f"{mem_max}g", "--memory-swap", f"{mem_max}g",
           "-v", f"{results_dir}:/results"] + env + [image] + build_args(row) + ["--host-port", str(8453 + slot), "--mem-max", "0", "--min-free", "0"]
    return run_child(cmd)


def verify(results_dir: Path):
    """List finished results directories that fail the validity checks; say whether a passing run supersedes them."""
    dirs = [d for d in sorted(results_dir.iterdir()) if d.is_dir() and (d / "summary.json").exists()]
    summaries = {d: load_summary(d) for d in dirs}
    passing = {dir_prefix(d.name) for d, s in summaries.items() if s is not None and not summary_problems(s)}
    ok, bad = 0, []
    for d, s in summaries.items():
        problems = ["summary.json unreadable"] if s is None else summary_problems(s)
        if problems:
            bad.append((d.name, problems, dir_prefix(d.name) in passing))
        else:
            ok += 1
    print(f"verified {len(summaries)} finished episodes in {results_dir}: {ok} OK, {len(bad)} failing")
    for name, pr, superseded in bad:
        note = "(superseded by a passing run)" if superseded else f"(pending: the runner will move it to {FAILED_SUBDIR}/ and re-run the episode)"
        print("  FAIL", name, "->", "; ".join(pr), note)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("manifest")
    ap.add_argument("--executor", choices=["local", "docker"], default="local")
    ap.add_argument("--image", default="bar-6g-testbed:revision-v1")
    ap.add_argument("--parallel", type=int, default=1, help="concurrent engines; each needs ~5-6 GB RAM (default 1)")
    ap.add_argument("--mem-max", default=os.environ.get("BAR_MEM_MAX_GB", "7"), help="GB cap per engine (docker: --memory; local: systemd scope)")
    ap.add_argument("--results-dir", default=str(REPO / "agent" / "results_v2"))
    ap.add_argument("--status", action="store_true", help="only report done/pending")
    ap.add_argument("--verify", action="store_true", help="list finished episodes that fail the validity checks (summary.json) and exit")
    ap.add_argument("--filter", default="", help="substring filter on scenario_backend_tag")
    ap.add_argument("--min-tps", type=float, default=0.0, help="before each LLM episode, probe the endpoint and wait until it generates at least this many tokens/s "
                    "in two consecutive probes (0 = off); the platform cuts requests after ~180 s, so thinking arms need about 100 tok/s")
    ap.add_argument("--probe-interval", type=float, default=600.0, help="seconds between speed probes while waiting (default 600)")
    ap.add_argument("--probe", action="store_true", help="measure the endpoint speed once for the first pending LLM row and exit")
    a = ap.parse_args()
    sys.stdout.reconfigure(line_buffering=True)   # progress visible through pipes/tee
    results_dir = Path(a.results_dir).resolve()
    results_dir.mkdir(parents=True, exist_ok=True)
    if a.verify:
        verify(results_dir)
        return
    rows = [r for r in csv.DictReader(l for l in open(a.manifest) if not l.lstrip().startswith("#")) if r.get("scenario")]
    if a.filter:
        rows = [r for r in rows if a.filter in episode_prefix(r)]
    pending = [r for r in rows if not is_done(results_dir, r)]
    reruns = [r for r in pending if any(s is not None for _, s in episode_dirs(results_dir, r))]
    print(f"manifest: {len(rows)} episodes, done: {len(rows) - len(pending)}, pending: {len(pending)} "
          f"(of which {len(reruns)} re-runs of episodes whose finished results failed the validity checks)")
    if a.probe:
        row = next((r for r in pending if r["backend"].startswith("llm")), None) or next((r for r in rows if r["backend"].startswith("llm")), None)
        tps, tok, dt, note = probe_tps(row) if row else (0, 0, 0, "no LLM row")
        print(f"speed probe for {row['tag'] if row else '-'} ({(row.get('orch_args') or '-')[:60]}): {tps:.0f} tok/s ({tok} tokens in {dt:.0f}s, {note})")
        return
    if a.status or not pending:
        return
    avail_gb = int(open("/proc/meminfo").read().split("MemAvailable:")[1].split()[0]) / 2**20
    if a.executor == "local" and a.parallel > max(1, int(avail_gb // 8)):
        print(f"WARNING: {a.parallel} parallel engines need ~{a.parallel*8} GB but only {avail_gb:.1f} GB are available; "
              f"run_episode.sh will serialise them (RAM gate). Consider --parallel {max(1, int(avail_gb // 8))}.")
    t0 = time.time()
    results = {}

    def work(item):
        idx, row = item
        slot = idx % a.parallel
        retire_failed(results_dir, row)
        if a.min_tps and row["backend"].startswith("llm"):
            wait_for_speed(row, a.min_tps, a.probe_interval, log=str(results_dir / "speed_probes.log"))
        rc = run_local(row, slot, results_dir, a.mem_max) if a.executor == "local" else run_docker(row, slot, results_dir, a.image, a.mem_max)
        results[episode_prefix(row)] = rc
        print(f"[{time.strftime('%H:%M:%S')}] {'OK ' if rc == 0 else 'FAIL'} rc={rc} {episode_prefix(row)} ({len(results)}/{len(pending)}, {(time.time()-t0)/60:.1f} min)", flush=True)

    # Stagger slot assignment so that concurrent workers never share a write dir
    ex = ThreadPoolExecutor(max_workers=a.parallel)
    try:
        list(ex.map(work, list(enumerate(pending))))
        ex.shutdown(wait=True)
    except KeyboardInterrupt:
        print(f"\n[{time.strftime('%H:%M:%S')}] interrupted: stopping {len(CHILDREN)} running episode(s); finished episodes are kept, "
              "the interrupted one is re-run on the next invocation", flush=True)
        for p in list(CHILDREN):
            p.terminate()
        ex.shutdown(wait=True, cancel_futures=True)
        sys.exit(130)
    failed = [k for k, rc in results.items() if rc != 0]
    print(f"done in {(time.time()-t0)/60:.1f} min; failed: {len(failed)}")
    for k in failed:
        print("  FAIL", k)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
