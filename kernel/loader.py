from PIL import Image
import bpy
import os
import yaml
import numpy as np
from mathutils import Vector
import json
from tqdm import tqdm

from kernel.geometry import _pose2Rotation, _rotation2Pose
from kernel.ply_importer.point_data_file_handler import(
    PointDataFileHandler
)
from kernel.ply_importer.utility import(
    draw_points
)
from kernel.utility import _transstring2trans, _parse_camfile

from kernel.logging_utility import log_report
from registeration.init_configuration import config_json_dict, decode_dict
from kernel.blender_utility import \
    _get_configuration, _get_obj_insameworkspace, _apply_trans2obj, \
    _clear_allrgbdcam_insameworkspace, _getsameinstance, _getnextperfixforinstance
from kernel.utility import _select_sample_files, _generate_image_list
import time


def load_configuration(filepath):
    if os.path.exists(filepath):
        with open(filepath) as file:
            configuration = json.load(file)

        if configuration['projectname'] not in bpy.data.collections:
            config = bpy.context.scene.configuration.add()
            config_from_file(config, configuration)

        else:
            for config in bpy.context.scene.configuration:
                if config.projectname == configuration['projectname']:
                    config_from_file(config, configuration)
                    break
        
        create_workspace(os.path.dirname(filepath), 
                         configuration['projectname'], 
                         config = config)


def load_model(filepath, config_id):
    config = bpy.context.scene.configuration[config_id]
    workspace_name = config.projectname
    objFilename = filepath.split("/")[-1]
    objname = objFilename.split(".")[0]
    obj_instancename = workspace_name + ":" + objname + ".instance{0:03d}".format(_getnextperfixforinstance(config, objname))
    # if objName in bpy.data.objects:
    #     print("Unsupported for same object loaded several times")
    bpy.ops.import_scene.obj(filepath=filepath)
    bpy.context.selected_objects[0].name = obj_instancename
    bpy.ops.object.select_all(action='DESELECT')
    bpy.data.objects[obj_instancename].rotation_mode = 'QUATERNION'
    bpy.data.objects[obj_instancename].rotation_quaternion = [1., 0., 0., 0.]
    bpy.data.objects[obj_instancename]["type"] = "model"
    bpy.data.objects[obj_instancename]["path"] = filepath
    ## first unlink all collection, then link to Model collection
    for collection in bpy.data.objects[obj_instancename].users_collection:
        collection.objects.unlink(bpy.data.objects[obj_instancename])

    create_collection(workspace_name + ":Model", parent_collection = workspace_name)

    bpy.data.collections[workspace_name + ":Model"].objects.link(bpy.data.objects[obj_instancename])

    ### check whether the object is normal, split or URDF
    files = os.listdir(os.path.dirname(filepath))
    if 'split' in files:
        bpy.data.objects[obj_instancename]["modeltype"] = "split"
    else:
        bpy.data.objects[obj_instancename]["modeltype"] = "normal"

    

def load_model_from_pose(filepath, config_id):
    config = bpy.context.scene.configuration[config_id]
    workspace_name = config.projectname
    with open(filepath, 'r') as file:
        poses = yaml.load(file, Loader=yaml.FullLoader)
    if config.modelsrc == "":
        log_report(
            "INFO", "You should initialize the modelsrc before using this function", None
        )       
    else:
        model_dir = os.listdir(config.modelsrc)
        print(poses)
        for obj_instancename in poses:
            objname = obj_instancename.split(".")[0]
            if objname in model_dir:
                objworkspacename = workspace_name + ":" + obj_instancename
                if objworkspacename in bpy.data.objects:
                    bpy.data.objects[objworkspacename].location = poses[obj_instancename]['pose'][0]
                    bpy.data.objects[objworkspacename].rotation_quaternion = poses[obj_instancename]['pose'][1]/np.linalg.norm(poses[obj_instancename]['pose'][1])
                else:
                    load_model(os.path.join(config.modelsrc, objname, objname + ".obj" ), config_id)
                    bpy.data.objects[objworkspacename].location = poses[obj_instancename]['pose'][0]
                    bpy.data.objects[objworkspacename].rotation_quaternion = poses[obj_instancename]['pose'][1]/np.linalg.norm(poses[obj_instancename]['pose'][1])


