# Dependencies

Versions are those used for the experiments reported in the paper (September 2026, Ubuntu 24.04, x86-64).

## Run-time (required to run an episode)

| Dependency | Version used | Purpose | Licence |
|---|---|---|---|
| Recoil RTS engine, headless build (`spring-headless`) and windowed build (`spring`) | 2025.06.24 (statically linked, only libc needed) | Deterministic lock-step simulation, Lua 5.1 scripting host | GPL-2.0-or-later |
| Beyond All Reason game content (checkout as `.sdd` game archive) | master commit 2b63eb3d (2026-05-29) plus the files in `game/` | Units, economy, AI framework (STAI/Shard) that the testbed extends | GPL-2.0 (code); CC-BY-SA 4.0 / CC-BY-NC-ND 4.0 (art, see NOTICE.md) |
| Map `mediterraneum_v1.sd7` | v1 | 16 384 x 16 384 elmo coastal terrain used by all scenarios | per map archive |
| Python | 3.12.3 | Orchestrator (`agent/orchestrator.py`), episode/campaign runners | PSF |
| Bash, coreutils, `setarch` (util-linux), `systemd-run` (optional) | Ubuntu 24.04 | `run_episode.sh`: ASLR off for the engine, RAM cap per engine | GPL/LGPL |

The orchestrator itself uses only the Python standard library (`urllib`, `json`, `re`, `collections`, `hashlib`, `socket`, `subprocess`).

## LLM inference (required for the LLM agents only)

| Dependency | Used in the paper | Notes |
|---|---|---|
| OpenAI-compatible `/v1/chat/completions` endpoint | Corporate inference platform via `agent/ericai_proxy.py` (adapter over the proprietary EricAI client, not included) | Configure with `LLM_URL`, `LLM_MODEL`, `LLM_API_KEY` or the orchestrator flags `--url/--model/--api-key` |
| Models | `Qwen/Qwen3.8-27B-FP8-1M` (primary, thinking off), `openai/gpt-oss-120b` (reasoning effort low/high), `Microsoft/FastContext-1.0-4B-RL` | Any chat model works; thinking modes are controlled with `--extra-body` |
| Ollama (optional, local models) | tested with gemma4 for smoke tests | `docker/README.md` section 5 |

## Analysis pipeline (required to reproduce tables and figures)

| Dependency | Version used | Licence |
|---|---|---|
| Python | 3.12.3 | PSF |
| numpy | 1.26.4 | BSD-3-Clause |
| scipy | 1.11.4 | BSD-3-Clause |
| matplotlib | 3.6.3 | matplotlib licence (PSF-based) |

## Optional

| Dependency | Version used | Purpose | Licence |
|---|---|---|---|
| Docker | 27.3.1, base image `ubuntu:24.04` | Containerised headless episodes (`docker/`) | Apache-2.0 |
| PlantUML + Java | 1.2026.6 | Regenerate the protocol sequence diagram | GPL |
| Inkscape | 1.2.2 | SVG to PDF conversion of diagrams | GPL |
| TeX Live | 2023 | Compile the paper (not part of this package) | LPPL and others |

## Hardware used

One laptop (Intel 6-core, 15 GB RAM, no GPU needed): one headless engine instance at 5x simulation speed peaks at
about 6.1 GB RSS and completes a 30-minute episode in about 8 minutes; the 155-episode core campaign took 21 h.
