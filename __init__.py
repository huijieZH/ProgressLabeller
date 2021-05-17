bl_info = {
    "name": "Progress Labeller",
    "description": "Precisely segment object-wise image from sfm results",
    "author": "Huijie Zhang, Zeren Yu",
    "version": (1, 0),
    "blender": (2, 92, 0),
}


import bpy
import sys
sys.path.append("./")

from registeration.register import register, unregister

if __name__ == "__main__":
    register()
