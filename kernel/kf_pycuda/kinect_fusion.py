import os
import pickle
import copy
import json
import open3d as o3d
import numpy as np
# import cv2
# import matplotlib.pyplot as plt
import scipy.linalg as la
from scipy.io import loadmat
from tqdm import tqdm
from tqdm.contrib import tzip

import pycuda.autoinit
import pycuda.driver as cuda
from pycuda import gpuarray

from kernel.kf_pycuda.tsdf_lib import TSDFVolume
from kernel.kf_pycuda.cuda_kernels import source_module
from kernel.kf_pycuda import utils
from kernel.kf_pycuda.config import get_config, print_config

from kernel.geometry import _rotation2Pose

# open3d version should be at least 0.11.0
reg = o3d.pipelines.registration

class KinectFusion:

    def __init__(self, cfg: dict = None):
        self.cfg = cfg
        self.tsdf_volume = None
        self.init_transformation = None
        self.transformation = None
        self.prev_pcd = None
        self.cam_poses = []   # store the tracking results

    def initialize_tsdf_volume(self, color_im, depth_im, visualize=False):
        pcd = utils.create_pcd(depth_im, self.cfg['cam_intr'], color_im)
        plane_frame, inlier_ratio = utils.plane_detection_ransac(pcd, inlier_thresh=0.005, early_stop_thresh=0.6,
                                                                 visualize=visualize)
        
        cam_pose = la.inv(plane_frame)
        transformed_pcd = copy.deepcopy(pcd).transform(la.inv(plane_frame))
        transformed_pts = np.asarray(transformed_pcd.points)

        vol_bnds = np.zeros((3, 2), dtype=np.float32)
        vol_bnds[:, 0] = transformed_pts.min(0)
        vol_bnds[:, 1] = transformed_pts.max(0)
        print(vol_bnds)
        # vol_bnds[2] = [-0.01, 0.25]

        if visualize:
            vol_box = o3d.geometry.OrientedBoundingBox()
            vol_box.center = vol_bnds.mean(1)
            vol_box.extent = vol_bnds[:, 1] - vol_bnds[:, 0]
            o3d.visualization.draw_geometries([vol_box, transformed_pcd])

        self.init_transformation = plane_frame.copy()
        self.transformation = plane_frame.copy()
        self.tsdf_volume = TSDFVolume(vol_bnds=vol_bnds,
                                      voxel_size=self.cfg['tsdf_voxel_size'],
                                      trunc_margin=self.cfg['tsdf_trunc_margin'])
        self.tsdf_volume.integrate(color_im, depth_im, self.cfg['cam_intr'], cam_pose)
        self.prev_pcd = pcd
        self.cam_poses.append(cam_pose)

    @staticmethod
    def multiscale_icp(src: o3d.geometry.PointCloud,
                       tgt: o3d.geometry.PointCloud,
                       voxel_size_list: list, 
                       max_iter_list: list,
                       init: np.ndarray = np.eye(4),
                       inverse: bool = False):

        if len(src.points) > len(tgt.points):
            return KinectFusion.multiscale_icp(tgt, src, voxel_size_list, max_iter_list,
                                               init=la.inv(init), inverse=True)

        transformation = init
        result_icp = None
        for i, (voxel_size, max_iter) in enumerate(zip(voxel_size_list, max_iter_list)):
            src_down = src.voxel_down_sample(voxel_size)
            tgt_down = tgt.voxel_down_sample(voxel_size)

            src_down.estimate_normals(o3d.geometry.KDTreeSearchParamHybrid(radius=voxel_size*3, max_nn=30))
            tgt_down.estimate_normals(o3d.geometry.KDTreeSearchParamHybrid(radius=voxel_size*3, max_nn=30))

            estimation_method = reg.TransformationEstimationPointToPlane()
            # estimation_method = reg.TransformationEstimationPointToPoint()
            result_icp = reg.registration_icp(
                src_down, tgt_down, max_correspondence_distance=voxel_size*3,
                init=transformation,
                estimation_method=estimation_method,
                criteria=reg.ICPConvergenceCriteria(max_iteration=max_iter))
            transformation = result_icp.transformation

        if inverse and result_icp is not None:
            result_icp.transformation = la.inv(result_icp.transformation)

        return result_icp

    def update_pose_using_icp(self, depth_im):
        curr_pcd = utils.create_pcd(depth_im, self.cfg['cam_intr'])

        # #------------------------------ frame to frame ICP (open loop) ------------------------------
        # open_loop_fitness = 0
        # result_icp = self.multiscale_icp(self.prev_pcd, curr_pcd,
        #                                  voxel_size_list=[0.025, 0.01, 0.005],
        #                                  max_iter_list=[10, 10, 10], init=np.eye(4))
        # if result_icp is not None:
        #     self.transformation = result_icp.transformation @ self.transformation

        #------------------------------ model to frame ICP (closed loop) ------------------------------
        cam_pose = la.inv(self.transformation)
        rendered_depth, _ = self.tsdf_volume.ray_casting(self.cfg['im_w'], self.cfg['im_h'], self.cfg['cam_intr'], 
                                                         cam_pose, to_host=True)
        rendered_pcd = utils.create_pcd(rendered_depth, self.cfg['cam_intr'])

        result_icp = self.multiscale_icp(rendered_pcd,
                                         curr_pcd,
                                         voxel_size_list=[0.025, 0.01],
                                         max_iter_list=[5, 10])
        if result_icp is None:
            return False

        self.transformation = result_icp.transformation @ self.transformation
        self.prev_observation = curr_pcd
        return True

    def update(self, color_im, depth_im):
        if self.tsdf_volume is None:
            self.initialize_tsdf_volume(color_im, depth_im, visualize=False)
            return True

        success = self.update_pose_using_icp(depth_im)
        if success:
            cam_pose = la.inv(self.transformation)
            self.cam_poses.append(cam_pose)
            self.tsdf_volume.integrate(color_im, depth_im, self.cfg['cam_intr'], cam_pose, weight=1)
        else:
            self.cam_poses.append(np.eye(4))

    def save(self, output_folder, prefix_list):
        # if os.path.exists(output_folder):
        #     key = input(f"{output_folder} exists. Do you want to overwrite? (y/n)")
        #     while key.lower() not in ['y', 'n']:
        #         key = input(f"{output_folder} exists. Do you want to overwrite? (y/n)")
        #     if key.lower() == 'n':
        #         return
        # else:
        #     os.makedirs(output_folder)

        cam_poses = np.stack(self.cam_poses)
        camout = open(os.path.join(output_folder, "campose.txt"), "w+")
        camout.writelines("# IMAGE_ID, QW, QX, QY, QZ, TX, TY, TZ, CAMERA_ID, NAME\n")
        camout.writelines("\n")
        for index, rot, prefix in zip(range(1, cam_poses.shape[0] + 1), cam_poses, prefix_list):
            pose = _rotation2Pose(rot)
            line = str(index) + " " + str(pose[1][0]) + " " + str(pose[1][1])\
                    + " " + str(pose[1][2]) + " " + str(pose[1][3])\
                    + " " + str(pose[0][0]) + " " + str(pose[0][1]) + " " + str(pose[0][2])\
                    + " " + "1" + " " + prefix + "_rgb.png\n"
            camout.writelines(line)
        camout.close()
        # np.savez_compressed(os.path.join(output_folder, 'kf_results.npz'),
        #     cam_poses=cam_poses,
        #     **self.cfg, 
        # )
        # self.tsdf_volume.save(os.path.join(output_folder, 'tsdf.npz'))
        surface = self.tsdf_volume.get_surface_cloud_marching_cubes(voxel_size=0.005)
        o3d.io.write_point_cloud(os.path.join(output_folder, 'fused.ply'), surface)
        print(f"Results have been saved to {output_folder}.")


