#!/usr/bin/env bash
# Idempotent first-run setup inside the progresslabeller container.
#   1. Apply the ProgressLabeller patch to ORB_SLAM3 (skip if already applied).
#   2. Build ORB_SLAM3 + its Thirdparty deps (skip if libORB_SLAM3.so exists).
#   3. Build the orb3_extension pybind11 module.
set -euo pipefail

: "${ORB3_SOURCE_DIR:?ORB3_SOURCE_DIR must be set (compose.yaml provides it)}"
: "${PROGRESSLABELLER_PATH:=/workspace/ProgressLabeller}"

cd "$ORB3_SOURCE_DIR"
patch_applied_now=0
if ! grep -q "GetTrackedMapPoints_progresslabeler" include/System.h; then
    echo "Applying ProgressLabeller patch to ORB_SLAM3..."
    git apply --check "$PROGRESSLABELLER_PATH/docker/orb_slam3_progresslabeller.patch"
    git apply "$PROGRESSLABELLER_PATH/docker/orb_slam3_progresslabeller.patch"
    patch_applied_now=1
fi

# Rebuild if the lib is missing OR if it predates the patched System.cc.
need_build=0
if [ ! -f lib/libORB_SLAM3.so ]; then
    need_build=1
elif [ src/System.cc -nt lib/libORB_SLAM3.so ] || [ "$patch_applied_now" -eq 1 ]; then
    need_build=1
fi
if [ "$need_build" -eq 1 ]; then
    echo "Building ORB_SLAM3 (incremental rebuild picks up patched System.cc)..."
    ./build.sh
fi

cd "$PROGRESSLABELLER_PATH/kernel/orb_slam3"
rm -rf build  # force re-detect Python on each run
mkdir -p build
cd build
cmake .. \
    -DPython_EXECUTABLE="$BLENDERPY" \
    -DPython3_EXECUTABLE="$BLENDERPY" \
    -DPYTHON_EXECUTABLE="$BLENDERPY"
make -j"$(nproc)"
ls orb3_extension*.so
echo "Done. orb3_extension is ready at $PROGRESSLABELLER_PATH/kernel/orb_slam3/build/"
