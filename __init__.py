bl_info = {
    "name": "Progress Labeller",
    "description": "Precisely segment object-wise image from sfm results",
    "author": "Huijie Zhang, Zeren Yu",
    "location": "File/Import and File/Export",
    "version": (1, 0),
    "blender": (2, 92, 0),
}


import bpy
import sys
import os

## if start run from script, the root is the addons
if "ProgressLabeller" in os.listdir("./"):
    sys.path.append("./ProgressLabeller")
## if start run from script, the root is the ProgressLabeller
else:
    sys.path.append("./")

import registeration.register 

def register():
    registeration.register.register()

def unregister():
    registeration.register.unregister()

if __name__ == "__main__":
    register()
