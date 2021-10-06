import numpy as np
import open3d as o3d
from PIL import Image
import tqdm
import os

def _pose2Rotation(pose):
    x, y, z = pose[0]
    q0, q1, q2, q3 = pose[1] / np.linalg.norm(pose[1])

    r00 = 2 * (q0 * q0 + q1 * q1) - 1
    r01 = 2 * (q1 * q2 - q0 * q3)
    r02 = 2 * (q1 * q3 + q0 * q2)

    r10 = 2 * (q1 * q2 + q0 * q3)
    r11 = 2 * (q0 * q0 + q2 * q2) - 1
    r12 = 2 * (q2 * q3 - q0 * q1)

    r20 = 2 * (q1 * q3 - q0 * q2)
    r21 = 2 * (q2 * q3 + q0 * q1)
    r22 = 2 * (q0 * q0 + q3 * q3) - 1

    rot_matrix = np.array([[r00, r01, r02],
                            [r10, r11, r12],
                            [r20, r21, r22]])

    move = np.array([x, y, z])
    move.resize((3, 1))
    T = np.hstack((rot_matrix, move))
    T = np.vstack((T, np.array([0, 0, 0, 1])))
    return T


def _rotation2Pose(rotation):
    m = rotation.copy()
    tr = rotation[0, 0] + rotation[1, 1] + rotation[2, 2]
    if tr > 0:
        S = np.sqrt(tr + 1.) * 2
        qw = S/4
        qx = (m[2, 1] - m[1, 2])/S
        qy = (m[0, 2] - m[2, 0])/S
        qz = (m[1, 0] - m[0, 1])/S
    elif (m[0, 0] > m[1, 1]) and (m[0, 0] > m[2, 2]):
        S = np.sqrt(1. + m[0, 0] - m[1, 1] - m[2, 2]) * 2
        qw = (m[2, 1] - m[1, 2])/S
        qx = S/4
        qy = (m[0, 1] + m[1, 0])/S
        qz = (m[0, 2] + m[2, 0])/S
    elif m[1, 1] > m[2, 2]:
        S = np.sqrt(1. + m[1, 1] - m[2, 2] - m[0, 0]) * 2
        qw = (m[0, 2] - m[2, 0])/S
        qx = (m[0, 1] + m[1, 0])/S
        qy = S/4
        qz = (m[1, 2] + m[2, 1])/S
    else:
        S = np.sqrt(1. + m[2, 2] - m[1, 1] - m[0, 0]) * 2
        qw = (-m[0, 1] + m[1, 0])/S
        qx = (m[0, 2] + m[2, 0])/S
        qy = (m[1, 2] + m[2, 1])/S
        qz = S/4
    location = rotation[:3, 3]
    return [[float(location[0]), float(location[1]), float(location[2])], [float(qw), float(qx), float(qy), float(qz)]]

def _render(image, pose, intrinsic, model):
    homoP = np.dot(pose[0:3, :], model.T)
    homoP = homoP / homoP[2]
    pixel = intrinsic.dot(homoP)
    pixel = (np.around(pixel[0:2])).astype(np.int32)
    pixel[0, pixel[0] < 0] = 0
    pixel[1, pixel[1] < 0] = 0
    pixel[0, pixel[0] >=image.shape[1]] = image.shape[1] - 1
    pixel[1, pixel[1] >=image.shape[0]] = image.shape[0] - 1
    ## remove the repeate pixel
    pixel_sort = pixel[:, np.argsort(pixel[0] * 10000 + pixel[1], axis=0)]
    _unique = np.unique(pixel[0] * 10000 + pixel[1])
    pixel_sort_unique = np.vstack((np.floor(_unique / 10000).astype(np.uint32), (_unique % 10000).astype(np.uint32)))
    ## mask
    maskimage = np.zeros_like(image)
    maskimage[pixel_sort_unique[1], pixel_sort_unique[0], :] = 1
    segimage = maskimage * image
    segimage[maskimage == 0] = 1.
    return segimage

