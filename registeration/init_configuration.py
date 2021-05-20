import bpy
import json
import os
import numpy as np

class config(bpy.types.PropertyGroup):
    # The properties for this class which is referenced as an 'entry' below.

    modelsrc: bpy.props.StringProperty(name = "modelsrc", 
                subtype = "DIR_PATH")
    modelposesrc: bpy.props.StringProperty(name = "modelposesrc", 
                subtype = "DIR_PATH")   
    reconstructionsrc: bpy.props.StringProperty(name = "modelposesrc", 
                subtype = "DIR_PATH") 
    imagesrc: bpy.props.StringProperty(name = "imagesrc", 
                subtype = "DIR_PATH") 

    resX: bpy.props.IntProperty(name = "resX")
    resY: bpy.props.IntProperty(name = "resX")
    fx: bpy.props.FloatProperty(name="fx", description="camera intrinsic fx.", 
        min=0.00, max=1500.00, step=3, precision=2)    
    fy: bpy.props.FloatProperty(name="fy", description="camera intrinsic fy.", 
        min=0.00, max=1500.00, step=3, precision=2)   
    px: bpy.props.FloatProperty(name="px", description="camera intrinsic px.", 
        min=0.00, max=1000.00, step=3, precision=2)    
    py: bpy.props.FloatProperty(name="py", description="camera intrinsic py.", 
        min=0.00, max=1000.00, step=3, precision=2)
    lens: bpy.props.FloatProperty(name="lens", description="camera lens length", 
        min=0.00, max=100.00, step=3, precision=2)

    # plane_trans: np.array([[1, 0, 0, 0],
    #                        [0, 1, 0, 0],
    #                        [0, 0, 1, 0],
    #                        [0, 0, 0, 1]])        


def register():
    bpy.utils.register_class(config)
    bpy.types.Scene.configuration = bpy.props.PointerProperty(type=config)  

def unregister():
    bpy.utils.unregister_class(config)