def load_pc(filepath, pointcloudscale, config_id):
    workspace_name = bpy.context.scene.configuration[config_id].projectname

    if workspace_name + ":" + 'reconstruction' in bpy.data.objects:
        bpy.ops.object.select_all(action='DESELECT')
        bpy.data.objects[workspace_name + ":" + 'reconstruction'].select_set(True)
        bpy.ops.object.delete() 
    points = PointDataFileHandler.parse_point_data_file(filepath)
    draw_points(points = points, 
                point_size = 3, 
                add_points_to_point_cloud_handle = True, 
                reconstruction_collection = bpy.data.collections[workspace_name + ":" + "Pointcloud"], 
                object_anchor_handle_name=workspace_name + ":" + "reconstruction", op=None)
    bpy.data.objects[workspace_name + ":" + 'reconstruction']["type"] = "reconstruction"
    bpy.data.objects[workspace_name + ":" + 'reconstruction'].scale = Vector((pointcloudscale, 
                                                        pointcloudscale, 
                                                        pointcloudscale))

    bpy.data.objects[workspace_name + ":" + 'reconstruction']["path"] = filepath
    bpy.data.objects[workspace_name + ":" + 'reconstruction']["scale"] = pointcloudscale
    bpy.data.objects[workspace_name + ":" + 'reconstruction'].rotation_mode = 'QUATERNION'
    bpy.data.objects[workspace_name + ":" + 'reconstruction']["alignT"] = [[1., 0., 0., 0.],
                                                                            [0., 1., 0., 0.], 
                                                                            [0., 0., 1., 0.], 
                                                                            [0., 0., 0., 1.]]

def load_pc(filepath, pointcloudscale, config_id, name = 'reconstruction'):
    if os.path.exists(filepath):
        workspace_name = bpy.context.scene.configuration[config_id].projectname

        if workspace_name + ":" + name in bpy.data.objects:
            bpy.ops.object.select_all(action='DESELECT')
            bpy.data.objects[workspace_name + ":" + name].select_set(True)
            bpy.ops.object.delete() 
        points = PointDataFileHandler.parse_point_data_file(filepath)
        draw_points(points = points, 
                    point_size = 3, 
                    add_points_to_point_cloud_handle = True, 
                    reconstruction_collection = bpy.data.collections[workspace_name + ":" + "Pointcloud"], 
                    object_anchor_handle_name=workspace_name + ":" + name, op=None)
        bpy.data.objects[workspace_name + ":" + name]["type"] = "reconstruction"
        bpy.data.objects[workspace_name + ":" + name].scale = Vector((pointcloudscale, 
                                                                    pointcloudscale, 
                                                                    pointcloudscale))

        bpy.data.objects[workspace_name + ":" + name]["path"] = filepath
        bpy.data.objects[workspace_name + ":" + name]["scale"] = pointcloudscale
        bpy.data.objects[workspace_name + ":" + name].rotation_mode = 'QUATERNION'
        bpy.data.objects[workspace_name + ":" + name]["alignT"] = [[1., 0., 0., 0.],
                                                                    [0., 1., 0., 0.], 
                                                                    [0., 0., 1., 0.], 
                                                                    [0., 0., 0., 1.]]

