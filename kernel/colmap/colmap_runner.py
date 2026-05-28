"""Standalone COLMAP runner driven by pycolmap.

Invoked as a subprocess from operators/ReconstructionOperator.py under a
sidecar venv (default /opt/colmap-venv/bin/python — pycolmap requires
Python 3.10+, but Blender 2.92 ships 3.7).

Feature extraction and matching are done by COLMAP; the reconstruction /
bundle-adjustment stage uses COLMAP's incremental SfM via
`pycolmap.incremental_mapping`.

Supports monocular and stereo reconstruction. In stereo mode, both left
and right images are registered as a two-camera SfM, and the known
stereo baseline is used to recover absolute metric scale via
RANSAC-style consensus over per-pair recovered baselines.

GPU SIFT requires a from-source pycolmap build with CUDA; PyPI wheels are
CPU-only, so num_threads is the only knob we expose.
"""
import argparse
import os
import shutil
import sys

import numpy as np
import pycolmap


def _filter_campose(images_txt, campose_txt, name_map=None):
    """COLMAP images.txt -> ProgressLabeller's campose.txt.

    Keeps the image-header lines (start with image_id int, end with .png)
    and drops every POINTS2D line and comment line. In stereo mode the
    caller passes name_map={staged_left_name: "left/<base>"}: only entries
    whose NAME is a key are kept (drops the right-camera entries) and the
    NAME field is rewritten back to the original "left/<base>" so the
    loader, which keys cameras by filename basename (see
    kernel/loader.py:300), sees the real frame names.
    """
    with open(images_txt) as fin, open(campose_txt, "w") as fout:
        fout.write("# IMAGE_ID, QW, QX, QY, QZ, TX, TY, TZ, CAMERA_ID, NAME\n")
        fout.write(" \n")
        for line in fin:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            first = stripped.split(" ", 1)[0]
            if not first.isdigit():
                continue
            if not stripped.endswith(".png"):
                continue
            if name_map is not None:
                head, name = stripped.rsplit(" ", 1)
                if name not in name_map:
                    continue
                fout.write("{0} {1}\n".format(head, name_map[name]))
                continue
            fout.write(line if line.endswith("\n") else line + "\n")


def _build_extract_opts(num_threads):
    opts = pycolmap.FeatureExtractionOptions()
    opts.use_gpu = False
    if num_threads >= 0:
        opts.num_threads = num_threads
    return opts


def _build_match_opts(num_threads):
    opts = pycolmap.FeatureMatchingOptions()
    opts.use_gpu = False
    if num_threads >= 0:
        opts.num_threads = num_threads
    return opts


def _extract_single_camera(database_path, image_path, image_names,
                           camera_params, num_threads):
    reader_opts = pycolmap.ImageReaderOptions()
    reader_opts.camera_model = "PINHOLE"
    reader_opts.camera_params = camera_params
    pycolmap.extract_features(
        database_path=database_path,
        image_path=image_path,
        image_names=image_names,
        camera_mode=pycolmap.CameraMode.SINGLE,
        reader_options=reader_opts,
        extraction_options=_build_extract_opts(num_threads),
    )


def _build_sequential_opts(overlap):
    # pycolmap 4.x: the sequential window is a pairing option, separate
    # from FeatureMatchingOptions. overlap = number of subsequent images
    # (in filename-sorted order) each image is matched against.
    opts = pycolmap.SequentialPairingOptions()
    opts.overlap = overlap
    return opts


def _run_matching(database_path, matcher, num_threads, overlap):
    match_opts = _build_match_opts(num_threads)
    if matcher == "exhaustive":
        pycolmap.match_exhaustive(
            database_path=database_path,
            matching_options=match_opts,
        )
    else:
        pycolmap.match_sequential(
            database_path=database_path,
            pairing_options=_build_sequential_opts(overlap),
            matching_options=match_opts,
        )


