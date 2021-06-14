import bpy
from registeration.init_configuration import config_json_dict, encode_dict
import json
import os
import yaml

def configuration_export(config, path):
    configuration = encode_dict(config)
    with open(path, "w") as f:
        json.dump(configuration, f, indent = True)


def objectposes_export(name, path):
    pose = {}
    for obj in bpy.data.objects:
        if obj["type"] == "model" and obj.name.split(":")[0] == name:
            pose[obj.name.split(":")[1]] = {'pose': [list(obj.location), list(obj.rotation_quaternion)]}
    with open(path, 'w') as file:
        documents = yaml.dump(pose, file)