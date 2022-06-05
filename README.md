# ProgressLabeller

<img src='doc/fig/overview.png' width="1000"/>

## Overview

ProgressLabeller is a method for more efficiently generating large amounts of 6D pose training data from color images sequences for custom scenes in a scalable manner. ProgressLabeller is intended to also support transparent or translucent objects, for which the previous methods based on depth dense reconstruction will fail. The project is an blender add-on implementation of Progresslabeller. 

If you use this project for your research, please cite:
```bash
@article{chen2022progresslabeller,
  title={ProgressLabeller: Visual Data Stream Annotation for Training Object-Centric 3D Perception},
  author={Chen, Xiaotong and Zhang, Huijie and Yu, Zeren and Lewis, Stanley and Jenkins, Odest Chadwicke},
  journal={arXiv preprint arXiv:2203.00283},
  year={2022}
}
```


## Table of contents
-----
  * [Installation](#installation)
    * [Install denpencies](#install-denpencies)
    * [Install add-on in blender](#install-add-on-in-blender)
  * [Data structure](#data-structure)
    * [Dataset](#dataset)
    * [Configuration](#configuration)
    * [Collection](#collection)
  * [Usage](#usage)
  * [Reference](#references)
------

## Installation

Our blender add-on has been tested in the following environment:

* Ubuntu 18.04/20.04
* Blender 2.92/2.93

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

It should be mentioned that blender itself use it build-in python, so be sure to install the packages in the correct way. More specific, we use conda to install library, __please replace </PATH/TO/BLENDER>, <PATH/TO/Progresslabeller> to your own path__: 
```bash
echo "export PROGRESSLABELLER_BLENDER_PATH=</PATH/TO/BLENDER>" >> ~/.bashrc
echo "export PROGRESSLABELLER_PATH=<PATH/TO/Progresslabeller>" >> ~/.bashrc
source ~/.bashrc
conda create -n progresslabeller python=3.7
conda activate progresslabeller
python -m pip install -r requirements.txt
python -m pip install -r requirements.txt --target $PROGRESSLABELLER_BLENDER_PATH/2.92/python/lib/python3.7/site-packages 
```

For some reason, it is not recommended to directly use blender's python to install those package, you might meet some problems when install pycuda. Our way is to use the pip from python3.7 in conda.


### Build COLMAP_extension(only needed when you want to use COLMAP)

To enableing [COLMAP reconstruction](https://colmap.github.io/), please also following its official guidance to install COLMAP. Remember install the make file to the system use:
```bash
sudo make install
```

We use pybind to transform COLMAP C++ code to python interface， so after installing COLMAP and pybind, we could build the interface in Progresslabeller. 
```bash
cd $PROGRESSLABELLER_PATH/kernel/colmap
conda activate progresslabeller
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

Then to build the interface between ORB-SLAM2 and Progresslabeller. 
```bash
export ORB_SOURCE_DIR=</PATH/TO/ORB_SLAM2>
cd $PROGRESSLABELLER_PATH/kernel/orb_slam
tar -xf ORBvoc.txt.tar.gz
conda activate progresslabeller
mkdir build
cd build
cmake ..
make
```


### Build ORB-SLAM3_extension(only needed when you want to use ORB_SLAM3)

To enableing ORB-SLAM3 reconstruction, you should clone [my branch](https://github.com/ZerenYu/ORB_SLAM3.git), containing a little modification from official version. Please follow the guidance to install ORB_SLAM3.

Then to build the interface between ORB-SLAM3 and Progresslabeller. 
```bash
export ORB3_SOURCE_DIR=</PATH/TO/ORB_SLAM3>
cd $PROGRESSLABELLER_PATH/kernel/orb_slam3
tar -xf ../orb_slam/ORBvoc.txt.tar.gz
conda activate progresslabeller
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
cd $PROGRESSLABELLER_PATH/..
zip -r ProgressLabeller.zip ProgressLabeller/
```
Open ``Edit > Preferences > Install...`` in blender, search ``PATH/TO/REPO/ProgressLabeller.zip`` and install it. After successful installation, you could see Progress Labeller in your Add-ons lists.
<p align="center">
<img src='doc/fig/installadd-on.png' width="500"/>
</p>


## Data structure

### Dataset

To prepare a new dataset, please follow the structure below. We also provide a **demo dataset** [here](https://www.dropbox.com/s/pwmr3qwiuomgc0d/progresslabellerdemo.zip?dl=0)

```bash
<dataset>
|-- <path/to/data>              # pairwise rgb and depth images
                                # should have the same name
                                # the perfix sequential should follow the view sequential. 
                                # We use .sort() function to sort filenames
    |-- rgb           
        |-- 000000.png        
        |-- 000001.png
        ...
    |-- depth         # 
        |-- 000000.png        
        |-- 000001.png
        ...
|-- <path/to/model>
    |-- object1        # model for pose labelling, should have the same package name and model file name. (right now only support .obj model)
        |-- object1.obj
    |-- object2
        |-- object2.obj
    ...
|-- <path/to/recon>     # reconstruction result, the package store the intermediate results from reconstruction.
    |-- campose.txt            # Name should be the same. Camera poses file, stored camera pose for each images
    |-- fused.ply              # Name should be the same. Reconstructed point clound
    |-- label_pose.yaml        # Name should be the same. Object poses file, stored labelled objects poses, 
                               # generated from our pipline.
    ...
|-- <path/to/output>           # Stored output labelled objects poses and segmentation per frame, generated from our pipline.
```
#### Object poses file

Object pose file is a ``.yaml`` file stored all labelled pose in world coordinate. It will be created or stored every time you click "Save Object Poses":

```bash
object1.instance001:
   pose:
   - [x, y, z]
   - [qw, qx, qy, qz]
   type:
   - normal
object2.instance001:
   pose:
   - [x, y, z]
   - [qw, qx, qy, qz]
   type:
   - normal
...   
```

#### Camera poses file

Object pose file is a ``.txt`` file stored camera poses for every image. It is generated from our pipeline. It is be aranged as:

```bash
# IMAGE_ID, QW, QX, QY, QZ, TX, TY, TZ, CAMERA_ID, NAME

1 qw, qx, qy, qz, tx, ty, tz, 1, 000000.png
2 qw, qx, qy, qz, tx, ty, tz, 1, 000001.png
...   
```

### Configuration

You could design your own configuration in a ``.json`` file, it could also be created by ProgressLabeller
```python
{
    "projectname": "Demo",
    "environment":{
      "modelsrc": 
      ## path for the model
          "<path/to/model>",
      "reconstructionsrc":
      ## path for the reconstruction package 
          "<path/to/recon>",
      "datasrc":
      ## path for the data(rgb and depth)
          "<path/to/data> "
      },
    "camera":{
      "resolution": [rx, ry],
      "intrinsic": [[fx, 0, cx],
                    [0, fy, cy],
                    [0, 0, 1]],
      "inverse_pose": false, # inverse the cam pose when loading, used when output of reconstruction is world pose in camera coordinate. When using COLMAP, this should be true
      "lens": 30.0, # just leave this as 30.0
    },
    "reconstruction": {
       "scale": 1.0,  # scale for the reconstruction, for depth-based method, it would be 1; 
                      # for rgb-based method, we use depth information to auto-align the scale
                      # You could also slightly change it for a better label result
       "cameradisplayscale": 0.01,
                      # display size for the camera, just use default
       "recon_trans":[t11, t12, t13, t14; t21, t22, t23, t24; t31, t32, t33, t34; t41, t42, t43, t44;] ## 4X4 transformation matrix
    },
    "data": {
        "sample_rate": 0.1,
        "depth_scale": 0.001
        "depth_ignore": 8.0
    }
}
```

### Collection


We create new collections in blender for a better arrangement for our pipline, it has the following structure:

<p align="center">
<img src='doc/fig/collection.png' width="300"/>
</p>

```bash
|-- Scene Collection              # root cocllection in blender
    |-- <Your project name>       # collection for your project workspace name, is same as the projectname in the configuration.json file.
        |-- <Your project name>:Model                     
            |-- <Your project name>:object1.instance001                # model. we support loading same objects multiple times, they will be differed as <object>.instance001, <object>.instance002
            |-- <Your project name>:object2.instance001
            ...
        |-- <Your project name>:Reconstruction  
            |-- <Your project name>:Pointcloud
                |-- <Your project name>:reconstruction     # point cloud of feature points from reconstruction
                |-- <Your project name>:reconstruction_depthfusion # depth fusion using signed distance fuction based method.
            |-- <Your project name>:Camera
                |-- <Your project name>:view0              # camera 
                |-- <Your project name>:view1
                ...
        |-- <Your project name>:Setting                    # setting 
    ...
```

## Usage

[![Little red riding hood](https://img.youtube.com/vi/GnahM0Z6A0U/0.jpg)]((https://www.youtube.com/watch?v=GnahM0Z6A0U) "Little red riding hood - Click to Watch!")

## References
[1] Marion, Pat, Peter R. Florence, Lucas Manuelli, and Russ Tedrake. **"Label fusion: A pipeline for generating ground truth labels for real rgbd data of cluttered scenes."** In 2018 IEEE International Conference on Robotics and Automation (ICRA), pp. 3235-3242. IEEE, 2018.

[2] Schonberger, Johannes L., and Jan-Michael Frahm. "Structure-from-motion revisited." In Proceedings of the IEEE conference on computer vision and pattern recognition, pp. 4104-4113. 2016.

[3] Mur-Artal, Raul, and Juan D. Tardós. "Orb-slam2: An open-source slam system for monocular, stereo, and rgb-d cameras." IEEE transactions on robotics 33, no. 5 (2017): 1255-1262.

[4] Campos, Carlos, Richard Elvira, Juan J. Gómez Rodríguez, José MM Montiel, and Juan D. Tardós. "Orb-slam3: An accurate open-source library for visual, visual–inertial, and multimap slam." IEEE Transactions on Robotics 37, no. 6 (2021): 1874-1890.

