# CUDA 12.8 devel base (Ubuntu 22.04 underneath, so the CPU-built Pangolin /
# ORB_SLAM3 / Blender layers below are unchanged). The toolkit is needed for
# the VGGT-SLAM 2.0 sidecar (GPU inference + any CUDA extension builds).
FROM nvidia/cuda:12.8.0-cudnn-devel-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC

# ORB_SLAM3 C++ toolchain + Pangolin v0.6 (replicated from the sibling
# ORB_SLAM3 dockerfile so this image is self-contained).
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential cmake git pkg-config wget ca-certificates \
        libgl1-mesa-dev libglew-dev libegl1-mesa-dev \
        libwayland-dev libxkbcommon-dev wayland-protocols libepoxy-dev \
        libeigen3-dev \
        libopencv-dev libopencv-contrib-dev python3-opencv \
        libboost-all-dev libssl-dev \
        python3 python3-numpy python3-pip \
        unzip \
    && rm -rf /var/lib/apt/lists/*

RUN git clone --depth 1 --branch v0.6 https://github.com/stevenlovegrove/Pangolin.git /opt/Pangolin \
    && cd /opt/Pangolin && mkdir build && cd build \
    && cmake .. -DBUILD_PANGOLIN_PYTHON=OFF -DBUILD_EXAMPLES=OFF -DBUILD_TESTS=OFF \
    && make -j"$(nproc)" \
    && make install \
    && ldconfig \
    && rm -rf /opt/Pangolin/build

ARG UID=1000
ARG GID=1000
RUN if getent group ${GID} >/dev/null; then \
        groupmod -n dev "$(getent group ${GID} | cut -d: -f1)" || true; \
    else \
        groupadd -g ${GID} dev; \
    fi \
    && useradd -m -u ${UID} -g ${GID} -s /bin/bash dev

# Blender 2.92 + pyrender/EGL runtime deps.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libxkbcommon0 libxfixes3 libxrandr2 libxi6 \
        libsm6 libxinerama1 libxcursor1 libdbus-1-3 \
        libopenexr-dev libxxf86vm-dev libfontconfig1 libxrender1 \
        libegl1 xz-utils \
    && rm -rf /var/lib/apt/lists/*

# Blender 2.92 (Feb 2021). Final layout: /opt/blender-2.92/2.92/python/...
RUN mkdir -p /opt/blender-2.92 \
    && wget -q https://download.blender.org/release/Blender2.92/blender-2.92.0-linux64.tar.xz -O /tmp/blender.tar.xz \
    && tar -xf /tmp/blender.tar.xz -C /opt/blender-2.92 --strip-components=1 \
    && rm /tmp/blender.tar.xz \
    && ln -sf /opt/blender-2.92/blender /usr/local/bin/blender

ENV BLENDER_PATH=/opt/blender-2.92/2.92
ENV BLENDERPY=/opt/blender-2.92/2.92/python/bin/python3.7m
ENV PROGRESSLABELLER_BLENDER_PATH=/opt/blender-2.92

# Python 3.7 headers (Blender ships without them; pybind11 build needs them).
RUN wget -q https://www.python.org/ftp/python/3.7.0/Python-3.7.0.tgz -O /tmp/py.tgz \
    && tar -xzf /tmp/py.tgz -C /tmp \
    && cp -r /tmp/Python-3.7.0/Include/* /opt/blender-2.92/2.92/python/include/python3.7m/ \
    && rm -rf /tmp/py.tgz /tmp/Python-3.7.0

# Replace Blender's stale bundled numpy; install pinned cp37 wheels.
RUN rm -rf /opt/blender-2.92/2.92/python/lib/python3.7/site-packages/numpy \
    && $BLENDERPY -m ensurepip \
    && $BLENDERPY -m pip install --no-cache-dir --upgrade "pip<24" "setuptools<68" "wheel"

COPY docker/requirements.docker.txt /tmp/requirements.docker.txt
RUN $BLENDERPY -m pip install --no-cache-dir -r /tmp/requirements.docker.txt \
    && rm /tmp/requirements.docker.txt

# pycolmap sidecar venv. pycolmap 4.x wheels are cp310+ and Blender 2.92
# ships Python 3.7m, so we run COLMAP under a separate interpreter and
# invoke it as a subprocess from operators/ReconstructionOperator.py. The
# wheel bundles libcolmap; no system COLMAP install needed.
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3.10 python3.10-venv \
    && rm -rf /var/lib/apt/lists/* \
    && python3.10 -m venv /opt/colmap-venv \
    && /opt/colmap-venv/bin/pip install --no-cache-dir --upgrade pip \
    && /opt/colmap-venv/bin/pip install --no-cache-dir \
        pycolmap==4.0.4 numpy
ENV COLMAP_PY=/opt/colmap-venv/bin/python

# VGGT-SLAM 2.0 sidecar venv. Like COLMAP, it needs a newer Python (3.11) + CUDA
# than Blender 2.92's bundled 3.7, so it runs under its own interpreter and is
# invoked as a subprocess from operators/ReconstructionOperator.py. The upstream
# setup.sh installs requirements.txt and the third_party stack (Salad, the
# MIT-SPARK VGGT fork, Perception Encoder, SAM 3). The ~GB VGGT-1B weights are
# NOT baked in -- they download lazily into $VGGT_WEIGHTS (the bind-mounted repo
# weights/ folder) on the first reconstruction, via TORCH_HOME.
ENV VGGT_SLAM_DIR=/opt/VGGT-SLAM
ENV VGGT_WEIGHTS=/workspace/ProgressLabeller/weights
ENV TORCH_HOME=/workspace/ProgressLabeller/weights
RUN apt-get update && apt-get install -y --no-install-recommends \
        software-properties-common \
    && add-apt-repository -y ppa:deadsnakes/ppa \
    && apt-get update && apt-get install -y --no-install-recommends \
        python3.11 python3.11-venv python3.11-dev \
    && rm -rf /var/lib/apt/lists/* \
    && git clone https://github.com/MIT-SPARK/VGGT-SLAM.git "$VGGT_SLAM_DIR" \
    && python3.11 -m venv /opt/vggt-venv \
    && /opt/vggt-venv/bin/pip install --no-cache-dir --upgrade pip setuptools wheel \
    && bash -c 'set -e && source /opt/vggt-venv/bin/activate && cd "$VGGT_SLAM_DIR" && ./setup.sh'
ENV VGGT_PY=/opt/vggt-venv/bin/python

# Clone ORB_SLAM3, apply the ProgressLabeller patch, build libORB_SLAM3.so + Thirdparty.
ENV ORB3_SOURCE_DIR=/opt/ORB_SLAM3
COPY docker/orb_slam3_progresslabeller.patch /tmp/orb_slam3_progresslabeller.patch
RUN git clone https://github.com/UZ-SLAMLab/ORB_SLAM3.git "$ORB3_SOURCE_DIR" \
    && cd "$ORB3_SOURCE_DIR" \
    && git apply /tmp/orb_slam3_progresslabeller.patch \
    && chmod +x build.sh && ./build.sh \
    && rm /tmp/orb_slam3_progresslabeller.patch

# Build the orb3_extension pybind11 module (linked against the ORB_SLAM3 above).
COPY kernel/orb_slam3/CMakeLists.txt \
     kernel/orb_slam3/orb3_extension.cpp \
     kernel/orb_slam3/orb3_extension.h \
     /opt/orb3_extension_src/
RUN cd /opt/orb3_extension_src && mkdir build && cd build \
    && cmake .. -DPython_EXECUTABLE="$BLENDERPY" \
                -DPython3_EXECUTABLE="$BLENDERPY" \
                -DPYTHON_EXECUTABLE="$BLENDERPY" \
    && make -j"$(nproc)"

# Override VGGT-SLAM's pinned torch==2.3.1 (default cu121 wheel, kernels only up
# to sm_90) with a CUDA 12.8 (cu128) build so it runs on Blackwell GPUs (sm_120,
# RTX 50-series / B-series), which otherwise fail with "no kernel image is
# available for execution on the device". torch >= 2.7 adds sm_120. Kept as the
# last layer so the expensive setup.sh layer above stays cached on rebuild.
RUN /opt/vggt-venv/bin/pip install --no-cache-dir --upgrade --force-reinstall \
        --index-url https://download.pytorch.org/whl/cu128 torch torchvision torchaudio

USER dev
WORKDIR /workspace/ProgressLabeller
CMD ["bash"]
