import bpy
import os
import yaml
import numpy as np
from mathutils import Vector

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
        ## first unlink all collection, then link to Model collection
        for collection in bpy.data.objects[objName].users_collection:
            collection.objects.unlink(bpy.data.objects[objName])
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

def load_reconstruction_result(filepath, reconstruction_method, pointcloudscale):
    if reconstruction_method == 'COLMAP':

        ## load reconstruction result
        camera_rgb_file = os.path.join(filepath, "extracted_campose.txt")
        reconstruction_path = os.path.join(filepath, "fused.ply")
        bpy.ops.import_mesh.ply(filepath=reconstruction_path)

        bpy.data.objects['fused'].name = 'reconstruction'
        bpy.ops.object.select_all(action='DESELECT')

        bpy.data.collections["Model"].objects.link(bpy.data.objects['reconstruction'])
        ## first unlink all collection, then link to Model collection
        for collection in bpy.data.objects['reconstruction'].users_collection:
            collection.objects.unlink(bpy.data.objects['reconstruction'])
        bpy.data.collections['PointCloud'].objects.link(bpy.data.objects['reconstruction'])
        bpy.data.objects['reconstruction'].scale = Vector((pointcloudscale, 
                                                           pointcloudscale, 
                                                           pointcloudscale))

        ## load camera and image result
        # file = open(filepath, "r")
        # lines = file.read().split("\n")
        # for l in lines:
        #     data = l.split(" ")
        #     if data[0].isnumeric():
        #         pose = [[float(data[5]) * pointcloudscale, float(data[6]) * pointcloudscale, float(data[7]) * pointcloudscale], 
        #                 [float(data[1]), float(data[2]), float(data[3]), float(data[4])]]
        #         Trans = np.linalg.inv(self._pose2Rotation(pose))
        #         # Trans = self._pose2Rotation(pose)
        #         frame_prefix = data[-1].split("_")[0]
        #         self.prefix_list.append(frame_prefix)
        #         self.framePoses[frame_prefix] = Trans

    elif reconstruction_method == 'KinectFusion':
        print("not finish yet")
    
    elif reconstruction_method == 'Meshroom':
        print("not finish yet")