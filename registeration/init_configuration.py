import bpy
import json
import os

class Configuration(bpy.types.PropertyGroup):
    # The properties for this class which is referenced as an 'entry' below.
    if os.path.exists('configuration.json'):
        with open('configuration.json') as file:
            configuration = json.load(file)
        modelsrc: bpy.props.StringProperty(name = "modelsrc", 
                    subtype = "DIR_PATH", default= configuration['environment']['modelsrc'])
        modelposesrc: bpy.props.StringProperty(name = "modelposesrc", 
                    subtype = "DIR_PATH", default= configuration['environment']['modelposesrc'])   
        reconstructionsrc: bpy.props.StringProperty(name = "modelposesrc", 
                    subtype = "DIR_PATH", default= configuration['environment']['reconstructionsrc']) 
        imagesrc: bpy.props.StringProperty(name = "imagesrc", 
                    subtype = "DIR_PATH", default= configuration['environment']['imagesrc']) 

        resX: bpy.props.IntProperty(name = "resX",  default= configuration['camera']['resolution'][0])
        resY: bpy.props.IntProperty(name = "resX",  default= configuration['camera']['resolution'][1])
        fx: bpy.props.FloatProperty(name="fx", description="camera intrinsic fx.", 
            default=configuration['camera']['intrinsic'][0][0], min=0.00, max=1500.00, step=3, precision=2)    
        fy: bpy.props.FloatProperty(name="fy", description="camera intrinsic fy.", 
            default=configuration['camera']['intrinsic'][1][1], min=0.00, max=1500.00, step=3, precision=2)   
        px: bpy.props.FloatProperty(name="px", description="camera intrinsic px.", 
            default=configuration['camera']['intrinsic'][0][2], min=0.00, max=1000.00, step=3, precision=2)    
        py: bpy.props.FloatProperty(name="py", description="camera intrinsic py.", 
            default=configuration['camera']['intrinsic'][1][2], min=0.00, max=1000.00, step=3, precision=2)
        lens: bpy.props.FloatProperty(name="lens", description="camera lens length", 
            default=configuration['camera']['lens'], min=0.00, max=100.00, step=3, precision=2)


def register():
    bpy.utils.register_class(Configuration)
    bpy.types.Scene.configuration = bpy.props.PointerProperty(type=Configuration)  

def unregister():
    bpy.utils.unregister_class(Configuration)