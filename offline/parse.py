
import json
import numpy as np
from kernel.utility import _transstring2trans

class offlineParam:
    def __init__(self, config_path) -> None:
        f = open(config_path)
        configuration = json.load(f)
        self.config = configuration
        self.parsecamera()
        self.parseenv()
        self.parsereconpara()
        self.parsedatapara()


    def parsecamera(self):
        self.camera = {}
        self.camera["resolution"] = self.config["camera"]["resolution"]
        self.camera["intrinsic"] = np.array(self.config["camera"]["intrinsic"])


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
        self.data.sample_scale = self.config['data']['sample_scale']


