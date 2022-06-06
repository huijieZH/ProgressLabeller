import bpy
import json

from kernel.exporter import configuration_export

# ImportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.
from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty
from bpy.types import Operator


class ExportConfiguration(Operator, ExportHelper):
    """This appears in the tooltip of the operator and in the generated docs"""
    bl_idname = "export_data.configuration" 
    bl_label = "Save Configuration"

    filename_ext = ".json"

    filter_glob: StringProperty(
        default="*.json",
        options={'HIDDEN'},
        maxlen=255,  
    )

    def execute(self, context):
        assert context.object['type'] == 'setting'
        config_id = context.object['config_id']
        path = context.object['dir']
        config = bpy.context.scene.configuration[config_id]
        configuration_export(config, self.filepath)
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        if "dir" in context.object:
            self.filepath = (context.object["dir"] if context.object["dir"].endswith("/") else context.object["dir"] + "/") + "configuration.json"
        return {'RUNNING_MODAL'}



def register():
    bpy.utils.register_class(ExportConfiguration)

def unregister():
    bpy.utils.unregister_class(ExportConfiguration)