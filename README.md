# Progress Labeller

<img src='doc/fig/overview.png' width="1000"/>

## Overview

**This is an developing repository**. The project is an blender add-on to re-implement a pipeline, Labelfusion. Labelfusion is a pipleine to generate ground truth object-centric pose and mask labels from sequential images. It is powerful, but we find it is hard to install due to some out-of-date dependencies. Therefore, this project is trying to re-implement Labelfusion in a more user-friendly, cross-platform software, blender. Moreover, we would further improve the accuracy of Labelfusion, and make it model-free.

## Table of contents
-----
  * [Installation](#installation)
    * [Install add-on in blender](#install-add-on-in-blender)
    * [Install denpencies](#install-denpencies)
  * [Data structure](#data-structure)
    * [Dataset](#dataset)
    * [Configuration](#configuration)
    * [Collection](#collection)
  * [Quick Start](#what-we-have-achieved)
    * [Import](#import)
    * [Collection-wise property](#collection-wise-property)
  * [Reference](#references)
------

## Installation

Our blender add-on has been tested in the following environment:

* Ubuntu 18.04
* Blender 2.9.2

### Install add-on in blender

In order to see some running message about our pipeline, it is recommended to run the blender in the terminal. Just run:
```bash
blender
```

Open ``Edit > Preferences > Install...`` in blender, search ``PATH/TO/REPO/ProgressLabeller.zip`` and install it. After successful installation, you could see Progress Labeller in your Add-ons lists.

<img src='doc/fig/installadd-on.png' width="500"/>


### Install denpencies

Our add-on depends on the following libraries:

* open3d
* Pillow
* pycuda
* scipy

It should be mentioned that blender itself use it build-in python, so be sure to install the packages in the correct way. More specific, pip install command shoudld be 
```bash
pip3 install --target /PATH/TO/BLENDER/2.92/python/lib/python3.7/site-packages open3d Pillow pycuda scipy
```

## Data structure

### Dataset

To prepare a new dataset, please follow the structure below. We also provide a **demo dataset** [here](https://www.dropbox.com/s/qrgare7rg579m48/ProgressLabellerDemoDateset.zip?dl=0)

```bash
<dataset>
|-- data              # pairwise rgb and depth images, no need for the name, just pairwise rgb and depth images 
                      # should have the same name
    |-- rgb
        |-- 0.png        
        |-- 1.png
        ...
    |-- depth
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



## What we have achieved

### Import

#### Import Configuration

``File > Import > ProgressLabeller Configuration(.json)`` would load [configuration file](#configuration), which provides environment path and load some basic parameters for our pipeline.

#### Import object model

``File > Import > ProgressLabeller Model(.obj)`` would load single object model (right now only support .obj file) into [Model collection](#collection)

``File > Import > ProgressLabeller Model from pose file(.yaml)`` would load multiple object models mentioned in [object pose file](#object-poses-file) into [Model collection](#collection), automatically search in the environment(please load configuration before use this function). The function is designed not for first time labeling, but to make it convenient to reload the model after the first time. 

#### Import reconstruction result

``File > Import > ProgressLabeller Load Reconstruction Result(package)`` would read a [reconstruction package](#dataset) (right now we only support COLMAP results). It loads merged point cloud to [PointCloud collection](#collection) and loads pair-wise pose-aligned camera and rgb image mentioned in [camera poses file](#camera-pose-file) to [Camera collection](#collection)



### Collection-wise property

Collection-wise properties are all added as panels in ``Object Properties``, you could find them when you click any object instance.

<img src='doc/fig/objproperty2.png' width="300"/>
<img src='doc/fig/objproperty1.png' width="300"/>

#### PointCloud Collection

Plane Alignment: We would use RANSAC to search the plane in the point cloud and align the plane to X-Y plane. 

#### Camera Collection

View Mode: For object instances in Camera collection, we could change the cooresponding rgb image display mode in the ``UV Editing`` workspace. When selecting ``Origin``, it would display the original image, when selecting ``Segment``, it would render the Silhouettes of each model in Model collection and show the segment on the image.


<img src='doc/fig/render.png' width="1000"/>




## References
[1] Marion, Pat, Peter R. Florence, Lucas Manuelli, and Russ Tedrake. **"Label fusion: A pipeline for generating ground truth labels for real rgbd data of cluttered scenes."** In 2018 IEEE International Conference on Robotics and Automation (ICRA), pp. 3235-3242. IEEE, 2018.

