import bpy
from bpy.props import StringProperty, EnumProperty, FloatProperty
from bpy.types import Operator
import numpy as np
from PIL import Image
import os
import time



from kernel.render import save_img
from kernel.geometry import plane_alignment, transform_from_plane, _pose2Rotation, _rotation2Pose, modelICP
from kernel.logging_utility import log_report
from kernel.loader import load_cam_img_depth, load_reconstruction_result, updateprojectname, removeworkspace



# class ViewImage(Operator):
#     """This appears in the tooltip of the operator and in the generated docs"""
#     bl_idname = "object_property.viewimage"  # important since its how bpy.ops.import_test.some_data is constructed
#     bl_label = "View Image"

#     def execute(self, context):
#         ### init to UV Editing frame

#         bpy.context.window.workspace = bpy.data.workspaces['UV Editing']
#         current_object = bpy.context.object.name

#         assert "type" in bpy.data.objects[current_object] and\
#                 bpy.data.objects[current_object]["type"] == "camera"

#         config_id = bpy.data.objects[current_object.split(":")[0] + ":Setting"]['config_id']

#         pair_image_name = bpy.data.objects[current_object]["rgb"].name
#         ## change the active image
#         bpy.context.scene.camera = bpy.data.objects[current_object]
#         for area in bpy.data.screens['UV Editing'].areas:
#             ## display image
#             if area.type == 'IMAGE_EDITOR':
#                 area.spaces.active.image = bpy.data.images[pair_image_name]

#         img_rgb = np.array(bpy.data.images[pair_image_name].pixels).reshape(bpy.context.scene.configuration[config_id].resY\
#                                                                             , bpy.context.scene.configuration[config_id].resX, 4)
#         ### for different view mode, change the alpha channel only
#         if bpy.context.scene.floatscreenproperty.viewimage_mode == 'Origin':
#             for area in bpy.data.screens['UV Editing'].areas:
#                 ## change camera view
#                 if area.type == 'VIEW_3D':
#                     area.spaces[0].region_3d.view_perspective = 'CAMERA'
#             img_rgb[:, :, 3] = bpy.context.scene.floatscreenproperty.segment_alpha
#             bpy.data.images[pair_image_name].pixels = img_rgb.ravel()

#         elif bpy.context.scene.floatscreenproperty.viewimage_mode == 'Segment':
#             # current_object = bpy.context.object.name
#             # assert "type" in bpy.data.objects[current_object] and\
#             #         bpy.data.objects[current_object]["type"] == "camera"
#             # pair_image_name = bpy.data.objects[current_object]["image"].name
#             # # ## change the active image
#             # bpy.context.scene.camera = bpy.data.objects[current_object]
            
#             # H = img_rgb.shape[0]
#             # W = img_rgb.shape[1]
#             # img_rgb = np.concatenate((img_rgb.astype(np.float16), np.ones((H, W, 1), dtype = np.float16)), axis = 2)
#             tmpimgname_render = './tmp/tmp.png'
#             # bpy.context.scene.render.engine = "CYCLES"
#             # bpy.context.preferences.addons[
#             #     "cycles"
#             # ].preferences.compute_device_type = "CUDA"
#             # bpy.context.scene.cycles.device = "GPU"
#             bpy.context.scene.render.filepath = tmpimgname_render
#             bpy.context.scene.render.image_settings.file_format='PNG' 
#             bpy.context.scene.render.image_settings.color_mode ='RGBA'
#             bpy.context.scene.render.film_transparent = True
#             bpy.context.scene.render.resolution_x = bpy.context.scene.configuration[config_id].resX
#             bpy.context.scene.render.resolution_y = bpy.context.scene.configuration[config_id].resY
#             res = bpy.ops.render.render(write_still = True)
#             img_render = np.array(Image.open(tmpimgname_render))
#             foreground_mask = img_render[:, :, 3] == 0
#             foreground_mask = foreground_mask[::-1, :]
#             img_rgb[foreground_mask, 3] = bpy.context.scene.floatscreenproperty.empty_alpha
#             img_rgb[~foreground_mask, 3] = bpy.context.scene.floatscreenproperty.segment_alpha
#             os.system('rm ' + tmpimgname_render)
#             bpy.data.images[pair_image_name].pixels = img_rgb.ravel()

#             #### save current image
#             # foreground_mask = img_render[:, :, 3] == 0
#             # img_origin = (img_rgb[::-1, :, :3]*255).astype(np.uint8)
#             # img_segment = img_origin.copy()
#             # img_segment[foreground_mask, :3] = 0
#             # save_img(img_render[:, :, :3], img_origin, img_segment, pair_image_name)

#         elif bpy.context.scene.floatscreenproperty.viewimage_mode == 'Segment(Inverse)':
#             # current_object = bpy.context.object.name
#             # assert "type" in bpy.data.objects[current_object] and\
#             #         bpy.data.objects[current_object]["type"] == "camera"
#             # pair_image_name = bpy.data.objects[current_object]["image"].name
#             # # ## change the active image
#             # bpy.context.scene.camera = bpy.data.objects[current_object]
            
