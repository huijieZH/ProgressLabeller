import bpy
import bgl
import gpu
from gpu_extras.presets import draw_texture_2d
from bpy_extras.view3d_utils import location_3d_to_region_2d
from bpy.props import StringProperty, EnumProperty, FloatProperty, BoolProperty
from bpy.types import Operator
from kernel.geometry import depthfilter

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
                    # if len(show_frame["alpha"]) == 1:
                    #     pixels = list(show_frame.pixels) 
                    #     for i in range(3, len(pixels), 4):
                    #         pixels[i] = show_frame["alpha"][0]
                    #     show_frame.pixels[:] = pixels
                    # else:
                    #     pixels = list(show_frame.pixels) 
                    #     for i in range(0, int(len(pixels)/4)):
                    #         pixels[4 * i + 3] = show_frame["alpha"][i]
                    #     show_frame.pixels[:] = pixels   
                    
                    alpha = depthfilter(obj["depth"]["depth"], config.depth_scale, config.depth_ignore)
                    pixels = list(show_frame.pixels) 
                    for i in range(0, int(len(pixels)/4)):
                        pixels[4 * i + 3] = float(alpha[i])
                    show_frame.pixels[:] = pixels                   
                obj.data.show_background_images = scene.floatscreenproperty.BACKGROUND
                obj.data.background_images[0].image = show_frame
                obj.data.background_images[0].alpha = scene.floatscreenproperty.background_alpha

                if scene.floatscreenproperty.TRACK:
                    for area in bpy.context.screen.areas:
                        ## change camera view
                        if area.type == 'VIEW_3D':
                            area.spaces[0].region_3d.view_perspective = 'CAMERA'
                    bpy.context.scene.render.resolution_x = bpy.context.scene.configuration[config_id].resX
                    bpy.context.scene.render.resolution_y = bpy.context.scene.configuration[config_id].resY
                    bpy.context.scene.camera = obj
                

                if scene.floatscreenproperty.TRACK and scene.floatscreenproperty.ALIGN:
                    for area in bpy.context.screen.areas:
                        if area.type == 'VIEW_3D':
                            cam = bpy.context.scene.camera
                            frame = cam.data.view_frame(scene = bpy.context.scene)
                            frame = [cam.matrix_world @ corner for corner in frame]
                            region = bpy.context.region

                            rv3d = bpy.context.region_data
                            frame_px = [location_3d_to_region_2d(region, rv3d, corner) for corner in frame]           
                            bias_X = min([v[0] for v in frame_px])
                            bias_Y = min([v[1] for v in frame_px])
                            res_X = max([v[0] for v in frame_px]) - min([v[0] for v in frame_px])
                            res_Y = max([v[1] for v in frame_px]) - min([v[1] for v in frame_px])                    
                            break
                        else:
                            bias_X = scene.floatscreenproperty.display_X
                            bias_Y = scene.floatscreenproperty.display_Y
                            res_X = int(config.resX * scene.floatscreenproperty.display_scale)
                            res_Y = int(config.resY * scene.floatscreenproperty.display_scale) 
                else:
                    bias_X = scene.floatscreenproperty.display_X
                    bias_Y = scene.floatscreenproperty.display_Y
                    res_X = int(config.resX * scene.floatscreenproperty.display_scale)
                    res_Y = int(config.resY * scene.floatscreenproperty.display_scale)   
                  
                if scene.floatscreenproperty.DISPLAY:
                    draw_texture_2d(show_frame.bindcode, 
                                    (bias_X, bias_Y), 
                                    res_X, 
                                    res_Y)
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

def register():
    global floatscreen_handler
    bpy.utils.register_class(FloatScreenProperty)
    bpy.types.Scene.floatscreenproperty = bpy.props.PointerProperty(type=FloatScreenProperty)
    floatscreen_handler = bpy.types.SpaceView3D.draw_handler_add(draw, (), 'WINDOW', 'POST_PIXEL')

def unregister():
    bpy.utils.unregister_class(FloatScreenProperty)
    bpy.types.SpaceView3D.draw_handler_remove(floatscreen_handler, 'WINDOW')