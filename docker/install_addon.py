"""Auto-install + enable the ProgressLabeller add-on on Blender startup.

Blender's `addon_install` op expects a .zip or single .py; ProgressLabeller is a
multi-file directory, so we symlink the bind-mounted repo into the user
addons dir and enable it by module name.
"""
import bpy
import os
import sys
import importlib
import pathlib
import addon_utils

ADDON_NAME = "ProgressLabeller"
ADDON_SRC = "/workspace/ProgressLabeller"

addons_dir = pathlib.Path(bpy.utils.user_resource("SCRIPTS", path="addons"))
addons_dir.mkdir(parents=True, exist_ok=True)

link = addons_dir / ADDON_NAME
if link.is_symlink() or link.exists():
    if not link.is_symlink() or os.readlink(link) != ADDON_SRC:
        if link.is_symlink() or link.is_file():
            link.unlink()
        else:
            import shutil
            shutil.rmtree(link)
        link.symlink_to(ADDON_SRC)
else:
    link.symlink_to(ADDON_SRC)

# Make the new addon visible to Blender's addon loader.
sys.path.insert(0, str(addons_dir))
importlib.invalidate_caches()
addon_utils.modules_refresh()

bpy.ops.preferences.addon_enable(module=ADDON_NAME)
bpy.ops.wm.save_userpref()
print(f"[{ADDON_NAME}] add-on linked at {link} and enabled")
