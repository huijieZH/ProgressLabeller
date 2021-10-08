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
from kernel.geometry import plane_alignment, transform_from_plane, _pose2Rotation, _rotation2Pose, modelICP, globalRegisteration
from kernel.logging_utility import log_report
from kernel.loader import load_cam_img_depth, load_reconstruction_result, updateprojectname, removeworkspace
from kernel.blender_utility import \
    _get_configuration, _get_reconstruction_insameworkspace, _get_obj_insameworkspace, _get_workspace_name, _apply_trans2obj, \
    _align_reconstruction
from registeration.init_configuration import config
from kernel.utility import _trans2transstring


class PlaneAlignment(Operator):
    """Using RANSAC to detect the plane and align it"""
    bl_idname = "object_property.planealignment"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "Plane Alignment"

    def execute(self, context):
        # current_object = bpy.context.object.name
        # workspace_name = current_object.split(":")[0]
        recon = _get_reconstruction_insameworkspace(context.object)

        log_report(
            "INFO", "Starting calculate the plane function", None
        )      
        

        [a, b, c, d], plane_center = plane_alignment(recon["path"], 
                                                     recon["scale"],
                                                     np.array(recon["alignT"]),
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

        obj_lists = _get_obj_insameworkspace(context.object, ["reconstruction", "camera"])
        
        for obj in obj_lists:
            _apply_trans2obj(obj, trans)


        
        recon["alignT"] = (trans.dot(np.array(recon["alignT"]))).tolist()

        _, config = _get_configuration(context.object)
        config.recon_trans = _trans2transstring(np.array(recon["alignT"]))

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
        config_id, config = _get_configuration(context.object)
        packagepath = config.datasrc
        files = os.listdir(packagepath)
        if "rgb" not in files or "depth" not in files:
            log_report(
                "Error", "either rgb or depth package is not in the datasrc", None
            )       
        elif config.resX == 0 or config.resY == 0\
            or config.fx == 0 or config.fy == 0\
            or config.cx == 0 or config.cy == 0:
            log_report(
                "ERROR", "Please set the camera parameters before loading the RGB and Camera", None
            )   
            return {'FINISHED'}      
        else:   
            load_cam_img_depth(packagepath, config_id, camera_display_scale = 0.1, sample_rate=config.sample_rate)
        return {'FINISHED'}
    
    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width = 400)

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        config_id, config = _get_configuration(context.object)
        layout.label(text="Set Sample Rate for RGB to reconstruct:")
        box = layout.box() 
        row = box.row()
        row.prop(config, "sample_rate") 


class ImportReconResult(Operator):
    """This appears in the tooltip of the operator and in the generated docs"""
    bl_idname = "object_property.importreconresult"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "Import Reconstruction Result"

    def execute(self, context): 
        scene = context.scene
        config_id, config = _get_configuration(context.object)
        datasrc = config.datasrc
        filepath = config.reconstructionsrc
        scene.loadreconparas.pointcloud_scale = config.reconstructionscale
        # config.cameradisplayscale = scene.loadreconparas.camera_display_scale

        if not scene.loadreconparas.AUTOALIGN:
            load_reconstruction_result(filepath = filepath, 
                                        pointcloudscale = scene.loadreconparas.pointcloud_scale, 
                                        datasrc = datasrc,
                                        config_id = config_id,
                                        camera_display_scale = config.cameradisplayscale,
                                        CAMPOSE_INVERSE = scene.loadreconparas.CAMPOSE_INVERSE
                                        )
        else:
            log_report(
            "INFO", "Starting aligning the point cloud", None
            )     

            scale = _align_reconstruction(config, scene)
                
            config.reconstructionscale = scale
            load_reconstruction_result(filepath = filepath, 
                                        pointcloudscale = scale, 
                                        datasrc = datasrc,
                                        config_id = config_id,
                                        camera_display_scale = config.cameradisplayscale,
                                        CAMPOSE_INVERSE = scene.loadreconparas.CAMPOSE_INVERSE
                                        )
            
        return {'FINISHED'}

    def invoke(self, context, event):
        filepath = bpy.context.scene.configuration[context.object["config_id"]].reconstructionsrc
        files = os.listdir(filepath)
        _, config = _get_configuration(context.object)
        context.scene.loadreconparas.pointcloud_scale = config["reconstructionscale"]
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
        _, config = _get_configuration(context.object)
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
        row.prop(config, "cameradisplayscale")
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
        name  = _get_workspace_name(context.object)
        removeworkspace(name)
        return {'FINISHED'}  

class ModelICP(Operator):
    """This appears in the tooltip of the operator and in the generated docs"""
    bl_idname = "object_property.modelicp"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "Model Alignment"

    def execute(self, context):
        obj = context.object
        assert obj['type'] == 'model'
        name  = _get_workspace_name(obj)
        model_vertices = np.array([list(obj.matrix_world @ v.co) for v in obj.data.vertices])
        if name + ":reconstruction" not in bpy.data.objects:
            log_report(
                "Error", "You should upload the reconstruction result first", None
            )     
            return {'FINISHED'}
        else:
            recon = _get_reconstruction_insameworkspace(obj)
            recon_vertices = np.array(recon["particle_coords"])
            rot = np.array(recon.matrix_world)
            recon_vertices_rotated = (rot[:3, :3].dot(recon_vertices.T) + rot[:3, [3]]).T
            trans_obj_icp = modelICP(recon_vertices_rotated, model_vertices)
            _apply_trans2obj(obj, trans_obj_icp)
        return {'FINISHED'} 

class AllModelsICP(Operator):
    """This appears in the tooltip of the operator and in the generated docs"""
    bl_idname = "object_property.allmodelsicp"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "All Models Alignment"

    def execute(self, context):
        recon = context.object
        assert recon['type'] == 'reconstruction'
        objects = _get_obj_insameworkspace(recon, 'model')

        for obj in objects:
            model_vertices = np.array([list(obj.matrix_world @ v.co) for v in obj.data.vertices])
            recon_vertices = np.array(recon["particle_coords"])
            rot = np.array(recon.matrix_world)
            recon_vertices_rotated = (rot[:3, :3].dot(recon_vertices.T) + rot[:3, [3]]).T
            trans_obj_icp = modelICP(recon_vertices_rotated, model_vertices)
            _apply_trans2obj(obj, trans_obj_icp)
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
    bpy.utils.register_class(AllModelsICP)

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
    bpy.utils.unregister_class(AllModelsICP)
    
    bpy.utils.unregister_class(WorkspaceRename)
    bpy.utils.unregister_class(RemoveWorkspace)
