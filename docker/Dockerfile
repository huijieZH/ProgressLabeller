FROM ubuntu:22.04

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

COPY requirements.docker.txt /tmp/requirements.docker.txt
RUN $BLENDERPY -m pip install --no-cache-dir -r /tmp/requirements.docker.txt \
    && rm /tmp/requirements.docker.txt

USER dev
WORKDIR /workspace/ProgressLabeller
CMD ["bash"]
