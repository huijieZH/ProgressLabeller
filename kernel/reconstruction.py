from kernel.kf_pycuda.config import set_config, print_config
from kernel.kf_pycuda.kinect_fusion import KinectFusion
from tqdm import tqdm
from PIL import Image
import os
import numpy as np


def KinectfusionRecon(
    data_folder, save_folder, prefix_list,
    resX, resY, fx, fy, cx, cy, 
    tsdf_voxel_size, tsdf_trunc_margin, pcd_voxel_size, depth_scale, depth_ignore, 
    DISPLAY, frame_per_display,
    ):
    depth_path = os.path.join(data_folder, "depth")
    color_path = os.path.join(data_folder, "rgb")

    config = set_config(resX, resY, fx, fy, cx, cy, tsdf_voxel_size, tsdf_trunc_margin, pcd_voxel_size)
    kf = KinectFusion(cfg=config)
    print_config(config)


    for idx, prefix in enumerate(tqdm(prefix_list)):
        color_im_path = os.path.join(color_path, prefix + '_rgb.png')
        depth_im_path = os.path.join(depth_path, prefix + '_depth.png')
        
        color_im = np.asarray(Image.open(color_im_path))
        depth_im = np.asarray(Image.open(depth_im_path)).astype(np.float32) * depth_scale
        depth_im[depth_im > depth_ignore] = 0

        kf.update(color_im, depth_im)
        # if (idx + 1) % 500 == 0:
        #     kf.save(save_folder)
    kf.save(save_folder, prefix_list)