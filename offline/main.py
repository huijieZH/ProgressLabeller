import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from parse import offlineParam
from render import offlineRender
from offlineRecon import offlineRecon


if __name__ == "__main__":
    # config_path = sys.argv[1]
    # output_dir = sys.argv[2]
    output_dir = "/home/huijie/Desktop/test"
    config_path = "/media/huijie/photos/datasets_bop/YCB_Progresslabeler/different_sensor/realsenseL515_Label/train_scene1/configuration.json"
    param = offlineParam(config_path)
    #["KF_forward_m2f", "KF_forward_f2f", "all"]
    interpolation_type = "all"
    offlineRecon(param, interpolation_type)
    offlineRender(param, output_dir, interpolation_type, pkg_type="BOP")
