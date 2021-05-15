import bpy
from FileImporter import model_loader, reconstruction_result_loader
from Registeration import init_configuration, init_collection

def register():
    init_configuration.register()
    init_collection.register()
    model_loader.register()
    reconstruction_result_loader.register()

def unregister():
    init_configuration.unregister()
    init_collection.unregister()
    model_loader.unregister()
    reconstruction_result_loader.register()