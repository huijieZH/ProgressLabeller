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
        scene = context.scene
        if "type" in bpy.data.objects[current_object]:
            name = current_object.split(":")[0]
            config_id =  bpy.data.objects[name + ":Setting"]['config_id']
            config = scene.configuration[config_id]
            object_type = bpy.data.objects[current_object]["type"]
            if object_type == "model":
                layout = self.layout
                scene = context.scene
                layout.label(text="Align model to reconstruction:")
                row = layout.row()
                row.operator("object_property.modelicp")
            elif object_type == "reconstruction":
                workspace_name = current_object.split(":")[0]   
                config_id = bpy.data.objects[workspace_name + ":Setting"]['config_id']

                layout = self.layout
                scene = context.scene
                layout.label(text="Set reconstruction scale:")
                row = layout.row()
                row.prop(scene.configuration[config_id], 'reconstructionscale')
                layout.label(text="Align plane in reconstruction to X-Y:")
                row = layout.row()
                row.operator("object_property.planealignment")

            elif object_type == "camera":
                layout = self.layout
                scene = context.scene
                layout.label(text="Set FloatingScreen Property:")
                box = layout.box() 
                row = box.row(align=True)
                row.prop(scene.floatscreenproperty, "viewimage_mode")
                # row = box.row(align=True)
                # row.operator("object_property.viewimage")
                # row.prop(scene.floatscreenproperty, "empty_alpha")
                # row.prop(scene.floatscreenproperty, "segment_alpha")
                row = box.row()
                row.prop(scene.floatscreenproperty, "DISPLAY")
                row = box.row()
                row.prop(scene.floatscreenproperty, "TRACK")
                if scene.floatscreenproperty.TRACK:
                    row = box.row()
                    row.prop(scene.floatscreenproperty, "ALIGN")
                row = box.row(align=True)
                row.prop(scene.floatscreenproperty, "BACKGROUND")
                row.prop(scene.floatscreenproperty, "background_alpha")

                if not scene.floatscreenproperty.ALIGN:
                    row = box.row(align=True)
                    row.prop(scene.floatscreenproperty, "display_scale")
                    row = box.row(align=True)
                    row.prop(scene.floatscreenproperty, "display_X")
                    row.prop(scene.floatscreenproperty, "display_Y")
            elif object_type == "setting":
                object = bpy.data.objects[current_object]
                scene = context.scene
                layout = self.layout
                layout.label(text="Set Workspace Name:")
                row = layout.row()
                row.prop(scene.configuration[object["config_id"]], 'projectname')
                row.operator("object_property.workspacerename")
                layout.label(text="Set Environment:")

                row = layout.row()
                row.prop(scene.configuration[object["config_id"]], 'modelsrc')
                row.operator("import_data.model")

                row = layout.row()
                row.prop(scene.configuration[object["config_id"]], 'modelposesrc')
                row.operator("import_data.modelfrompose")
                row.operator("export_data.objectposes")

                row = layout.row()
                row.prop(scene.configuration[object["config_id"]], 'datasrc')
                row.operator("object_property.importcamrgbdepth")

                row = layout.row()
                row.prop(scene.configuration[object["config_id"]], 'reconstructionsrc')
                row.operator("object_property.importreconresult")


                layout.label(text="Set Camera Parameters:")
                box = layout.box() 
                row = box.row(align=True)
                row.prop(scene.configuration[object["config_id"]], "fx")
                row.prop(scene.configuration[object["config_id"]], "fy")
                row = box.row(align=True)
                row.prop(scene.configuration[object["config_id"]], "cx")
                row.prop(scene.configuration[object["config_id"]], "cy")
                row = box.row(align=True)
                row.prop(scene.configuration[object["config_id"]], "resX")
                row.prop(scene.configuration[object["config_id"]], "resY")

                layout.label(text="Export Configuration:")
                box = layout.box() 
                row = box.row(align=True)
                row.operator("export_data.configuration")

                layout.label(text="Remove Current Workspace:")
                box = layout.box() 
                row = box.row(align=True)
                row.operator("object_property.removeworkspace")

                layout.label(text="Reconstruction:")
                box = layout.box() 
                row = box.row(align=True)
                row.operator("reconstruction.methodselect")  

                layout.label(text="Data Output:")
                box = layout.box() 
                row = box.row(align=True)
                row.operator("export_data.dataoutput")  
                              
                # row = box.row()
                # row.operator("default.intrinsic")

def register():
    bpy.utils.register_class(ObjectPropertyPanel)


def unregister():
    bpy.utils.unregister_class(ObjectPropertyPanel)