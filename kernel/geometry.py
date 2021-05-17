import numpy as np

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