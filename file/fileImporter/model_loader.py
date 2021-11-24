import bpy
from kernel.loader import load_model, load_model_from_pose

# ImportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty
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
        load_model(self.filepath, context.object["config_id"])
        return {'FINISHED'}
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        if hasattr(bpy.context.scene.configuration[context.object["config_id"]], 'modelsrc'):
            self.filepath = bpy.context.scene.configuration[context.object["config_id"]].modelsrc + "/"
        # Tells Blender to hang on for the slow user input
        return {'RUNNING_MODAL'}


class ImportModelfromPoseFile(Operator, ImportHelper):
    """Load model for pose alignment and segmentation from a pose file"""
    bl_idname = "import_data.modelfrompose"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "Import Model from pose"

    # ImportHelper mixin class uses this
    filename_ext = ".yaml"

    filter_glob: StringProperty(
        default="*.yaml",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    # List of operator properties, the attributes will be assigned
    # to the class instance from the operator settings before calling.

    def execute(self, context):
        print(self.filepath)
        load_model_from_pose(self.filepath, context.object["config_id"])
        return {'FINISHED'}
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        if hasattr(bpy.context.scene.configuration[context.object["config_id"]], 'reconstructionsrc'):
            if bpy.context.scene.configuration[context.object["config_id"]].reconstructionsrc[-1] != "/":
                self.filepath = bpy.context.scene.configuration[context.object["config_id"]].reconstructionsrc + "/"
            else:
                self.filepath = bpy.context.scene.configuration[context.object["config_id"]].reconstructionsrc
        # Tells Blender to hang on for the slow user input
        return {'RUNNING_MODAL'}

def _menu_func_import(self, context):
    self.layout.operator(ImportModel.bl_idname, text="ProgressLabeller Model(.obj)")
    self.layout.operator(ImportModelfromPoseFile.bl_idname, text="ProgressLabeller Model from pose file(.yaml)")



def register():
    bpy.utils.register_class(ImportModel)
    bpy.utils.register_class(ImportModelfromPoseFile)
    # bpy.types.TOPBAR_MT_file_import.append(_menu_func_import)


def unregister():
    bpy.utils.unregister_class(ImportModel)
    bpy.utils.unregister_class(ImportModelfromPoseFile)
    # bpy.types.TOPBAR_MT_file_import.remove(_menu_func_import)