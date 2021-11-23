import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from parse import offlineParam
from render import offlineRender
from offlineRecon import offlineRecon


if __name__ == "__main__":
    # config_path = sys.argv[1]
    # output_dir = sys.argv[2]
    # data_format = sys.argv[3]
    output_dir = "/media/huijie/photos/datasets_bop/YCB_Progresslabeler/different_sensor/realsenseD435_Label/test_scene2/output"
    config_path = "/media/huijie/photos/datasets_bop/YCB_Progresslabeler/different_sensor/realsenseD435_Label/test_scene2/configuration.json"
    data_format = "ProgressLabeller"
    param = offlineParam(config_path)
    #["KF_forward_m2f", "KF_forward_f2f", "all"]
    interpolation_type = "all"
    offlineRecon(param, interpolation_type)
    offlineRender(param, output_dir, interpolation_type, pkg_type=data_format)

    # for i in range(2, 12):
    #     output_dir = "/media/huijie/photos/datasets_bop/YCB/D435/train_scene{}".format(i)
    #     config_path = "/media/huijie/photos/datasets_bop/YCB_Progresslabeler/different_sensor/realsenseD435_Label/train_scene{}/configuration.json".format(i)
    #     param = offlineParam(config_path)
    #     #["KF_forward_m2f", "KF_forward_f2f", "all"]
    #     interpolation_type = "all"
    #     offlineRecon(param, interpolation_type)
    #     offlineRender(param, output_dir, interpolation_type, pkg_type="YCBV")        
