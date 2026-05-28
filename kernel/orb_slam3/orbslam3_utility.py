import json
import os

try:
    import yaml as _yaml
except ImportError:
    _yaml = None


def _load_stereo_calib(path):
    """Load a stereo calibration file (YAML or JSON).

    Required keys:
        fx2, fy2, cx2, cy2   right camera intrinsics
        baseline             stereo baseline in meters
        T_c1_c2              4x4 transform from left to right camera
    Optional keys (default 0):
        k1, k2, p1, p2       right camera distortion
    Returns a dict with the same key names.
    """
    if not path or not os.path.isfile(path):
        raise FileNotFoundError(
            "Stereo calibration file not found: {0!r}".format(path))

    ext = os.path.splitext(path)[1].lower()
    with open(path, "r") as fh:
        if ext in (".yaml", ".yml"):
            if _yaml is None:
                raise ImportError(
                    "PyYAML is required to read .yaml stereo calibration files")
            data = _yaml.safe_load(fh)
        else:
            data = json.load(fh)

    required = ["fx2", "fy2", "cx2", "cy2", "baseline", "T_c1_c2"]
    missing = [k for k in required if k not in data]
    if missing:
        raise KeyError(
            "Stereo calibration file is missing keys: {0}".format(missing))

    T = data["T_c1_c2"]
    if len(T) != 4 or any(len(row) != 4 for row in T):
        raise ValueError("T_c1_c2 must be a 4x4 matrix")

    return {
        "fx2": float(data["fx2"]),
        "fy2": float(data["fy2"]),
        "cx2": float(data["cx2"]),
        "cy2": float(data["cy2"]),
        "k1": float(data.get("k1", 0.0)),
        "k2": float(data.get("k2", 0.0)),
        "p1": float(data.get("p1", 0.0)),
        "p2": float(data.get("p2", 0.0)),
        "baseline": float(data["baseline"]),
        "T_c1_c2": [[float(v) for v in row] for row in T],
    }


def _write_camera1_block(f, fx, fy, cx, cy):
    f.write("# Left/main camera calibration and distortion parameters (OpenCV)\n")
    f.write("Camera1.fx: {0:.3f}\n".format(fx))
    f.write("Camera1.fy: {0:.3f}\n".format(fy))
    f.write("Camera1.cx: {0:.3f}\n".format(cx))
    f.write("Camera1.cy: {0:.3f}\n".format(cy))
    f.write("\n")
    f.write("Camera1.k1: 0.0\n")
    f.write("Camera1.k2: 0.0\n")
    f.write("Camera1.p1: 0.0\n")
    f.write("Camera1.p2: 0.0\n")
    f.write("\n")


def _write_camera2_block(f, calib):
    f.write("# Right camera calibration and distortion parameters (OpenCV)\n")
    f.write("Camera2.fx: {0:.3f}\n".format(calib["fx2"]))
    f.write("Camera2.fy: {0:.3f}\n".format(calib["fy2"]))
    f.write("Camera2.cx: {0:.3f}\n".format(calib["cx2"]))
    f.write("Camera2.cy: {0:.3f}\n".format(calib["cy2"]))
    f.write("\n")
    f.write("Camera2.k1: {0:.6f}\n".format(calib["k1"]))
    f.write("Camera2.k2: {0:.6f}\n".format(calib["k2"]))
    f.write("Camera2.p1: {0:.6f}\n".format(calib["p1"]))
    f.write("Camera2.p2: {0:.6f}\n".format(calib["p2"]))
    f.write("\n")


def _write_stereo_extrinsic(f, calib):
    T = calib["T_c1_c2"]
    flat = ", ".join("{0:.9f}".format(v) for row in T for v in row)
    f.write("Stereo.T_c1_c2: !!opencv-matrix\n")
    f.write("   rows: 4\n")
    f.write("   cols: 4\n")
    f.write("   dt: f\n")
    f.write("   data: [{0}]\n".format(flat))
    f.write("\n")


