# Containerised experiment runs (revision campaign)

**Docker is optional.** Any Linux machine can run episodes natively: `git clone` this repository, copy the engine
directory (~114 MB) and the map (~317 MB) once, run `agent/setup_native.sh ENGINE_DIR MAP_FILE`, export the two
variables it prints, and use `agent/campaign.py --executor local --parallel N`. No 4 GB image to transfer. The image
only adds OS isolation; the runner, seeding, guards and logging are identical.

## 1. Build (on a machine with >= 8 GB free disk for Docker)
```bash
docker/build.sh                     # stages engine + map into docker/assets, builds bar-6g-testbed:revision-v1 (~4 GB)
docker run --rm bar-6g-testbed:revision-v1 --help
```
Docker's `data-root` must be on a disk with space. On the author's laptop `/etc/docker/daemon.json` points to
Repoint it (needs sudo) before building there:
```bash
sudo systemctl stop docker
sudo systemctl start docker && docker info --format 'data-root: {{.DockerRootDir}}'
```

## 2. One episode
```bash
mkdir -p results
docker run --rm --network host --memory 7g --memory-swap 7g -v "$PWD/results:/results" \
  -e LLM_URL=https://<endpoint>/v1/chat/completions -e LLM_API_KEY=... \
  bar-6g-testbed:revision-v1 s1_peaceful llm --seed 1001 --orch-args "--model openai/gpt-oss-120b --prompt-version v1"
```
Baselines (`rule`, `random`, `noop`, `replay`) need no endpoint. Every run is headless, 5x, seeded and reproducible
(see REVISION_PLAN.md §11 for the determinism recipe); `results/<episode_id>/summary.json` must say `EPISODE OK`
(`ai_orders_late == 0`, `ai_warmup_frame == 150`, `lag_violations == 0`, `match_ended == true`).

## 3. Campaign (many episodes, several machines)
```bash
agent/campaign.py agent/campaign_manifest_template.csv --executor docker --parallel 3 --results-dir /srv/results
agent/campaign.py MANIFEST.csv --status        # done / pending (and how many pending are re-runs)
agent/campaign.py MANIFEST.csv --verify        # finished episodes that fail the validity checks
```
The runner is idempotent: an episode is done when one of its result directories has a `summary.json` that passes the
validity checks above plus `llm_infra_errors <= max(2, decisions/10)` (LLM timeouts / connection failures are logged
as forced `noop`). An episode whose finished results all fail is re-run automatically; the failing directories are
moved to `<results-dir>/failed/` first (the analysis loader ignores that folder), directories without `summary.json`
(still running) are left alone. So the same manifest can be started on several machines writing to a shared results
folder (or disjoint `--filter` slices, merged later).

## 4. RAM/CPU budget
One headless engine peaks at ~6 GB RSS and needs ~2 cores at 5x. Rule of thumb: `--parallel = min(cores/2, (RAM-4 GB)/7 GB)`
(e.g. 32 GB / 12 cores -> 3; 64 GB / 16 cores -> 8). `run_episode.sh` inside the container has the RAM gate and cgroup
cap disabled (`--mem-max 0 --min-free 0`); `campaign.py` passes `--memory` to docker instead.

## 5. Local small LLMs with Ollama (company machine with a big GPU)
The orchestrator speaks the OpenAI chat-completions protocol, so any Ollama model works unchanged
(validated 27 Sep 2026 with `gemma4:latest` on the laptop: `parse_status=valid`, `served_model` and token usage logged).
On a machine with e.g. 24-80 GB VRAM:
```bash
export OLLAMA_NUM_PARALLEL=3 OLLAMA_KEEP_ALIVE=24h     # serve 3 concurrent episodes, keep weights resident
ollama serve &                                        # or the systemd service with these env vars
ollama pull qwen3:8b; ollama pull gemma3:12b; ollama pull phi4:14b   # candidates; check `ollama list` / library
```
Manifest rows then use `--url http://localhost:11434/v1/chat/completions --model qwen3:8b` in `orch_args`
(containers use `--network host`, so `localhost` is the host's Ollama). Keep `--parallel` <= OLLAMA_NUM_PARALLEL, or the
LLM calls queue and the game pauses longer (the sim is paused during every call, so this only costs wall-clock, not
validity). Latency is logged per decision (`latency_s`), so throughput can be checked after the first episode.
Why: a size axis (8-14B local vs 27B/120B hosted) answers the reviewers' single-model concern more convincingly than
hosted models alone, and it is free and reproducible (fixed weights, `served_model` in every header).
