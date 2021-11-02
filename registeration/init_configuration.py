import bpy
import json
import os
import numpy as np
from mathutils import Vector
from kernel.geometry import _pose2Rotation, _rotation2Pose
from kernel.blender_utility import _is_progresslabeller_object, _get_allrgb_insameworkspace, _get_configuration, _get_obj_insameworkspace

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
    'lens':[['camera', 'lens']],
    'inverse_pose':[['camera', 'inverse_pose']],
    'reconstructionscale': [['reconstruction', 'scale']],
    'cameradisplayscale': [['reconstruction', 'cameradisplayscale']],
    'recon_trans': [['reconstruction', 'recon_trans']],
    'sample_rate': [['data', 'sample_rate']],
    'depth_scale': [['data', 'depth_scale']],
    'depth_ignore': [['data', 'depth_ignore']],

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
        "inverse_pose": configuration.inverse_pose,
        "lens": configuration.lens, 
        },
        'reconstruction':{
        "scale": configuration.reconstructionscale,
        "cameradisplayscale": configuration.cameradisplayscale,
        "recon_trans": configuration.recon_trans
        },
        'data':{
        "sample_rate": configuration.sample_rate,
        "depth_scale": configuration.depth_scale,
        "depth_ignore": configuration.depth_ignore,
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
        min=0.000, max=1000.000, step=3, precision=3, default = 30)

    inverse_pose: bpy.props.BoolProperty(
        name="Inverse Camera Pose",
        description="Need when given poses are from world to camera",
        default=False,
    )       
    
    recon_trans: bpy.props.StringProperty(name = "recon_trans", default = "1,0,0,0;0,1,0,0;0,0,1,0;0,0,0,1;")
    
    sample_rate: bpy.props.FloatProperty(name="Sample Rate", 
                                        description="Sample rate for loading in blender for visualize", 
                                        default=0.10, 
                                        min=0.00, 
                                        max=1.00, 
                                        step=0.1, 
                                        precision=2)
    
    def depthInfoUpdate(self, context):
        if context.object != None and _is_progresslabeller_object(context.object):
            _, config = _get_configuration(context.object)
            im_list = _get_allrgb_insameworkspace(config)
            for im in im_list:
                im["UPDATEALPHA"] = True
                        
    depth_scale: bpy.props.FloatProperty(name="Depth Scale", 
                                        description="Scale for depth image", 
                                        default=0.00025, 
                                        min=0.000000, 
                                        max=10.000000, 
                                        step=6, 
                                        precision=6,
                                        update=depthInfoUpdate)  

    depth_ignore: bpy.props.FloatProperty(name="Depth Ignore (m)", 
                                        description="Use depth as a filter for rgb", 
                                        default=1.5, 
                                        min=0.0, 
                                        max=10000.0, 
                                        step=3, 
                                        precision=3,
                                        update=depthInfoUpdate)  

    cameradisplayscale: bpy.props.FloatProperty(name="reconstruction scale", 
                                        description="reconstruction scale for the fused.ply", 
                                        default=0.05, 
                                        min=0.00, 
                                        max=1000.00, 
                                        step=0.01, 
                                        precision=2)   



    def scale_update(self, context):
        
        if hasattr(context, "object") \
            and context.object \
            and "type" in context.object \
            and context.object["type"] == "reconstruction":

            recon = context.object
            workspacename = recon.name.split(":")[0]
            old_scale = recon["scale"]
            new_scale = self.reconstructionscale
            alignT = np.asarray(recon["alignT"])

            self.cameradisplayscale = self.cameradisplayscale * new_scale/old_scale

            for obj in bpy.data.objects:
                if obj.name.startswith(workspacename):
                    if obj["type"] == "reconstruction":
                        obj.scale = Vector((new_scale, new_scale, new_scale))
                    if obj["type"] == "camera":
                        current_location = np.asarray(obj.location).reshape((3, 1))
                        origin_location = np.linalg.inv(alignT[:3, :3]).dot(current_location - alignT[:3, [3]])/old_scale
                        scaled_location = origin_location * new_scale
                        current_scaled_location = (alignT[:3, :3].dot(scaled_location) + alignT[:3, [3]]).reshape((3, ))
                        obj.location = Vector(current_scaled_location)

            recons = _get_obj_insameworkspace(recon, ["reconstruction"])

            for obj in recons:
                obj["scale"] = self.reconstructionscale   

    
    reconstructionscale: bpy.props.FloatProperty(name="reconstruction scale", description="scale of the reconstruction model", 
        min=0.01, max=1000.000, step=3, precision=3, default = 1.000, 
        update=scale_update)

    def cameradisplayscale_update(self, context):
        
        if hasattr(context, "object") \
            and context.object \
            and "type" in context.object \
            and context.object["type"] == "reconstruction":
            recon = context.object
            workspacename = recon.name.split(":")[0]
            for obj in bpy.data.objects:
                if obj.name.startswith(workspacename):
                    if obj["type"] == "camera":
                        obj.data.display_size = self.cameradisplayscale
                    

    cameradisplayscale: bpy.props.FloatProperty(name="camera display scale", description="scale of the camera display size", 
        min=0.01, max=1.000, step=0.1, precision=3, default = 0.1, 
        update=cameradisplayscale_update)



def register():
    bpy.utils.register_class(config)
    bpy.types.Scene.configuration = bpy.props.CollectionProperty(type=config)  

def unregister():
    bpy.utils.unregister_class(config)