#             # H = img_rgb.shape[0]
#             # W = img_rgb.shape[1]
#             # img_rgb = np.concatenate((img_rgb.astype(np.float16), np.ones((H, W, 1), dtype = np.float16)), axis = 2)
#             tmpimgname_render = './tmp/tmp.png'
#             bpy.context.scene.render.filepath = tmpimgname_render
#             bpy.context.scene.render.image_settings.file_format='PNG' 
#             bpy.context.scene.render.image_settings.color_mode ='RGBA'
#             bpy.context.scene.render.film_transparent = True
#             bpy.context.scene.render.resolution_x = bpy.context.scene.configuration[config_id].resX
#             bpy.context.scene.render.resolution_y = bpy.context.scene.configuration[config_id].resY
#             res = bpy.ops.render.render(write_still = True)
#             img_render = np.array(Image.open(tmpimgname_render))
#             foreground_mask = img_render[:, :, 3] == 0
#             foreground_mask = foreground_mask[::-1, :]
#             img_rgb[foreground_mask, 3] = bpy.context.scene.floatscreenproperty.segment_alpha
#             img_rgb[~foreground_mask, 3] = bpy.context.scene.floatscreenproperty.empty_alpha
#             os.system('rm ' + tmpimgname_render)
#             # img_rgb = img_rgb[::-1, :]
#             bpy.data.images[pair_image_name].pixels = img_rgb.ravel()


#         return {'FINISHED'}


class PlaneAlignment(Operator):
    """This appears in the tooltip of the operator and in the generated docs"""
    bl_idname = "object_property.planealignment"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "Plane Alignment"

    def execute(self, context):
        current_object = bpy.context.object.name
        workspace_name = current_object.split(":")[0]

        if not bpy.data.objects[workspace_name + ":" + 'reconstruction']["align"]:
            log_report(
                "INFO", "Starting calculate the plane function", None
            )      

            config_id = bpy.data.objects[workspace_name + ":Setting"]['config_id']
            

            [a, b, c, d], plane_center = plane_alignment(bpy.data.objects[workspace_name + ":reconstruction"]["path"], 
                                                         bpy.data.objects[workspace_name + ":reconstruction"]["scale"])

            log_report(
                "INFO", f"Plane equation: {a:.2f}x + {b:.2f}y + {c:.2f}z + {d:.2f} = 0", None
            )        
            if d < 0:
                trans  = transform_from_plane([-a, -b, -c, -d], plane_center)
            else:
                trans  = transform_from_plane([a, b, c, d], plane_center)
            log_report(
                "INFO", "Starting Transform the scene", None
            )   
            
            for obj in bpy.data.objects:
                if "type" in obj and (obj["type"] == "reconstruction" or obj["type"] == "camera")\
                    and obj.name.split(":")[0] == workspace_name:

                    origin_pose = [list(obj.location), list(obj.rotation_quaternion)]
                    origin_trans = _pose2Rotation(origin_pose)
                    after_align_trans = trans.dot(origin_trans)
                    after_align_pose = _rotation2Pose(after_align_trans)
                    obj.location = after_align_pose[0]
                    obj.rotation_quaternion = after_align_pose[1]/np.linalg.norm(after_align_pose[1])
            bpy.data.objects[workspace_name + ":" + 'reconstruction']["align"] = True

        else:
            log_report(
                "INFO", "Model has been aligned", None
            )                  
        return {'FINISHED'}

class ImportCamRGBDepth(Operator):
    """This appears in the tooltip of the operator and in the generated docs"""
    bl_idname = "object_property.importcamrgbdepth"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "Import RGB & Depth"

    def execute(self, context): 
        config_id = context.object["config_id"]
        packagepath = bpy.context.scene.configuration[context.object["config_id"]].datasrc
        files = os.listdir(packagepath)
        if "rgb" not in files or "depth" not in files:
            log_report(
                "Error", "either rgb or depth package is not in the datasrc", None
            )             
        else:   
            load_cam_img_depth(packagepath, config_id, camera_display_scale = 0.1)
        return {'FINISHED'}