# if __name__ == '__main__':
#     ycb_data_folder = os.path.expanduser('/home/huijiezhang/Dense_Reconstruction/YCB_dataset')

#     for video_id in range(2):
#         video_folder = os.path.join(ycb_data_folder, 'data', str(video_id).zfill(4))
#         prefix_list = sorted([i.split('-')[0] for i in os.listdir(video_folder) if i.endswith('mat')])

#         color_im_list = []
#         depth_im_list = []
#         meta_list = []
#         box_list = []

#         if video_id <= 59:
#             config = get_config(camera='uw')
#         else:
#             config = get_config(camera='cmu')
        
#         print_config(config)
#         print("reading images and meta files...")
#         for idx, prefix in enumerate(tqdm(prefix_list)):
#             color_im_path = os.path.join(video_folder, f'{prefix}-color.png')
#             depth_im_path = os.path.join(video_folder, f'{prefix}-depth.png')
#             meta_path = os.path.join(video_folder, f"{prefix}-meta.mat")
#             # box_path = os.path.join(video_folder, f"{prefix}-box.txt")

#             meta = loadmat(meta_path)
#             depth_scale = meta['factor_depth']
#             color_im = cv2.cvtColor(cv2.imread(color_im_path), cv2.COLOR_BGR2RGB)
#             depth_im = cv2.imread(depth_im_path, cv2.IMREAD_UNCHANGED).astype(np.float32) / depth_scale
#             depth_im[depth_im > 1.5] = 0  # depth truncation

#             color_im_list.append(color_im)
#             depth_im_list.append(depth_im)
#             meta_list.append(meta)
            
#         kf = KinectFusion(cfg=config)
#         for idx, (color_im, depth_im) in enumerate(tzip(color_im_list, depth_im_list)):
#             kf.update(color_im, depth_im)
#         output_dir = os.path.join(ycb_data_folder, 'recon', str(video_id).zfill(4))
#         kf.save(output_dir)
