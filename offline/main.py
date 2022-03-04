import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from parse import offlineParam
from render import offlineRender
from offlineRecon import offlineRecon

# transparent
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
    "mug_2": 35,
    "pitcher_1": 36,
    "plate_1": 37,
    "plate_2": 38,
    "spoon_1": 39,
    "spoon_2": 40,
    "water_cup_1": 41,
    "water_cup_2": 42,
    "water_cup_3": 43,
    "water_cup_4": 44,
    "water_cup_5": 45,
    "water_cup_6": 46,
    "water_cup_7": 47,
    "water_cup_8": 48,
    "water_cup_9": 49,
    "water_cup_10": 50,
    "water_cup_11": 51,
    "water_cup_12": 52,
    "water_cup_13": 53,
    "water_cup_14": 54,
    "wine_cup_1": 55,
    "wine_cup_2": 56,
    "wine_cup_3": 57,
    "wine_cup_4": 58,
    "wine_cup_5": 59,
    "wine_cup_6": 60,
    "wine_cup_7": 61,
    "wine_cup_8": 62,
    "wine_cup_9": 63,
    "round_table": 64,
    "003_cracker_box": 200, # distractor objects from YCB and HOPE datasets
    "005_tomato_soup_can": 201,
    "006_mustard_bottle": 202,
    "007_tuna_fish_can": 203,
    "009_gelatin_box": 204,
    "BBQSauce": 205,
    "Mayo": 206,
    "OrangeJuice": 207,
}

# affordance-cup-spoon
# object_label = {
#     'blue_cup_dark': 1,
#     'bottle_coke': 2,
#     'detergent': 3,
#     'mug_bline': 4,
#     'plastic_bowl_large': 5,
#     'plastic_shovel_askew': 6,
#     'sclupt_mug': 7,
#     'spoon_metal_2': 8,
#     'white_mug': 9,
#     'blue_cup_tall': 10,
#     'bottle_eco': 11,
#     'downy': 12,
#     'mug_darkgrey': 13,
#     'plastic_bowl': 14,
#     'plastic_shovel': 15,
#     'sculpt_mug': 16,
#     'spoon_pink': 17,
#     'white_mug_tall': 18,
#     'blue_cup_whiteinner': 19,
#     'bottle_zico': 20,
#     'fish_can': 21,
#     'mustard_bottle': 22,
#     'plastic_grey_cup_tall': 23,
#     'plastic_spoon': 24,
#     'spoon_ice': 25,
#     'spoon_white': 26,
#     'wooden_spoon': 27,
#     'blue_mug': 28,
#     'bowl_red': 29,
#     'mug_51': 30,
#     'pan_grey': 31,
#     'plastic_mug': 32,
#     'red_mug':33,
#     'spoon_metal_1': 34,
#     'tomato_can': 35,
#     'yellow_cup': 36,
# }

if __name__ == "__main__":
    # root_path = '/media/cxt/PortableSSD/trans_data/515_realsense/'
    # output_path = '/media/cxt/PortableSSD/trans_data/output'
    data_format = 'Transparent_YCBV' # sys.argv[3]
    # data_format = 'ProgressLabeller' # sys.argv[3]
    # reshape_640_480 = True
    set_scene_list = [
        'set9_scene3', 'set9_scene4', 'set9_scene7', 'set9_scene8', 'set9_scene9', 'set9_scene10'
    ]
    # set_scene_list = [
    #     # 'set1_scene1', 'set1_scene2', 'set1_scene3', 'set1_scene4', 'set1_scene5',
    #     # 'set2_scene1', 'set2_scene6', 'set2_scene3', 'set2_scene4', 'set2_scene5',
    #     # 'set3_scene1', 'set3_scene3', 'set3_scene4', 'set3_scene8', 'set3_scene11',
    #     # 'set4_scene1', 'set4_scene2', 'set4_scene3', 'set4_scene4', 'set4_scene5', 'set4_scene6',
    #     # 'set5_scene1', 'set5_scene2', 'set5_scene3', 'set5_scene4', 'set5_scene5', 'set5_scene6',
    #     # 'set6_scene1', 'set6_scene2', 'set6_scene3', 'set6_scene4', 'set6_scene5', 'set6_scene6',
    #     # 'set7_scene1', 'set7_scene2', 'set7_scene3', 'set7_scene4', 'set7_scene5', 
    #     'set7_scene6',
    #     'set8_scene1', 'set8_scene2', 'set8_scene3', 'set8_scene4', 'set8_scene5', 'set8_scene6',
    # ]
    # set_scene_list = ['1', '2', '3', '4']
    # blank table setting
    root_path = '/media/cxt/216F2E9C45E9E56E/'
    output_path = '/media/cxt/216F2E9C45E9E56E/set9_output/'
    reshape_640_480 = True
    for set_scene in set_scene_list:
        print(set_scene)
        path = os.path.join(root_path, set_scene.split('_')[0], set_scene.split('_')[1])
        config_path = path + '/configuration.json' # sys.argv[1]
        output_dir = os.path.join(output_path, set_scene.split('_')[0], set_scene.split('_')[1])
        os.system('rm -rf {}/*'.format(output_dir))
        param = offlineParam(config_path, object_label=object_label)
        if reshape_640_480: # from 1280*720 to 640*480, first cut left and right (1280-640*3/2)/2=160 pixels, then do a 3->2 rescale
            int_mat = param.camera['intrinsic']
            ratio = 2 / 3
            fx, fy, cx, cy = int_mat[0, 0], int_mat[1, 1], int_mat[0, 2], int_mat[1, 2]
            int_mat[0, 0], int_mat[1, 1], int_mat[0, 2], int_mat[1, 2] = fx * ratio, fy * ratio, (cx - 160) * ratio, cy * ratio
            param.camera['resolution'] = [640, 480]
        interpolation_type = "all"
        offlineRecon(param, interpolation_type)
        offlineRender(param, output_dir, interpolation_type, pkg_type=data_format)

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