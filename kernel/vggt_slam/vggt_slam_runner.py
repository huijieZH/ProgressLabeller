"""Standalone VGGT-SLAM 2.0 runner driven by the upstream MIT-SPARK package.

Invoked as a subprocess from operators/ReconstructionOperator.py under a
sidecar interpreter (default /opt/vggt-venv/bin/python -- VGGT-SLAM needs
Python 3.11 + CUDA, but Blender 2.92 ships 3.7). The VGGT-SLAM repo is added
to sys.path via --vggt_slam_dir, and the VGGT-1B weights are cached under
--weights_dir (via TORCH_HOME) so they download once and persist.

It replicates main.py's submap loop, then extracts per-frame camera poses and
the fused point cloud directly from the solver's map (rather than its
write_poses_to_file, whose frame ids are parsed back out of filenames) and
writes ProgressLabeller's contract:

    campose.txt : IMAGE_ID QW QX QY QZ TX TY TZ CAMERA_ID NAME   (camera-to-world)
    fused.ply   : colored point cloud

Monocular mode is up-to-scale. Stereo mode feeds the left and right images
together as one reconstruction, then recovers a single metric scale by
comparing the reconstructed distance between each left/right camera pair to the
known baseline (= ||translation of T_c1_c2||, valid for a non-parallel rig).
The same RANSAC consensus voter as kernel/colmap/colmap_runner.py is used.
"""
import argparse
import glob
import os
import shutil
import sys

import numpy as np


def _prepare_environment(vggt_slam_dir, weights_dir):
    """Put the VGGT-SLAM repo on sys.path and pin the weights cache."""
    if weights_dir:
        os.makedirs(weights_dir, exist_ok=True)
        # VGGT downloads VGGT-1B via torch.hub.load_state_dict_from_url, which
        # honours TORCH_HOME; HF_HOME covers any huggingface_hub downloads.
        os.environ.setdefault("TORCH_HOME", weights_dir)
        os.environ.setdefault("HF_HOME", weights_dir)
    if vggt_slam_dir and vggt_slam_dir not in sys.path:
        sys.path.insert(0, vggt_slam_dir)


def _list_basenames(image_dir, image_list_path):
    """Frames to reconstruct: the image-list if given, else every png/jpg."""
    if image_list_path and os.path.isfile(image_list_path):
        with open(image_list_path) as f:
            names = [ln.strip() for ln in f if ln.strip()]
        if names:
            return names
    names = [os.path.basename(p) for p in glob.glob(os.path.join(image_dir, "*"))
             if os.path.splitext(p)[1].lower() in (".png", ".jpg", ".jpeg")]
    return sorted(names)


def _run_slam(solver, model, image_paths, max_loops,
              use_keyframe_downsample, min_disparity, submap_size,
              overlapping_window_size):
    """Replicate main.py's submap-building loop (headless, no viewer)."""
    import cv2

    image_subset = []
    for image_path in image_paths:
        if use_keyframe_downsample:
            img = cv2.imread(image_path)
            if solver.flow_tracker.compute_disparity(img, min_disparity, False):
                image_subset.append(image_path)
        else:
            image_subset.append(image_path)

        is_last = image_path == image_paths[-1]
        if len(image_subset) == submap_size + overlapping_window_size or \
                (is_last and len(image_subset) > 0):
            predictions = solver.run_predictions(
                image_subset, model, max_loops, None, None)
            solver.add_points(predictions)
            solver.graph.optimize()
            image_subset = image_subset[-overlapping_window_size:]


def _collect_poses(solver):
    """name -> (R_cam_to_world 3x3, camera_center 3,) for every non-LC frame.

    Overlapping frames recur across submaps; the later (optimized) submap wins,
    which is fine because all poses share one graph-optimized world frame.
    """
    from vggt_slam.slam_utils import decompose_camera

    poses = {}
    for submap in solver.map.ordered_submaps_by_key():
        if submap.get_lc_status():
            continue
        pose_mats = submap.get_all_poses_world(solver.graph, give_camera_mat=True)
        img_paths = submap.img_names
        for index in range(len(pose_mats)):
            _, rotation, center, _ = decompose_camera(pose_mats[index])
            poses[os.path.basename(img_paths[index])] = (
                np.asarray(rotation), np.asarray(center))
    return poses