def _build_incremental_mapper_opts(num_threads, refine_focal_length):
    opts = pycolmap.IncrementalPipelineOptions()
    # User supplies calibrated fx,fy,cx,cy (and right intrinsics from
    # stereo_calib.yaml in stereo mode). Lock the intrinsics by default;
    # refine_focal_length is the Blender-panel toggle. principal_point /
    # extra_params stay off (PINHOLE has no extra params).
    opts.ba_refine_focal_length = refine_focal_length
    opts.ba_refine_principal_point = False
    opts.ba_refine_extra_params = False
    if num_threads >= 0:
        opts.num_threads = num_threads
    return opts


def _run_incremental_mapping(database_path, image_dir, output_path,
                             num_threads, refine_focal_length):
    reconstructions = pycolmap.incremental_mapping(
        database_path=database_path,
        image_path=image_dir,
        output_path=output_path,
        options=_build_incremental_mapper_opts(num_threads, refine_focal_length),
    )
    if not reconstructions:
        raise RuntimeError("COLMAP incremental mapper produced no reconstruction")
    return reconstructions[min(reconstructions)]


def _camera_center(image):
    """Camera center in world frame from a pycolmap Image.

    pycolmap stores image.cam_from_world as a Rigid3d (world->camera).
    Camera center C = -R^T @ t. Prefer projection_center() if exposed.
    """
    if hasattr(image, "projection_center"):
        return np.asarray(image.projection_center())
    pose = image.cam_from_world
    rotation = pose.rotation
    if hasattr(rotation, "matrix"):
        R = np.asarray(rotation.matrix())
    else:
        R = np.asarray(rotation)
    t = np.asarray(pose.translation)
    return -R.T @ t


def _ransac_consensus_scale(scales, inlier_tol):
    """Pick the scale with the largest agreement set, then refine.

    Each candidate s_i votes for the inlier set
        { s_j : |s_j/s_i - 1| < inlier_tol }.
    Returns (refined_scale, inlier_count) where refined_scale is the
    mean over the winning inlier set.
    """
    scales = np.asarray(scales, dtype=np.float64)
    best_count = 0
    best_inliers = None
    best_seed = float(scales[0])
    for s_i in scales:
        rel_err = np.abs(scales / s_i - 1.0)
        inliers = scales[rel_err < inlier_tol]
        if len(inliers) > best_count:
            best_count = len(inliers)
            best_inliers = inliers
            best_seed = float(s_i)
    refined = float(np.mean(best_inliers)) if best_inliers is not None \
        else best_seed
    return refined, int(best_count)


def _recover_stereo_scale(rec, baseline, pair_map, min_pairs, inlier_tol):
    """Vote for the scale that makes the most paired baselines agree.

    pair_map maps each left staged image name to its right counterpart
    (same captured frame).
    """
    img_by_name = {img.name: img for img in rec.images.values()}

    pairs = []
    for l_name, r_name in pair_map.items():
        l_img = img_by_name.get(l_name)
        r_img = img_by_name.get(r_name)
        if l_img is None or r_img is None:
            continue
        d = float(np.linalg.norm(_camera_center(l_img) - _camera_center(r_img)))
        if d <= 1e-9:
            continue
        pairs.append((l_name, d, baseline / d))

    if len(pairs) < min_pairs:
        raise RuntimeError(
            "Stereo scale recovery failed: only {0} valid left/right pose "
            "pairs (need >= {1}). Check that both left and right images "
            "registered and the stereo calib baseline ({2} m) is correct.".format(
                len(pairs), min_pairs, baseline))

    scales = [p[2] for p in pairs]
    scale, inlier_count = _ransac_consensus_scale(scales, inlier_tol)
    return scale, inlier_count, len(pairs)


def _apply_scale(rec, scale):
    """Apply a uniform Sim3 scale to cameras + 3D points in-place."""
    try:
        sim3 = pycolmap.Sim3d(scale, pycolmap.Rotation3d(), np.zeros(3))
        rec.transform(sim3)
        return
    except Exception as e:
        sys.stderr.write(
            "[colmap_runner] pycolmap.Sim3d transform failed ({0}); "
            "falling back to manual scaling.\n".format(e))

    for img_id in list(rec.images):
        img = rec.images[img_id]
        pose = img.cam_from_world
        scaled_t = np.asarray(pose.translation) * scale
        img.cam_from_world = pycolmap.Rigid3d(pose.rotation, scaled_t)
    for pt_id in list(rec.points3D):
        pt = rec.points3D[pt_id]
        pt.xyz = np.asarray(pt.xyz) * scale


