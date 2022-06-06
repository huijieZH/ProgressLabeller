bl_info = {
    "name": "ProgressLabeller",
    "description": "Precisely segment object-wise image from sfm results",
    "location": "File/Import and File/Export",
    "version": (1, 0),
    "blender": (2, 92, 0),
}


import bpy
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import registeration.register 


def register():
    registeration.register.register()

def unregister():
    registeration.register.unregister()

if __name__ == "__main__":
    register()
