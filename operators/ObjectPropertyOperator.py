import bpy
from bpy.props import StringProperty, EnumProperty, FloatProperty
from bpy.types import Operator

class ViewImage(Operator):
    """This appears in the tooltip of the operator and in the generated docs"""
    bl_idname = "object_property.viewimage"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "View Image"

    def execute(self, context):
        print()
        if bpy.context.scene.objectproperty.viewimage_mode == 'Origin':
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
        elif bpy.context.scene.objectproperty == 'Segment':
            pass
        elif bpy.context.scene.objectproperty == 'Segment(Inverse)':
            pass
        return {'FINISHED'}

class ObjectProperty(bpy.types.PropertyGroup):
    # The properties for this class which is referenced as an 'entry' below.
    viewimage_mode: EnumProperty(
        name="ViewMode",
        description="Choose the mode for viewing the frame",
        items=(
            ('Origin', "Origin", "Display Origin Image"),
            ('Segment', "Segment", "Display Segment Image"),
            ('Segment(Inverse)', "Segment(Inverse)", "Display Inverse Segment Image"),
        ),
        default='Origin',
    )

def register():
    bpy.utils.register_class(ViewImage)
    bpy.utils.register_class(ObjectProperty)
    bpy.types.Scene.objectproperty = bpy.props.PointerProperty(type=ObjectProperty)   

def unregister():
    bpy.utils.unregister_class(ViewImage)
    bpy.utils.unregister_class(ObjectProperty)