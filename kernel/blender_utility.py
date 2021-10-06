import bpy
import numpy as np
import open3d as o3d
import os
import tqdm
from PIL import Image

from kernel.logging_utility import log_report
from kernel.geometry import _pose2Rotation, _rotation2Pose
from kernel.scale import _parseImagesFile, _parsePoints3D, _scaleFordepth, _calculateDepth

def _is_progresslabeller_object(obj):
    if "type" in obj:
        return True
    else:
        log_report(
            "Error", "Current object is not ProgressLabeller object", None
        )  
        return False

def _is_in_blender(name):
    if name in bpy.data.objects:
        return True
    else:
        log_report(
            "Error", "Object {0} is in Blender".format(name), None
        )  
        return False

def _get_workspace_name(obj):
    if _is_progresslabeller_object(obj):
        return obj.name.split(":")[0]
    else:
        return None

def _get_configuration(obj):
    if _is_progresslabeller_object(obj):
        workspaceName = _get_workspace_name(obj)
        config_id = bpy.data.objects[workspaceName + ":Setting"]['config_id']
        return config_id, bpy.context.scene.configuration[config_id]
    else:
        return None, None

def _get_reconstruction_insameworkspace(obj):
    if _is_progresslabeller_object(obj):
        workspaceName = _get_workspace_name(obj)
        if _is_in_blender(workspaceName + ":reconstruction"):
            return bpy.data.objects[workspaceName + ":reconstruction"]
        else:
            return None
    else:
        return None

def _is_obj_type(obj, types):
    if _is_progresslabeller_object(obj) and obj["type"] in types:
        return True
    else:
        return False

def _get_obj_insameworkspace(obj, types):
    if _is_progresslabeller_object(obj):
        obj_list = []
        workspaceName = _get_workspace_name(obj)
        for o in bpy.data.objects:
            if "type" in o and o.name.split(":")[0] == workspaceName and o["type"] in types:
                obj_list.append(o)
        return obj_list
    else:
        return []

def _apply_trans2obj(obj, trans):
    origin_pose = [list(obj.location), list(obj.rotation_quaternion)]
    origin_trans = _pose2Rotation(origin_pose)
    after_align_trans = trans.dot(origin_trans)
    after_align_pose = _rotation2Pose(after_align_trans)
    obj.location = after_align_pose[0]
    obj.rotation_quaternion = after_align_pose[1]/np.linalg.norm(after_align_pose[1])


def _transstring2trans(transstring):
    vectorstring = transstring.split(';')[:-1]
    vectorstring = [v.split(',') for v in vectorstring]
    return np.array(vectorstring).astype(np.float32)

def _trans2transstring(trans):
    trans_u1 = trans.astype(dtype='<U8')
    transstring = ''
    for i in range(trans_u1.shape[0]):
        for j in range(trans_u1.shape[1]):
            transstring+=trans_u1[i, j]
            if j == trans_u1.shape[1] - 1:
                transstring+=';'
            else:
                transstring+=','
    return transstring

# def _align_reconstruction(config, scene):
#     datasrc = config.datasrc
#     filepath = config.reconstructionsrc

#     camera_rgb_file = os.path.join(filepath, "campose.txt")
#     reconstruction_path = os.path.join(filepath, "fused.ply")
#     depth_path = os.path.join(datasrc, "depth")

#     pcd = o3d.io.read_point_cloud(reconstruction_path)
#     _, inliers = pcd.segment_plane(distance_threshold=scene.planalignmentparas.threshold,
#                                                 ransac_n=scene.planalignmentparas.n,
#                                                 num_iterations=scene.planalignmentparas.iteration)
    
#     plane_pcd = pcd.select_by_index(inliers)
#     points = np.asarray(plane_pcd.points)

#     intrinsic = np.array([
#         [config.fx, 0, config.cx],
#         [0, config.fy, config.cy],
#         [0, 0, 1],
#     ])

#     scales = align_scale_among_depths(camera_rgb_file, depth_path,
#                                         points, scene.loadreconparas.depth_scale,
#                                         intrinsic, config.resX, config.resY, 
#                                         camposeinv = scene.loadreconparas.CAMPOSE_INVERSE)            
    
#     if len(scales) != 0:
#         scale = np.mean(scales)
#         log_report(
#         "INFO", "The aligning scale is {0}".format(scale), None
#         )   
#     else:
#         scale = 1.0
#         log_report(
#         "ERROR", "Failed finding the scale, maybe there is not a plane in your ", None
#         )  
#     return scale

def _align_reconstruction(config, scene, THRESHOLD = 0.0001, NUM_THRESHOLD = 8):
    filepath = config.reconstructionsrc

    imagefilepath = os.path.join(filepath, "images.txt")
    points3Dpath = os.path.join(filepath, "points3D.txt")
    datapath = config.datasrc  

    intrinsic = np.array([
        [config.fx, 0, config.cx],
        [0, config.fy, config.cy],
        [0, 0, 1],
    ])

    depth_scale = scene.loadreconparas.depth_scale

    Camera_dict = {}
    PointsDict = {}
    PointsDepth = {}
    _parseImagesFile(imagefilepath, Camera_dict, PointsDict)
    _parsePoints3D(points3Dpath, PointsDict)
    for camera_idx in tqdm.tqdm(Camera_dict):
            rgb_name = Camera_dict[camera_idx]["name"]
            with Image.open(os.path.join(datapath, "depth", rgb_name)) as im:
                depth = np.array(im) * depth_scale
                _scaleFordepth(depth, camera_idx, intrinsic, Camera_dict, PointsDict, PointsDepth)
        
    scale = _calculateDepth(THRESHOLD = 0.005, NUM_THRESHOLD = 3, PointsDepth = PointsDepth)

    return scale