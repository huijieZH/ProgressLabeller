import bpy
from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator
from kernel.loader import create_workspace
import os

class CreateNewWorkspace(Operator, ExportHelper):
    """This appears in the tooltip of the operator and in the generated docs"""
    bl_idname = "new.new_work_space"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "Create New Work Space"

    # ExportHelper mixin class uses this
    filename_ext = ""

    filter_glob: StringProperty(
        default="/",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    def execute(self, context):
        path, name = os.path.split(self.filepath)
        create_workspace(path, name)
        return {'FINISHED'}

    # def invoke(self, context, event):
    #     context.window_manager.fileselect_add(self)
    #     self.filepath = "/home/"
    #     # Tells Blender to hang on for the slow user input
    #     return {'RUNNING_MODAL'}

  


# Only needed if you want to add into a dynamic menu
def menu_func_export(self, context):
    self.layout.operator(CreateNewWorkspace.bl_idname, text="ProgressLabeller Create New Workspace")


def register():
    bpy.utils.register_class(CreateNewWorkspace)
    bpy.types.TOPBAR_MT_file_new.append(menu_func_export)


def unregister():
    bpy.utils.unregister_class(CreateNewWorkspace)
    bpy.types.TOPBAR_MT_file_new.remove(menu_func_export)
