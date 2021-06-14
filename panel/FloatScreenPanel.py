import bpy
import bgl
import gpu
from gpu_extras.presets import draw_texture_2d
from bpy.props import StringProperty, EnumProperty, FloatProperty
from bpy.types import Operator

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

            if show_frame:
                if show_frame["UPDATEALPHA"]:
                    if len(show_frame["alpha"]) == 1:
                        pixels = list(show_frame.pixels) 
                        for i in range(3, len(pixels), 4):
                            pixels[i] = show_frame["alpha"][0]
                        show_frame.pixels[:] = pixels
                    else:
                        pixels = list(show_frame.pixels) 
                        for i in range(3, len(pixels), 4):
                            pixels[i] = show_frame["alpha"][i]
                        show_frame.pixels[:] = pixels     
                    
                for area in bpy.context.screen.areas:
                    ## change camera view
                    if area.type == 'VIEW_3D':
                        area.spaces[0].region_3d.view_perspective = 'CAMERA'
                bpy.context.scene.render.resolution_x = bpy.context.scene.configuration[config_id].resX
                bpy.context.scene.render.resolution_y = bpy.context.scene.configuration[config_id].resY
                bpy.context.scene.camera = obj
                draw_texture_2d(show_frame.bindcode, 
                                (scene.floatscreenproperty.display_X, scene.floatscreenproperty.display_Y), 
                                int(config.resX * scene.floatscreenproperty.display_scale), 
                                int(config.resY * scene.floatscreenproperty.display_scale))
                show_frame["UPDATEALPHA"] = False

class FloatScreenProperty(bpy.types.PropertyGroup):
    # The properties for this class which is referenced as an 'entry' below.
    viewimage_mode: EnumProperty(
        name="View Mode",
        description="Choose the mode for viewing the frame",
        items=(
            ('RGB Origin', "RGB Origin", "Display Origin RGB Image"),
            ('Depth Origin', "Depth Origin", "Display Origin Depth Image"),
            ('Segment', "Segment", "Display Segment Image"),
            ('Segment(Inverse)', "Segment(Inverse)", "Display Inverse Segment Image"),
        ),
        default='RGB Origin',
    )
    empty_alpha: bpy.props.FloatProperty(name="EmptyAlpha", 
                                        description="Alhpa value for empty regin", 
                                        default=0.2, 
                                        min=0.00, 
                                        max=1.00, 
                                        step=0.1, 
                                        precision=2)

    segment_alpha: bpy.props.FloatProperty(name="SegmentAlpha", 
                                            description="Alhpa value for segmented regin", 
                                            default=1.00, 
                                            min=0.00, 
                                            max=1.00, 
                                            step=0.1, 
                                            precision=2)

    display_scale: bpy.props.FloatProperty(name="Display Scale", 
                                            description="Display Scale for the floating screen", 
                                            default=0.50, 
                                            min=0.00, 
                                            max=1.00, 
                                            step=0.1, 
                                            precision=2)
    display_X: bpy.props.FloatProperty(name="X position", 
                                        description="X bias position for the floating screen", 
                                        default=0, 
                                        min=0, 
                                        max=2000, 
                                        step=100, 
                                        precision=0)
    display_Y: bpy.props.FloatProperty(name="Y position", 
                                        description="Y bias position for the floating screen", 
                                        default=0, 
                                        min=0, 
                                        max=2000, 
                                        step=100, 
                                        precision=0)

def register():
    global floatscreen_handler
    bpy.utils.register_class(FloatScreenProperty)
    bpy.types.Scene.floatscreenproperty = bpy.props.PointerProperty(type=FloatScreenProperty)
    floatscreen_handler = bpy.types.SpaceView3D.draw_handler_add(draw, (), 'WINDOW', 'POST_PIXEL')

def unregister():
    bpy.utils.unregister_class(FloatScreenProperty)
    bpy.types.SpaceView3D.draw_handler_remove(floatscreen_handler)