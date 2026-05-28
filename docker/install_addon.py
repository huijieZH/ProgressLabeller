"""Auto-install + enable the ProgressLabeller add-on on Blender startup.

Blender's `addon_install` op expects a .zip or single .py; ProgressLabeller is a
multi-file directory, so we symlink the bind-mounted repo into the user
addons dir and enable it by module name.
"""
import bpy
import os
import sys
import glob
import shutil
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

# Drop the image-built orb3_extension .so into the bind-mounted addon tree
# where `from kernel.orb_slam3.build import orb3_extension` expects it.
for built in glob.glob("/opt/orb3_extension_src/build/orb3_extension*.so"):
    dest_dir = pathlib.Path(ADDON_SRC) / "kernel" / "orb_slam3" / "build"
    dest_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(built, dest_dir / pathlib.Path(built).name)

# Extract the ORB vocabulary if only the tarball is present. The default
# vocab path in operators/ReconstructionOperator.py points at the .txt;
# without this step ORB_SLAM3 fails with "Wrong path to vocabulary".
import tarfile
vocab_dir = pathlib.Path(ADDON_SRC) / "kernel" / "orb_slam"
vocab_txt = vocab_dir / "ORBvoc.txt"
vocab_tgz = vocab_dir / "ORBvoc.txt.tar.gz"
if not vocab_txt.exists() and vocab_tgz.exists():
    print(f"[{ADDON_NAME}] extracting {vocab_tgz.name} (one-time, ~145MB)")
    with tarfile.open(vocab_tgz, "r:gz") as tf:
        tf.extractall(vocab_dir)

# Make the new addon visible to Blender's addon loader.
sys.path.insert(0, str(addons_dir))
importlib.invalidate_caches()
addon_utils.modules_refresh()

bpy.ops.preferences.addon_enable(module=ADDON_NAME)
bpy.ops.wm.save_userpref()
print(f"[{ADDON_NAME}] add-on linked at {link} and enabled")
