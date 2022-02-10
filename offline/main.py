import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from parse import offlineParam
from render import offlineRender
from offlineRecon import offlineRecon


if __name__ == "__main__":
    config_path = '/media/cxt/PortableSSD/trans_data/515_realsense/set5/scene1/configuration_cxt.json' # sys.argv[1]
    output_dir = sys.argv[2]
    data_format = 'YCBV' # sys.argv[3]
    print(sys.argv)
    # object_label = {
    #     "cham_cup_correct" :1, 
    #     "short_cup_correct" : 2, 
    #     "starbucks" : 3,
    #     "tall_cup_correct": 4,
    #     "wine_cup_correct": 5,
    # }
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
    object_label = {
        "beaker_1": 1,
        "dropper_1": 2,
        "dropper_2": 3,
        "flask_1": 4,
        "funnel_1": 5,
        "graduated_cylinder_1": 6,
        "graduated_cylinder_2": 7,
        "pan_1": 8,
        "pan_2": 9,
        "pan_3": 10,
        "reagent_bottle_1": 11,
        "reagent_bottle_2": 12,
        "stick_1": 13,
        "syringe_1": 14,
        "bottle_1": 15,
        "bottle_2": 16,
        "bottle_3": 17,
        "bottle_4": 18,
        "bottle_5": 19,
        "bowl_1": 20,
        "bowl_2": 21,
        "bowl_3": 22,
        "bowl_4": 23,
        "bowl_5": 24,
        "bowl_6": 25,
        "container_1": 26,
        "container_2": 27,
        "container_3": 28,
        "container_4": 29,
        "container_5": 30,
        "fork_1": 31,
        "knife_1": 32,
        "knife_2": 33,
        "mug_1": 34,
        "pitcher_1": 35,
        "plate_1": 36,
        "plate_2": 37,
        "spoon_1": 38,
        "spoon_2": 39,
        "water_cup_1": 40,
        "water_cup_2": 41,
        "water_cup_3": 42,
        "water_cup_4": 43,
        "water_cup_5": 44,
        "water_cup_6": 45,
        "water_cup_7": 46,
        "water_cup_8": 47,
        "water_cup_9": 48,
        "water_cup_10": 49,
        "water_cup_11": 50,
        "water_cup_12": 51,
        "water_cup_13": 52,
        "water_cup_14": 53,
        "wine_cup_1": 54,
        "wine_cup_2": 55,
        "wine_cup_3": 56,
        "wine_cup_4": 57,
        "wine_cup_5": 58,
        "wine_cup_6": 59,
        "wine_cup_7": 60,
        "wine_cup_8": 61,
    }

    # param = offlineParam(config_path, object_label= None)

    param = offlineParam(config_path, object_label= object_label)
    interpolation_type = "all"
    offlineRecon(param, interpolation_type)
    offlineRender(param, output_dir, interpolation_type, pkg_type=data_format)    
    # data_format = "YCBV"
    # for i in range(1, 12):
    #     config_path = f"/media/huijie/photos/datasets_bop/YCB_Progresslabeler/different_sensor/primesense_labelfusion_Label/train_scene{i}/configuration.json"
    #     output_dir=f"/media/huijie/PortableSSD/labelfusion_ycbformat/scene{i}"
    #     param = offlineParam(config_path, object_label= object_label)
    #     interpolation_type = "all"
    #     offlineRecon(param, interpolation_type)
    #     offlineRender(param, output_dir, interpolation_type, pkg_type=data_format)  
    
    # i = 3
    # config_path = f"/media/huijie/HUIJIE/dataset/Transparentdataset/realsense_data_trans/realsense_data/l515_apriltag/label_scene{i}/configuration.json"
    # output_dir=f"/media/huijie/HUIJIE/dataset/Transparentdataset/realsense_data_trans/realsense_data/l515_apriltag/outputdataset/val/scene{i}"
    # param = offlineParam(config_path, object_label= object_label)
    # interpolation_type = "all"
    # offlineRecon(param, interpolation_type)
    # offlineRender(param, output_dir, interpolation_type, pkg_type=data_format)  