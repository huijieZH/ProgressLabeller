import logging
import bpy

logging.basicConfig(level=logging.INFO)
_logger = logging.getLogger()

def ShowMessageBox(message = "", title = "An ProgressLabeller error", icon = 'ERROR'):

    def draw(self, context):
        self.layout.label(text = message)

    bpy.context.window_manager.popup_menu(draw, title = title, icon = icon)


def log_report(output_type, some_str, op=None):
    """ Write a string to the console and to Blender's info area."""
    # output_type is one of: 'INFO', 'WARNING' or 'ERROR'
    if output_type in ['ERROR', 'Error']:
        ShowMessageBox(message=some_str)
    _logger.info(output_type + ": " + some_str)
    if op is not None:
        op.report({output_type}, some_str)