def _loadModel(modelPath):

    ## load vertex from .obj
    pointCloud = []
    f = open(modelPath, "r")
    line = f.readline()
    while line:
        if line.startswith("v "):
            line = line.replace("\n", "")
            point = line.split(" ")[1:]
            pointCloud.append([float(point[i]) for i in range(3)] + [1.])
        else:
            pass
        line = f.readline()
    return np.array(pointCloud)

def plane_alignment(filepath, scale, alignT, threshold, n, iteration):
    pcd = o3d.io.read_point_cloud(filepath)
    scaled_xyz = (alignT[:3, :3].dot(np.asarray(pcd.points).T * scale) + alignT[:3, [3]]).T 
    scaled_pcd = o3d.geometry.PointCloud()
    scaled_pcd.points = o3d.utility.Vector3dVector(scaled_xyz)
    plane_model, inliers = scaled_pcd.segment_plane(distance_threshold=threshold,
                                         ransac_n=n,
                                         num_iterations=iteration)
    [a, b, c, d] = plane_model
    plane_cloud = scaled_pcd.select_by_index(inliers)
    plane_xyz = np.asarray(plane_cloud.points)
    plane_center = np.mean(plane_xyz, axis = 0)
    plane_center[2] = -(a * plane_center[0] + b * plane_center[1] + d)/c
    
    return [a, b, c, d], list(plane_center)

def transform_from_plane(plane, plane_center):
    [a, b, c, d] = plane
    ct = c/np.sqrt(a**2 + b**2 + c**2)
    st = np.sqrt(a**2 + b**2)/np.sqrt(a**2 + b**2 + c**2)
    u1 = b/np.sqrt(a**2 + b**2)
    u2 = -a/np.sqrt(a**2 + b**2)
    move = np.array([[1, 0, 0, -plane_center[0]],
                     [0, 1, 0, -plane_center[1]],
                     [0, 0, 1, -plane_center[2]],
                     [0, 0, 0, 1]])
    rotate = np.array([[ct + u1**2 * (1 - ct), u1 * u2*(1 - ct), u2 * st, 0],
                       [u1 * u2 * (1 - ct), ct + u2**2 * (1 - ct), -u1 * st, 0],
                       [-u2 *st, u1 *st, ct, 0],
                       [0, 0, 0, 1]])
    return rotate.dot(move)

def modelICP(scene_vertices, model_vertices):
    scene = o3d.geometry.PointCloud()
    scene.points = o3d.utility.Vector3dVector(scene_vertices)
    model = o3d.geometry.PointCloud()
    model.points = o3d.utility.Vector3dVector(model_vertices)
    trans_init = np.identity(4)
    threshold = 0.02
    reg_p2p = o3d.pipelines.registration.registration_icp(
        model, scene, threshold, trans_init,
        o3d.pipelines.registration.TransformationEstimationPointToPoint())
    # print(reg_p2p.transformation)
    return reg_p2p.transformation


def globalRegisteration(scene_vertices, model_vertices):
    scene = o3d.geometry.PointCloud()
    scene.points = o3d.utility.Vector3dVector(scene_vertices)
    model = o3d.geometry.PointCloud()
    model.points = o3d.utility.Vector3dVector(model_vertices)
    _, modelfpfh = _preprocess_point_cloud(model)
    _, scenefpfh = _preprocess_point_cloud(scene)
    return _register_point_cloud_fpfh(model, scene, modelfpfh, scenefpfh)

def _preprocess_point_cloud(pcd, voxel_size = 0.005):
    pcd_down = pcd.voxel_down_sample(voxel_size)
    pcd_down.estimate_normals(
        o3d.geometry.KDTreeSearchParamHybrid(radius=voxel_size * 2.0,
                                             max_nn=30))
    pcd_fpfh = o3d.pipelines.registration.compute_fpfh_feature(
        pcd_down,
        o3d.geometry.KDTreeSearchParamHybrid(radius=voxel_size * 5.0,
                                             max_nn=100))
    return (pcd_down, pcd_fpfh)

