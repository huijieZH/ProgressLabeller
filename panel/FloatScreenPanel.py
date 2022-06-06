import bpy
import bgl
import gpu
from gpu_extras.presets import draw_texture_2d
from bpy_extras.view3d_utils import location_3d_to_region_2d
from bpy.props import StringProperty, EnumProperty, FloatProperty, BoolProperty
from bpy.types import Operator
from kernel.geometry import depthfilter
from kernel.blender_utility import _get_configuration
import registeration.register 
import numpy as np
from mathutils import Matrix

def draw():
    context = bpy.context
    scene = context.scene
    obj = context.object
    if obj and "type" in obj:
        ## the obj is progresslabeller's object
        name = obj.name.split(":")[0]
        config_id =  bpy.data.objects[name + ":Setting"]['config_id']
        config = scene.configuration[config_id]
        if obj['type'] == "camera":
            if scene.floatscreenproperty.viewimage_mode == "RGB Origin":
                show_frame = obj["rgb"]
                if show_frame.bindcode == 0:
                    show_frame.gl_load()
            elif scene.floatscreenproperty.viewimage_mode == "Depth Origin":
                show_frame = obj["depth"]
                if show_frame.bindcode == 0:
                    show_frame.gl_load()
            
            for area in bpy.context.screen.areas:
                if area.type == 'IMAGE_EDITOR': 
                    area.spaces.active.image = show_frame

            if show_frame:
                if show_frame["UPDATEALPHA"] and scene.floatscreenproperty.UPDATE_DEPTHFILTER:
                    alpha = depthfilter(obj["depth"]["depth"], config.depth_scale, config.depth_ignore, scene.floatscreenproperty.IGNORE_ZERODEPTH)
                    pixels = list(show_frame.pixels) 
                    for i in range(0, int(len(pixels)/4)):
                        pixels[4 * i + 3] = float(alpha[i]) * 1
                    show_frame.pixels[:] = pixels                   
                obj.data.show_background_images = scene.floatscreenproperty.BACKGROUND
                obj.data.background_images[0].image = show_frame
                obj.data.background_images[0].alpha = scene.floatscreenproperty.background_alpha

                if scene.floatscreenproperty.TRACK:
                    for area in bpy.context.screen.areas:
                        ## change camera view
                        if area.type == 'VIEW_3D' and area not in registeration.register.area_image_pair:
                            area.spaces.active.region_3d.view_perspective = 'CAMERA'
                            bpy.context.scene.render.resolution_x = bpy.context.scene.configuration[config_id].resX
                            bpy.context.scene.render.resolution_y = bpy.context.scene.configuration[config_id].resY
                            # bpy.context.scene.camera = obj
                            area.spaces[0].use_local_camera = True
                            area.spaces[0].camera = obj
                show_frame["UPDATEALPHA"] = False

def draw_for_area(area, camera_obj):
    context = bpy.context
    scene = context.scene
    config_id, config = _get_configuration(camera_obj)
    if scene.floatscreenproperty.viewimage_mode == "RGB Origin":
        show_frame = camera_obj["rgb"]
        if show_frame.bindcode == 0:
            show_frame.gl_load()
    elif scene.floatscreenproperty.viewimage_mode == "Depth Origin":
        show_frame = camera_obj["depth"]
        if show_frame.bindcode == 0:
            show_frame.gl_load()
    if show_frame:

        if show_frame["UPDATEALPHA"]:
            pixels = list(show_frame.pixels) 
            for i in range(0, int(len(pixels)/4)):
                pixels[4 * i + 3] = 1
            show_frame.pixels[:] = pixels      
        camera_obj.data.show_background_images = scene.floatscreenproperty.BACKGROUND
        camera_obj.data.background_images[0].image = show_frame
        camera_obj.data.background_images[0].alpha = scene.floatscreenproperty.background_alpha   
        bpy.context.scene.render.resolution_x = bpy.context.scene.configuration[config_id].resX
        bpy.context.scene.render.resolution_y = bpy.context.scene.configuration[config_id].resY
        if len(area.spaces) > 0:
            area.spaces[0].use_local_camera = True
            area.spaces[0].region_3d.view_perspective = 'CAMERA'
            area.spaces[0].camera = camera_obj
            # 
            # area.spaces[0].overlay.show_wireframes = True
            # area.spaces[0].overlay.wireframe_threshold = 06
        show_frame["UPDATEALPHA"] = False        


