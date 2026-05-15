# ProgressLabeller's container is built from the shared image
# `orbslam3:dev`, defined in /home/yuzeren/sudo/ws/ORB_SLAM3/docker/Dockerfile.
# That image now bundles the ORB_SLAM3 toolchain + Blender 2.92 + Python 3.7 deps.
#
# Build the shared image once:
#   cd /home/yuzeren/sudo/ws/ORB_SLAM3/docker
#   UID=$(id -u) GID=$(id -g) docker compose build
#
# Run ProgressLabeller against it:
#   cd /home/yuzeren/sudo/ws/ProgressLabeller/docker
#   bash run.bash
#
# First time only, inside the container, build the ORB_SLAM3 patch + orb3_extension:
#   bash /workspace/ProgressLabeller/docker/build.sh