def _register_point_cloud_fpfh(source, target, source_fpfh, target_fpfh, distance_threshold = 0.005 * 1.4):

    # result = o3d.pipelines.registration.registration_fast_based_on_feature_matching(
    #     source, target, source_fpfh, target_fpfh,
    #     o3d.pipelines.registration.FastGlobalRegistrationOption(
    #         maximum_correspondence_distance=distance_threshold))
    result = o3d.pipelines.registration.registration_ransac_based_on_feature_matching(
        source, target, source_fpfh, target_fpfh, True, distance_threshold,
        o3d.pipelines.registration.TransformationEstimationPointToPoint(
            False), 3,
        [
            o3d.pipelines.registration.
            CorrespondenceCheckerBasedOnEdgeLength(0.9),
            o3d.pipelines.registration.CorrespondenceCheckerBasedOnDistance(
                distance_threshold)
        ],
        o3d.pipelines.registration.RANSACConvergenceCriteria(
            1000000, 0.999))
    if (result.transformation.trace() == 4.0):
        print("fail")
        return np.identity(4)
    else:
        return result.transformation

# def align_scale(pc, cam_pose, filename,
#                 depthscale,
#                 intrinsic, rX, rY,
#                 camposeinv = False):
#     if not camposeinv:
#         camT = np.linalg.inv(_pose2Rotation(cam_pose))
#     else:
#         camT = _pose2Rotation(cam_pose)

#     points_cam = camT[:3, :3].dot(pc.T) + camT[:3, [3]]

#     pixel_homo = intrinsic.dot(points_cam)
#     pixel = np.around(pixel_homo[:2]/pixel_homo[2]).astype(np.int32)
#     inside_mask = (pixel[0, :] >=0) * (pixel[0, :] <rX) * (pixel[1, :] >=0) * (pixel[1, :] <rY)
#     if np.sum(inside_mask) == 0:
#         ## maybe the camera intrinsic is set wrong
#         return (False, None)
#     pixel_inframe = pixel[:, inside_mask]
#     point_inframe = points_cam[2, inside_mask]
#     transform = pixel_inframe[0] * rY + pixel_inframe[1]


#     d = np.bincount(transform, point_inframe)
#     num = np.bincount(transform)
    
#     max_density = num.max()
#     dp = np.divide(d, num, out=np.zeros_like(d), where=num > max_density*0.5)
#     depth = np.concatenate((dp, np.zeros(rX*rY - dp.shape[0])), axis = 0)

#     depth_im = depth.reshape((rX, rY)).T

#     real_depth = np.asarray(Image.open(filename)) * depthscale
#     depth_mask = (real_depth > 0) * (depth_im > 0) * (real_depth < 1.5)
#     real = real_depth[depth_mask]
#     render = depth_im[depth_mask]
#     if real.shape[0] > 0 and render.shape[0] > 0:
#         scale = np.mean(real/render)
#         return (True, scale)
#     else:
#         return (False, None)

# def align_scale_among_depths(camera_rgb_file, depth_path,
#                              pc, depthscale,
#                              intrinsic, rX, rY,
#                              camposeinv = False):
#         file = open(camera_rgb_file, "r")
#         lines = file.read().split("\n")
#         scales = []
#         for l in tqdm.tqdm(lines):
#             data = l.split(" ")
#             if data[0].isnumeric():
#                 framename = data[-1]
#                 perfix = framename.split(".")[0]
#                 pose = [[float(data[5]), float(data[6]), float(data[7])], 
#                         [float(data[1]), float(data[2]), float(data[3]), float(data[4])]]
#                 depthfile = os.path.join(depth_path, perfix + ".png")
#                 if os.path.exists(depthfile):

#                     SUCCESS, scale = align_scale(pc, pose, depthfile,
#                                         depthscale,
#                                         intrinsic, rX, rY, 
#                                         camposeinv = camposeinv)
#                     if SUCCESS:
#                         scales.append(scale)  
#         return scales 

