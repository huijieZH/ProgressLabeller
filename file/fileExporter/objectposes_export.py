import bpy

from kernel.exporter import objectposes_export

# ImportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.
from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty
from bpy.types import Operator


class ExportObjectPoses(Operator, ExportHelper):
    """This appears in the tooltip of the operator and in the generated docs"""
    bl_idname = "export_data.objectposes"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "Save Object Poses"

    # ExportHelper mixin class uses this
    filename_ext = ".yaml"

    filter_glob: StringProperty(
        default="*.yaml",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    def execute(self, context):
        assert context.object['type'] == 'setting'
        config_id = context.object['config_id']
        config = bpy.context.scene.configuration[config_id]
        workspace_name = config.projectname
        objectposes_export(workspace_name, self.filepath)
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        assert context.object['type'] == 'setting'
        config_id = context.object['config_id']
        config = bpy.context.scene.configuration[config_id]
        if "dir" in context.object:
            self.filepath = (config.reconstructionsrc if config.reconstructionsrc.endswith("/") else config.reconstructionsrc + "/") + "label_pose.yaml"
        # Tells Blender to hang on for the slow user input
        return {'RUNNING_MODAL'}

def register():
    bpy.utils.register_class(ExportObjectPoses)

def unregister():
    bpy.utils.unregister_class(ExportObjectPoses)