class ImportReconResult(Operator):
    """This appears in the tooltip of the operator and in the generated docs"""
    bl_idname = "object_property.importreconresult"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "Import Reconstruction Result"

    def execute(self, context): 
        scene = context.scene
        config_id = context.object["config_id"]
        datasrc = bpy.context.scene.configuration[context.object["config_id"]].datasrc
        filepath = bpy.context.scene.configuration[context.object["config_id"]].reconstructionsrc
        load_reconstruction_result(filepath = filepath, 
                                    pointcloudscale = scene.loadreconparas.pointcloud_scale, 
                                    datasrc = datasrc,
                                    config_id = config_id,
                                    camera_display_scale = scene.loadreconparas.camera_display_scale,
                                    CAMPOSE_INVERSE = scene.loadreconparas.CAMPOSE_INVERSE
                                    )
        return {'FINISHED'}

    def invoke(self, context, event):
        filepath = bpy.context.scene.configuration[context.object["config_id"]].reconstructionsrc
        files = os.listdir(filepath)
        if "campose.txt" not in files:
            log_report(
                "ERROR", "campose.txt file not in your reconstrution package, \
                    please reconstruction first or change another package", None
            )               
        elif "fused.ply" not in files:
            log_report(
                "ERROR", "fused.ply file not in your reconstrution package, \
                    please reconstruction first or change another package", None
            )   
        else:
            return context.window_manager.invoke_props_dialog(self, width = 400)

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        config_id = bpy.context.object["config_id"]
        config = scene.configuration[config_id]
        layout.label(text="Set Reconstruction Loading Parameters:")
        row = layout.row() 
        row.prop(scene.loadreconparas, "pointcloud_scale")
        row = layout.row() 
        row.prop(scene.loadreconparas, "camera_display_scale")
        row = layout.row() 
        row.prop(scene.loadreconparas, "CAMPOSE_INVERSE")       
            

class LoadRecon(bpy.types.PropertyGroup):
    # The properties for this class which is referenced as an 'entry' below.
    pointcloud_scale: bpy.props.FloatProperty(name="Point Cloud Display Scale", 
                                            description="Scale for display reconstruction point cloud", 
                                            default=1.00, 
                                            min=0.00, 
                                            max=1.00, 
                                            step=2, 
                                            precision=2)  
    camera_display_scale: bpy.props.FloatProperty(name="Cameras Display Scale", 
                                            description="Scale for cameras", 
                                            default=0.1, 
                                            min=0.0, 
                                            max=1.0, 
                                            step=2, 
                                            precision=2)      
    CAMPOSE_INVERSE: bpy.props.BoolProperty(
        name="Inverse Camera Pose",
        description="Need when given poses are from world to camera",
        default=False,
    )       
  


class WorkspaceRename(Operator):
    """This appears in the tooltip of the operator and in the generated docs"""
    bl_idname = "object_property.workspacerename"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "Rename"

    def execute(self, context): 
        updateprojectname()
        return {'FINISHED'}

class RemoveWorkspace(Operator):
    """This appears in the tooltip of the operator and in the generated docs"""
    bl_idname = "object_property.removeworkspace"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "Remove Current Workspace"

    def execute(self, context):
        assert context.object['type'] == 'setting'
        config_id = context.object['config_id']
        config = bpy.context.scene.configuration[config_id]
        name = config.projectname
        removeworkspace(name)
        return {'FINISHED'}  

class ModelICP(Operator):
    """This appears in the tooltip of the operator and in the generated docs"""
    bl_idname = "object_property.modelicp"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "Model Alignment"

    def execute(self, context):
        assert context.object['type'] == 'model'
        obj = context.active_object
        name = obj.name.split(":")[0]
        config_id =  bpy.data.objects[name + ":Setting"]['config_id']
        config = bpy.context.scene.configuration[config_id]
        

        model_vertices = np.array([list(obj.matrix_world @ v.co) for v in obj.data.vertices])
        if name + ":reconstruction" not in bpy.data.objects:
            log_report(
                "Error", "You should upload the reconstruction result first", None
            )     
            return {'FINISHED'}
        else:
            scene = bpy.data.objects[name + ":reconstruction"]
            scene_vertices = np.array(scene["particle_coords"])
            rot = np.array(scene.matrix_world)
            scene_vertices_rotated = (rot[:3, :3].dot(scene_vertices.T) + rot[:3, [3]]).T
            trans_obj_icp = modelICP(scene_vertices_rotated, model_vertices)
            current_pose = [list(obj.location), list(obj.rotation_quaternion)]
            current_trans = _pose2Rotation(current_pose)
            mew_trans = trans_obj_icp @ current_trans
            new_pose = _rotation2Pose(mew_trans)
            obj.location = new_pose[0]
            obj.rotation_quaternion = new_pose[1]
        return {'FINISHED'}      

def register():
    # bpy.utils.register_class(ViewImage)
    bpy.utils.register_class(PlaneAlignment)
    bpy.utils.register_class(ImportCamRGBDepth)
    bpy.utils.register_class(ImportReconResult)
    bpy.utils.register_class(LoadRecon)
    bpy.types.Scene.loadreconparas = bpy.props.PointerProperty(type=LoadRecon)   

    

    bpy.utils.register_class(ModelICP)

    bpy.utils.register_class(WorkspaceRename)
    bpy.utils.register_class(RemoveWorkspace)

def unregister():
    # bpy.utils.unregister_class(ViewImage)
    
    bpy.utils.unregister_class(PlaneAlignment)
    bpy.utils.unregister_class(ImportCamRGBDepth)
    bpy.utils.unregister_class(ImportReconResult)
    bpy.utils.unregister_class(LoadRecon)
    bpy.utils.unregister_class(ModelICP)
    
    bpy.utils.unregister_class(WorkspaceRename)
    bpy.utils.unregister_class(RemoveWorkspace)