def load_cam_img_depth(packagepath, config_id, camera_display_scale, sample_rate):

    workspace_name = bpy.context.scene.configuration[config_id].projectname

    work_space_collection = create_collection(workspace_name, parent_collection = None)
    recon_collection = create_collection(workspace_name + ":Reconstruction", 
                                         parent_collection = work_space_collection)
    cam_collection = create_collection(workspace_name + ":Camera", 
                                       parent_collection = recon_collection)
    

    rgb_path = os.path.join(packagepath, "rgb")
    depth_path = os.path.join(packagepath, "depth")
    
    rgb_files = os.listdir(rgb_path)
    depth_files = os.listdir(depth_path)

    rgb_files.sort()
    rgb_sample_files = _select_sample_files(rgb_files, sample_rate)
    os.system("mkdir -p " + bpy.context.scene.configuration[config_id].reconstructionsrc)
    _generate_image_list(bpy.context.scene.configuration[config_id].reconstructionsrc, rgb_sample_files)
    _clear_allrgbdcam_insameworkspace(bpy.context.scene.configuration[config_id])
    log_report(
        "INFO", "Loading camera, rgb and depth images", None
    )
    for rgb in tqdm(rgb_sample_files):
        perfix = rgb.split(".")[0]
        if perfix + ".png" in depth_files:
            cam_name = workspace_name + ":view" + perfix
            if cam_name not in bpy.data.objects:
                cam_data = bpy.data.cameras.new(cam_name)
                cam_data.lens = bpy.context.scene.configuration[config_id].lens
                f = (bpy.context.scene.configuration[config_id].fx + bpy.context.scene.configuration[config_id].fy)/2
                cam_data.sensor_width = cam_data.lens * bpy.context.scene.configuration[config_id].resX/f
                cam_data.display_size = camera_display_scale
                
                cam_data.shift_x = (bpy.context.scene.configuration[config_id].resX/2 - bpy.context.scene.configuration[config_id].cx)/bpy.context.scene.configuration[config_id].resX
                cam_data.shift_y = (bpy.context.scene.configuration[config_id].cy - bpy.context.scene.configuration[config_id].resY/2)/bpy.context.scene.configuration[config_id].resX
                cam_data.background_images.new()
                
                cam_object = bpy.data.objects.new(cam_name, cam_data)
                cam_collection.objects.link(cam_object)
                cam_object.rotation_mode = 'QUATERNION'
                cam_object.location = [0, 0, 0]
                cam_object.rotation_quaternion = [1., 0, 0, 0]
            else:
                cam_object = bpy.data.objects[cam_name]

            ## load rgb
            rgb_name = workspace_name + ":rgb" + perfix
            if rgb_name not in bpy.data.images:
                bpy.ops.image.open(filepath=os.path.join(rgb_path, perfix + ".png"), show_multiview=False)
                bpy.data.images[perfix + ".png"].name = rgb_name
            bpy.data.images[rgb_name]["UPDATEALPHA"] = True
            bpy.data.images[rgb_name]["alpha"] = [0.5]
            ## load depth
            depth_name = workspace_name + ":depth" + perfix
            if depth_name not in bpy.data.images:
                bpy.ops.image.open(filepath=os.path.join(depth_path, perfix + ".png"), 
                                    directory=depth_path, 
                                    files=[{"name":perfix + ".png"}], 
                                    relative_path=True, show_multiview=False)
                bpy.data.images[perfix + ".png"].name = depth_name
                
                depth = np.array(Image.open(os.path.join(depth_path, perfix + ".png")))
                depth = depth[::-1, ::]
                bpy.data.images[depth_name]["depth"] = depth.flatten().astype(np.float32)
                ## change transparency
            bpy.data.images[depth_name]["UPDATEALPHA"] = True
            bpy.data.images[depth_name]["alpha"] = [0.5]
            cam_object["depth"] = bpy.data.images[depth_name]
            cam_object["rgb"] = bpy.data.images[rgb_name]
            cam_object["type"] = "camera"



