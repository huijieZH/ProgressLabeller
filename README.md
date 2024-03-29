# ProgressLabeller: Visual Data Stream Annotation for Training Object-Centric 3D Perception

<img src='doc/fig/overview.png' width="1000"/>

# Overview

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


# Table of contents
-----
  * [Installation](#installation)
  * [Data structure](#data-structure)
  * [Usage](#usage)
  * [Output](#output)
  * [Reference](#references)
------

# Installation

Our blender add-on has been tested in the following environment:

* Ubuntu 18.04/20.04
* Blender 2.92/2.93

## Install dependencies

Our add-on depends on the following python libraries:
* numpy>=1.18
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
* opencv-python

It should be mentioned that blender itself use it build-in python, so be sure to install the packages in the correct way. More specific, we use conda to install library, __please replace </PATH/TO/BLENDER>, <PATH/TO/Progresslabeller> to your own root directories of Progresslabeller and Blender__: 
```bash

echo "export PROGRESSLABELLER_BLENDER_PATH=</PATH/TO/BLENDER>" >> ~/.bashrc
echo "export PROGRESSLABELLER_PATH=<PATH/TO/Progresslabeller>" >> ~/.bashrc
source ~/.bashrc
cd $PROGRESSLABELLER_PATH
conda create -n progresslabeller python=3.7 ## note that the version of python here should be consistent with the version of your blender's python. For blender 2.92, its python version is 3.7
conda activate progresslabeller
python -m pip install -r requirements.txt
python -m pip install -r requirements.txt --target $PROGRESSLABELLER_BLENDER_PATH/2.92/python/lib/python3.7/site-packages 
```

For some reason, it is not recommended to directly use blender's python to install those package, you might meet some problems when install pycuda. Our way is to use the pip from python3.7 in conda.


## Build COLMAP_extension(only needed when you want to use COLMAP [2])

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

## Build ORB-SLAM2_extension (only needed when you want to use ORB_SLAM2 [3])

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


## Build ORB-SLAM3_extension (only needed when you want to use ORB_SLAM3 [4])

To enabling ORB-SLAM3 reconstruction, you should clone [my branch](https://github.com/ZerenYu/ORB_SLAM3.git), containing a little modification from official version. Please follow the guidance to install ORB_SLAM3.

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

## Run in terminal
In order to see some running message about our pipeline, it is recommended to run the blender in the terminal. Just run:
```bash
cd $PROGRESSLABELLER_PATH
blender --python __init__.py ## remember to add blender to your bash first.
```
## Install add-on in blender

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


# Data structure

## Multi-camera YCB dataset

We collected a 3 camera RGB-D dataset [link](https://drive.google.com/file/d/1IRmwclPwCWqvSz1Eh5jcTb9f1uznWtlH/view?usp=sharing) of YCB objects as discussed in the paper. We use RealSense L515, RealSense D435, and Primesense Carmine 1.09 RGB-D sensors to capture 11 training scenes and 5 test scenes over 10 YCB objects. The dataset contains about 120K images and is saved in [BOP format](https://github.com/thodan/bop_toolkit/blob/master/docs/bop_datasets_format.md).

## Create your own Dataset

To prepare a new dataset, please follow the structure below. We also provide a **demo dataset** [here](https://www.dropbox.com/s/3z7ky2q1izdywm9/progresslabellerdemo.zip?dl=0)

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
    |-- object_label.json # dictionary file contain all objects name and the label you defined them
|-- <path/to/recon>     # reconstruction result, the package store the intermediate results from reconstruction.
    |-- campose.txt            # Name should be the same. Camera poses file, stored camera pose for each images
    |-- fused.ply              # Name should be the same. Reconstructed point clound
    |-- label_pose.yaml        # Name should be the same. Object poses file, stored labelled objects poses, 
                               # generated from our pipline.
    ...
|-- <path/to/output>           # Stored output labelled objects poses and segmentation per frame, generated from our pipline.
```
### Object poses file

Object pose file is a ``.yaml`` file stored all labelled pose in world coordinate under ``<path/to/recon>``. It will be created or stored every time you click "Save Object Poses":

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

### Camera poses file

Object pose file is a ``.txt`` file stored camera poses for every image under ``<path/to/recon>``. It is generated from our pipeline. It should be aranged as:

```bash
# IMAGE_ID, QW, QX, QY, QZ, TX, TY, TZ, CAMERA_ID, NAME

1 qw, qx, qy, qz, tx, ty, tz, 1, 000000.png
2 qw, qx, qy, qz, tx, ty, tz, 1, 000001.png
...   
```

### Object Label File
```object_label.json``` is a dictionary file contains all objects name and the label you defined them under ``<path/to/model>``. It should be create by yourself before output. It should be aranged as:
```bash
{
    "beaker_1": 1,
    "dropper_1": 2,
    "dropper_2": 3,
    "flask_1": 4,
    "funnel_1": 5,
    "graduated_cylinder_1": 6,
    "graduated_cylinder_2": 7,
    "pan_1": 8,
    "pan_2": 9,
    "pan_3": 10,
    "reagent_bottle_1": 11,
}
```


## Configuration

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

## Collection


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

# Usage

[<img src='doc/fig/video.png' width="1000"/>](https://www.youtube.com/watch?v=GnahM0Z6A0U "Click to watch the ProgressLabeller usage")

# Output

Before ouput, make sure you have define your own [``object_label.json``](#object-label-file).

There are several formats for the ouput data. We have provide BOP [5] format, YCB-V format [6], our own Progresslabeller format.

## Progresslabeller format

```bash
<outputpath>
|-- <object1>              
    |-- pose           
        |-- 000000.txt  # object transformation for frame 000000
        |-- 000001.txt
        ...
    |-- rgb         
        |-- 000000.png  # object image after segmentation     
        |-- 000001.png
        ...
|-- <object2>
    |-- pose           
        |-- 000000.txt  
        |-- 000001.txt
        ...
    |-- rgb         
        |-- 000000.png       
        |-- 000001.png
        ...
...  
```

## Define your own format

You could also specify your own format In function renderYourtype() in the file ``offline/render.py``. There are some guidances in the function to help you get access to parameters you need. 

## Offline data generation

It is also possible to generate the dataset offline for fully annotation workspace. 
```bash
cd $PROGRESSLABELLER_BLENDER_PATH
python offline/main.py [path/to/configuration.json] [path/to/outputdir] [data_format] [path/to/objectlabelfile] 
# <data_format> in ["ProgressLabeller", "BOP", "YCBV", "Yourtype"]
```


# References
[1] Marion, Pat, Peter R. Florence, Lucas Manuelli, and Russ Tedrake. "Label fusion: A pipeline for generating ground truth labels for real rgbd data of cluttered scenes." In 2018 IEEE International Conference on Robotics and Automation (ICRA), pp. 3235-3242. IEEE, 2018.

[2] Schonberger, Johannes L., and Jan-Michael Frahm. "Structure-from-motion revisited." In Proceedings of the IEEE conference on computer vision and pattern recognition, pp. 4104-4113. 2016.

[3] Mur-Artal, Raul, and Juan D. Tardós. "Orb-slam2: An open-source slam system for monocular, stereo, and rgb-d cameras." IEEE transactions on robotics 33, no. 5 (2017): 1255-1262.

[4] Campos, Carlos, Richard Elvira, Juan J. Gómez Rodríguez, José MM Montiel, and Juan D. Tardós. "Orb-slam3: An accurate open-source library for visual, visual–inertial, and multimap slam." IEEE Transactions on Robotics 37, no. 6 (2021): 1874-1890.

[5] Hodan, Tomas, Frank Michel, Eric Brachmann, Wadim Kehl, Anders GlentBuch, Dirk Kraft, Bertram Drost et al. "Bop: Benchmark for 6d object pose estimation." In Proceedings of the European Conference on Computer Vision (ECCV), pp. 19-34. 2018.

[6] Xiang, Yu, Tanner Schmidt, Venkatraman Narayanan, and Dieter Fox. "Posecnn: A convolutional neural network for 6d object pose estimation in cluttered scenes." arXiv preprint arXiv:1711.00199 (2017).

