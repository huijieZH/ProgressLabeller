import bpy
from fileImporter import model_loader, reconstruction_result_loader
from registeration import init_configuration, init_collection
from panel import ObjectPropertyPanel
from operators import ObjectPropertyOperator

def register():
    ### init to UV Editing frame
    bpy.context.window.workspace = bpy.data.workspaces['UV Editing']
    
    init_configuration.register()
    init_collection.register()
    model_loader.register()
    reconstruction_result_loader.register()

    ObjectPropertyOperator.register()
    ObjectPropertyPanel.register()

def unregister():
    init_configuration.unregister()
    init_collection.unregister()
    model_loader.unregister()
    reconstruction_result_loader.unregister()
    ObjectPropertyPanel.unregister()
    ObjectPropertyOperator.unregister()