def load_reconstruction_result(filepath, 
                               pointcloudscale, 
                               datasrc,
                               config_id,
                               camera_display_scale = 0.1,
                               IMPORT_RATIO = 1.0,
                               CAMPOSE_INVERSE = False
                               ):
                            
    packagepath = bpy.context.scene.configuration[config_id].datasrc
    rgb_path = os.path.join(datasrc, "rgb")
    depth_path = os.path.join(datasrc, "depth")    

    workspace_name = bpy.context.scene.configuration[config_id].projectname
    work_space_collection = create_collection(workspace_name, parent_collection = None)
    recon_collection = create_collection(workspace_name + ":Reconstruction", 
                                         parent_collection = work_space_collection)
    cam_collection = create_collection(workspace_name + ":Camera", 
                                       parent_collection = recon_collection)
    pc_collection = create_collection(workspace_name + ":Pointcloud", 
                                      parent_collection = recon_collection)    
    ## load reconstruction result
    
    camera_rgb_file = os.path.join(filepath, "campose.txt")
    reconstruction_path = os.path.join(filepath, "fused.ply")
    load_pc(reconstruction_path, pointcloudscale, config_id)
    bpy.ops.object.select_all(action='DESELECT')

    rgb_files = os.listdir(rgb_path)
    depth_files = os.listdir(depth_path)
    
    ## load camera and image result
    camera_lines = _parse_camfile(camera_rgb_file)
    camera_selected_lines = _select_sample_files(camera_lines, IMPORT_RATIO)
    _clear_allrgbdcam_insameworkspace(bpy.context.scene.configuration[config_id])
    for l in tqdm(camera_selected_lines):
        data = l.split(" ")
        if data[0].isnumeric():
            pose = [[float(data[5]) * pointcloudscale, float(data[6]) * pointcloudscale, float(data[7]) * pointcloudscale], 
                    [float(data[1]), float(data[2]), float(data[3]), float(data[4])]]
            Axis_align = np.array([[1, 0, 0, 0],
                                    [0, -1, 0, 0],
                                    [0, 0, -1, 0],
                                    [0, 0, 0, 1],]
            )
            Trans = _pose2Rotation(pose).dot(Axis_align) if not CAMPOSE_INVERSE else np.linalg.inv(_pose2Rotation(pose)).dot(Axis_align)
            pose = _rotation2Pose(Trans)
            framename = data[-1]
            perfix = framename.split(".")[0]

            cam_name = workspace_name + ":view" + perfix
            if cam_name in bpy.data.objects:
                cam_object = bpy.data.objects[cam_name]
                cam_object.location = pose[0]
                cam_object.rotation_quaternion = pose[1]
            elif perfix + ".png" in rgb_files and perfix + ".png" in depth_files:
                cam_data = bpy.data.cameras.new(cam_name)
                cam_data.lens = bpy.context.scene.configuration[config_id].lens
                f = (bpy.context.scene.configuration[config_id].fx + bpy.context.scene.configuration[config_id].fy)/2
                cam_data.sensor_width = cam_data.lens * bpy.context.scene.configuration[config_id].resX/f
                cam_data.shift_x = (bpy.context.scene.configuration[config_id].resX/2 - bpy.context.scene.configuration[config_id].cx)/bpy.context.scene.configuration[config_id].resX
                ### divide resX not resY
                cam_data.shift_y = (bpy.context.scene.configuration[config_id].cy - bpy.context.scene.configuration[config_id].resY/2)/bpy.context.scene.configuration[config_id].resX
                cam_data.display_size = camera_display_scale
                ## allow background display
                cam_data.background_images.new()

                cam_object = bpy.data.objects.new(cam_name, cam_data)
                cam_collection.objects.link(cam_object)
                cam_object.rotation_mode = 'QUATERNION'
                cam_object.location = pose[0]
                cam_object.rotation_quaternion = pose[1]
                ## load rgb
                rgb_name = workspace_name + ":rgb" + perfix
                if rgb_name not in bpy.data.images:
                    bpy.ops.image.open(filepath=os.path.join(rgb_path, perfix + ".png"), 
                                        directory=rgb_path, 
                                        files=[{"name":perfix + ".png"}], 
                                        relative_path=True, show_multiview=False)
                    bpy.data.images[perfix + ".png"].name = rgb_name
                bpy.data.images[rgb_name]["UPDATEALPHA"] = True
                bpy.data.images[rgb_name]["alpha"] = [0.5]
                ## load depth
                depth_name = workspace_name + ":depth" + perfix
                if depth_name not in bpy.data.images:
                    bpy.ops.image.open(filepath=os.path.join(depth_path, perfix + ".png"), 
                                        directory=depth_path, 
                                        files=[{"name":perfix + ".png"}], 
                                        relative_path=True, show_multiview=False)
                    bpy.data.images[perfix + ".png"].name = depth_name
                    depth = np.array(Image.open(os.path.join(depth_path, perfix + ".png")))
                    depth = depth[::-1, ::]
                    bpy.data.images[depth_name]["depth"] = depth.flatten().astype(np.float32)
                bpy.data.images[depth_name]["UPDATEALPHA"] = True
                bpy.data.images[depth_name]["alpha"] = [0.5]
                cam_object["depth"] = bpy.data.images[depth_name]
                cam_object["rgb"] = bpy.data.images[rgb_name]
                cam_object["type"] = "camera" 
    
    obj_lists = _get_obj_insameworkspace(cam_object, ["reconstruction", "camera"])
    _, config = _get_configuration(cam_object)

    trans = _transstring2trans(config.recon_trans)
    for obj in obj_lists:
        _apply_trans2obj(obj, trans)  
        if obj['type'] == 'reconstruction':
            obj["alignT"] = trans.tolist()      
    


