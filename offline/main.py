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
    
    object_label = {
        "cham_cup_correct" :1, 
        "short_cup_correct" : 2, 
        "starbucks" : 3,
        "tall_cup_correct": 4,
        "wine_cup_correct": 5,
    }
    # object_label = { # according to 21 objects in ycbv
    # "002_master_chef_can" : 1,
    # "003_cracker_box" : 2,
    # "004_sugar_box" : 3,
    # "005_tomato_soup_can" : 4,
    # "006_mustard_bottle" : 5,
    # "007_tuna_fish_can" : 6,
    # "009_gelatin_box" : 8,
    # "010_potted_meat_can" : 9,
    # "025_mug" : 14,
    # "040_large_marker" : 18
    # }
    # param = offlineParam(config_path, object_label= None)
    param = offlineParam(config_path, object_label= object_label)
    interpolation_type = "all"
    offlineRecon(param, interpolation_type)
    offlineRender(param, output_dir, interpolation_type, pkg_type=data_format)    

