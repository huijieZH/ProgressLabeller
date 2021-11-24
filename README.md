# Progress Labeller

<img src='doc/fig/overview.png' width="1000"/>

## Overview

**This is an developing repository**. The project is an blender add-on to an object pose annotation pipeline, Progresslabeler. Progresslabeler is a pipleine to generate ground truth object-centric poses and mask labels from sequential images.

## Table of contents
-----
  * [Installation](#installation)
    * [Install add-on in blender](#install-add-on-in-blender)
    * [Install denpencies](#install-denpencies)
  * [Data structure](#data-structure)
    * [Dataset](#dataset)
    * [Configuration](#configuration)
    * [Collection](#collection)
  * [Quick Start](#quick-start)
    * [Reconstruction from build-in KinectFusion](#reconstruction-from-build-in-kinectfusion)
    * [Reconstruction from COLMAP](#reconstruction-from-colmap)
    * [Tools for better alignment](#tools-for-better-alignment)
  * [Reference](#references)
------

## Installation

Our blender add-on has been tested in the following environment:

* Ubuntu 18.04/20.04
* Blender 2.92

### Install denpencies

Our add-on depends on the following python libraries:

* open3d
* Pillow
* pycuda (only needed when you want to use build-in kinectfustion)
* pybind11 (only needed when you want to use COLMAP, ORB2-SLAM)
* scipy
* pyyaml
* tqdm
* pyrender
* trimesh
* scikit-image
* pyntcloud

It should be mentioned that blender itself use it build-in python, so be sure to install the packages in the correct way. More specific, we use conda to install library, __please replace </PATH/TO/BLENDER>, <PATH/TO/Progresslabeler> to your own path__: 
```bash
echo "export PROGRESSLABELER_BLENDER_PATH=</PATH/TO/BLENDER>" >> ~/.bashrc
echo "export PROGRESSLABELER_PATH=<PATH/TO/Progresslabeler>" >> ~/.bashrc
source ~/.bashrc
conda create -n progresslabeler python=3.7
conda activate progresslabeler
python -m pip install -r requirements.txt
python -m pip install -r requirements.txt --target $PROGRESSLABELER_BLENDER_PATH/2.92/python/lib/python3.7/site-packages 
```

For some reason, it is not recommended to directly use blender's python to install those package, you might meet some problems when install pycuda. Our way is to use the pip from python3.7 in conda.


### Build COLMAP_extension(only needed when you want to use COLMAP)

To enableing [COLMAP reconstruction](https://colmap.github.io/), please also following its official guidance to install COLMAP. Remember install the make file to the system use:
```bash
sudo make install
```

We use pybind to transform COLMAP C++ code to python interface， so after installing COLMAP and pybind, we could build the interface in Progresslabeler. 
```bash
cd $PROGRESSLABELER_PATH/kernel/colmap
conda activate progresslabeler
mkdir build
cd build
cmake ..
make
```

### Build ORB-SLAM2_extension(only needed when you want to use ORB_SLAM2)

To enableing ORB-SLAM2 reconstruction, you should clone [my branch](https://github.com/huijieZH/ORB_SLAM2), containing a little modification from official version. Please follow the guidance to install ORB_SLAM2.
<!-- ```bash
git clone https://github.com/huijieZH/ORB_SLAM2.git ORB_SLAM2
cd ORB_SLAM2
chmod +x build.sh
./build.sh
``` -->

Then to build the interface between ORB-SLAM2 and Progresslabeler. 
```bash
export ORB_SOURCE_DIR=</PATH/TO/ORB_SLAM2>
cd $PROGRESSLABELER_PATH/kernel/orb_slam
tar -xf ORBvoc.txt.tar.gz
conda activate progresslabeler
mkdir build
cd build
cmake ..
make
```


### Install add-on in blender

In order to see some running message about our pipeline, it is recommended to run the blender in the terminal. Just run:
```bash
blender
```
First prepare the zip file for blender:
```bash
sudo apt-get install zip
cd $PROGRESSLABELER_PATH/..
zip -r ProgressLabeler.zip ProgressLabeler/
```
Open ``Edit > Preferences > Install...`` in blender, search ``PATH/TO/REPO/ProgressLabeller.zip`` and install it. After successful installation, you could see Progress Labeller in your Add-ons lists.

<img src='doc/fig/installadd-on.png' width="500"/>

