import bpy
from kernel.loader import load_model, load_model_from_pose

# ImportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty
from bpy.types import Operator


class ImportModel(Operator, ImportHelper):
    """Load model for pose alignment and segmentation"""
    bl_idname = "import_data.model"  
    bl_label = "Import Model"
    filename_ext = ".obj"

    filter_glob: StringProperty(
        default="*.obj",
        options={'HIDDEN'},
        maxlen=255,  
    )

    def execute(self, context):
        load_model(self.filepath, context.object["config_id"])
        return {'FINISHED'}
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        if hasattr(bpy.context.scene.configuration[context.object["config_id"]], 'modelsrc'):
            self.filepath = bpy.context.scene.configuration[context.object["config_id"]].modelsrc + "/"
        return {'RUNNING_MODAL'}


class ImportModelfromPoseFile(Operator, ImportHelper):
    """Load model for pose alignment and segmentation from a pose file"""
    bl_idname = "import_data.modelfrompose"  
    bl_label = "Import Model from pose"

    filename_ext = ".yaml"

    filter_glob: StringProperty(
        default="*.yaml",
        options={'HIDDEN'},
        maxlen=255,  
    )


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
        return {'RUNNING_MODAL'}

def _menu_func_import(self, context):
    self.layout.operator(ImportModel.bl_idname, text="ProgressLabeller Model(.obj)")
    self.layout.operator(ImportModelfromPoseFile.bl_idname, text="ProgressLabeller Model from pose file(.yaml)")



def register():
    bpy.utils.register_class(ImportModel)
    bpy.utils.register_class(ImportModelfromPoseFile)



def unregister():
    bpy.utils.unregister_class(ImportModel)
    bpy.utils.unregister_class(ImportModelfromPoseFile)