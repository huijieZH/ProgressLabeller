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
        self.cam_poses = []  
    
    def initialize_tsdf_volume(self, color_im, depth_im, pose=None, visualize=False):
        if pose is not None:
            pcd = utils.create_pcd(depth_im, self.cfg['cam_intr'], color_im, depth_trunc = self.cfg['tsdf_trunc_margin']*10000)
            
            transformed_pcd = copy.deepcopy(pcd).transform(pose)
            transformed_pts = np.asarray(transformed_pcd.points)
            
            vol_bnds = np.zeros((3, 2), dtype=np.float32)
            vol_bnds[:, 0] = np.mean(transformed_pts, axis = 0) - np.abs(transformed_pts - np.mean(transformed_pts, axis = 0)).max(0)*1.2
            vol_bnds[:, 1] = np.mean(transformed_pts, axis = 0) + np.abs(transformed_pts - np.mean(transformed_pts, axis = 0)).max(0)*1.2
            self.init_transformation = la.inv(pose).copy()
            self.transformation = la.inv(pose).copy()
            self.tsdf_volume = TSDFVolume(vol_bnds=vol_bnds,
                                        voxel_size=self.cfg['tsdf_voxel_size'],
                                        trunc_margin=self.cfg['tsdf_trunc_margin'])
            self.tsdf_volume.integrate(color_im, depth_im, self.cfg['cam_intr'], pose)
            self.prev_pcd = pcd
            self.cam_poses.append(pose)
        else:
            pcd = utils.create_pcd(depth_im, self.cfg['cam_intr'], color_im)
            plane_frame, inlier_ratio = utils.plane_detection_ransac(pcd, inlier_thresh=0.005, early_stop_thresh=0.6,
                                                                    visualize=visualize)
            
            cam_pose = la.inv(plane_frame)
            transformed_pcd = copy.deepcopy(pcd).transform(la.inv(plane_frame))
            transformed_pts = np.asarray(transformed_pcd.points)

            vol_bnds = np.zeros((3, 2), dtype=np.float32)
            vol_bnds[:, 0] = np.mean(transformed_pts, axis = 0) - np.abs(transformed_pts - np.mean(transformed_pts, axis = 0)).max(0)*1.2
            vol_bnds[:, 1] = np.mean(transformed_pts, axis = 0) + np.abs(transformed_pts - np.mean(transformed_pts, axis = 0)).max(0)*1.2

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

    
    
    def update(self, color_im, depth_im, pose = None):
        if pose is not None:
            ## update with pose
            if self.tsdf_volume is None:
                self.initialize_tsdf_volume(color_im, depth_im, pose, visualize=False)
                return True

            self.tsdf_volume.integrate(color_im, depth_im, self.cfg['cam_intr'], pose, weight=1)
        else:
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
     

    def interpolation_update(self, color_im, depth_im, accurate_pose = None):
        if accurate_pose is None:
            self.update(color_im, depth_im)
        else:
            if self.tsdf_volume is None:
                assert(accurate_pose is not None)
                self.initialize_tsdf_volume_withaccuratepose(color_im, depth_im, accurate_pose, None)
                return True
            else:
                cam_pose = accurate_pose
                curr_pcd = utils.create_pcd(depth_im, self.cfg['cam_intr'])
                self.transformation = la.inv(cam_pose)
                self.prev_observation = curr_pcd                
                self.cam_poses.append(cam_pose)
                self.tsdf_volume.integrate(color_im, depth_im, self.cfg['cam_intr'], cam_pose, weight=1)            
    

    def initialize_tsdf_volume_withaccuratepose(self, color_im, depth_im, accurate_pose = None, visualize=False):
        pcd = utils.create_pcd(depth_im, self.cfg['cam_intr'], color_im)
        
        cam_pose = accurate_pose
        transformed_pcd = copy.deepcopy(pcd).transform(cam_pose)
        transformed_pts = np.asarray(transformed_pcd.points)

        vol_bnds = np.zeros((3, 2), dtype=np.float32)
        vol_bnds[:, 0] = transformed_pts.min(0)
        vol_bnds[:, 1] = transformed_pts.max(0)


        if visualize:
            vol_box = o3d.geometry.OrientedBoundingBox()
            vol_box.center = vol_bnds.mean(1)
            vol_box.extent = vol_bnds[:, 1] - vol_bnds[:, 0]
            o3d.visualization.draw_geometries([vol_box, transformed_pcd])

        self.init_transformation = la.inv(cam_pose.copy())
        self.transformation = la.inv(cam_pose.copy())
        self.tsdf_volume = TSDFVolume(vol_bnds=vol_bnds,
                                      voxel_size=self.cfg['tsdf_voxel_size'],
                                      trunc_margin=self.cfg['tsdf_trunc_margin'])
        self.tsdf_volume.integrate(color_im, depth_im, self.cfg['cam_intr'], cam_pose)
        self.prev_pcd = pcd
        self.cam_poses.append(cam_pose)

    def F2FPoseEstimation(self, color_im, depth_im, accurate_pose = None):
        if accurate_pose is None:
            curr_pcd = utils.create_pcd(depth_im, self.cfg['cam_intr'])
            # #------------------------------ frame to frame ICP (open loop) ------------------------------
            result_icp = self.multiscale_icp(self.prev_pcd, curr_pcd,
                                             voxel_size_list=[0.025, 0.01, 0.005],
                                             max_iter_list=[10, 10, 10], init=np.eye(4))
            if result_icp is not None:
                self.transformation = result_icp.transformation @ self.transformation
            self.prev_pcd = curr_pcd
            cam_pose = la.inv(self.transformation)
            return cam_pose
        else:
            cam_pose = accurate_pose
            curr_pcd = utils.create_pcd(depth_im, self.cfg['cam_intr'])
            self.transformation = la.inv(cam_pose)
            self.prev_pcd = curr_pcd   
            return True


    def save(self, output_folder, prefix_list):

        cam_poses = np.stack(self.cam_poses)
        camout = open(os.path.join(output_folder, "campose.txt"), "w+")
        camout.writelines("# IMAGE_ID, QW, QX, QY, QZ, TX, TY, TZ, CAMERA_ID, NAME\n")
        camout.writelines("\n")
        for index, rot, prefix in zip(range(1, cam_poses.shape[0] + 1), cam_poses, prefix_list):
            pose = _rotation2Pose(rot)
            line = str(index) + " " + str(pose[1][0]) + " " + str(pose[1][1])\
                    + " " + str(pose[1][2]) + " " + str(pose[1][3])\
                    + " " + str(pose[0][0]) + " " + str(pose[0][1]) + " " + str(pose[0][2])\
                    + " " + "1" + " " + prefix + ".png\n"
            camout.writelines(line)
        camout.close()
        surface = self.tsdf_volume.get_surface_cloud_marching_cubes(voxel_size=0.005)
        o3d.io.write_point_cloud(os.path.join(output_folder, 'fused.ply'), surface)
        print(f"Results have been saved to {output_folder}.")

