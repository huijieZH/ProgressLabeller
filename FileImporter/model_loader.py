import bpy





# ImportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator


class ImportModel(Operator, ImportHelper):
    """Load model for pose alignment and segmentation"""
    bl_idname = "import_data.model"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "Import Model"

    # ImportHelper mixin class uses this
    filename_ext = ".obj"

    filter_glob: StringProperty(
        default="*.obj",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    # List of operator properties, the attributes will be assigned
    # to the class instance from the operator settings before calling.

    def execute(self, context):
        return _load_model(self.filepath)

def _load_model(filepath):
    objFilename = filepath.split("/")[-1]
    objName = objFilename.split(".")[0]
    bpy.ops.import_scene.obj(filepath=filepath)
    bpy.context.selected_objects[0].name = objName
    bpy.ops.object.select_all(action='DESELECT')
    bpy.data.objects[objName].rotation_mode = 'QUATERNION'
    return {'FINISHED'}

def _menu_func_import(self, context):
    self.layout.operator(ImportModel.bl_idname, text="ProgressLabeller Model(.obj)")


def register():
    bpy.utils.register_class(ImportModel)
    bpy.types.TOPBAR_MT_file_import.append(_menu_func_import)


def unregister():
    bpy.utils.unregister_class(ImportModel)
    bpy.types.TOPBAR_MT_file_import.remove(_menu_func_import)