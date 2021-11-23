import bpy
import json
import os

from kernel.exporter import data_export
from kernel.logging_utility import log_report

# ImportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.
from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty, EnumProperty
from bpy.types import Operator
from kernel.exporter import configuration_export, objectposes_export

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

    dataformatType: EnumProperty(
        name="Output format",
        description="Choose a output format",
        items=(
            ('BOP', "BOP", "BOP challenge format"),
            ('YCBV', "YCBV", "YCBV dataset format"),
            ('ProgressLabeller', "ProgressLabeller", "ProgressLabeller format")
        ),
        default='ProgressLabeller',
    )

    def execute(self, context):

        assert context.object['type'] == 'setting'
        config_id = context.object['config_id']
        path = context.object['dir']
        config = bpy.context.scene.configuration[config_id]

        files = os.listdir(config.reconstructionsrc)
        if "campose.txt" not in files:
            log_report(
                "Error", "Please do reconstruction first", None
            )
        elif "label_pose.yaml" not in files:
            log_report(
                "Error", "Please allocate the object in the scene and save object poses", None
            )
        else:
            configuration_export(config, "/tmp/progresslabeler.json")
            # objectposes_export(config.projectname, os.path.join(config.reconstructionsrc, "label_pose.yaml"))
            log_report(
                "Info", "Export data to" + self.filepath, None
            )
            data_export("/tmp/progresslabeler.json", self.filepath, self.dataformatType)
            os.remove("/tmp/progresslabeler.json")
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