def create_workspace(path, name, 
                     config = None):
    if not config:
        config = bpy.context.scene.configuration.add()
        config_id = len(bpy.context.scene.configuration) - 1
        config.projectname = name
    else:
        for idx, c in enumerate(bpy.context.scene.configuration):
            if c.projectname == name:
                config_id = idx
    
    work_space_collection = create_collection(name, parent_collection = None)
    setting = setting_init(name + ":Setting", work_space_collection, path)
    setting["config_id"] = config_id
    model_collection = create_collection(name + ":Model", 
                                         parent_collection = work_space_collection)
    recon_collection = create_collection(name + ":Reconstruction", 
                                         parent_collection = work_space_collection)
    pc_collection = create_collection(name + ":Pointcloud", 
                                      parent_collection = recon_collection)
    cam_collection = create_collection(name + ":Camera", 
                                       parent_collection = recon_collection)

def init_package(path, config):
    create_packages(path, ["model", "recon", "data"])
    config.modelsrc = os.path.join(path, "model")
    config.datasrc = os.path.join(path, "data")
    config.reconstructionsrc = os.path.join(path, "recon")

def create_packages(path, packages):
    for package in packages:
        dir = os.path.join(path, package)
        if not os.path.exists(dir):
            os.mkdir(dir)


def create_collection(new_name, parent_collection = None):
    if new_name not in bpy.data.collections:
        new_collection = bpy.data.collections.new(new_name)
        if not parent_collection:
            bpy.context.scene.collection.children.link(new_collection)
        elif parent_collection.name in bpy.data.collections:
            parent_collection.children.link(new_collection)
        else:
            raise Exception("parent collection not exists")
        return new_collection
    else: 
        return bpy.data.collections[new_name]

def setting_init(name, collection, path):
    if name not in bpy.data.objects:
        setting = bpy.data.objects.new(name, None)
        setting["type"] = "setting"
        setting["dir"] = path
        collection.objects.link(setting)
    else:
        setting = bpy.data.objects[name]
        print(name.split(":")[0] + " is currently in the Blender")
    return setting


def config_from_file(config, configuration):
    for item in config_json_dict:
        value = decode_dict(configuration, config_json_dict[item])
        setattr(config, item, value)



def updateprojectname():
    current_object = bpy.context.object.name
    
    old_name = current_object.split(":")[0]
    config_id = bpy.data.objects[old_name + ":Setting"]['config_id']

    new_name = bpy.context.scene.configuration[config_id].projectname
    for config in bpy.context.scene.configuration:
        if config.projectname == new_name and config != bpy.context.scene.configuration[config_id]:
            log_report(
                "INFO", "Same name is existing in Blender", None
            )                   
            bpy.context.scene.configuration[config_id].projectname = old_name
            return 
    for collection in bpy.data.collections:
        if collection.name.split(":")[0] == old_name:
            collection.name = collection.name.replace(old_name, new_name)
    
    for obj in bpy.data.objects:
        if obj.name.split(":")[0] == old_name:
            obj.name = obj.name.replace(old_name, new_name)    

    for img in bpy.data.images:
        if img.name.split(":")[0] == old_name:
            img.name = img.name.replace(old_name, new_name)          
    return

def removeworkspace(name):
    for obj in bpy.data.objects:
        if obj.name.split(":")[0] == name:
            bpy.data.objects.remove(obj)    
    for collection in bpy.data.collections:
        if collection.name.split(":")[0] == name:
            bpy.data.collections.remove(collection)
    for img in bpy.data.images:
        if img.name.split(":")[0] == name:
            bpy.data.images.remove(img)         
    return 



