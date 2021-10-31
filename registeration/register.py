import bpy
from file.fileImporter import model_loader, reconstruction_result_loader, configuration_loader
from file.fileNew import new_workspace
from file.fileExporter import configuration_export, objectposes_export, data_export
from registeration import init_configuration
from panel import ObjectPropertyPanel, FloatScreenPanel
from operators import ObjectPropertyOperator, ReconstructionOperator

def register():
    init_configuration.register()
    configuration_loader.register()
    model_loader.register()
    reconstruction_result_loader.register()
    new_workspace.register()
    ObjectPropertyOperator.register()
    ReconstructionOperator.register()
    ObjectPropertyPanel.register()
    FloatScreenPanel.register()

    configuration_export.register()
    objectposes_export.register()
    data_export.register()

def unregister():
    init_configuration.unregister()
    configuration_loader.unregister()
    model_loader.unregister()
    reconstruction_result_loader.unregister()
    new_workspace.unregister()
    ObjectPropertyPanel.unregister()
    ObjectPropertyOperator.unregister()
    ReconstructionOperator.unregister()
    configuration_export.unregister()
    objectposes_export.unregister()
    FloatScreenPanel.unregister()
    data_export.unregister()