#!/usr/bin/env python3
"""Convert an AILight stereo recording into the ProgressLabeller dataset layout.

Reads:
  - left/right per-frame PNGs (timestamp-named, shared filenames across the pair)
  - left/right AILight calibration YAMLs (intrinsic, distortion, extrinsic_pose)

Writes:
  <output>/
    configuration.json     # sensor_mode=STEREO, paths, left intrinsics
    stereo_calib.yaml      # right intrinsics + distortion + baseline + T_c1_c2
    data/left/000000.png ...
    data/right/000000.png ...

Quaternion convention in the calibration YAML is Hamilton order: q = [qw, qx, qy, qz].
"""

import argparse
import json
import math
import os
import shutil
import sys

import numpy as np
import yaml


def _quat_wxyz_to_R(q):
    w, x, y, z = q
    n = math.sqrt(w * w + x * x + y * y + z * z)
    if n == 0:
        raise ValueError("zero quaternion")
    w, x, y, z = w / n, x / n, y / n, z / n
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w),     2 * (x * z + y * w)],
        [2 * (x * y + z * w),     1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w),     2 * (y * z + x * w),     1 - 2 * (x * x + y * y)],
    ])


def _pose_to_T(p, q_wxyz):
    R = _quat_wxyz_to_R(q_wxyz)
    T = np.eye(4)
    T[:3, :3] = R
    T[:3, 3] = p
    return T


def _load_calib(path):
    with open(path, "r") as fh:
        data = yaml.safe_load(fh)
    K = np.array(data["intrinsic"], dtype=float)
    dist = list(data.get("distortion", []))
    while len(dist) < 4:
        dist.append(0.0)
    p = np.array(data["extrinsic_pose"]["p"], dtype=float)
    q = np.array(data["extrinsic_pose"]["q"], dtype=float)
    return {
        "K": K,
        "dist": [float(v) for v in dist[:4]],
        "p": p,
        "q": q,
    }


def _copy_pairs(left_dir, right_dir, out_left, out_right, limit=None):
    left_files = sorted(os.listdir(left_dir))
    right_files = set(os.listdir(right_dir))
    pairs = []
    skipped = []
    for name in left_files:
        if name in right_files:
            pairs.append(name)
        else:
            skipped.append(name)

    if limit is not None:
        pairs = pairs[:limit]

    os.makedirs(out_left, exist_ok=True)
    os.makedirs(out_right, exist_ok=True)

    for idx, name in enumerate(pairs):
        out_name = "{0:06d}.png".format(idx)
        shutil.copyfile(os.path.join(left_dir, name), os.path.join(out_left, out_name))
        shutil.copyfile(os.path.join(right_dir, name), os.path.join(out_right, out_name))

    return pairs, skipped


def _write_stereo_calib(path, right_calib, baseline, T_c1_c2):
    payload = {
        "fx2": float(right_calib["K"][0, 0]),
        "fy2": float(right_calib["K"][1, 1]),
        "cx2": float(right_calib["K"][0, 2]),
        "cy2": float(right_calib["K"][1, 2]),
        "k1": right_calib["dist"][0],
        "k2": right_calib["dist"][1],
        "p1": right_calib["dist"][2],
        "p2": right_calib["dist"][3],
        "baseline": float(baseline),
        "T_c1_c2": [[float(v) for v in row] for row in T_c1_c2],
    }
    with open(path, "w") as fh:
        yaml.safe_dump(payload, fh, sort_keys=False, default_flow_style=None)


def _write_configuration_json(path, project_name, output_root, modelsrc, left_K, width, height):
    cfg = {
        "projectname": project_name,
        "environment": {
            "modelsrc": modelsrc,
            "reconstructionsrc": os.path.join(output_root, "recon"),
            "datasrc": os.path.join(output_root, "data"),
        },
        "camera": {
            "resolution": [int(width), int(height)],
            "intrinsic": [[float(left_K[i, j]) for j in range(3)] for i in range(3)],
            "inverse_pose": False,
            "lens": 30.0,
        },
        "reconstruction": {
            "scale": 1.0,
            "cameradisplayscale": 0.01,
            "recon_trans": "1,0,0,0;0,1,0,0;0,0,1,0;0,0,0,1;",
            "sensor_mode": "STEREO",
        },
        "data": {
            "sample_rate": 0.1,
            "depth_scale": 0.001,
            "depth_ignore": 8.0,
        },
    }
    with open(path, "w") as fh:
        json.dump(cfg, fh, indent=2)


