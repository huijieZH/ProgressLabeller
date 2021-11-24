import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from parse import offlineParam
from render import offlineRender
from offlineRecon import offlineRecon


if __name__ == "__main__":
    config_path = sys.argv[1]
    output_dir = sys.argv[2]
    data_format = sys.argv[3]
    param = offlineParam(config_path)
    interpolation_type = "all"
    offlineRecon(param, interpolation_type)
    offlineRender(param, output_dir, interpolation_type, pkg_type=data_format)    

