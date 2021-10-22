import os
import numpy as np
from tqdm import tqdm
from PIL import Image
from kernel.geometry import _pose2Rotation, _rotation2Pose
from kernel.utility import _select_sample_files

class offlineRecon:
    def __init__(self, param, interpolation_type = "KF_forward") -> None:
        print("Start offline reconstruction interpolation")
        self.param = param
        self.datasrc = self.param.datasrc
        self.reconstructionsrc = self.param.reconstructionsrc
        self.CAM_INVERSE = self.param.camera["inverse_pose"]
        self.wholemap = {} ## mapping the keyframe pair to frame under estimation
        self.wholecam = {} ## mapping all frames to their poses
        self.keyposes = {} ## mapping all key frames to their poses
        self._parsecamfile()
        self._applytrans2cam()
        self._parsewholeimg()
        self.rgb_path = os.path.join(self.datasrc, "rgb")
        self.depth_path = os.path.join(self.datasrc, "depth")
        self.depth_scale = self.param.data['depth_scale']
        self._interpolation(type = interpolation_type)
        self._savecampose("campose_all_{0}.txt".format(interpolation_type))
    
    def _parsewholeimg(self):
        imagefiles = os.listdir(os.path.join(self.datasrc, "rgb"))
        imagefiles.sort()
        keyframe = sorted(self.keyposes.keys())
        index_whole = 0
        index_key = 0
        while(index_whole < len(imagefiles)):
            current_image_name = imagefiles[index_whole]
            if (current_image_name in keyframe) and (index_key + 1 < len(keyframe)):
                key_pair = (keyframe[index_key], keyframe[index_key+1])
                self.wholemap[key_pair] = []
                index_key += 1
            elif (current_image_name in keyframe) and (index_key + 1 >= len(keyframe)):
                pass
            else:
                self.wholemap[key_pair].append(current_image_name)
            index_whole += 1
        for img in imagefiles:
            self.wholecam[img] = np.empty((0, 0))
            if img in self.keyposes:
                self.wholecam[img] = self.keyposes[img]

    def _parsecamfile(self):
        f = open(os.path.join(self.reconstructionsrc, "campose.txt"))
        lines = f.readlines()
        for l in lines:
            datas = l.split(" ")
            if datas[0].isnumeric():
                self.keyposes[datas[-1].split("\n")[0]] = _pose2Rotation([[float(datas[5]), float(datas[6]), float(datas[7])],\
                                                        [float(datas[1]), float(datas[2]), float(datas[3]), float(datas[4])]])
                pass

    def _applytrans2cam(self):
        # Axis_align = np.array([[1, 0, 0, 0],
        #                       [0, -1, 0, 0],
        #                       [0, 0, -1, 0],
        #                       [0, 0, 0, 1],]
        #     )
        scale = self.param.recon["scale"]
        trans = self.param.recon["trans"]
        for cam in self.keyposes:
            origin_pose = self.keyposes[cam]
            origin_pose[:3, 3] = origin_pose[:3, 3] * scale
            # origin_pose = np.linalg.inv(origin_pose).dot(Axis_align)
            if self.CAM_INVERSE:
                origin_pose = np.linalg.inv(origin_pose)
            self.keyposes[cam] = trans.dot(origin_pose)
    
    def _interpolation(self, type):
        assert type in ["KF_forward_m2f", "KF_forward_f2f", "all"]
        if type == "all":
            ## don't need do anything
            pass
        if type == "KF_forward_m2f":
            try: 
                from kernel.kf_pycuda.kinect_fusion import KinectFusion
                from kernel.kf_pycuda.config import set_config
            except:
                print(
                    "Error", "Please successfully install pycuda", None
                )        
            else:  
                
                config = set_config(resX = self.param.camera["resolution"][0], 
                    resY = self.param.camera["resolution"][0], 
                    fx = self.param.camera["intrinsic"][0, 0], 
                    fy = self.param.camera["intrinsic"][1, 1], 
                    cx = self.param.camera["intrinsic"][0, 2], 
                    cy = self.param.camera["intrinsic"][1, 2], 
                    tsdf_voxel_size = 0.0025, 
                    tsdf_trunc_margin = 0.015, 
                    pcd_voxel_size = 0.005) 
                self.kf = KinectFusion(cfg=config)
                for keypair in tqdm(self.wholemap):
                    self._interpolationKFForwardM2F(keypair, self.wholemap[keypair])
                for idx, prefix in enumerate(self.wholecam.keys()):
                    if idx < len(self.kf.cam_poses):
                        self.wholecam[prefix] = self.kf.cam_poses[idx]
        if type == "KF_forward_f2f":
            try: 
                from kernel.kf_pycuda.kinect_fusion import KinectFusion
                from kernel.kf_pycuda.config import set_config
            except:
                print(
                    "Error", "Please successfully install pycuda", None
                )        
            else:  
                
                config = set_config(resX = self.param.camera["resolution"][0], 
                    resY = self.param.camera["resolution"][0], 
                    fx = self.param.camera["intrinsic"][0, 0], 
                    fy = self.param.camera["intrinsic"][1, 1], 
                    cx = self.param.camera["intrinsic"][0, 2], 
                    cy = self.param.camera["intrinsic"][1, 2], 
                    tsdf_voxel_size = 0.0025, 
                    tsdf_trunc_margin = 0.015, 
                    pcd_voxel_size = 0.005) 
                self.kf = KinectFusion(cfg=config)
                for keypair in tqdm(self.wholemap):
                    self._interpolationKFForwardF2F(keypair, self.wholemap[keypair])
                for idx, prefix in enumerate(self.wholecam.keys()):
                    if idx < len(self.kf.cam_poses):
                        self.wholecam[prefix] = self.kf.cam_poses[idx]

    def _interpolationKFForwardM2F(self, keypair, imglists):
        for imgname in [keypair[0]] + imglists:
            color_im_path = os.path.join(self.rgb_path, imgname)
            depth_im_path = os.path.join(self.depth_path, imgname)
            color_im = np.array(Image.open(color_im_path))
            depth_im = np.array(Image.open(depth_im_path)).astype(np.float32) * self.depth_scale
            depth_im[depth_im > 1.5] = 0
            if imgname == keypair[0]:
                self.kf.interpolation_update(color_im, depth_im, self.keyposes[keypair[0]])
            else:
                self.kf.interpolation_update(color_im, depth_im, None)

    def _interpolationKFForwardF2F(self, keypair, imglists):
        for imgname in [keypair[0]] + imglists[:int(len(imglists)/2)] + (imglists[int(len(imglists)/2):] + [keypair[1]])[::-1]:
            color_im_path = os.path.join(self.rgb_path, imgname)
            depth_im_path = os.path.join(self.depth_path, imgname)
            color_im = np.array(Image.open(color_im_path))
            depth_im = np.array(Image.open(depth_im_path)).astype(np.float32) * self.depth_scale
            depth_im[depth_im > 1.5] = 0
            if imgname == keypair[0]:
                self.kf.F2FPoseEstimation(color_im, depth_im, self.keyposes[keypair[0]])
            else:
                pose = self.kf.F2FPoseEstimation(color_im, depth_im, None)
                self.wholecam[imgname] = pose
              
            
    
    def _savecampose(self, campose_filename):
        with open(os.path.join(self.reconstructionsrc, campose_filename), 'w') as f:
            f.write('# IMAGE_ID, QW, QX, QY, QZ, TX, TY, TZ, CAMERA_ID, NAME\n')
            f.write('\n')
            for idx, cam in enumerate(self.wholecam.keys()):
                if self.wholecam[cam].any():
                    pose = _rotation2Pose(self.wholecam[cam])
                    f.write(str(idx) + " {0} {1} {2} {3} {4} {5} {6} 1 ".format(*pose[1], *pose[0])+ cam + "\n")

