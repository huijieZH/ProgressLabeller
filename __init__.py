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

# ## if start run from script, the root is the addons
# if "ProgressLabeller" in os.listdir("./"):
#     print(os.path.dirname(os.path.abspath(__file__)))
#     sys.path.append("./ProgressLabeller")
# ## if start run from script, the root is the ProgressLabeller
# else:
#     print(os.path.dirname(os.path.abspath(__file__)))
#     sys.path.append("./")

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import registeration.register 


def register():
    registeration.register.register()

def unregister():
    registeration.register.unregister()

if __name__ == "__main__":
    print(os.path.abspath(__file__))
    register()
