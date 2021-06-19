import bpy
from bpy.props import StringProperty, EnumProperty, FloatProperty, IntProperty
from bpy.types import Operator
import numpy as np
from PIL import Image
import os
import time
import open3d as o3d
import tqdm



from kernel.render import save_img
from kernel.geometry import plane_alignment, transform_from_plane, _pose2Rotation, _rotation2Pose, modelICP, globalRegisteration, align_scale
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
    """Using RANSAC to detect the plane and align it"""
    bl_idname = "object_property.planealignment"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "Plane Alignment"

    def execute(self, context):
        current_object = bpy.context.object.name
        workspace_name = current_object.split(":")[0]

        log_report(
            "INFO", "Starting calculate the plane function", None
        )      

        config_id = bpy.data.objects[workspace_name + ":Setting"]['config_id']
        

        [a, b, c, d], plane_center = plane_alignment(bpy.data.objects[workspace_name + ":reconstruction"]["path"], 
                                                     bpy.data.objects[workspace_name + ":reconstruction"]["scale"],
                                                     np.array(bpy.data.objects[workspace_name + ":reconstruction"]["alignT"]),
                                                     bpy.context.scene.planalignmentparas.threshold,
                                                     bpy.context.scene.planalignmentparas.n,
                                                     bpy.context.scene.planalignmentparas.iteration)

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
        bpy.data.objects[workspace_name + ":" + 'reconstruction']["alignT"] = trans.tolist()
        
        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width = 400)

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        layout.label(text="Set Plane Alignment (ICP) Parameters:")
        box = layout.box() 
        row = box.row()
        row.prop(scene.planalignmentparas, "threshold") 
        row = box.row()
        row.prop(scene.planalignmentparas, "n") 
        row = box.row()
        row.prop(scene.planalignmentparas, "iteration") 

