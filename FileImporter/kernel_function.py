import bpy
import os
import yaml
import numpy as np

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
        bpy.data.collections["Model"].objects.link(bpy.data.objects[objName])
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