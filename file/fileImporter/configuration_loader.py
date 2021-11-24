import bpy
from kernel.loader import load_configuration

# ImportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty
from bpy.types import Operator


class ImportConfiguration(Operator, ImportHelper):
    """Load model for pose alignment and segmentation"""
    bl_idname = "import_data.configuration"  
    bl_label = "Import Configuration"

    # ImportHelper mixin class uses this
    filename_ext = ".json"

    filter_glob: StringProperty(
        default="*.json",
        options={'HIDDEN'},
        maxlen=255,  
    )

    def execute(self, context):
        load_configuration(self.filepath)
        return {'FINISHED'}
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}


def _menu_func_import(self, context):
    self.layout.operator(ImportConfiguration.bl_idname, text="ProgressLabeller Configuration(.json)")


def register():
    bpy.utils.register_class(ImportConfiguration)
    bpy.types.TOPBAR_MT_file_import.append(_menu_func_import)

def unregister():
    bpy.utils.unregister_class(ImportConfiguration)
    bpy.types.TOPBAR_MT_file_import.remove(_menu_func_import)