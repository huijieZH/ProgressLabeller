#!/usr/bin/env bash
# Launch the ProgressLabeller container.
#   run.bash                                   -> Blender GUI (default, X11 forwarding)
#   run.bash render [CONFIG] [OUTPUT] [FORMAT] -> headless offline render
#
# Add --rebuild (anywhere in the args) to rebuild the image before running;
# by default the existing image is reused (no build).
#
# The render mode runs the offline pipeline (offline/main.py) under Blender's
# bundled Python headlessly via EGL -- no display needed. FORMAT is one of
# ProgressLabeller / BOP / YCBV / Yourtype (defaults to ProgressLabeller).
set -euo pipefail

export HOST_UID="$(id -u)"
export HOST_GID="$(id -g)"

cd "$(dirname "$0")"

# Parse --rebuild out of the args; everything else stays positional.
BUILD_FLAG=""
ARGS=()
for arg in "$@"; do
    case "$arg" in
        --rebuild) BUILD_FLAG="--build" ;;
        *) ARGS+=("$arg") ;;
    esac
done

MODE="${ARGS[0]:-gui}"

if [ "$MODE" = "render" ]; then
    CONFIG="${ARGS[1]:-/workspace/ProgressLabeller/data/left_hand_dataset/configuration.json}"
    OUTPUT="${ARGS[2]:-/workspace/ProgressLabeller/data/left_hand_dataset/output}"
    FORMAT="${ARGS[3]:-ProgressLabeller}"
    docker compose run --rm ${BUILD_FLAG} progresslabeller \
        /opt/blender-2.92/2.92/python/bin/python3.7m \
        /workspace/ProgressLabeller/offline/main.py "$CONFIG" "$OUTPUT" "$FORMAT"
else
    xhost +local:docker
    docker compose run --rm ${BUILD_FLAG} progresslabeller \
        blender --python /workspace/ProgressLabeller/docker/install_addon.py
fi