def _run_monocular(database_path, image_dir, basenames, camera_params,
                   output_path, matcher, num_threads, overlap,
                   refine_focal_length):
    _extract_single_camera(database_path, image_dir, basenames,
                           camera_params, num_threads)
    _run_matching(database_path, matcher, num_threads, overlap)

    rec = _run_incremental_mapping(database_path, image_dir, output_path,
                                   num_threads, refine_focal_length)
    rec.write_text(output_path)
    rec.export_PLY(os.path.join(output_path, "fused.ply"))
    _filter_campose(
        os.path.join(output_path, "images.txt"),
        os.path.join(output_path, "campose.txt"),
    )


def _run_stereo(database_path, image_dir, basenames, camera_params,
                output_path, matcher, num_threads, overlap,
                left_subdir, right_subdir,
                right_camera_params, baseline, min_pairs, inlier_tol,
                refine_focal_length):
    left_dir = os.path.join(image_dir, left_subdir)
    right_dir = os.path.join(image_dir, right_subdir)
    if not os.path.isdir(left_dir) or not os.path.isdir(right_dir):
        raise RuntimeError(
            "Stereo mode expects {0} and {1} to exist".format(left_dir, right_dir))

    right_set = set(os.listdir(right_dir))
    left_set = set(os.listdir(left_dir))
    paired_bases = [b for b in basenames if b in left_set and b in right_set]
    if len(paired_bases) < min_pairs:
        raise RuntimeError(
            "Only {0} basenames found in both {1} and {2} (need >= {3})".format(
                len(paired_bases), left_dir, right_dir, min_pairs))

    # Stage symlinks named so the filename sort interleaves the pair as
    # left_0, right_0, left_1, right_1, ... COLMAP's sequential matcher
    # orders images by filename (DB order is irrelevant), so interleaving
    # lets a windowed sequential pass match each left/X with its right/X
    # and with temporal neighbours on both cameras. The zero-padded index
    # keeps the sort correct regardless of how the original basenames are
    # formatted (e.g. dotted TUM timestamps).
    staging_dir = os.path.join(output_path, "_seq_pairs")
    shutil.rmtree(staging_dir, ignore_errors=True)
    os.makedirs(staging_dir)

    left_names = []
    right_names = []
    pair_map = {}       # left staged name -> right staged name (same frame)
    left_rewrite = {}   # left staged name -> original "left/<base>"
    for i, base in enumerate(paired_bases):
        l_name = "{0:08d}_0.png".format(i)
        r_name = "{0:08d}_1.png".format(i)
        os.symlink(os.path.abspath(os.path.join(left_dir, base)),
                   os.path.join(staging_dir, l_name))
        os.symlink(os.path.abspath(os.path.join(right_dir, base)),
                   os.path.join(staging_dir, r_name))
        left_names.append(l_name)
        right_names.append(r_name)
        pair_map[l_name] = r_name
        left_rewrite[l_name] = "{0}/{1}".format(left_subdir, base)

    # Two extract_features calls, each CameraMode.SINGLE with its own
    # camera_params, against the staging dir. The database ends up with
    # exactly two PINHOLE cameras correctly seeded with left/right
    # intrinsics. (PER_FOLDER can't take per-folder camera_params via
    # ImageReaderOptions.)
    _extract_single_camera(database_path, staging_dir, left_names,
                           camera_params, num_threads)
    _extract_single_camera(database_path, staging_dir, right_names,
                           right_camera_params, num_threads)

    _run_matching(database_path, matcher, num_threads, overlap)

    rec = _run_incremental_mapping(database_path, staging_dir, output_path,
                                   num_threads, refine_focal_length)

    scale, inlier_count, pair_count = _recover_stereo_scale(
        rec, baseline, pair_map,
        min_pairs=min_pairs, inlier_tol=inlier_tol,
    )
    print("[colmap_runner] Recovered stereo scale: s = {0:.6f} "
          "({1} inliers / {2} pairs, baseline = {3} m)".format(
              scale, inlier_count, pair_count, baseline))

    _apply_scale(rec, scale)

    rec.write_text(output_path)
    rec.export_PLY(os.path.join(output_path, "fused.ply"))
    _filter_campose(
        os.path.join(output_path, "images.txt"),
        os.path.join(output_path, "campose.txt"),
        name_map=left_rewrite,
    )
    shutil.rmtree(staging_dir, ignore_errors=True)
    with open(os.path.join(output_path, "colmap_scale_info.txt"), "w") as f:
        f.write("scale: {0:.9f}\n".format(scale))
        f.write("baseline_m: {0}\n".format(baseline))
        f.write("inliers: {0}\n".format(inlier_count))
        f.write("pairs: {0}\n".format(pair_count))
        f.write("inlier_tol: {0}\n".format(inlier_tol))