def orbslam3_yaml(file_path, fx, fy, cx, cy, width, height, depthscale, frequency,
                  sensor_mode="RGBD", stereo_calib=None, stereo_th_depth=40.0):
    """Generate an ORB-SLAM3 YAML for one of three sensor modes.

    sensor_mode: "MONOCULAR" | "RGBD" | "STEREO"
    """
    if sensor_mode == "STEREO" and stereo_calib is None:
        raise ValueError("STEREO sensor mode requires stereo_calib")

    with open(file_path, "w") as f:
        f.write("%YAML:1.0\n\n")
        f.write("#--------------------------------------------------------------------------------------------\n")
        f.write("# Camera Parameters. Adjust them!\n")
        f.write("#--------------------------------------------------------------------------------------------\n")
        f.write("File.version: \"1.0\"\n\n")
        f.write("Camera.type: \"PinHole\"\n\n")

        _write_camera1_block(f, fx, fy, cx, cy)

        if sensor_mode == "STEREO":
            _write_camera2_block(f, stereo_calib)

        f.write("# Camera resolution\n")
        f.write("Camera.width: {0}\n".format(width))
        f.write("Camera.height: {0}\n\n".format(height))

        f.write("# Camera frames per second\n")
        f.write("Camera.fps: {0:d}\n\n".format(int(frequency)))

        f.write("# Color order of the images (0: BGR, 1: RGB. It is ignored if images are grayscale)\n")
        f.write("Camera.RGB: 1\n\n")

        if sensor_mode == "RGBD":
            f.write("# Close/Far threshold. Baseline times.\n")
            f.write("Stereo.ThDepth: 40.0\n")
            f.write("Stereo.b: 0.0745\n\n")
            f.write("# Depth map values factor\n")
            f.write("RGBD.DepthMapFactor: {0:.1f}\n\n".format(1 / depthscale))
        elif sensor_mode == "STEREO":
            f.write("# Close/Far threshold. Baseline times.\n")
            f.write("Stereo.ThDepth: {0:.1f}\n".format(stereo_th_depth))
            f.write("Stereo.b: {0:.6f}\n\n".format(stereo_calib["baseline"]))
            _write_stereo_extrinsic(f, stereo_calib)

        f.write("#--------------------------------------------------------------------------------------------\n")
        f.write("# ORB Parameters\n")
        f.write("#--------------------------------------------------------------------------------------------\n")
        f.write("ORBextractor.nFeatures: 2500\n\n")
        f.write("ORBextractor.scaleFactor: 1.2\n\n")
        f.write("ORBextractor.nLevels: 8\n\n")
        f.write("ORBextractor.iniThFAST: 20\n")
        f.write("ORBextractor.minThFAST: 7\n\n")

        f.write("#--------------------------------------------------------------------------------------------\n")
        f.write("# Viewer Parameters\n")
        f.write("#--------------------------------------------------------------------------------------------\n")
        f.write("Viewer.KeyFrameSize: 0.05\n")
        f.write("Viewer.KeyFrameLineWidth: 1.0\n")
        f.write("Viewer.GraphLineWidth: 0.9\n")
        f.write("Viewer.PointSize: 2.0\n")
        f.write("Viewer.CameraSize: 0.08\n")
        f.write("Viewer.CameraLineWidth: 3.0\n")
        f.write("Viewer.ViewpointX: 0.0\n")
        f.write("Viewer.ViewpointY: -0.7\n")
        f.write("Viewer.ViewpointZ: -3.5\n")
        f.write("Viewer.ViewpointF: 500.0\n")


def orbslam3_associatefile(file_path, dataset_path, frequency, sensor_mode="RGBD"):
    """Write the association file consumed by orb3_extension.

    MONOCULAR: "<ts> rgb/<file>"  (single column)
    RGBD:      "<ts> rgb/<file> <ts> depth/<file>"
    STEREO:    "<ts> left/<file> <ts> right/<file>"
    """
    step = 1.0 / frequency

    if sensor_mode == "MONOCULAR":
        primary_dir = "rgb"
        rgb_files = sorted(os.listdir(os.path.join(dataset_path, primary_dir)))
        index = step
        with open(file_path, "w") as f:
            for name in rgb_files:
                f.write("{0} {1}/{2}\n".format(index, primary_dir, name))
                index += step
        return

    if sensor_mode == "STEREO":
        left_dir, right_dir = "left", "right"
    else:
        left_dir, right_dir = "rgb", "depth"

    left_files = sorted(os.listdir(os.path.join(dataset_path, left_dir)))
    right_files = set(os.listdir(os.path.join(dataset_path, right_dir)))

    index = step
    with open(file_path, "w") as f:
        for name in left_files:
            if name in right_files:
                f.write("{0} {1}/{2} {0} {3}/{2}\n".format(
                    index, left_dir, name, right_dir))
                index += step