class FloatScreenProperty(bpy.types.PropertyGroup):
    # The properties for this class which is referenced as an 'entry' below.
    viewimage_mode: EnumProperty(
        name="View Mode",
        description="Choose the mode for viewing the frame",
        items=(
            ('RGB Origin', "RGB Origin", "Display Origin RGB Image"),
            ('Depth Origin', "Depth Origin", "Display Origin Depth Image"),
        ),
        default='RGB Origin',
    )
    DISPLAY:  BoolProperty(
                name="Show Float Screen",
                description="Display the float screen to show rgb and depth image",
                default=True,
            )
    TRACK:  BoolProperty(
                name="Track the camera",
                description="Automaticly change to active camera view",
                default=True,
            )
    BACKGROUND:  BoolProperty(
                name="Show pairwise image in background",
                description="Display the image(either depth or rgb) in the camera view background",
                default=True,
            )
    background_alpha: FloatProperty(name="BackgoundAlhpa", 
                            description="Alhpa value for background", 
                            default=1.00, 
                            min=0.00, 
                            max=1.00, 
                            step=0.1, 
                            precision=2)

    ALIGN:  BoolProperty(
                name="Align the float screen and camera view",
                description="Align the float screen and camera view to verify the model pose and segmentation",
                default=False,
            )
    empty_alpha: FloatProperty(name="EmptyAlpha", 
                                description="Alhpa value for empty regin", 
                                default=0.2, 
                                min=0.00, 
                                max=1.00, 
                                step=0.1, 
                                precision=2)

    segment_alpha: FloatProperty(name="SegmentAlpha", 
                                description="Alhpa value for segmented regin", 
                                default=1.00, 
                                min=0.00, 
                                max=1.00, 
                                step=0.1, 
                                precision=2)

    display_scale: FloatProperty(name="Display Scale", 
                                description="Display Scale for the floating screen", 
                                default=0.50, 
                                min=0.00, 
                                max=4.00, 
                                step=0.1, 
                                precision=2)
    display_X: FloatProperty(name="X position", 
                            description="X bias position for the floating screen", 
                            default=0, 
                            min=0, 
                            max=2000, 
                            step=100, 
                            precision=0)
    display_Y: FloatProperty(name="Y position", 
                            description="Y bias position for the floating screen", 
                            default=0, 
                            min=0, 
                            max=2000, 
                            step=100, 
                            precision=0)
    
    UPDATE_DEPTHFILTER: BoolProperty(
                name="Update depth filter on image",
                description="Display filtered depth on screen (would be slow)",
                default=True,
            )
    
    def ignorezerodepthUpdate(self, context):
        context.object['depth']["UPDATEALPHA"] = True
        context.object['rgb']["UPDATEALPHA"] = True
    IGNORE_ZERODEPTH: BoolProperty(
                name="Ignore zero depth",
                description="If true, depth with zero value would be filtered out",
                default=True,
                update=ignorezerodepthUpdate
            )
    
def right_click_menu_func(self, context):
    layout = self.layout
    layout.separator()
    layout.operator("object_property.lockcurrent3darea")
    layout.operator("object_property.unlockcurrent3darea")

def register():
    global floatscreen_handler
    bpy.utils.register_class(FloatScreenProperty)
    bpy.types.Scene.floatscreenproperty = bpy.props.PointerProperty(type=FloatScreenProperty)
    floatscreen_handler = bpy.types.SpaceView3D.draw_handler_add(draw, (), 'WINDOW', 'POST_PIXEL')
    bpy.types.VIEW3D_MT_object_context_menu.append(right_click_menu_func)

def unregister():
    bpy.utils.unregister_class(FloatScreenProperty)
    bpy.types.SpaceView3D.draw_handler_remove(floatscreen_handler, 'WINDOW')
    bpy.types.VIEW3D_MT_object_context_menu.remove(right_click_menu_func)