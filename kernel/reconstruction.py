from kernel.kf_pycuda.config import set_config, print_config
from kernel.kf_pycuda.kinect_fusion import KinectFusion
from offline.parse import offlineParam
from kernel.geometry import _pose2Rotation
from tqdm import tqdm
from PIL import Image
import os
import numpy as np
import open3d as o3d


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
        color_im_path = os.path.join(color_path, prefix + '.png')
        depth_im_path = os.path.join(depth_path, prefix + '.png')
        
        color_im = np.asarray(Image.open(color_im_path))
        depth_im = np.asarray(Image.open(depth_im_path)).astype(np.float32) * depth_scale
        depth_im[depth_im > depth_ignore] = 0

        kf.update(color_im, depth_im)
        # if (idx + 1) % 500 == 0:
        #     kf.save(save_folder)
    kf.save(save_folder, prefix_list)

def poseFusion(
    param_path,
    tsdf_voxel_size, tsdf_trunc_margin, pcd_voxel_size, depth_ignore,
    ):
    def parsecamfile(param):
        param.camposes = {}
        f = open(os.path.join(param.reconstructionsrc, "campose.txt"))
        lines = f.readlines()
        for l in lines:
            datas = l.split(" ")
            if datas[0].isnumeric():
                param.camposes[datas[-1].split("\n")[0]] = _pose2Rotation([[float(datas[5]), float(datas[6]), float(datas[7])],\
                                                        [float(datas[1]), float(datas[2]), float(datas[3]), float(datas[4])]])

    def applytrans2cam(param):
        scale = param.recon["scale"]
        trans = param.recon["trans"]
        for cam in param.camposes:
            origin_pose = param.camposes[cam]
            origin_pose[:3, 3] = origin_pose[:3, 3] * scale
            # origin_pose = np.linalg.inv(origin_pose).dot(Axis_align)
            if param.camera["inverse_pose"]:
                origin_pose = np.linalg.inv(origin_pose)
            param.camposes[cam] = trans.dot(origin_pose)  
    
    param = offlineParam(param_path)
    parsecamfile(param)
    applytrans2cam(param)
    depth_path = os.path.join(param.datasrc, "depth")
    rgb_path = os.path.join(param.datasrc, "rgb")

    config = set_config(param.camera["resolution"][0], param.camera["resolution"][1], 
                        param.camera["intrinsic"][0, 0], param.camera["intrinsic"][1, 1],
                        param.camera["intrinsic"][0, 2], param.camera["intrinsic"][1, 2], 
                        tsdf_voxel_size = tsdf_voxel_size, tsdf_trunc_margin = tsdf_trunc_margin, pcd_voxel_size = pcd_voxel_size)
    depth_ignore = depth_ignore
    kf = KinectFusion(cfg=config)
    for frame in tqdm(param.camposes):
        rgb = np.array(Image.open(os.path.join(rgb_path, frame)))
        depth = np.array(Image.open(os.path.join(depth_path, frame))).astype(np.float32) * param.data['depth_scale']

        depth[depth > depth_ignore] = 0
        kf.update(rgb, depth, param.camposes[frame])
    surface = kf.tsdf_volume.get_surface_cloud_marching_cubes(voxel_size=pcd_voxel_size)
    o3d.io.write_point_cloud(os.path.join(param.reconstructionsrc, 'depthfused.ply'), surface)
    


