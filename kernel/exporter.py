import bpy
import json
import os
import yaml
import numpy as np
from PIL import Image
from tqdm import tqdm
import trimesh
import pyrender

from registeration.init_configuration import config_json_dict, encode_dict
from kernel.logging_utility import log_report
from kernel.geometry import _loadModel, _pose2Rotation, _render

import os
os.environ['PYOPENGL_PLATFORM'] = 'osmesa'

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



# def data_export(config, target_dir):
#     if not os.path.exists(target_dir):
#         os.mkdir(target_dir)
#     name = config.projectname
#     intrinsic = np.array([[config.fx, 0, config.cx],
#                           [0, config.fy, config.cy],
#                           [0, 0, 1]])
#     print(intrinsic)
#     for model in bpy.data.objects:
#         if model.name.split(":")[0] == name and model["type"] == "model":
#             log_report(
#                 "INFO", "Starting prepare the dataset for {0} model in {1} workspace"\
#                     .format(model.name.split(":")[1], model.name.split(":")[0]), None
#             )

#             ## split render model and visual model
#             visual_model_path = model["path"]
#             model_dir = os.path.dirname(visual_model_path)
#             model_name = os.path.basename(visual_model_path)
#             render_model_path = os.path.join(model_dir, model_name.split(".")[0] + "_render.obj")
            
#             print(render_model_path)
#             #modelPC = _loadModel(model["path"])
#             modelPC = _loadModel(render_model_path)
#             modelT = _pose2Rotation([list(model.location), list(model.rotation_quaternion)])

#             modelPath = os.path.join(target_dir, model.name.split(":")[1])
#             if not os.path.exists(modelPath):
#                 os.mkdir(modelPath)

#             posepath = os.path.join(modelPath, "pose")            
#             if not os.path.exists(posepath):
#                 os.mkdir(posepath)
#             rgbpath = os.path.join(modelPath, "rgb")            
#             if not os.path.exists(rgbpath):
#                 os.mkdir(rgbpath)
#             for cam in tqdm(bpy.data.objects):     
#                 if cam.name.split(":")[0] == name and "type" in cam and cam["type"] == "camera":
#                     image = np.array(Image.open(cam["rgb"].filepath))
#                     cameraT = _pose2Rotation([list(cam.location), list(cam.rotation_quaternion)])
#                     # model_camT = np.linalg.inv(cameraT).dot(modelT)
#                     # model_camT = np.linalg.inv(cameraT.dot(np.linalg.inv(modelT)))
#                     Axis_align = np.array([[1, 0, 0, 0],
#                                            [0, -1, 0, 0],
#                                            [0, 0, -1, 0],
#                                            [0, 0, 0, 1],]
#                                             )


#                     model_camT = np.linalg.inv(cameraT.dot(Axis_align)).dot(modelT)
#                     # model_camT = modelT.dot(np.linalg.inv(cameraT))
#                     perfix = cam.name.split(":")[1].replace("view", "")
#                     _createpose(posepath, perfix, model_camT)
#                     _createrbg(image, modelPC, rgbpath, perfix, model_camT, intrinsic)

def data_export(config, target_dir):
    if not os.path.exists(target_dir):
        os.mkdir(target_dir)
    name = config.projectname
    intrinsic = np.array([[config.fx, 0, config.cx],
                          [0, config.fy, config.cy],
                          [0, 0, 1]])

    cameraPyrender =pyrender.camera.IntrinsicsCamera(config.fx, config.fy, config.cx, config.cy, znear=0.05, zfar=100.0, name=None)
    r = pyrender.OffscreenRenderer(1280, 720)
    for model in bpy.data.objects:
        if model.name.split(":")[0] == name and model["type"] == "model":
            log_report(
                "INFO", "Starting prepare the dataset for {0} model in {1} workspace"\
                    .format(model.name.split(":")[1], model.name.split(":")[0]), None
            )

            ## split render model and visual model
            model_path = model["path"]
            

            model_mesh = trimesh.load(model_path)
            mesh = pyrender.Mesh.from_trimesh(model_mesh)
            scene = pyrender.Scene()
            scene.add(mesh)
            node_camera = scene.add(cameraPyrender, pose=np.eye(4))

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
                if cam.name.split(":")[0] == name and "type" in cam and cam["type"] == "camera":
                    image = np.array(Image.open(cam["rgb"].filepath))
                    cameraT = _pose2Rotation([list(cam.location), list(cam.rotation_quaternion)])
                    Axis_align = np.array([[1, 0, 0, 0],
                                           [0, -1, 0, 0],
                                           [0, 0, -1, 0],
                                           [0, 0, 0, 1],]
                                            )
                    model_camT = np.linalg.inv(cameraT.dot(Axis_align)).dot(modelT)
                    perfix = cam.name.split(":")[1].replace("view", "")
                    scene.set_pose(node_camera, np.linalg.inv(model_camT).dot(Axis_align))
                    segement, _ = r.render(scene)
                    _createpose(posepath, perfix, model_camT)
                    _createbgpyrender(image, segement, rgbpath, perfix)
        scene.clear()
    r.delete()



def _createpose(path, perfix, T):
    # T = self.TfromPreviousFrame.dot(self.previousframePose[modelName])
    # self.previousframePose[modelName] = T
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