# Progress Labeller

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
  * [Quick Start](#what-we-have-achieved)
    * [Import](#import)
    * [Cameras and images](#cameras-and-images)
  * [Reference](#references)
------

## Installation

Our blender add-on has been tested in the following environment:

* Ubuntu 18.04
* Blender 2.9.2

### Install add-on in blender

Open ``Edit > Preferences > Install...``, search ``path/to/repo/ProgressLabeller.zip`` and install it. After successful installation, you could see Progress Labeller in your Add-ons lists.

<img src='doc/fig/installadd-on.png' width="500"/>


### Install denpencies

Our add-on depends on the following libraries:

* open3d >= 0.12.0

It should be mentioned that blender itself use it build-in python, so be sure to install the packages in the correct way. More specific, pip install command shoudld be 
```bash
pip3 install --target /path/to/blender/2.92/python/lib/python3.7/site-packages open3d
```

## Data structure

### Dataset

To prepare a new dataset, please follow. We also provide a demo dataset [here](https://www.dropbox.com/s/04ogfvubpgar695/ProgressLabellerData.zip?dl=0)

#### Object pose file

Object pose file is a ``.yaml`` file stored all labelled pose. It makes it more convenient for you to re-load your labelled results. We present a demo in the given demo dataset ```path/to/demodataset/COLMAP_recon/label_pose.yaml```, it should be aranged as:


```bash
object_name
```

#### Reconstruction package

### Configuration

You could design your own configuration in a ``.json`` file, we present a demo in ```path/to/repo/configuration.json```
```python
{
    "environment":{
        "modelsrc":
        ## path for the model used to label pose
            "/path/to/dataset/model/",
        "modelposesrc": 
        ## path for the files containing per-object labelled pose
            "/path/to/dataset/COLMAP_recon/",
        "reconstructionsrc":
        ## path for the reconstruction output
            "/path/to/dataset/",
        "imagesrc":
        ## path for the rgb data used for reconstruction
            "/path/to/dataset/data/rgb/"
        },
    "camera":{
        "resolution": [1280, 720],
        "intrinsic": [[904.572, 0, 635.981],
                      [0, 905.295, 353.060],
                      [0, 0, 1]],
        "lens": 25
    }
}
```





## What we have achieved

### Import

### Cameras and images

## References
[1] Marion, Pat, Peter R. Florence, Lucas Manuelli, and Russ Tedrake. **"Label fusion: A pipeline for generating ground truth labels for real rgbd data of cluttered scenes."** In 2018 IEEE International Conference on Robotics and Automation (ICRA), pp. 3235-3242. IEEE, 2018.
