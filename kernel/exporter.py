import bpy
import json
import os
import yaml
import numpy as np
from PIL import Image
from tqdm import tqdm

from registeration.init_configuration import config_json_dict, encode_dict
from kernel.logging_utility import log_report
from kernel.geometry import _loadModel, _pose2Rotation, _render

def configuration_export(config, path):
    configuration = encode_dict(config)
    with open(path, "w") as f:
        json.dump(configuration, f, indent = True)


def objectposes_export(name, path):
    pose = {}
    for obj in bpy.data.objects:
        if obj["type"] == "model" and obj.name.split(":")[0] == name:
            pose[obj.name.split(":")[1]] = {'pose': [list(obj.location), list(obj.rotation_quaternion)]}
    with open(path, 'w') as file:
        documents = yaml.dump(pose, file)



def data_export(config, target_dir):
    if not os.path.exists(target_dir):
        os.mkdir(target_dir)
    name = config.projectname
    intrinsic = np.array([[config.fx, 0, config.cx],
                          [0, config.fy, config.cy],
                          [0, 0, 1]])
    print(intrinsic)
    for model in bpy.data.objects:
        if model.name.split(":")[0] == name and model["type"] == "model":
            log_report(
                "INFO", "Starting prepare the dataset for {0} model in {1} workspace"\
                    .format(model.name.split(":")[1], model.name.split(":")[0]), None
            )   
            modelPC = _loadModel(model["path"])
            modelT = _pose2Rotation([list(model.location), list(model.rotation_quaternion)])

            modelPath = os.path.join(target_dir, model.name.split(":")[1])
            if not os.path.exists(modelPath):
                os.mkdir(modelPath)

            posepath = os.path.join(modelPath, "pose")            
            if not os.path.exists(posepath):
                os.mkdir(posepath)
            rgbpath = os.path.join(modelPath, "rgb")            
            if not os.path.exists(rgbpath):
                os.mkdir(rgbpath)
            for cam in tqdm(bpy.data.objects):     
                if cam.name.split(":")[0] == name and cam["type"] == "camera":
                    image = np.array(Image.open(cam["rgb"].filepath))
                    cameraT = _pose2Rotation([list(cam.location), list(cam.rotation_quaternion)])
                    # model_camT = np.linalg.inv(cameraT).dot(modelT)
                    # model_camT = np.linalg.inv(cameraT.dot(np.linalg.inv(modelT)))
                    Axis_align = np.array([[1, 0, 0, 0],
                                           [0, -1, 0, 0],
                                           [0, 0, -1, 0],
                                           [0, 0, 0, 1],]
                                            )


                    model_camT = np.linalg.inv(cameraT.dot(Axis_align)).dot(modelT)
                    # model_camT = modelT.dot(np.linalg.inv(cameraT))
                    perfix = cam.name.split(":")[1].replace("view", "")
                    _createpose(posepath, perfix, model_camT)
                    _createrbg(image, modelPC, rgbpath, perfix, model_camT, intrinsic)


def _createpose(path, perfix, T):
    # T = self.TfromPreviousFrame.dot(self.previousframePose[modelName])
    # self.previousframePose[modelName] = T
    posefileName = os.path.join(path, perfix + ".txt")
    np.savetxt(posefileName, np.linalg.inv(T), fmt='%f', delimiter=' ')


def _createrbg(image, model, dirpath, perfix, T, intrinsic):
    segment = _render(image, T, intrinsic, model)
    colorfileName = os.path.join(dirpath, perfix + ".png")
    img = Image.fromarray(segment.astype(np.uint8))
    img.save(colorfileName)