class PlaneAlignmentConfig(bpy.types.PropertyGroup):
    # The properties for this class which is referenced as an 'entry' below.
    threshold: bpy.props.FloatProperty(name="Inlier Threshold", 
                                        description="Inlier threshold for points aligned to plane", 
                                        default=0.01, 
                                        min=0.001, 
                                        max=1.000, 
                                        step=0.001, 
                                        precision=3)

    n: bpy.props.IntProperty(name="Fit Number", 
                                description="Numbers for fitting a plane", 
                                default=3, 
                                min=3, 
                                max=10, 
                                step=1)
    iteration: bpy.props.IntProperty(name="Fit Iteration", 
                                        description="ICP Iteration", 
                                        default=1000, 
                                        min=10, 
                                        max=10000, 
                                        step=100)


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
        config = bpy.context.scene.configuration[context.object["config_id"]]
        datasrc = config.datasrc
        filepath = config.reconstructionsrc
        scene.loadreconparas.pointcloud_scale = config.reconstructionscale

        if not scene.loadreconparas.AUTOALIGN:
            load_reconstruction_result(filepath = filepath, 
                                        pointcloudscale = scene.loadreconparas.pointcloud_scale, 
                                        datasrc = datasrc,
                                        config_id = config_id,
                                        camera_display_scale = scene.loadreconparas.camera_display_scale,
                                        CAMPOSE_INVERSE = scene.loadreconparas.CAMPOSE_INVERSE
                                        )
        else:
            log_report(
            "INFO", "Starting aligning the point cloud", None
            )     
            camera_rgb_file = os.path.join(filepath, "campose.txt")
            reconstruction_path = os.path.join(filepath, "fused.ply")
            depth_path = os.path.join(datasrc, "depth")

            pcd = o3d.io.read_point_cloud(reconstruction_path)
            plane_model, inliers = pcd.segment_plane(distance_threshold=scene.planalignmentparas.threshold,
                                                     ransac_n=scene.planalignmentparas.n,
                                                     num_iterations=scene.planalignmentparas.iteration)
            plane_pcd = pcd.select_by_index(inliers)
            points = np.asarray(plane_pcd.points)
            file = open(camera_rgb_file, "r")
            lines = file.read().split("\n")
            scales = []
            intrinsic = np.array([
                [config.fx, 0, config.cx],
                [0, config.fy, config.cy],
                [0, 0, 1],
            ])
            
            for l in tqdm.tqdm(lines):
                data = l.split(" ")
                if data[0].isnumeric():
                    framename = data[-1]
                    perfix = framename.split("_")[0]
                    pose = [[float(data[5]), float(data[6]), float(data[7])], 
                            [float(data[1]), float(data[2]), float(data[3]), float(data[4])]]
                    depthfile = os.path.join(depth_path, perfix + "_depth.png")
                    if os.path.exists(depthfile):

                        SUCCESS, scale = align_scale(points, pose, depthfile,
                                            scene.loadreconparas.depth_scale,
                                            intrinsic, config.resX, config.resY)
                        if SUCCESS:
                            scales.append(scale)
            if len(scales) != 0:
                scale = np.mean(scales)
                log_report(
                "INFO", "The aligning scale is {0}".format(scale), None
                )   
            else:
                scale = 1.0
                log_report(
                "ERROR", "Failed finding the scale", None
                )  
                
            config.reconstructionscale = scale
            load_reconstruction_result(filepath = filepath, 
                                        pointcloudscale = scale, 
                                        datasrc = datasrc,
                                        config_id = config_id,
                                        camera_display_scale = scene.loadreconparas.camera_display_scale,
                                        CAMPOSE_INVERSE = scene.loadreconparas.CAMPOSE_INVERSE
                                        )
            
        return {'FINISHED'}

    def invoke(self, context, event):
        filepath = bpy.context.scene.configuration[context.object["config_id"]].reconstructionsrc
        files = os.listdir(filepath)
        config = bpy.context.scene.configuration[context.object["config_id"]]
        if "campose.txt" not in files:
            log_report(
                "ERROR", "campose.txt file not in your reconstrution package, \
                    please reconstruction first or change another package", None
            )
            return {'FINISHED'}               
        elif "fused.ply" not in files:
            log_report(
                "ERROR", "fused.ply file not in your reconstrution package, \
                    please reconstruction first or change another package", None
            )   
            return {'FINISHED'}
        elif config.resX == 0 or config.resY == 0\
            or config.fx == 0 or config.fy == 0\
            or config.cx == 0 or config.cy == 0:
            log_report(
                "ERROR", "Please set the camera parameters before loading the reconstruction", None
            )   
            return {'FINISHED'}
        else:
            return context.window_manager.invoke_props_dialog(self, width = 400)

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        config_id = bpy.context.object["config_id"]
        config = scene.configuration[config_id]
        layout.label(text="Set Reconstruction Loading Parameters:")        
        layout.label(text="Set Plane Alignment (ICP) Parameters:")
        box = layout.box() 
        row = box.row()
        row.prop(scene.planalignmentparas, "threshold") 
        row = box.row()
        row.prop(scene.planalignmentparas, "n") 
        row = box.row()
        row.prop(scene.planalignmentparas, "iteration") 
        box = layout.box() 
        box.label(text="Point Cloud Scale:")
        row = box.row()
        row.prop(scene.loadreconparas, "AUTOALIGN")
        if not scene.loadreconparas.AUTOALIGN:
            row = box.row()
            row.prop(scene.loadreconparas, "pointcloud_scale")
        else:
            row = box.row()
            row.prop(scene.loadreconparas, "depth_scale")
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
    AUTOALIGN: bpy.props.BoolProperty(name="Auto Align Point Cloud Scale", 
                                      description="Algin the Point Clound from Depth Information", 
                                      default=True)  
    camera_display_scale: bpy.props.FloatProperty(name="Cameras Display Scale", 
                                            description="Scale for cameras", 
                                            default=0.1, 
                                            min=0.0, 
                                            max=1.0, 
                                            step=2, 
                                            precision=2)      
    depth_scale: bpy.props.FloatProperty(name="Depth Data Scale", 
                                            description="Scale for depth", 
                                            default=0.00025)  
                                        
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
            # trans_obj_icp = globalRegisteration(scene_vertices_rotated, model_vertices)
            # print(trans_obj_icp)
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
    bpy.utils.register_class(PlaneAlignmentConfig)
    bpy.types.Scene.planalignmentparas = bpy.props.PointerProperty(type=PlaneAlignmentConfig) 
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
    bpy.utils.unregister_class(PlaneAlignmentConfig)
    bpy.utils.unregister_class(ImportCamRGBDepth)
    bpy.utils.unregister_class(ImportReconResult)
    bpy.utils.unregister_class(LoadRecon)
    bpy.utils.unregister_class(ModelICP)
    
    bpy.utils.unregister_class(WorkspaceRename)
    bpy.utils.unregister_class(RemoveWorkspace)
