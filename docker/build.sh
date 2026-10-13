#!/bin/bash
# Stage the engine and the map into docker/assets and build the image.
#   docker/build.sh [IMAGE_TAG]      (default bar-6g-testbed:revision-v1)
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
TAG="${1:-bar-6g-testbed:revision-v1}"
WD="${BAR_WRITE_DIR:-$HOME/.local/state/Beyond All Reason}"
ENGINE="${BAR_ENGINE_DIR:-$WD/engine/recoil_2025.06.24}"
MAP="${BAR_MAP_FILE:-$WD/maps/mediterraneum_v1.sd7}"
mkdir -p "$REPO/docker/assets/maps"
rsync -a --delete "$ENGINE/" "$REPO/docker/assets/engine/"
cp -u "$MAP" "$REPO/docker/assets/maps/"
cp -u "$WD/springsettings.cfg" "$REPO/docker/assets/springsettings.cfg" 2>/dev/null || echo "" > "$REPO/docker/assets/springsettings.cfg"
COMMIT="$(git -C "$REPO" rev-parse HEAD 2>/dev/null || echo unknown)"
echo "Building $TAG (commit $COMMIT) -- context: $REPO"
docker build -f "$REPO/docker/Dockerfile" -t "$TAG" --build-arg BAR_COMMIT="$COMMIT" "$REPO"
docker image inspect "$TAG" --format 'Image size: {{.Size}} bytes'
