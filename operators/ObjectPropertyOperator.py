import bpy
from bpy.props import StringProperty, EnumProperty, FloatProperty
from bpy.types import Operator
import numpy as np
from PIL import Image
import os

from kernel.render import save_img


class ViewImage(Operator):
    """This appears in the tooltip of the operator and in the generated docs"""
    bl_idname = "object_property.viewimage"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "View Image"

    def execute(self, context):
        current_object = bpy.context.object.name
        assert "type" in bpy.data.objects[current_object] and\
                bpy.data.objects[current_object]["type"] == "camera"
        pair_image_name = bpy.data.objects[current_object]["image"].name
        ## change the active image
        bpy.context.scene.camera = bpy.data.objects[current_object]
        for area in bpy.data.screens['UV Editing'].areas:
            ## display image
            if area.type == 'IMAGE_EDITOR':
                area.spaces.active.image = bpy.data.images[pair_image_name]
            ## change camera view
            if area.type == 'VIEW_3D':
                area.spaces[0].region_3d.view_perspective = 'CAMERA'

        img_rgb = np.array(bpy.data.images[pair_image_name].pixels).reshape(bpy.context.scene.configuration.resY, bpy.context.scene.configuration.resX, 4)
        ### for different view mode, change the alpha channel only
        if bpy.context.scene.objectproperty.viewimage_mode == 'Origin':
            img_rgb[:, :, 3] = bpy.context.scene.objectproperty.segment_alpha
            bpy.data.images[pair_image_name].pixels = img_rgb.ravel()
        elif bpy.context.scene.objectproperty.viewimage_mode == 'Segment':
            current_object = bpy.context.object.name
            assert "type" in bpy.data.objects[current_object] and\
                    bpy.data.objects[current_object]["type"] == "camera"
            pair_image_name = bpy.data.objects[current_object]["image"].name
            # ## change the active image
            bpy.context.scene.camera = bpy.data.objects[current_object]
            
            # H = img_rgb.shape[0]
            # W = img_rgb.shape[1]
            # img_rgb = np.concatenate((img_rgb.astype(np.float16), np.ones((H, W, 1), dtype = np.float16)), axis = 2)
            tmpimgname_render = './tmp/tmp.png'
            bpy.context.scene.render.filepath = tmpimgname_render
            bpy.context.scene.render.image_settings.file_format='PNG' 
            bpy.context.scene.render.image_settings.color_mode ='RGBA'
            bpy.context.scene.render.film_transparent = True
            bpy.context.scene.render.resolution_x = bpy.context.scene.configuration.resX
            bpy.context.scene.render.resolution_y = bpy.context.scene.configuration.resY
            res = bpy.ops.render.render(write_still = True)
            img_render = np.array(Image.open(tmpimgname_render))
            foreground_mask = img_render[:, :, 3] == 0
            foreground_mask = foreground_mask[::-1, :]
            img_rgb[foreground_mask, 3] = bpy.context.scene.objectproperty.empty_alpha
            img_rgb[~foreground_mask, 3] = bpy.context.scene.objectproperty.segment_alpha
            os.system('rm ' + tmpimgname_render)
            # img_rgb = img_rgb[::-1, :]
            bpy.data.images[pair_image_name].pixels = img_rgb.ravel()

            #### save current image
            foreground_mask = img_render[:, :, 3] == 0
            img_origin = (img_rgb[::-1, :, :3]*255).astype(np.uint8)
            img_segment = img_origin.copy()
            img_segment[foreground_mask, :3] = 0
            save_img(img_render[:, :, :3], img_origin, img_segment, pair_image_name)


        elif bpy.context.scene.objectproperty.viewimage_mode == 'Segment(Inverse)':
            current_object = bpy.context.object.name
            assert "type" in bpy.data.objects[current_object] and\
                    bpy.data.objects[current_object]["type"] == "camera"
            pair_image_name = bpy.data.objects[current_object]["image"].name
            # ## change the active image
            bpy.context.scene.camera = bpy.data.objects[current_object]
            
            # H = img_rgb.shape[0]
            # W = img_rgb.shape[1]
            # img_rgb = np.concatenate((img_rgb.astype(np.float16), np.ones((H, W, 1), dtype = np.float16)), axis = 2)
            tmpimgname_render = './tmp/tmp.png'
            bpy.context.scene.render.filepath = tmpimgname_render
            bpy.context.scene.render.image_settings.file_format='PNG' 
            bpy.context.scene.render.image_settings.color_mode ='RGBA'
            bpy.context.scene.render.film_transparent = True
            bpy.context.scene.render.resolution_x = bpy.context.scene.configuration.resX
            bpy.context.scene.render.resolution_y = bpy.context.scene.configuration.resY
            res = bpy.ops.render.render(write_still = True)
            img_render = np.array(Image.open(tmpimgname_render))
            foreground_mask = img_render[:, :, 3] == 0
            foreground_mask = foreground_mask[::-1, :]
            img_rgb[foreground_mask, 3] = bpy.context.scene.objectproperty.segment_alpha
            img_rgb[~foreground_mask, 3] = bpy.context.scene.objectproperty.empty_alpha
            os.system('rm ' + tmpimgname_render)
            # img_rgb = img_rgb[::-1, :]
            bpy.data.images[pair_image_name].pixels = img_rgb.ravel()


        return {'FINISHED'}

