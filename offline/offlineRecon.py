import os
import numpy as np
from kernel.geometry import _pose2Rotation
from kernel.utility import _select_sample_files

class offlineRecon:
    def __init__(self, param) -> None:
        self.param = param
        self.datasrc = self.param.datasrc
        self.reconstructionsrc = self.param.reconstructionsrc
        self.wholemap = {} ## mapping the keyframe pair to frame under estimation
        self.wholecam = {} ## mapping all frames to their poses
        self.keyposes = {} ## mapping all key frames to their poses
        self._parsecamfile()
        self._applytrans2cam()
        self._parsewholeimg()
        self._interpolation(type = "KF_forward")
        pass
    
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
            self.wholecam[img] = {}
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

    def _applytrans2cam(self):
        Axis_align = np.array([[1, 0, 0, 0],
                              [0, -1, 0, 0],
                              [0, 0, -1, 0],
                              [0, 0, 0, 1],]
            )
        scale = self.param.recon["scale"]
        trans = self.param.recon["trans"]
        for cam in self.keyposes:
            origin_pose = self.keyposes[cam]
            origin_pose[:3, 3] = origin_pose[:3, 3] * scale
            origin_pose = np.linalg.inv(origin_pose).dot(Axis_align)
            self.keyposes[cam] = trans.dot(origin_pose)
    
    def _interpolation(self, type):
        assert type in ["KF_forward"]
        for keypair in self.wholemap:
            if type == "KF_forward":
                self._interpolationKFForward(keypair, self.wholemap[keypair])

    def _interpolationKFForward(self, keypair, imglists):
        try: 
            from kernel.reconstruction import KinectfusionRecon
        except:
            print(
                "Error", "Please successfully install pycuda", None
            )        
        else:  
            pass 