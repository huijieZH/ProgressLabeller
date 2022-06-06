import sys
import os
import json
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from parse import offlineParam
from render import offlineRender
from offlineRecon import offlineRecon

if __name__ == "__main__":
    config_path = sys.argv[1]
    output_dir = sys.argv[2]
    data_format = sys.argv[3]
    object_label_file = sys.argv[4] 
    with open(object_label_file) as objlabelf:
        object_label = json.load(objlabelf)
    for obj in object_label:
        object_label[obj] = int(object_label[obj])  
    param = offlineParam(config_path, object_label= object_label)
    interpolation_type = "all"
    offlineRecon(param, interpolation_type)
    offlineRender(param, output_dir, interpolation_type, pkg_type=data_format)  