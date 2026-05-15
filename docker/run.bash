#!/usr/bin/env bash
# Launch the ProgressLabeller container with X11 forwarding for the Blender GUI.
# The container uses the shared `orbslam3:dev` image, built from
# /home/yuzeren/sudo/ws/ORB_SLAM3/docker/Dockerfile.
set -euo pipefail

xhost +local:docker
cd "$(dirname "$0")"
docker compose run --rm progresslabeller \
    blender --python /workspace/ProgressLabeller/docker/install_addon.py
