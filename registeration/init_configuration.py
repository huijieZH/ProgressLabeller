import bpy
import json
import os
import numpy as np

config_json_dict = {
    'projectname': [['projectname']],
    'modelsrc': [['environment', 'modelsrc']],
    'modelposesrc': [['environment', 'modelposesrc']],
    'reconstructionsrc':[['environment', 'reconstructionsrc']] ,
    'datasrc': [['environment', 'datasrc']],
    'resX':[['camera', 'resolution'], ['0']],  
    'resY':[['camera', 'resolution'], ['1']], 
    'fx':[['camera', 'intrinsic'], ['0', '0']],  
    'fy':[['camera', 'intrinsic'], ['1', '1']],   
    'cx':[['camera', 'intrinsic'], ['0', '2']],    
    'cy':[['camera', 'intrinsic'], ['1', '2']],    
    'lens':[['camera', 'lens']]
}

def decode_dict(configuration, code):
    value = configuration
    for item in code[0]:
        value = value[item]
    if len(code) == 2:
        for item in code[1]:
            value = value[int(item)]
    return value

def encode_dict(configuration):
    output_dict = {
        'projectname': configuration.projectname,
        'environment': {
            'modelsrc':configuration.modelsrc,
            "modelposesrc": configuration.modelposesrc,
            "reconstructionsrc":configuration.reconstructionsrc,
            "datasrc": configuration.datasrc,           
        },
        'camera':{
        "resolution": [configuration.resX, configuration.resY],
        "intrinsic": [[configuration.fx, 0, configuration.cx],
                      [0, configuration.fy, configuration.cy],
                      [0, 0, 1]],
        "lens": configuration.lens, 
        }
    }
    return output_dict


class config(bpy.types.PropertyGroup):
    # The properties for this class which is referenced as an 'entry' below.

    projectname: bpy.props.StringProperty(name = "projectname")
    modelsrc: bpy.props.StringProperty(name = "modelsrc", 
                subtype = "DIR_PATH")
    modelposesrc: bpy.props.StringProperty(name = "modelposesrc", 
                subtype = "DIR_PATH")   
    reconstructionsrc: bpy.props.StringProperty(name = "reconstructionsrc", 
                subtype = "DIR_PATH") 
    datasrc: bpy.props.StringProperty(name = "datasrc", 
                subtype = "DIR_PATH") 

    resX: bpy.props.IntProperty(name = "resX")
    resY: bpy.props.IntProperty(name = "resY")
    fx: bpy.props.FloatProperty(name="fx", description="camera intrinsic fx.", 
        min=0.00, max=1500.00, step=10, precision=2)    
    fy: bpy.props.FloatProperty(name="fy", description="camera intrinsic fy.", 
        min=0.00, max=1500.00, step=10, precision=2)   
    cx: bpy.props.FloatProperty(name="cx", description="camera intrinsic cx.", 
        min=0.00, max=1000.00, step=10, precision=2)    
    cy: bpy.props.FloatProperty(name="cy", description="camera intrinsic cy.", 
        min=0.00, max=1000.00, step=10, precision=2)
    lens: bpy.props.FloatProperty(name="lens", description="camera lens length", 
        min=0.000, max=1.000, step=3, precision=3)

    # plane_trans: np.array([[1, 0, 0, 0],
    #                        [0, 1, 0, 0],
    #                        [0, 0, 1, 0],
    #                        [0, 0, 0, 1]])        




def register():
    bpy.utils.register_class(config)
    bpy.types.Scene.configuration = bpy.props.CollectionProperty(type=config)  

def unregister():
    bpy.utils.unregister_class(config)

