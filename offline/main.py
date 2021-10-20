import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from parse import offlineParam
from render import offlineRender
from offlineRecon import offlineRecon


if __name__ == "__main__":
    param = offlineParam("/home/huijie/Desktop/orb_slam_test/configuration.json")
    #["KF_forward_m2f", "KF_forward_f2f", "all"]
    interpolation_type = "all"
    offlineRecon(param, interpolation_type)
    offlineRender(param, "output_" + interpolation_type, interpolation_type)
