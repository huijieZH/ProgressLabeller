import os
from tqdm import tqdm
import cv2
import numpy as np
if __name__ == '__main__':
    import sys
    sys.path.append("/home/huijiezhang/ProgressLabeller")
from kernel.kf_pycuda.kinect_fusion import KinectFusion
from kernel.kf_pycuda.config import get_config, print_config



if __name__ == '__main__':
    data_folder = "/home/huijiezhang/Desktop/ProgressLabellerData/data/"
    save_folder = "/home/huijiezhang/Desktop/ProgressLabellerTest/ReconKinectFusion/"
    depth_path = os.path.join(data_folder, "depth")
    color_path = os.path.join(data_folder, "rgb")

    prefix_list = sorted([i.split('_')[0] for i in os.listdir(depth_path) if i.endswith('png')])
    
    # color_im_list = []
    # depth_im_list = []

    depth_scale = 0.00025

    print("Fusion......")

    config = get_config(camera='umich')
    print_config(config)

    kf = KinectFusion(cfg=config)

    for idx, prefix in enumerate(tqdm(prefix_list)):
        color_im_path = os.path.join(color_path, prefix + '_rgb.png')
        depth_im_path = os.path.join(depth_path, prefix + '_depth.png')
        
        color_im = cv2.cvtColor(cv2.imread(color_im_path), cv2.COLOR_BGR2RGB)
        depth_im = cv2.imread(depth_im_path, cv2.IMREAD_UNCHANGED).astype(np.float32) * depth_scale
        depth_im[depth_im > 1.5] = 0

        kf.update(color_im, depth_im)
        if (idx + 1) % 500 == 0:
            kf.save(save_folder)
    kf.save(save_folder)