def _collect_pointcloud(solver):
    """Fused colored cloud in world frame: (N,3) points, (N,3) uint8 colors."""
    points_all, colors_all = [], []
    for submap in solver.map.ordered_submaps_by_key():
        pts = submap.get_points_in_world_frame(solver.graph).reshape(-1, 3)
        points_all.append(pts)
        colors_all.append(submap.get_points_colors())
    points = np.concatenate(points_all, axis=0)
    colors = np.concatenate(colors_all, axis=0)
    return points, colors


def _write_ply(points, colors, ply_path):
    import open3d as o3d

    colors = np.asarray(colors, dtype=np.float64)
    if colors.size and colors.max() > 1.0:
        colors = colors / 255.0
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(np.asarray(points, dtype=np.float64))
    pcd.colors = o3d.utility.Vector3dVector(colors)
    o3d.io.write_point_cloud(ply_path, pcd)


def _write_campose(campose_path, ordered_names, poses):
    """poses: name -> (R_cam_to_world, center). Writes ProgressLabeller format."""
    from scipy.spatial.transform import Rotation as R

    with open(campose_path, "w") as f:
        f.write("# IMAGE_ID, QW, QX, QY, QZ, TX, TY, TZ, CAMERA_ID, NAME\n")
        f.write(" \n")
        for image_id, name in enumerate(ordered_names):
            rotation, center = poses[name]
            qx, qy, qz, qw = R.from_matrix(rotation).as_quat()  # scipy: x,y,z,w
            cx, cy, cz = center
            f.write("{0} {1:.8f} {2:.8f} {3:.8f} {4:.8f} {5:.8f} {6:.8f} {7:.8f} 1 {8}\n".format(
                image_id, qw, qx, qy, qz, cx, cy, cz, name))


def _ransac_consensus_scale(scales, inlier_tol):
    """Largest-agreement scale, refined over its inlier set.

    Mirrors kernel/colmap/colmap_runner.py::_ransac_consensus_scale: each
    candidate s_i votes for { s_j : |s_j/s_i - 1| < inlier_tol }; the winning
    set's mean is returned with its size.
    """
    scales = np.asarray(scales, dtype=np.float64)
    best_count = 0
    best_inliers = None
    best_seed = float(scales[0])
    for s_i in scales:
        inliers = scales[np.abs(scales / s_i - 1.0) < inlier_tol]
        if len(inliers) > best_count:
            best_count = len(inliers)
            best_inliers = inliers
            best_seed = float(s_i)
    refined = float(np.mean(best_inliers)) if best_inliers is not None else best_seed
    return refined, int(best_count)


def _stage_interleaved(left_dir, right_dir, basenames, staging_dir):
    """Symlink left/right images as frame_000000.png, frame_000001.png, ...

    The global sequential index is the *last* number group in the name so
    VGGT-SLAM's sort_images_by_number keeps the temporal interleave (left_t0,
    right_t0, left_t1, ...). A `_0/_1` suffix would not -- its regex pulls the
    last group, collapsing all lefts and all rights together.
    """
    shutil.rmtree(staging_dir, ignore_errors=True)
    os.makedirs(staging_dir)
    left_set = set(os.listdir(left_dir))
    right_set = set(os.listdir(right_dir))
    paired = [b for b in basenames if b in left_set and b in right_set]

    stage_map = {}   # staged basename -> (orig_base, cam: 0=left 1=right)
    idx = 0
    for base in paired:
        for cam, src_dir in ((0, left_dir), (1, right_dir)):
            staged = "frame_{0:06d}.png".format(idx)
            os.symlink(os.path.abspath(os.path.join(src_dir, base)),
                       os.path.join(staging_dir, staged))
            stage_map[staged] = (base, cam)
            idx += 1
    return stage_map, paired


