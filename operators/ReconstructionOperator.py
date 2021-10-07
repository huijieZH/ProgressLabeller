import bpy
from bpy.props import StringProperty, EnumProperty, FloatProperty
from bpy.types import Operator
import os

from kernel.logging_utility import log_report
from kernel.loader import load_reconstruction_result
from kernel.blender_utility import _get_configuration, _align_reconstruction

class Reconstruction(Operator):
    """This appears in the tooltip of the operator and in the generated docs"""
    bl_idname = "reconstruction.methodselect"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "3D Reconstruction from data (Depth, RGB or both)"

    # bl_options = {'REGISTER', 'INTERNAL'}

    ReconstructionType: EnumProperty(
        name="Reconstruction Method",
        description="Choose a reconstruction method",
        items=(
            ('KinectFusion', "KinectFusion", "Need depth & rgb data information"),
            ('COLMAP', "COLMAP", "Need depth & rgb data information"),
        ),
        default='KinectFusion',
    )

    PerfixList = list()

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        scene = context.scene
        config_id, config = _get_configuration(context.object)
        if self.ReconstructionType == "KinectFusion":
            try: 
                from kernel.reconstruction import KinectfusionRecon
            except:
                log_report(
                    "Error", "Please successfully install pycuda", None
                )        
            else:             
                KinectfusionRecon(
                    data_folder = config.datasrc,
                    save_folder = config.reconstructionsrc,
                    prefix_list = self.PerfixList,
                    resX = config.resX, 
                    resY = config.resY, 
                    fx = config.fx, 
                    fy = config.fy, 
                    cx = config.cx, 
                    cy = config.cy,
                    tsdf_voxel_size = scene.kinectfusionparas.tsdf_voxel_size, 
                    tsdf_trunc_margin = scene.kinectfusionparas.tsdf_trunc_margin, 
                    pcd_voxel_size = scene.kinectfusionparas.pcd_voxel_size, 
                    depth_scale = scene.kinectfusionparas.depth_scale, 
                    depth_ignore = scene.kinectfusionparas.depth_ignore, 
                    DISPLAY = scene.kinectfusionparas.DISPLAY,  
                    frame_per_display = scene.kinectfusionparas.frame_per_display, 
                )
            
                load_reconstruction_result(filepath = config.reconstructionsrc, 
                                    pointcloudscale = 1.0, 
                                    datasrc = config.datasrc,
                                    config_id = config_id,
                                    camera_display_scale = config.cameradisplayscale,
                                    CAMPOSE_INVERSE= False
                                    )
        elif self.ReconstructionType == "COLMAP":
            try: 
                from kernel.colmap.build import colmap_extension
            except:
                log_report(
                    "Error", "Please successfully install COLMAP, pybind11 and complie colmap_extension", None
                )            
            else:
                colmap_extension.colmap_reconstruction(
                    os.path.join(config.reconstructionsrc, "reconstruction.db"),
                    os.path.join(config.datasrc, "rgb"),
                    os.path.join(config.reconstructionsrc, "image-list.txt"),
                    f"{config.fx}, {config.fy}, {config.cx}, {config.cy}",
                    config.reconstructionsrc
                )

                colmap_extension.parseReconstruction(config.reconstructionsrc)

                scale = _align_reconstruction(config, scene)
                config.reconstructionscale = scale
                load_reconstruction_result(filepath = config.reconstructionsrc, 
                                    pointcloudscale = scale, 
                                    datasrc = config.datasrc,
                                    config_id = config_id,
                                    camera_display_scale = config.cameradisplayscale,
                                    CAMPOSE_INVERSE= True
                                    )
        return {'FINISHED'}


    def invoke(self, context, event):
        current_object = bpy.context.object.name
        workspace_name = current_object.split(":")[0]        
        for obj in bpy.data.objects:
            if obj.name.startswith(workspace_name) and obj['type'] == "camera":
                perfix = (obj.name.split(":")[1]).replace("view", "")
                if (workspace_name + ":" + "depth" + perfix in bpy.data.images) and (workspace_name + ":" + "rgb" + perfix in bpy.data.images) and (perfix not in self.PerfixList):
                    self.PerfixList.append(perfix)
        self.PerfixList.sort(key = lambda x:int(x))

        config_id = context.object["config_id"]
        config = bpy.context.scene.configuration[config_id]  

        if len(self.PerfixList) == 0:
            log_report(
                "Error", "You should upload the rgb and depth data before doing reconstruction", None
            )     
            return {'FINISHED'}
        elif config.reconstructionsrc == "":
            log_report(
                "Error", "You should specify your reconstruction path first", None
            )     
            return {'FINISHED'}            
        else:
            return context.window_manager.invoke_props_dialog(self, width = 400)

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        config_id = bpy.context.object["config_id"]
        config = scene.configuration[config_id]
        layout.prop(self, "ReconstructionType", text="Reconstruction Method")
        if self.ReconstructionType == "KinectFusion":
            layout.label(text="Set Camera Parameters:")
            box = layout.box() 
            row = box.row(align=True)
            row.prop(config, "fx")
            row.prop(config, "fy")
            row = box.row(align=True)
            row.prop(config, "cx")
            row.prop(config, "cy")
            row = box.row(align=True)
            row.prop(config, "resX")
            row.prop(config, "resY")
            layout.label(text="Set KinectFusion Parameters:")
            row = layout.row() 
            row.prop(scene.kinectfusionparas, "depth_scale")
            row = layout.row() 
            row.prop(scene.kinectfusionparas, "tsdf_voxel_size")
            row = layout.row() 
            row.prop(scene.kinectfusionparas, "tsdf_trunc_margin")
            row = layout.row() 
            row.prop(scene.kinectfusionparas, "pcd_voxel_size")
            row = layout.row() 
            row.prop(scene.kinectfusionparas, "depth_ignore")
            box = layout.box() 
            row = box.row(align=True)
            row.prop(scene.kinectfusionparas, "DISPLAY")
            if scene.kinectfusionparas.DISPLAY:
                row.prop(scene.kinectfusionparas, "frame_per_display")            
            
        elif self.ReconstructionType == "COLMAP":
            layout.label(text="Set Camera Parameters:")
            box = layout.box() 
            row = box.row(align=True)
            row.prop(config, "fx")
            row.prop(config, "fy")
            row = box.row(align=True)
            row.prop(config, "cx")
            row.prop(config, "cy")
            row = box.row(align=True)
            row.prop(config, "resX")
            row.prop(config, "resY")
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
            row = box.row()
            row.prop(scene.loadreconparas, "depth_scale")
            row = layout.row()
            row.prop(config, "cameradisplayscale")

