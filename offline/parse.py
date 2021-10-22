
import json
import yaml
import numpy as np
import os


from kernel.utility import _transstring2trans
from kernel.geometry import _pose2Rotation, _rotation2Pose

class offlineParam:
    def __init__(self, config_path) -> None:
        f = open(config_path)
        configuration = json.load(f)
        self.config = configuration
        self.dir = os.path.dirname(config_path)
        self.parsecamera()
        self.parseenv()
        self.parsereconpara()
        self.parsedatapara()
        self.parseobj()


    def parsecamera(self):
        self.camera = {}
        self.camera["resolution"] = self.config["camera"]["resolution"]
        self.camera["intrinsic"] = np.array(self.config["camera"]["intrinsic"])
        self.camera["inverse_pose"] = self.config["camera"]["inverse_pose"]

    def parseenv(self):
        self.modelsrc = self.config["environment"]["modelsrc"]
        self.modelposesrc = self.config["environment"]["modelposesrc"]
        self.reconstructionsrc = self.config["environment"]["reconstructionsrc"]
        self.datasrc = self.config["environment"]["datasrc"]


    def parsereconpara(self):
        self.recon = {}
        self.recon["scale"] = self.config['reconstruction']['scale']
        self.recon["trans"] = _transstring2trans(self.config['reconstruction']['recon_trans'])

    def parsedatapara(self):
        self.data = {}
        self.data['sample_rate'] = self.config['data']['sample_rate']
        self.data['depth_scale'] = self.config['data']['depth_scale']
    
    def parseobj(self):
        self.objs = {}
        f = open(os.path.join(self.modelposesrc, "label_pose.yaml"))
        poses = yaml.safe_load(f)
        model_dir = os.listdir(self.modelsrc)
        for objname in poses:
            if objname in model_dir:
                self.objs[objname] = {}
                self.objs[objname]['type'] = poses[objname]['type']
                self.objs[objname]['trans'] = _pose2Rotation(poses[objname]['pose'])

