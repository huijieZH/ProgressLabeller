import bpy
import json

from kernel.exporter import data_export

# ImportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.
from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty
from bpy.types import Operator


class DataOutput(Operator, ExportHelper):
    """This appears in the tooltip of the operator and in the generated docs"""
    bl_idname = "export_data.dataoutput"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "Output Data"

    # ExportHelper mixin class uses this
    filename_ext = "/"

    filter_glob: StringProperty(
        default="/",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    def execute(self, context):
        assert context.object['type'] == 'setting'
        config_id = context.object['config_id']
        path = context.object['dir']
        config = bpy.context.scene.configuration[config_id]
        data_export(config, self.filepath)
        print('hi')
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        if "dir" in context.object:
            self.filepath = (context.object["dir"] if context.object["dir"].endswith("/") else context.object["dir"] + "/") + "output"
        # Tells Blender to hang on for the slow user input
        return {'RUNNING_MODAL'}



def register():
    bpy.utils.register_class(DataOutput)

def unregister():
    bpy.utils.unregister_class(DataOutput)