import bpy
from FileImporter.kernel_function import load_reconstruction_result

# ImportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, EnumProperty, FloatProperty
from bpy.types import Operator


class ImportReconstruction(Operator, ImportHelper):
    """Load model for pose alignment and segmentation"""
    bl_idname = "import_data.reconstruction"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "Import Reconstruction Result"

    # ImportHelper mixin class uses this
    filename_ext = "/"

    filter_glob: StringProperty(
        default="/",
        options={'HIDDEN'},
        maxlen=255,  # Max internal buffer length, longer would be clamped.
    )

    reconstruction_method: EnumProperty(
        name="Reconstruction Method",
        description="Choose the method you use for your reconstruction data",
        items=(
            ('COLMAP', "COLMAP", "COLMAP"),
            ('KinectFusion', "KinectFusion", "KinectFusion"),
            ('Meshroom', "Meshroom", "Meshroom"),
        ),
        default='COLMAP',
    )    

    pointcloudscale: FloatProperty(
        name="Scale", 
        description="scale for the loading point cloud", 
        default=0.2, min=0.00, 
        max=1.00, step=2, precision=2)


    # List of operator properties, the attributes will be assigned
    # to the class instance from the operator settings before calling.

    def execute(self, context):
        load_reconstruction_result(filepath = self.filepath, 
                                   reconstruction_method = self.reconstruction_method,
                                   pointcloudscale = self.pointcloudscale)
        return {'FINISHED'}
    
    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        if bpy.context.scene.configuration.reconstructionsrc != "":
            self.filepath = bpy.context.scene.configuration.reconstructionsrc
        # Tells Blender to hang on for the slow user input
        return {'RUNNING_MODAL'}

def _menu_func_import(self, context):
    self.layout.operator(ImportReconstruction.bl_idname, text="ProgressLabeller Load Reconstruction Result(package)")



def register():
    bpy.utils.register_class(ImportReconstruction)
    bpy.types.TOPBAR_MT_file_import.append(_menu_func_import)


def unregister():
    bpy.utils.unregister_class(ImportReconstruction)
    bpy.types.TOPBAR_MT_file_import.remove(_menu_func_import)