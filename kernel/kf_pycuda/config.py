import numpy as np
import numpy.linalg as la

def get_config(camera='uw'):
    config = dict()
    config['im_w'] = 1280
    config['im_h'] = 720
    if camera == 'uw':
        config['cam_intr'] = np.array([ 
            [1066.778, 0, 312.9869],
            [0, 1067.487, 241.3109],
            [0, 0, 1]
        ])
    elif camera == 'umich':
        config['cam_intr'] = np.array([ 
            [904.572, 0., 635.981],
            [0., 905.295, 353.060],
            [0., 0., 1.]
        ])
    else:
        config['cam_intr'] = np.array([
            [1077.836, 0, 323.7872],
            [0, 1078.189, 279.6921],
            [0, 0, 1]
        ])
    config['tsdf_voxel_size'] = 0.0025  # in meter
    config['tsdf_trunc_margin'] = 0.015 # in meter
    config['pcd_voxel_size'] = 0.005  # in meter

    return config

def set_config(resX, resY, fx, fy, cx, cy, tsdf_voxel_size, tsdf_trunc_margin, pcd_voxel_size):
    config = dict()
    config['im_w'] = resX
    config['im_h'] = resY
    config['cam_intr'] = np.array([ 
        [fx, 0., cx],
        [0., fy, cy],
        [0., 0., 1.]
    ])  
    config['tsdf_voxel_size'] = tsdf_voxel_size  # in meter
    config['tsdf_trunc_margin'] = tsdf_trunc_margin # in meter
    config['pcd_voxel_size'] = pcd_voxel_size  # in meter

    return config          

def print_config(cfg):
    for key, value in cfg.items():
        if isinstance(value, np.ndarray):
            print(f"{key}:\n{value}")
        else:
            print(f"{key}: {value}")


if __name__ == '__main__':
    cfg = get_config("test")
    print_config(cfg)
