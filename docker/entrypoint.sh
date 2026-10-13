#!/bin/bash
# Container entrypoint: run one headless episode.
#   docker run --rm -v $PWD/results:/results -e LLM_URL=... -e LLM_MODEL=... IMAGE s1_peaceful llm --seed 42 [--orch-args "..."]
# Every argument is passed to agent/run_episode.sh; --headless and a per-container write dir are added.
set -e
if [ "${1:-}" = "--help" ] || [ -z "${1:-}" ]; then
  sed -n '2,40p' /opt/bar/base/games/bar.sdd/agent/run_episode.sh | grep -E "^#" | sed 's/^# \{0,1\}//'
  exit 0
fi
if [ "${1:-}" = "shell" ]; then shift; exec bash "$@"; fi
exec /opt/bar/base/games/bar.sdd/agent/run_episode.sh "$@" --headless --fresh-write-dir /data/wd --results-dir "${RESULTS_DIR:-/results}"