def run(database_path, image_dir, image_list_path, camera_params,
        output_path, matcher, num_threads, overlap=10,
        stereo=False, left_subdir="left", right_subdir="right",
        right_camera_params=None, baseline=None,
        min_pairs=10, inlier_tol=0.05, refine_focal_length=False):
    os.makedirs(output_path, exist_ok=True)

    with open(image_list_path) as f:
        basenames = [ln.strip() for ln in f if ln.strip()]

    if stereo:
        if right_camera_params is None or baseline is None:
            raise ValueError(
                "stereo mode requires --right_camera_params and --baseline")
        _run_stereo(database_path, image_dir, basenames, camera_params,
                    output_path, matcher, num_threads, overlap,
                    left_subdir, right_subdir,
                    right_camera_params, baseline, min_pairs, inlier_tol,
                    refine_focal_length)
    else:
        _run_monocular(database_path, image_dir, basenames, camera_params,
                       output_path, matcher, num_threads, overlap,
                       refine_focal_length)


def _parse_args(argv):
    p = argparse.ArgumentParser()
    p.add_argument("--database_path", required=True)
    p.add_argument("--image_dir", required=True)
    p.add_argument("--image_list_path", required=True)
    p.add_argument("--camera_params", required=True,
                   help="fx,fy,cx,cy for the primary (or left, in stereo) camera")
    p.add_argument("--output_path", required=True)
    p.add_argument("--matcher", default="sequential",
                   choices=["sequential", "exhaustive"])
    p.add_argument("--num_threads", type=int, default=-1)
    p.add_argument("--overlap", type=int, default=10,
                   help="Sequential matcher: neighbours each image matches "
                        "against in filename order (stereo interleaves L/R)")
    p.add_argument("--stereo", action="store_true",
                   help="Run as a two-camera reconstruction and recover scale "
                        "from the known stereo baseline")
    p.add_argument("--left_subdir", default="left",
                   help="Stereo: subfolder of image_dir holding left images")
    p.add_argument("--right_subdir", default="right",
                   help="Stereo: subfolder of image_dir holding right images")
    p.add_argument("--right_camera_params", default=None,
                   help="Stereo: fx,fy,cx,cy for right camera")
    p.add_argument("--baseline", type=float, default=None,
                   help="Stereo: known baseline in meters")
    p.add_argument("--min_pairs", type=int, default=10,
                   help="Stereo: minimum left/right pose pairs required")
    p.add_argument("--inlier_tol", type=float, default=0.05,
                   help="Stereo: relative tolerance for the consensus voter "
                        "(scales within this fraction of each other agree)")
    p.add_argument("--refine_focal_length", action="store_true",
                   help="Let COLMAP bundle adjustment refine the focal length "
                        "(default: locked to the supplied intrinsics)")
    return p.parse_args(argv)


def main(argv):
    args = _parse_args(argv[1:])
    run(
        database_path=args.database_path,
        image_dir=args.image_dir,
        image_list_path=args.image_list_path,
        camera_params=args.camera_params,
        output_path=args.output_path,
        matcher=args.matcher,
        num_threads=args.num_threads,
        overlap=args.overlap,
        stereo=args.stereo,
        left_subdir=args.left_subdir,
        right_subdir=args.right_subdir,
        right_camera_params=args.right_camera_params,
        baseline=args.baseline,
        min_pairs=args.min_pairs,
        inlier_tol=args.inlier_tol,
        refine_focal_length=args.refine_focal_length,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
