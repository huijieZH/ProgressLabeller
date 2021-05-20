import bpy
from fileImporter import model_loader, reconstruction_result_loader, configuration_loader
from registeration import init_configuration
from panel import ObjectPropertyPanel
from operators import ObjectPropertyOperator

def register():

    init_configuration.register()
    configuration_loader.register()
    model_loader.register()
    reconstruction_result_loader.register()

    ObjectPropertyOperator.register()
    ObjectPropertyPanel.register()

def unregister():
    init_configuration.unregister()
    configuration_loader.unregister()
    model_loader.unregister()
    reconstruction_result_loader.unregister()
    ObjectPropertyPanel.unregister()
    ObjectPropertyOperator.unregister()