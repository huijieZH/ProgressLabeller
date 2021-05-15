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


def register():
    bpy.utils.register_class(Configuration)
    bpy.types.Scene.configuration = bpy.props.PointerProperty(type=Configuration)  

def unregister():
    bpy.utils.unregister_class(Configuration)