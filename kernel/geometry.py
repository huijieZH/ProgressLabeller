import numpy as np
import open3d as o3d

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

def plane_alignment(filepath, scale):
    pcd = o3d.io.read_point_cloud(filepath)
    scaled_xyz = np.asarray(pcd.points)* scale
    scaled_pcd = o3d.geometry.PointCloud()
    scaled_pcd.points = o3d.utility.Vector3dVector(scaled_xyz)
    plane_model, inliers = scaled_pcd.segment_plane(distance_threshold=0.03,
                                         ransac_n=3,
                                         num_iterations=1000)
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