class KinectfusionConfig(bpy.types.PropertyGroup):
    # The properties for this class which is referenced as an 'entry' below.
    depth_scale: bpy.props.FloatProperty(name="Depth Scale", 
                                        description="Scale for depth image", 
                                        default=0.00025, 
                                        min=0.000000, 
                                        max=1.000000, 
                                        step=6, 
                                        precision=6)

    tsdf_voxel_size: bpy.props.FloatProperty(name="TSDF Voxel Size (m)", 
                                            description="Voxel size for truncated signed distance function, in meter", 
                                            default=0.0025, 
                                            min=0.00, 
                                            max=1.00, 
                                            step=4, 
                                            precision=4)
    tsdf_trunc_margin: bpy.props.FloatProperty(name="TSDF Truncated Margin (m)", 
                                            description="Truncated margin for truncated signed distance function, in meter", 
                                            default=0.015, 
                                            min=0.00, 
                                            max=1.00, 
                                            step=4, 
                                            precision=4)
    pcd_voxel_size: bpy.props.FloatProperty(name="Model Voxel Size (m)", 
                                            description="Voxel size for rendered model, in meter", 
                                            default=0.005, 
                                            min=0.00, 
                                            max=1.00, 
                                            step=4, 
                                            precision=4)  
    depth_ignore: bpy.props.FloatProperty(name="Ignore depth range (m)", 
                                            description="Depth beyond this value would be ignore, in meter", 
                                            default=1.5, 
                                            min=0.0, 
                                            max=10.0, 
                                            step=3, 
                                            precision=3)      
    DISPLAY: bpy.props.BoolProperty(
        name="Display during reconstruction",
        description="During reconstruction simutaneously display the reconstruction result in Blender",
        default=False,
    )       

    frame_per_display: bpy.props.IntProperty(name="Frames per display", 
                                                description="Frame interval between two displays", 
                                                default=5)                                                                           

def register():
    bpy.utils.register_class(Reconstruction)
    bpy.utils.register_class(KinectfusionConfig)
    bpy.types.Scene.kinectfusionparas = bpy.props.PointerProperty(type=KinectfusionConfig)   


def unregister():
    bpy.utils.unregister_class(Reconstruction)
    bpy.utils.unregister_class(KinectfusionConfig)
