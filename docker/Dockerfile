# Dockerfile autogenerated on 06/29/2022, 21:14:33 by root
# Please do not edit this file directly

FROM nvidia/cudagl:10.1-devel-ubuntu18.04
FROM nvidia/cudagl:10.1-base-ubuntu18.04
LABEL Author="Huijie Zhang"
LABEL Title="Progresslabeller"

# Environment variables
ENV DEBIAN_FRONTEND noninteractive
ENV LC_ALL C.UTF-8
ENV LANG C.UTF-8
ENV PATH "$PATH:/bin/2.92/python/bin/"
ENV BLENDER_PATH "/bin/2.92"
ENV BLENDERPIP "/bin/2.92/python/bin/pip3"
ENV BLENDERPY "/bin/2.92/python/bin/python3.7m"
ENV HW="GPU"

# Install dependencies
RUN apt-get update && apt-get install -y \
	wget \ 
	libopenexr-dev \ 
	bzip2 \ 
	build-essential \ 
	zlib1g-dev \ 
	libxmu-dev \ 
	libxi-dev \ 
	libxxf86vm-dev \ 
	libfontconfig1 \ 
	libxrender1 \ 
	libgl1-mesa-glx \ 
	xz-utils

# Download and install Blender
RUN wget https://mirror.clarkson.edu/blender/release/Blender2.92/blender-2.92.0-linux64.tar.xz \
	&& tar -xvf blender-2.92.0-linux64.tar.xz --strip-components=1 -C /bin \
	&& rm -rf blender-2.92.0-linux64.tar.xz \
	&& rm -rf blender-2.92.0-linux64

# Download the Python source since it is not bundled with Blender
RUN wget https://www.python.org/ftp/python/3.7.0/Python-3.7.0.tgz \
	&& tar -xzf Python-3.7.0.tgz \
	&& cp -r Python-3.7.0/Include/* $BLENDER_PATH/python/include/python3.7m/ \
	&& rm -rf Python-3.7.0.tgz \
	&& rm -rf Python-3.7.0

# Blender comes with a super outdated version of numpy (which is needed for matplotlib / opencv) so override it with a modern one
RUN rm -rf ${BLENDER_PATH}/python/lib/python3.7m/site-packages/numpy

# Must first ensurepip to install Blender pip3 and then new numpy
RUN ${BLENDERPY} -m ensurepip && ${BLENDERPIP} install --upgrade pip && ${BLENDERPIP} install numpy


### install progresslabeller
RUN apt-get update && \
    apt-get -y upgrade && \
    apt-get install -y git

RUN ls
RUN git clone https://github.com/huijieZH/ORB_SLAM2.git && \
    git clone https://github.com/huijieZH/ProgressLabeller.git && \
    git clone https://github.com/ZerenYu/ORB_SLAM3

## install conda
RUN wget https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh -O /miniconda.sh && \
    bash /miniconda.sh -b -p && \
    rm /miniconda.sh

ENV PROGRESSLABELLER_BLENDER_PATH "/bin"
ENV PROGRESSLABELLER_PATH "/ProgressLabeller"

RUN cd ${PROGRESSLABELLER_PATH}

RUN $PROGRESSLABELLER_BLENDER_PATH/2.92/python/bin/python3.7m -m pip install -r $PROGRESSLABELLER_PATH/requirements.txt --target $PROGRESSLABELLER_BLENDER_PATH/2.92/python/lib/python3.7/site-packages

# Set the working directory
WORKDIR /ProgressLabeller
