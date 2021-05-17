import bpy


class ObjectPropertyPanel(bpy.types.Panel):
    """Creates a Panel in the scene context of the properties editor"""
    bl_label = "Progress Labeller"
    bl_idname = "OBJECT_PROPERTY_layout"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "object"

    def draw(self, context):
        current_object = bpy.context.object.name
        if "type" in bpy.data.objects[current_object]:
            object_type = bpy.data.objects[current_object]["type"]
            if object_type == "model":
                pass
            elif object_type == "reconstruction":
                pass
            elif object_type == "camera":
                layout = self.layout
                scene = context.scene
                box = layout.box() 
                row = box.row(align=True)
                row.prop(scene.objectproperty, "viewimage_mode")
                row.operator("object_property.viewimage")

def register():
    bpy.utils.register_class(ObjectPropertyPanel)


def unregister():
    bpy.utils.unregister_class(ObjectPropertyPanel)