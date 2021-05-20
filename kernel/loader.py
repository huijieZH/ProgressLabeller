import bpy
import os
import yaml
import numpy as np
from mathutils import Vector
import json

from kernel.geometry import _pose2Rotation, _rotation2Pose
from kernel.ply_importer.point_data_file_handler import(
    PointDataFileHandler
)
from kernel.ply_importer.utility import(
    draw_points
)

def load_configuration(filepath):
    if os.path.exists(filepath):
        with open(filepath) as file:
            configuration = json.load(file)
        bpy.context.scene.configuration.modelsrc = configuration['environment']['modelsrc']
        bpy.context.scene.configuration.modelposesrc = configuration['environment']['modelposesrc']
        bpy.context.scene.configuration.reconstructionsrc = configuration['environment']['reconstructionsrc']
        bpy.context.scene.configuration.imagesrc = configuration['environment']['imagesrc']

        bpy.context.scene.configuration.resX = configuration['camera']['resolution'][0]
        bpy.context.scene.configuration.resY = configuration['camera']['resolution'][1]
        bpy.context.scene.configuration.fx = configuration['camera']['intrinsic'][0][0]
        bpy.context.scene.configuration.fy = configuration['camera']['intrinsic'][1][1]
        bpy.context.scene.configuration.px = configuration['camera']['intrinsic'][0][2]
        bpy.context.scene.configuration.py = configuration['camera']['intrinsic'][1][2]
        bpy.context.scene.configuration.lens = configuration['camera']['lens']

def load_model(filepath):
    objFilename = filepath.split("/")[-1]
    objName = objFilename.split(".")[0]
    if objName in bpy.data.objects:
        print("Unsupported for same object loaded several times")
    else:
        bpy.ops.import_scene.obj(filepath=filepath)
        bpy.context.selected_objects[0].name = objName
        bpy.ops.object.select_all(action='DESELECT')
        bpy.data.objects[objName].rotation_mode = 'QUATERNION'
        bpy.data.objects[objName]["type"] = "model"
        ## first unlink all collection, then link to Model collection
        for collection in bpy.data.objects[objName].users_collection:
            collection.objects.unlink(bpy.data.objects[objName])
        if "Model" not in bpy.data.collections:
            model_collection = bpy.data.collections.new("Model")
            bpy.context.scene.collection.children.link(model_collection)
        bpy.data.collections['Model'].objects.link(bpy.data.objects[objName])
    
def load_model_from_pose(filepath):
    with open(filepath, 'r') as file:
        poses = yaml.load(file, Loader=yaml.FullLoader)
    # print(bpy.context.scene.env.labelmodel)
    if bpy.context.scene.configuration.modelsrc == "":
        pass
    else:
        ## automatically load object from model(label) env
        model_dir = os.listdir(bpy.context.scene.configuration.modelsrc)
        for objname in poses:
            if objname in model_dir:
                if objname in bpy.data.objects:
                    bpy.data.objects[objname].location = poses[objname]['pose'][0]
                    bpy.data.objects[objname].rotation_quaternion = poses[objname]['pose'][1]/np.linalg.norm(poses[objname]['pose'][1])
                else:
                    load_model(os.path.join(bpy.context.scene.configuration.modelsrc, objname, objname + ".obj" ))
                    bpy.data.objects[objname].location = poses[objname]['pose'][0]
                    bpy.data.objects[objname].rotation_quaternion = poses[objname]['pose'][1]/np.linalg.norm(poses[objname]['pose'][1])

def load_pc(filepath, pointcloudscale):
    points = PointDataFileHandler.parse_point_data_file(filepath)
    draw_points(points = points, 
                point_size = 5, 
                add_points_to_point_cloud_handle = True, 
                reconstruction_collection = bpy.data.collections["PointCloud"], 
                object_anchor_handle_name="reconstruction", op=None)
    bpy.data.objects['reconstruction']["type"] = "reconstruction"
    bpy.data.objects['reconstruction'].scale = Vector((pointcloudscale, 
                                                        pointcloudscale, 
                                                        pointcloudscale))

    bpy.data.objects['reconstruction']["path"] = filepath
    bpy.data.objects['reconstruction']["scale"] = pointcloudscale
    bpy.data.objects['reconstruction'].rotation_mode = 'QUATERNION'

