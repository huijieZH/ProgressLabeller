import os

def orbslam_yaml(file_path, fx, fy, cx,cy, width, height, depthscale, frequency):
    f = open(file_path, "w")
    f.write("%YAML:1.0\n")
    f.write("\n")
    f.write("#--------------------------------------------------------------------------------------------\n")
    f.write("# Camera Parameters. Adjust them!\n")
    f.write("#--------------------------------------------------------------------------------------------\n")
    f.write("\n")
    f.write("# Camera calibration and distortion parameters (OpenCV)\n")
    f.write("Camera.fx: {0:.3f}\n".format(fx))
    f.write("Camera.fy: {0:.3f}\n".format(fy))
    f.write("Camera.cx: {0:.3f}\n".format(cx))
    f.write("Camera.cy: {0:.3f}\n\n".format(cy))

    f.write("Camera.k1: 0\n")
    f.write("Camera.k2: 0\n")
    f.write("Camera.p1: 0\n")
    f.write("Camera.p2: 0\n")
    f.write("Camera.k3: 0\n\n")

    f.write("Camera.width: {0}\n".format(width))
    f.write("Camera.height: {0}\n\n".format(height))

    f.write("# Camera frames per second\n") 
    f.write("Camera.fps: {0:.1f}\n\n".format(frequency))

    f.write("# IR projector baseline times fx (aprox.)\n")
    f.write("Camera.bf: 40.0\n\n")

    f.write("# Color order of the images (0: BGR, 1: RGB. It is ignored if images are grayscale)\n")
    f.write("Camera.RGB: 1\n\n")

    f.write("# Close/Far threshold. Baseline times.\n")
    f.write("ThDepth: 40.0\n\n")

    f.write("# Deptmap values factor\n") 
    f.write("DepthMapFactor: {0:.1f}\n".format(1/depthscale))

    f.write("#--------------------------------------------------------------------------------------------\n")
    f.write("# ORB Parameters\n")
    f.write("#--------------------------------------------------------------------------------------------\n\n")

    f.write("# ORB Extractor: Number of features per image\n")
    f.write("ORBextractor.nFeatures: 1000\n\n")

    f.write("# ORB Extractor: Scale factor between levels in the scale pyramid\n") 	
    f.write("ORBextractor.scaleFactor: 1.2\n\n")

    f.write("# ORB Extractor: Number of levels in the scale pyramid\n")	
    f.write("ORBextractor.nLevels: 8\n\n")

    f.write("# ORB Extractor: Fast threshold\n")
    f.write("# Image is divided in a grid. At each cell FAST are extracted imposing a minimum response.\n")
    f.write("# Firstly we impose iniThFAST. If no corners are detected we impose a lower value minThFAST\n")
    f.write("# You can lower these values if your images have low contrast\n")			
    f.write("ORBextractor.iniThFAST: 20\n")
    f.write("ORBextractor.minThFAST: 7\n\n")

    f.write("#--------------------------------------------------------------------------------------------\n")
    f.write("# Viewer Parameters\n")
    f.write("#--------------------------------------------------------------------------------------------\n")
    f.write("Viewer.KeyFrameSize: 0.05\n")
    f.write("Viewer.KeyFrameLineWidth: 1\n")
    f.write("Viewer.GraphLineWidth: 0.9\n")
    f.write("Viewer.PointSize: 2\n")
    f.write("Viewer.CameraSize: 0.08\n")
    f.write("Viewer.CameraLineWidth: 3\n")
    f.write("Viewer.ViewpointX: 0\n")
    f.write("Viewer.ViewpointY: -0.7\n")
    f.write("Viewer.ViewpointZ: -1.8\n")
    f.write("Viewer.ViewpointF: 500\n")
    f.close()

def orbslam_associatefile(file_path, dataset_path, frequency):
    rgb_files = os.listdir(os.path.join(dataset_path, "rgb"))
    depth_files = os.listdir(os.path.join(dataset_path, "depth"))
    rgb_files.sort()
    depth_files.sort()
    index = 1/frequency
    with open(file_path, "w") as f:
        for perfix in rgb_files:
            if perfix in depth_files:
                f.write(f'{index} ' + 'rgb/{0} '.format(perfix) + f'{index} ' + 'depth/{0}\n'.format(perfix))
                index += 1/frequency