def _recover_stereo_scale(poses, stage_map, baseline, min_pairs, inlier_tol):
    """Scale that aligns reconstructed left/right distances to the baseline."""
    left_poses = {}    # orig_base -> (R, C)
    right_centers = {}
    for staged_name, (rotation, center) in poses.items():
        if staged_name not in stage_map:
            continue
        orig_base, cam = stage_map[staged_name]
        if cam == 0:
            left_poses[orig_base] = (rotation, center)
        else:
            right_centers[orig_base] = center

    scales = []
    for base, (_, c_left) in left_poses.items():
        c_right = right_centers.get(base)
        if c_right is None:
            continue
        d = float(np.linalg.norm(np.asarray(c_left) - np.asarray(c_right)))
        if d > 1e-9:
            scales.append(baseline / d)

    if len(scales) < min_pairs:
        raise RuntimeError(
            "Stereo scale recovery failed: only {0} valid left/right pose pairs "
            "(need >= {1}). Check that both cameras reconstructed and the "
            "baseline ({2} m) is correct.".format(len(scales), min_pairs, baseline))

    scale, inlier_count = _ransac_consensus_scale(scales, inlier_tol)
    return scale, inlier_count, len(scales), left_poses


def _build_solver_and_model(conf_threshold):
    """Construct the VGGT-SLAM Solver (viewer stubbed out) and VGGT model."""
    import torch
    import vggt_slam.solver as solver_module
    from vggt.models.vggt import VGGT

    # Solver.__init__ starts a viser web server; we run headless and never
    # visualize, so replace it with a no-op before constructing the solver.
    class _NullViewer:
        def __init__(self, *args, **kwargs):
            pass

    solver_module.Viewer = _NullViewer
    solver = solver_module.Solver(
        init_conf_threshold=conf_threshold, lc_thres=0.95, vis_voxel_size=None)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print("[vggt_slam_runner] device:", device)
    model = VGGT()
    url = "https://huggingface.co/facebook/VGGT-1B/resolve/main/model.pt"
    model.load_state_dict(torch.hub.load_state_dict_from_url(url))
    model.eval()
    model = model.to(torch.bfloat16).to(device)
    return solver, model


def run(image_dir, output_path, image_list_path=None,
        stereo=False, left_subdir="left", right_subdir="right", baseline=None,
        min_pairs=10, inlier_tol=0.05,
        submap_size=16, overlapping_window_size=1, max_loops=1,
        conf_threshold=25.0, min_disparity=50.0, use_keyframe_downsample=False):
    os.makedirs(output_path, exist_ok=True)
    campose_path = os.path.join(output_path, "campose.txt")
    ply_path = os.path.join(output_path, "fused.ply")

    basenames = _list_basenames(
        os.path.join(image_dir, left_subdir) if stereo else image_dir,
        image_list_path)

    staging_dir = None
    stage_map = None
    if stereo:
        if baseline is None:
            raise ValueError("stereo mode requires --baseline")
        left_dir = os.path.join(image_dir, left_subdir)
        right_dir = os.path.join(image_dir, right_subdir)
        if not os.path.isdir(left_dir) or not os.path.isdir(right_dir):
            raise RuntimeError(
                "Stereo mode expects {0} and {1} to exist".format(left_dir, right_dir))
        staging_dir = os.path.join(output_path, "_vggt_stereo_pairs")
        stage_map, paired = _stage_interleaved(left_dir, right_dir, basenames, staging_dir)
        if len(paired) < min_pairs:
            raise RuntimeError(
                "Only {0} basenames found in both {1} and {2} (need >= {3})".format(
                    len(paired), left_dir, right_dir, min_pairs))
        image_paths = [os.path.join(staging_dir, n)
                       for n in sorted(stage_map, key=lambda s: int(
                           "".join(ch for ch in s if ch.isdigit())))]
    else:
        image_paths = [os.path.join(image_dir, b) for b in basenames]

    solver, model = _build_solver_and_model(conf_threshold)
    _run_slam(solver, model, image_paths, max_loops,
              use_keyframe_downsample, min_disparity,
              submap_size, overlapping_window_size)

    print("[vggt_slam_runner] submaps:", solver.map.get_num_submaps(),
          "loops:", solver.graph.get_num_loops())

    poses = _collect_poses(solver)
    points, colors = _collect_pointcloud(solver)

    if stereo:
        scale, inliers, pairs, left_poses = _recover_stereo_scale(
            poses, stage_map, baseline, min_pairs, inlier_tol)
        print("[vggt_slam_runner] stereo scale s = {0:.6f} "
              "({1} inliers / {2} pairs, baseline = {3} m)".format(
                  scale, inliers, pairs, baseline))
        # Bake metric scale into camera centers and the cloud.
        scaled_left = {base: (rotation, np.asarray(center) * scale)
                       for base, (rotation, center) in left_poses.items()}
        points = points * scale
        ordered = [b for b in basenames if b in scaled_left]
        _write_campose(campose_path, ordered, scaled_left)
        with open(os.path.join(output_path, "vggt_scale_info.txt"), "w") as f:
            f.write("scale: {0:.9f}\n".format(scale))
            f.write("baseline_m: {0}\n".format(baseline))
            f.write("inliers: {0}\n".format(inliers))
            f.write("pairs: {0}\n".format(pairs))
            f.write("inlier_tol: {0}\n".format(inlier_tol))
        shutil.rmtree(staging_dir, ignore_errors=True)
    else:
        ordered = [b for b in basenames if b in poses]
        _write_campose(campose_path, ordered, poses)

    _write_ply(points, colors, ply_path)
    print("[vggt_slam_runner] wrote {0} poses + {1} points".format(
        len(ordered), len(points)))


