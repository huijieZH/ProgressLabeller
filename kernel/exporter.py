import bpy
import json
import os
import yaml
import numpy as np
from PIL import Image
from tqdm import tqdm
import trimesh
import pyrender
import multiprocessing
import subprocess
import sys

from registeration.init_configuration import config_json_dict, encode_dict
from kernel.logging_utility import log_report
from kernel.geometry import _loadModel, _pose2Rotation, _render
from kernel.blender_utility import _is_progresslabeller_object


def configuration_export(config, path):
    configuration = encode_dict(config)
    with open(path, "w") as f:
        json.dump(configuration, f, indent = True)


def objectposes_export(name, path):
    pose = {}
    for obj in bpy.data.objects:
        if _is_progresslabeller_object(obj) and obj["type"] == "model" and obj.name.split(":")[0] == name:
            pose[obj.name.split(":")[1]] = {'pose': [list(obj.location), list(obj.rotation_quaternion)], 'type':obj["modeltype"]}
    with open(path, 'w') as file:
        documents = yaml.dump(pose, file)


def data_export(config_path, target_dir, data_format, object_label_file):
    source = os.path.dirname(os.path.dirname(__file__))
    code_path = os.path.join(source, "offline", "main.py")
    subprocess.call("{} {} {} {} {} {}".format(sys.executable, code_path, config_path, target_dir, data_format, object_label_file), shell=True)



def _createpose(path, perfix, T):
    posefileName = os.path.join(path, perfix + ".txt")
    np.savetxt(posefileName, np.linalg.inv(T), fmt='%f', delimiter=' ')

def _createbgpyrender(image, segement, dirpath, perfix):
    image[segement != 0] = 0
    colorfileName = os.path.join(dirpath, perfix + ".png")
    img = Image.fromarray(image.astype(np.uint8))
    img.save(colorfileName)

def _createrbg(image, model, dirpath, perfix, T, intrinsic):
    segement = _render(image, T, intrinsic, model)
    colorfileName = os.path.join(dirpath, perfix + ".png")
    img = Image.fromarray(segement.astype(np.uint8))
    img.save(colorfileName)