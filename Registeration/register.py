import bpy
import FileImporter.model_loader 

def register():
    FileImporter.model_loader.register()

def unregister():
    FileImporter.model_loader.unregister()