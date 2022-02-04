import bpy
from kernel.blender_utility import _get_configuration

import numpy as np

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
            object_type = bpy.data.objects[current_object]["type"]
            config_id, config = _get_configuration(context.object)
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
                layout.label(text="Set scale:")
                row = layout.row()
                row.prop(scene.configuration[config_id], 'reconstructionscale')
                row.prop(scene.configuration[config_id], 'cameradisplayscale')
                layout.label(text="Align plane in reconstruction to X-Y:")
                row = layout.row()
                row.operator("object_property.planealignment")

                layout.label(text="Align all models:")
                row = layout.row()
                row.operator("object_property.allmodelsicp")
                

            elif object_type == "camera":
                layout = self.layout
                scene = context.scene
                layout.label(text="Set FloatingScreen Property:")
                box = layout.box() 
                row = box.row(align=True)
                row.prop(scene.floatscreenproperty, "viewimage_mode")
                row = box.row()
                row.prop(scene.floatscreenproperty, "DISPLAY")
                row = box.row()
                row.prop(scene.floatscreenproperty, "TRACK")
                if scene.floatscreenproperty.TRACK:
                    row = box.row()
                    row.prop(scene.floatscreenproperty, "ALIGN")
                    # row.operator("object_property.current3darea")
                    
                row = box.row(align=True)
                row.prop(scene.floatscreenproperty, "BACKGROUND")
                row.prop(scene.floatscreenproperty, "background_alpha")

                if not scene.floatscreenproperty.ALIGN:
                    row = box.row(align=True)
                    row.prop(scene.floatscreenproperty, "display_scale")
                    row = box.row(align=True)
                    row.prop(scene.floatscreenproperty, "display_X")
                    row.prop(scene.floatscreenproperty, "display_Y")
                
                layout.label(text="Set depth filter parameter:")
                
                box = layout.box() 
                row = box.row(align=True)
                row = box.row()
                row.prop(scene.floatscreenproperty, "UPDATE_DEPTHFILTER")
                row = box.row()
                row.prop(scene.floatscreenproperty, "IGNORE_ZERODEPTH")
                row = box.row()
                row.prop(config, "depth_scale")
                row = box.row()
                row.prop(config, "depth_ignore")
                meandepth = np.mean(np.array(context.object["depth"]["depth"])) * config.depth_scale
                box.label(text="Mean depth for current image is : {0:.3f}m".format(meandepth))
                

            elif object_type == "setting":
                object = bpy.data.objects[current_object]
                scene = context.scene
                layout = self.layout
                layout.label(text="Set Workspace Name:")
                row = layout.row()
                row.prop(config, 'projectname')
                row.operator("object_property.workspacerename")
                layout.label(text="Set Environment:")

                row = layout.row()
                row.prop(config, 'modelsrc')
                row.operator("import_data.model")

                row = layout.row()
                # row.prop(config, 'modelposesrc')
                row.operator("import_data.modelfrompose")
                row.operator("export_data.objectposes")

                row = layout.row()
                row.prop(config, 'datasrc')
                row.operator("object_property.importcamrgbdepth")

                row = layout.row()
                row.prop(config, 'reconstructionsrc')
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
                row.operator("reconstruction.depthfusion")

                layout.label(text="Data Output:")
                box = layout.box() 
                row = box.row(align=True)
                row.operator("export_data.dataoutput")  

def register():
    bpy.utils.register_class(ObjectPropertyPanel)


def unregister():
    bpy.utils.unregister_class(ObjectPropertyPanel)