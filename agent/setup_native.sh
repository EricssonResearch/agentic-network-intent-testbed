#!/bin/bash
# Set up a plain Linux machine (no Docker) to run experiment episodes natively.
#   agent/setup_native.sh ENGINE_SRC MAP_FILE [WRITE_DIR]
#     ENGINE_SRC  directory (or .tar.gz) of the recoil_2025.06.24 engine incl. spring-headless (~114 MB)
#     MAP_FILE    mediterraneum_v1.sd7 (~317 MB)
#     WRITE_DIR   default ~/.local/state/bar-6g  (holds engine/, games/, maps/, springsettings.cfg)
# Afterwards:  export BAR_WRITE_DIR=<WRITE_DIR> BAR_ENGINE_DIR=<WRITE_DIR>/engine/recoil_2025.06.24
#              agent/campaign.py MANIFEST.csv --executor local --parallel N --results-dir <dir>
# Requirements: python3 (numpy/scipy only for analysis), systemd-run (optional, for the RAM cap), setarch (util-linux).
set -euo pipefail
ENGINE_SRC="${1:?ENGINE_SRC}"; MAP_FILE="${2:?MAP_FILE}"; WD="${3:-$HOME/.local/state/bar-6g}"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
mkdir -p "$WD/engine" "$WD/games" "$WD/maps"
if [ -d "$ENGINE_SRC" ]; then rsync -a "$ENGINE_SRC/" "$WD/engine/recoil_2025.06.24/"; else tar -xzf "$ENGINE_SRC" -C "$WD/engine/"; fi
cp -u "$MAP_FILE" "$WD/maps/"
ln -sfn "$REPO" "$WD/games/bar-6g.sdd"          # the game content is this repository checkout
cp -u "$REPO/docker/springsettings.headless.cfg" "$WD/springsettings.cfg"
[ -x "$WD/engine/recoil_2025.06.24/spring-headless" ] || { echo "ERROR: spring-headless not found under $WD/engine/recoil_2025.06.24"; exit 1; }
echo "OK. Now run:"
echo "  export BAR_WRITE_DIR=\"$WD\" BAR_ENGINE_DIR=\"$WD/engine/recoil_2025.06.24\""
echo "  $REPO/agent/run_episode.sh s1_peaceful rule --seed 1 --duration 3 --speed 5 --headless --fresh-write-dir /tmp/bar_wd_0   # smoke test"
echo "  $REPO/agent/campaign.py MANIFEST.csv --executor local --parallel N --results-dir RESULTS"
echo "RAM: ~6 GB per engine; parallel N <= (RAM - 4 GB) / 7 GB."