def _parse_args(argv):
    p = argparse.ArgumentParser(description="VGGT-SLAM 2.0 runner for ProgressLabeller")
    p.add_argument("--image_dir", required=True,
                   help="Monocular: the rgb dir. Stereo: parent dir holding left/ and right/")
    p.add_argument("--output_path", required=True)
    p.add_argument("--image_list_path", default=None,
                   help="Optional one-basename-per-line subset to reconstruct")
    p.add_argument("--vggt_slam_dir", default=os.environ.get("VGGT_SLAM_DIR", "/opt/VGGT-SLAM"))
    p.add_argument("--weights_dir", default=os.environ.get("VGGT_WEIGHTS", ""))
    # stereo scale recovery
    p.add_argument("--stereo", action="store_true")
    p.add_argument("--left_subdir", default="left")
    p.add_argument("--right_subdir", default="right")
    p.add_argument("--baseline", type=float, default=None,
                   help="Stereo: known inter-camera distance in meters (||T_c1_c2 translation||)")
    p.add_argument("--min_pairs", type=int, default=10)
    p.add_argument("--inlier_tol", type=float, default=0.05)
    # VGGT-SLAM knobs
    p.add_argument("--submap_size", type=int, default=16)
    p.add_argument("--overlapping_window_size", type=int, default=1)
    p.add_argument("--max_loops", type=int, default=1)
    p.add_argument("--conf_threshold", type=float, default=25.0)
    p.add_argument("--min_disparity", type=float, default=50.0)
    p.add_argument("--use_keyframe_downsample", action="store_true",
                   help="Drop low-disparity frames via optical flow (default: keep all)")
    return p.parse_args(argv)


def main(argv):
    args = _parse_args(argv[1:])
    _prepare_environment(args.vggt_slam_dir, args.weights_dir)
    run(
        image_dir=args.image_dir,
        output_path=args.output_path,
        image_list_path=args.image_list_path,
        stereo=args.stereo,
        left_subdir=args.left_subdir,
        right_subdir=args.right_subdir,
        baseline=args.baseline,
        min_pairs=args.min_pairs,
        inlier_tol=args.inlier_tol,
        submap_size=args.submap_size,
        overlapping_window_size=args.overlapping_window_size,
        max_loops=args.max_loops,
        conf_threshold=args.conf_threshold,
        min_disparity=args.min_disparity,
        use_keyframe_downsample=args.use_keyframe_downsample,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
