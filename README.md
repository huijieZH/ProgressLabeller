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

## Data structure

### Dataset

To prepare a new dataset, please follow the structure below. We also provide a **demo dataset** [here](https://www.dropbox.com/s/qrgare7rg579m48/ProgressLabellerDemoDateset.zip?dl=0)

<!-- ```bash
<dataset>
|-- data              # pairwise rgb and depth images, no need for the name, just pairwise rgb and depth images 
                      # should have the same name
                      # the perfix sequential should follow the view sequential. 
                      # We use .sort() function to sort filenames
    |-- rgb           
        |-- 0.png        
        |-- 1.png
        ...
    |-- depth         # 
        |-- 0.png        
        |-- 1.png
        ...
|-- model
    |-- object1        # model for pose labelling, should have the same package structure
        |-- object1.obj
    |-- object2
        |-- object2.obj
    ...
|-- reconstruction package     # reconstruction result, the package name could be random, its files could either 
                               # be generated from our pipline or created from other methods.
    |-- campose.txt            # Name should be the same. Camera poses file, stored camera pose for each images
    |-- fused.ply              # Name should be the same. Reconstructed point clound
    |-- label_pose.yaml        # Name should be the same. Object poses file, stored labelled objects poses, 
                               # generated from our pipline.
    ...
|-- output                     # Stored output labelled objects poses and segmentation per frame, 
                               # generated from our pipline.
    |-- object1        
        |-- pose
            |--0.txt
            |--1.txt
            ...
        |-- rgb
            |--0.png
            |--1.png
            ...       
    |-- object2
        |-- pose
            |--0.txt
            |--1.txt
            ...
        |-- rgb
            |--0.png
            |--1.png
            ...   
     ...
```
#### Object poses file

Object pose file is a ``.yaml`` file stored all labelled pose in world coordinate. It makes it more convenient for you to re-load your labelled results. We present a demo in the given demo dataset ```PATH/TO/DEMODATASET/COLMAP_recon/label_pose.yaml```, it should be aranged as:

```bash
object1:
   pose:
   - [x, y, z]
   - [qw, qx, qy, qz]
object2:
   pose:
   - [x, y, z]
   - [qw, qx, qy, qz]
...   
```

The object name in Object pose file should be the same as the package and file name for models in ```PATH/TO/DATASET/model```, [using object pose file to import objects](#Import-object-model) would automatically search objects in ```PATH/TO/DATASET/model``` from names in object pose file.

#### Camera poses file

Object pose file is a ``.txt`` file stored camera poses for each image in ```PATH/TO/DATASET/data```. It could be generated from our pipeline (right now we use kinect fusion) or from other projects like [COLMAP](https://colmap.github.io/). We present a demo in the given demo dataset ```PATH/TO/DEMODATASET/COLMAP_recon/extracted_campose.txt```, it should be aranged as:

```bash
# IMAGE_ID, QW, QX, QY, QZ, TX, TY, TZ, CAMERA_ID, NAME

1 qw, qx, qy, qz, tx, ty, tz, 1, 0.png
...   
```

### Configuration

You could design your own configuration in a ``.json`` file, we present a demo in ```PATH/TO/DEMODATASET/configuration.json```
```python
{
    "projectname": "Demo",
    "environment":{
        "modelsrc": 
        ## path for the model
            "PATH/TO/DEMODATASET/model/",
        "modelposesrc": 
        ## path for the Object poses file
            "PATH/TO/DEMODATASET/COLMAP_recon/",
        "reconstructionsrc":
        ## path for the reconstruction package 
            "PATH/TO/DEMODATASET/COLMAP_recon/",
        "datasrc":
        ## path for the data(rgb and depth)
            "PATH/TO/DEMODATASET/data/"
        },
    "camera":{
        "resolution": [1280, 720],
        "intrinsic": [[915.869, 0, 635.981],
                      [0, 915.869, 353.060],
                      [0, 0, 1]],
        "lens": 0.025 # could be random number, no physical meaning
    },
    "reconstruction": {
       "scale": 1.0,  # scale for the reconstruction, for depth-based method, it would be 1; 
                      # for rgb-based method, we use depth information to auto-align the scale
       "cameradisplayscale": 0.1
                      # display size for the camera
      }
}
```

### Collection

We create new collections in blender for a better arrangement for our pipline, it has the following structure:

```bash

|-- Scene Collection              # root cocllection in blender
    |-- <Your project name>       # collection for your project workspace name, is same as 
                                  # the projectname in the configuration.json file
        |-- <Your project name>:Model                     
            |-- <Your project name>:object1                # model object
            |-- <Your project name>:object2
            ...
        |-- <Your project name>:Reconstruction  
            |-- <Your project name>:Pointcloud
                |-- <Your project name>:reconstruction     # point cloud object
            |-- <Your project name>:Camera
                |-- <Your project name>:view0              # camera object 
                |-- <Your project name>:view1
                ...
        |-- <Your project name>:Setting                    # setting object 
    ...
```

<img src='doc/fig/collection.png' width="300"/>



## Quick Start

### Reconstruction from build-in KinectFusion

#### Create Workspace
Create a new workspace ``File > New > ProgressLabeller Create New Workspace`` in blender, correctly link each path and camera intrinsic under the object properties of setting object. The model package and data package should contain datas [introduced before](#dataset) while reconstruction package could be empty.

<img src='doc/fig/setparas.png' width="1000"/>

#### Load Workspace

You could also load a saved workspace from ``File > Import > ProgressLabeller Configuration (.json)``

#### Load images

Then click the ``Import RGB & Depth`` under the object properties of setting object to load RGB, depth images and cameras into your worksapce. Don't forget to do this before starting reconstruction.

<img src='doc/fig/loadrgbdepth.png' width="1000"/>

#### Reconstruct

Then click the ``3D Reconstruction from data (Depth, RGB or both)`` under the object properties of setting object, select the reconstruction method as KinectFusion. Follow the guidance of (#kinectfusion-setting) to set the parameters, then start reconstruction. The process of the reconstruction would shown in the terminal.

After successful reconstruction, you would see the point cloud under the `` <Your project name>:Reconstruction`` collection and cameras with registered poses under the `` <Your project name>:Camera`` collection.

<img src='doc/fig/kinectfusionrecon.png' width="1000"/>

#### Align model

Then click the ``Import Model`` under the object properties of setting object to import obejct for labelling and drag models to algin the point cloud.

### Reconstruction from COLMAP

Instead of [load images](#load-images) and [reconstruct](#reconstruct) in our add-on, it is also supported to load other projects' reconstructions result. Just follow the [guidance](#dataset) to prepare the dataset, especially the [camera poses file](#camera-poses-file) and [reconstruction package](#dataset).

Then click the ``Import Model`` under the object properties of setting object to import cameras and reconstruction. It should be mentioned that COLMAP gives the inverse of the camera poses (world pose under the camera coordinate system), while build-in kinectfusion gives camera poses under the world system. When loading COLMAP result, please select ``Inverse Camera Pose``. Also, please select ``Auto Align Point Cloud Scale`` if you don't know the actual scale for the reconstruction. We would use depth information to fit the scale.

<img src='doc/fig/importcolmaprecon.png' width="300"/>

### Tools for better alignment
We prepare several tricks for a better alignment.



#### Plane Alignment

The ``Plane Alignment`` button under the object properties of reconstruction object using RANSAC algorithm to find plane in the point cloud and transform it to X-Y plane. It accelerates the process of model dragging. 

<img src='doc/fig/planealignment.png' width="700"/>

#### Camera and Image Align

When click on the camera object, the 3D scene would automatically align to camera pose. You could change ``View Mode`` between RGB and depth. ``Show Float Screen`` would create a float screen at the left-bottom corner of the screen displaying the image corresponding to the camera. ``Align the float screen and camera view`` would be useful to see the segmentation of your labelled poses. It is actively, user-friendly to adjust the pose from the segmentation. ``Show pairwise image in background`` would add the corresponding image as the background of the camera view. It is convenient to see the accuracy of the pose.

<img src='doc/fig/camera.png' width="1000"/>

#### Object Alignment

The ``Model Alignment`` button under the object properties of camera object using ICP algorithm for locally aligning the model and reconstruction. When aligning the model, first drag it to an approximate pose and than use ``Model Alignment`` for local alignment.

<img src='doc/fig/modelalignment.png' width="700"/> -->



## References
[1] Marion, Pat, Peter R. Florence, Lucas Manuelli, and Russ Tedrake. **"Label fusion: A pipeline for generating ground truth labels for real rgbd data of cluttered scenes."** In 2018 IEEE International Conference on Robotics and Automation (ICRA), pp. 3235-3242. IEEE, 2018.

