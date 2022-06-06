import bpy
from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator
from kernel.loader import create_workspace, init_package
from kernel.blender_utility import _get_configuration
import os

class CreateNewWorkspace(Operator, ExportHelper):
    """This appears in the tooltip of the operator and in the generated docs"""
    bl_idname = "new.new_work_space"  
    bl_label = "Create New Work Space"

    filename_ext = ""

    filter_glob: StringProperty(
        default="/",
        options={'HIDDEN'},
        maxlen=255,  
    )

    def execute(self, context):
        path, name = os.path.split(self.filepath)
        create_workspace(path, name)
        _, config = _get_configuration(bpy.data.objects[name + ":Setting"])
        init_package(path, config)
        
        return {'FINISHED'}


  


# Only needed if you want to add into a dynamic menu
def menu_func_export(self, context):
    self.layout.operator(CreateNewWorkspace.bl_idname, text="ProgressLabeller Create New Workspace")


def register():
    bpy.utils.register_class(CreateNewWorkspace)
    bpy.types.TOPBAR_MT_file_new.append(menu_func_export)


def unregister():
    bpy.utils.unregister_class(CreateNewWorkspace)
    bpy.types.TOPBAR_MT_file_new.remove(menu_func_export)