def main(argv=None):
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--left-images",
        default=os.path.join(repo_root, "data/test/video/left_hand_left_camera"))
    parser.add_argument("--right-images",
        default=os.path.join(repo_root, "data/test/video/left_hand_right_camera"))
    parser.add_argument("--left-calib",
        default="/opt/robot/RoboConfig/calib_param/aililight_cameras/left_hand_left_camera.yaml")
    parser.add_argument("--right-calib",
        default="/opt/robot/RoboConfig/calib_param/aililight_cameras/left_hand_right_camera.yaml")
    parser.add_argument("--output",
        default=os.path.join(repo_root, "data/left_hand_dataset"))
    parser.add_argument("--project-name", default="left_hand_video")
    parser.add_argument("--modelsrc",
        default="/home/yuzeren/Downloads/progresslabellerdemo/model")
    parser.add_argument("--limit", type=int, default=None,
        help="copy only the first N matched pairs (for testing)")
    parser.add_argument("--no-copy", action="store_true",
        help="emit configuration + stereo_calib only; skip image copy")
    args = parser.parse_args(argv)

    print("[1/4] Loading calibrations...")
    left = _load_calib(args.left_calib)
    right = _load_calib(args.right_calib)
    print("  left  K = {0}".format(left["K"][:2].tolist()))
    print("  right K = {0}".format(right["K"][:2].tolist()))

    print("[2/4] Computing stereo extrinsic (T_c1_c2)...")
    T_world_left = _pose_to_T(left["p"], left["q"])
    T_world_right = _pose_to_T(right["p"], right["q"])
    T_left_right = np.linalg.inv(T_world_left) @ T_world_right
    baseline = float(np.linalg.norm(T_left_right[:3, 3]))
    print("  baseline = {0:.4f} m".format(baseline))
    if not (0.01 <= baseline <= 0.50):
        print("  WARNING: baseline outside [0.01, 0.50] m -- quaternion convention may be wrong.")
    print("  T_left_right translation = {0}".format(T_left_right[:3, 3].tolist()))

    output_root = os.path.abspath(args.output)
    os.makedirs(output_root, exist_ok=True)
    data_root = os.path.join(output_root, "data")
    out_left = os.path.join(data_root, "left")
    out_right = os.path.join(data_root, "right")

    print("[3/4] Writing configuration files to {0}".format(output_root))
    # Determine resolution from one source image. Fall back to (1280, 800) if PIL unavailable.
    width, height = 1280, 800
    try:
        from PIL import Image
        sample_name = sorted(os.listdir(args.left_images))[0]
        with Image.open(os.path.join(args.left_images, sample_name)) as im:
            width, height = im.size
    except Exception as e:
        print("  (could not inspect image resolution: {0}; defaulting to {1}x{2})".format(
            e, width, height))

    _write_stereo_calib(os.path.join(output_root, "stereo_calib.yaml"),
                        right, baseline, T_left_right)
    _write_configuration_json(os.path.join(output_root, "configuration.json"),
                              args.project_name, output_root, args.modelsrc,
                              left["K"], width, height)

    print("[4/4] Copying image pairs...")
    if args.no_copy:
        print("  --no-copy set; skipping image copy.")
        pairs = sorted(set(os.listdir(args.left_images)) & set(os.listdir(args.right_images)))
        skipped = sorted(set(os.listdir(args.left_images)) - set(os.listdir(args.right_images)))
    else:
        pairs, skipped = _copy_pairs(args.left_images, args.right_images,
                                     out_left, out_right, limit=args.limit)

    print()
    print("Done.")
    print("  matched pairs : {0}".format(len(pairs)))
    if skipped:
        print("  unmatched left frames (skipped): {0}".format(len(skipped)))
    print("  output root   : {0}".format(output_root))
    print("  configuration : {0}".format(os.path.join(output_root, "configuration.json")))
    print("  stereo calib  : {0}".format(os.path.join(output_root, "stereo_calib.yaml")))
    print("  resolution    : {0}x{1}".format(width, height))
    print()
    print("In the Blender panel: set datasrc to '{0}',".format(data_root))
    print("and stereo_calib_path to '{0}'.".format(
        os.path.join(output_root, "stereo_calib.yaml")))


if __name__ == "__main__":
    sys.exit(main())