# def updataEmptyAlpha(self,context):
#     current_object = bpy.context.object.name
#     assert "type" in bpy.data.objects[current_object] and\
#             bpy.data.objects[current_object]["type"] == "camera"
#     pair_image_name = bpy.data.objects[current_object]["image"].name
#     img_rgb = np.array(bpy.data.images[pair_image_name].pixels).reshape(bpy.context.scene.configuration.resY, bpy.context.scene.configuration.resX, 4)
    
#     foreground_mask = img_rgb[:, :, 3] != bpy.context.scene.objectproperty.segment_alpha
#     img_rgb[foreground_mask, 3] = bpy.context.scene.objectproperty.empty_alpha

#     bpy.data.images[pair_image_name].pixels = img_rgb.ravel()

# def updataSegmentAlpha(self,context):
#     current_object = bpy.context.object.name
#     assert "type" in bpy.data.objects[current_object] and\
#             bpy.data.objects[current_object]["type"] == "camera"
#     pair_image_name = bpy.data.objects[current_object]["image"].name
#     img_rgb = np.array(bpy.data.images[pair_image_name].pixels).reshape(bpy.context.scene.configuration.resY, bpy.context.scene.configuration.resX, 4)
    
#     foreground_mask = img_rgb[:, :, 3] != bpy.context.scene.objectproperty.empty_alpha
#     img_rgb[foreground_mask, 3] = bpy.context.scene.objectproperty.segment_alpha
    
#     bpy.data.images[pair_image_name].pixels = img_rgb.ravel()

class ObjectProperty(bpy.types.PropertyGroup):
    # The properties for this class which is referenced as an 'entry' below.
    viewimage_mode: EnumProperty(
        name="View Mode",
        description="Choose the mode for viewing the frame",
        items=(
            ('Origin', "Origin", "Display Origin Image"),
            ('Segment', "Segment", "Display Segment Image"),
            ('Segment(Inverse)', "Segment(Inverse)", "Display Inverse Segment Image"),
        ),
        default='Origin',
    )
    empty_alpha = bpy.props.FloatProperty(name="EmptyAlpha", 
                                        description="Alhpa value for empty regin", 
                                        default=0.2, 
                                        min=0.00, 
                                        max=1.00, 
                                        step=3, 
                                        precision=2)

    segment_alpha = bpy.props.FloatProperty(name="SegmentAlpha", 
                                            description="Alhpa value for segmented regin", 
                                            default=1.00, 
                                            min=0.00, 
                                            max=1.00, 
                                            step=3, 
                                            precision=2)

    # empty_alpha = bpy.props.FloatProperty(name="EmptyAlpha", 
    #                                     description="Alhpa value for empty regin", 
    #                                     default=0.0, 
    #                                     min=0.00, 
    #                                     max=1.00, 
    #                                     step=3, 
    #                                     precision=2, 
    #                                     update=updataEmptyAlpha)

    # segment_alpha = bpy.props.FloatProperty(name="SegmentAlpha", 
    #                                         description="Alhpa value for segmented regin", 
    #                                         default=1.00, 
    #                                         min=0.00, 
    #                                         max=1.00, 
    #                                         step=3, 
    #                                         precision=2, 
    #                                         update=updataSegmentAlpha)



def register():
    bpy.utils.register_class(ViewImage)
    bpy.utils.register_class(ObjectProperty)
    bpy.types.Scene.objectproperty = bpy.props.PointerProperty(type=ObjectProperty)   

def unregister():
    bpy.utils.unregister_class(ViewImage)
    bpy.utils.unregister_class(ObjectProperty)