import os
from tqdm import tqdm
import cv2
import numpy as np
if __name__ == '__main__':
    import sys
    sys.path.append("/home/huijie/research/progresslabeller/ProgressLabeller")
from kernel.kf_pycuda.kinect_fusion import KinectFusion
from kernel.kf_pycuda.config import get_config, print_config
import open3d as o3d

def visualize(kf):
    surface = kf.tsdf_volume.get_surface_cloud_marching_cubes(voxel_size=0.005)
    vis = o3d.visualization.Visualizer()
    vis.create_window()
    vis.add_geometry(surface)
    vis.run()
    vis.destroy_window()    

if __name__ == '__main__':
    data_folder = "/home/huijie/research/progresslabeller/data/NeualDataNew/515_lying_1"
    save_folder = "/home/huijie/Desktop/testKinectFusion"
    depth_path = os.path.join(data_folder, "depth")
    color_path = os.path.join(data_folder, "rgb")

    prefix_list = sorted([i.split('.')[0] for i in os.listdir(color_path) if i.endswith('png') ])
    
    # color_im_list = []
    # depth_im_list = []

    depth_scale = 0.00025

    print("Fusion......")

    config = get_config(camera='umich')
    print_config(config)

    kf = KinectFusion(cfg=config)

    for idx, prefix in enumerate(tqdm(prefix_list)):
        color_im_path = os.path.join(color_path, prefix + '.png')
        depth_im_path = os.path.join(depth_path, prefix + '.png')
        
        color_im = cv2.cvtColor(cv2.imread(color_im_path), cv2.COLOR_BGR2RGB)
        depth_im = cv2.imread(depth_im_path, cv2.IMREAD_UNCHANGED).astype(np.float32) * depth_scale
        # depth_im[depth_im > 1.5] = 0

        kf.update(color_im, depth_im)
        # if (idx + 1) % 500 == 0:
        #     kf.save(save_folder)
    visualize(kf)
    kf.save(save_folder)
