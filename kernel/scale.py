from scipy.spatial.transform import Rotation as R
import numpy as np
from PIL import Image
import os
from kernel.logging_utility import log_report

def _parseImagesFile(filename, Camera_dict, PointsDict):
    with open(filename) as f:
        lines = f.readlines()
        for line in lines:
            if line.startswith("#"):
                pass
            else:
                words = line.split(" ")
                if '\n' in words:
                    words = words[:-1]
                if words[0].isnumeric() and words[-1].endswith(".png\n"): 
                    camera_idx = int(words[0])
                    Camera_dict[camera_idx] = {}
                    Camera_dict[camera_idx]["name"] = words[-1].split("\n")[0]
                    r = R.from_quat([float(words[2]), float(words[3]), float(words[4]), float(words[1])])
                    T = np.hstack((r.as_matrix(), np.array([[float(words[5])], [float(words[6])], [float(words[7])]])))
                    T = np.vstack((T, np.array([[0, 0, 0, 1]])))
                    Camera_dict[camera_idx]["pose"] = T
                    if "points" not in Camera_dict[camera_idx]: Camera_dict[camera_idx]["points"] = []

                else:
                    for i in range(0, len(words), 3):
                        if int(words[i + 2]) != -1:
                            pointidx = int(words[i + 2])
                            if pointidx not in PointsDict:
                                PointsDict[pointidx] = {}
                                PointsDict[pointidx]["camera"] = {}
                            PointsDict[pointidx]["camera"][camera_idx] = {}
                            PointsDict[pointidx]["camera"][camera_idx]["px"] = float(words[i])
                            PointsDict[pointidx]["camera"][camera_idx]["py"] = float(words[i + 1])
                            Camera_dict[camera_idx]["points"].append(pointidx)


def _parsePoints3D(filename, PointsDict):
    with open(filename) as f:
        lines = f.readlines()
        for line in lines:
            words = line.split(" ")
            if not words[0] == '#':
                PointsDict[int(words[0])]["location"] = np.array([float(words[1]), float(words[2]), float(words[3])])
                PointsDict[int(words[0])]["error"] = float(words[7])

def _depthInterpolation(depth, px, py):
    px_0 = int(np.floor(px))
    py_0 = int(np.floor(py))
    depth_inter = depth[px_0, py_0]
    return depth_inter

def _scaleFordepth(depth, index, intrinsic, Camera_dict, PointsDict, PointsDepth, POSE_INVERSE = True):
    if POSE_INVERSE:
        cam_pose = np.linalg.inv(Camera_dict[index]["pose"])
    else:
        cam_pose = Camera_dict[index]["pose"]
    for point_idx in Camera_dict[index]["points"]:
        point = PointsDict[point_idx]
        location = point['location']
        recon_error = point['error']
        pixel = point['camera'][index]
        depth_real = _depthInterpolation(depth, pixel['py'], pixel['px'])
        depth_recon = np.linalg.norm(location - cam_pose[:3, 3])
        if not point_idx in PointsDepth:
            PointsDepth[point_idx] = {}
        PointsDepth[point_idx][index] = {}
        PointsDepth[point_idx][index]['recon'] = depth_recon
        PointsDepth[point_idx][index]['real'] = depth_real
        PointsDepth[point_idx][index]['scale'] = depth_real/depth_recon

def _calculateDepth(THRESHOLD, NUM_THRESHOLD, PointsDepth):
    number = 0
    total_scale = 0
    for point in PointsDepth:
        scale_point = []
        number_point = 0
        for frame in PointsDepth[point]:
            scale = PointsDepth[point][frame]['scale']
            if scale == 0:
                pass
            else:
                scale_point.append(scale)
                number_point += 1
        if scale_point != []:
            std_point = np.std(np.array(scale_point))
            si = std_point/np.mean(np.array(scale_point))
            if si < THRESHOLD and si > 0 and number_point > NUM_THRESHOLD:
                number += number_point
                total_scale += np.sum(np.array(scale_point))
    print("remain {0:.2f}% vaild points".format(number * 100/len(PointsDepth)))
    if number == 0:
        return 0
    else:
        return total_scale/number



if __name__ == "__main__":
    Camera_dict = {}
    PointsDict = {}
    PointsDepth = {}
    imagefilepath = "/home/huijie/Desktop/testdataset/recon/images.txt"
    points3Dpath = "/home/huijie/Desktop/testdataset/recon/points3D.txt"
    datapath = "/home/huijie/Desktop/testdataset/data"
    intrinsic = np.array([
        [904.572, 0, 635.981 ],
        [0, 905.295, 353.06],
        [0, 0, 1]
    ])
    _parseImagesFile(imagefilepath, Camera_dict, PointsDict)
    _parsePoints3D(points3Dpath, PointsDict)

    for camera_idx in Camera_dict:
        rgb_name = Camera_dict[camera_idx]["name"]
        with Image.open(os.path.join(datapath, "depth", rgb_name)) as im:
            depth = np.array(im) * 0.00025
            _scaleFordepth(depth, camera_idx, intrinsic, Camera_dict, PointsDict, PointsDepth)
    
    scale = _calculateDepth(THRESHOLD = 0.005, NUM_THRESHOLD = 3, PointsDepth = PointsDepth)
    pass