def load_reconstruction_result(filepath, 
                               reconstruction_method, 
                               pointcloudscale, 
                               imagesrc,
                               camera_display_scale):
    if "Reconstruction" not in bpy.data.collections:
        reconstruction_collection = bpy.data.collections.new("Reconstruction")
        bpy.context.scene.collection.children.link(reconstruction_collection)

    ## pointcloud collection  
    if "PointCloud" not in bpy.data.collections:
        pointcloud_collection = bpy.data.collections.new("PointCloud")
        bpy.data.collections["Reconstruction"].children.link(pointcloud_collection)
    ## Camera collection  
    if "Camera" not in bpy.data.collections:
        camera_collection = bpy.data.collections.new("Camera")
        bpy.data.collections["Reconstruction"].children.link(camera_collection)
    
    if reconstruction_method == 'COLMAP':
        ## load reconstruction result
        camera_rgb_file = os.path.join(filepath, "extracted_campose.txt")
        reconstruction_path = os.path.join(filepath, "fused.ply")
        load_pc(reconstruction_path, pointcloudscale)
        bpy.ops.object.select_all(action='DESELECT')

        ## load camera and image result
        file = open(camera_rgb_file, "r")
        lines = file.read().split("\n")
        for l in lines:
            data = l.split(" ")
            if data[0].isnumeric():
                perfix = "{:04d}".format(int(data[0]))
                pose = [[float(data[5]) * pointcloudscale, float(data[6]) * pointcloudscale, float(data[7]) * pointcloudscale], 
                        [float(data[1]), float(data[2]), float(data[3]), float(data[4])]]
                Axis_align = np.array([[1, 0, 0, 0],
                                       [0, -1, 0, 0],
                                       [0, 0, -1, 0],
                                       [0, 0, 0, 1],]
                )
                Trans = np.linalg.inv(_pose2Rotation(pose)).dot(Axis_align)
                pose = _rotation2Pose(Trans)
                framename = data[-1]
                framepath = os.path.join(imagesrc, framename)

                ## create a new camera, specify its parameters
                ## the lens could be define by yourself, and the sensor size could be calculate from intrinsic
                camera_data = bpy.data.cameras.new(name="view" + perfix)
                camera_data.lens = bpy.context.scene.configuration.lens  # realsense L515
                f = (bpy.context.scene.configuration.fx + bpy.context.scene.configuration.fy)/2
                camera_data.sensor_width = camera_data.lens * bpy.context.scene.configuration.resX/f
                # camera_data.shift_x = (bpy.context.scene.configuration.px - bpy.context.scene.configuration.resX/2) * camera_data.sensor_width / bpy.context.scene.configuration.resX
                # camera_data.shift_y = (bpy.context.scene.configuration.py - bpy.context.scene.configuration.resY/2) * camera_data.sensor_width / bpy.context.scene.configuration.resX
                camera_data.display_size = camera_display_scale
                camera_object = bpy.data.objects.new("view" + perfix, camera_data)
                bpy.data.collections["Camera"].objects.link(camera_object)
                camera_object.rotation_mode = 'QUATERNION'
                camera_object.location = pose[0]
                camera_object.rotation_quaternion = pose[1]

                ## create new image
                bpy.ops.image.open(filepath=framepath, 
                                   directory=imagesrc, 
                                   files=[{"name":framename}], 
                                   relative_path=True, show_multiview=False)
                bpy.data.images[framename].name = "view" + perfix  
                camera_object["image"] = bpy.data.images["view" + perfix]
                camera_object["type"] = "camera"

    elif reconstruction_method == 'KinectFusion':
        print("not finish yet")
    
    elif reconstruction_method == 'Meshroom':
        print("not finish yet")