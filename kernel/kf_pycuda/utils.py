import time
import copy
from collections import deque
import open3d as o3d
import numpy as np
from numba import njit, prange
import scipy.linalg as la

def timeit(f, n=1, need_compile=False):
    def wrapper(*args, **kwargs):
        if need_compile:  # ignore the first run if needs compile
            result = f(*args, **kwargs)
        print("------------------------------------------------------------------------")
        tic = time.time()
        for i in range(n):
            result = f(*args, **kwargs)
        total_time = time.time() - tic
        print(f"time elapsed: {total_time}s. Average running time: {total_time / n}s")
        return result
    return wrapper


def create_pcd(depth_im: np.ndarray,
               cam_intr: np.ndarray,
               color_im: np.ndarray = None,
               depth_scale: float = 1,
               depth_trunc: float = 1.5,
               cam_extr: np.ndarray = np.eye(4)):

    intrinsic_o3d = o3d.camera.PinholeCameraIntrinsic()
    intrinsic_o3d.intrinsic_matrix = cam_intr
    depth_im_o3d = o3d.geometry.Image(depth_im)
    if color_im is not None:
        color_im_o3d = o3d.geometry.Image(color_im)
        rgbd = o3d.geometry.RGBDImage.create_from_color_and_depth(color_im_o3d, depth_im_o3d, 
            depth_scale=depth_scale, depth_trunc=depth_trunc, convert_rgb_to_intensity=False)
        pcd = o3d.geometry.PointCloud.create_from_rgbd_image(rgbd, intrinsic_o3d, extrinsic=cam_extr)
    else:
        pcd = o3d.geometry.PointCloud.create_from_depth_image(depth_im_o3d, intrinsic_o3d, extrinsic=cam_extr,
                                                              depth_scale=depth_scale, depth_trunc=depth_trunc)
    return pcd


@njit   # @njit(parallel=True) will be slower for whatever reason
def batch_compute_iou(roi: np.ndarray, proposals: np.ndarray, iou_threshold=0.8):
    """
    compute IoU between one roi and N proposals

    roi: np.ndarray of shape (4,)
    proposals: np.ndarray of shape (N, 4)
    """
    x1, y1, w, h = roi
    boxA = np.array([x1, y1, x1 + w, y1 + h])

    ious = np.zeros(len(proposals))
    for i in range(len(proposals)):
        boxB = proposals[i]
        xA = max(boxA[0], boxB[0])
        yA = max(boxA[1], boxB[1])
        xB = min(boxA[2], boxB[2])
        yB = min(boxA[3], boxB[3])

        # compute the area of intersection rectangle
        interArea = abs(max((xB - xA, 0)) * max((yB - yA), 0))

        # compute the area of both the prediction and ground-truth
        # rectangles
        boxAArea = abs((boxA[2] - boxA[0]) * (boxA[3] - boxA[1]))
        boxBArea = abs((boxB[2] - boxB[0]) * (boxB[3] - boxB[1]))

        # compute the intersection over union by taking the intersection
        # area and dividing it by the sum of prediction + ground-truth
        # areas - the interesection area
        iou = interArea / float(boxAArea + boxBArea - interArea)
        ious[i] = iou
    return ious


def plane_detection_ransac(pcd: o3d.geometry.PointCloud,
                           inlier_thresh: float,
                           max_iterations: int = 1000,
                           early_stop_thresh: float = 0.3,
                           visualize: bool = False):
    """detect plane (table) in a pointcloud for background removal

    Args:
        pcd (o3d.geometry.PointCloud): [input point cloud, assuming in the camera frame]
        inlier_thresh (float): [inlier distance threshold between a point to a plain]
        max_iterations (int): [max number of iteration to perform for RANSAC]
        early_stop_thresh (float): [inlier ratio to stop RANSAC early]
    
    Return:
        frame (np.ndarray): [z_dir is the estimated plane normal towards the camera, x_dir and y_dir randomly sampled]
        inlier ratio (float): [ratio of inliers in the estimated plane]
    """
    num_pts = len(pcd.points)
    pts = np.asarray(pcd.points)

    origin = None
    plane_normal = None
    max_inlier_ratio = 0
    max_num_inliers = 0

    for _ in range(max_iterations):
        # sample 3 points from the point cloud
        selected_indices = np.random.choice(num_pts, size=3, replace=False)
        selected_pts = pts[selected_indices]
        p1 = selected_pts[0]
        v1 = selected_pts[1] - p1
        v2 = selected_pts[2] - p1
        normal = np.cross(v1, v2)
        normal /= la.norm(normal)

        dist = np.abs((pts - p1) @ normal)
        num_inliers = np.sum(dist < inlier_thresh)
        inlier_ratio = num_inliers / num_pts

        if num_inliers > max_num_inliers:
            max_num_inliers = num_inliers
            origin = p1
            plane_normal = normal
            max_inlier_ratio = inlier_ratio

        if inlier_ratio > early_stop_thresh:
            break
    
    if plane_normal[2] < 0:
        plane_normal *= -1
    # if plane_normal @ origin > 0:
    #     plane_normal *= -1

    # randomly sample x_dir and y_dir given plane normal as z_dir
    x_dir = np.array([-plane_normal[2], 0, plane_normal[0]])
    x_dir /= la.norm(x_dir)
    y_dir = np.cross(plane_normal, x_dir)
    plane_frame = np.eye(4)
    plane_frame[:3, 0] = x_dir
    plane_frame[:3, 1] = y_dir
    plane_frame[:3, 2] = plane_normal
    plane_frame[:3, 3] = origin

    if visualize:
        dist = (pts - origin) @ plane_normal
        pcd_vis = copy.deepcopy(pcd)
        colors = np.asarray(pcd_vis.colors)
        colors[np.abs(dist) < inlier_thresh] = np.array([0, 0, 1])
        colors[dist < -inlier_thresh] = np.array([1, 0, 0])

        plane_frame_vis = generate_coordinate_frame(plane_frame, scale=0.05)
        cam_frame_vis = generate_coordinate_frame(np.eye(4), scale=0.05)
        o3d.visualization.draw_geometries([cam_frame_vis, plane_frame_vis, pcd_vis])

    return plane_frame, max_inlier_ratio


def extract_euclidean_clusters(pcd: o3d.geometry.PointCloud,
                               search_radius: 0.03,
                               min_pts_per_cluster=100,
                               max_pts_per_cluster=np.inf):
    """extract euclidean clusters from a point cloud
    https://pcl.readthedocs.io/en/latest/cluster_extraction.html
    https://github.com/PointCloudLibrary/pcl/blob/master/segmentation/include/pcl/segmentation/impl/extract_clusters.hpp

    Args:
        pcd (o3d.geometry.PointCloud): [input point cloud]
        search_radius (0.03): [max radius during clustering]
        min_pts_per_cluster (int, optional): [min number of points per cluster]. Defaults to 100.
        max_pts_per_cluster ([type], optional): [max number of points per cluster]. Defaults to np.inf.

    Returns:
        [list]: [a list of clusters, each cluster is a list of point indices]
    """
    pts = np.asarray(pcd.points)
    N = pts.shape[0]
    kd_tree = o3d.geometry.KDTreeFlann(pcd)

    clustered_indices = []  # a list of clusters, each cluster is a list of point indices

    processed = np.zeros(N, dtype=bool)

    for i in range(N):
        if processed[i]:
            continue

        processed[i] = True
        cluster = []
        queue = deque()
        queue.append(i)

        while queue:
            pt_idx = queue.popleft()
            pt = pts[pt_idx]
            cluster.append(pt_idx)
            
            # search_hybrid is much faster than search_radius
            _, neighbor_indices, _ = kd_tree.search_hybrid_vector_3d(pt, search_radius, max_nn=30)
            # _, neighbor_indices, _ = kd_tree.search_radius_vector_3d(pt, search_radius)

            for neighbor_idx in neighbor_indices:
                if not processed[neighbor_idx]:
                    queue.append(neighbor_idx)
                    processed[neighbor_idx] = True
        
        if min_pts_per_cluster < len(cluster) < max_pts_per_cluster:
            clustered_indices.append(cluster)

    return clustered_indices


def generate_coordinate_frame(T, scale=0.05):
    mesh = o3d.geometry.TriangleMesh.create_coordinate_frame()
    mesh.scale(scale, center=np.array([0, 0, 0]))
    return mesh.transform(T)


def get_view_frustum(depth_im, cam_intr, cam_pose):
    """
    Get corners of 3D camera view frustum of depth image
    """

    def rigid_transform(xyz, transform):
        """Applies a rigid transform to an (N, 3) pointcloud. """
        xyz_h = np.hstack([xyz, np.ones((len(xyz), 1), dtype=np.float32)])
        xyz_t_h = np.dot(transform, xyz_h.T).T
        return xyz_t_h[:, :3]

    im_h = depth_im.shape[0]
    im_w = depth_im.shape[1]
    max_depth = np.max(depth_im)
    view_frust_pts = np.array([
        (np.array([0,0,0,im_w,im_w])-cam_intr[0,2])*np.array([0,max_depth,max_depth,max_depth,max_depth])/cam_intr[0,0],
        (np.array([0,0,im_h,0,im_h])-cam_intr[1,2])*np.array([0,max_depth,max_depth,max_depth,max_depth])/cam_intr[1,1],
        np.array([0,max_depth,max_depth,max_depth,max_depth])
    ])
    view_frust_pts = rigid_transform(view_frust_pts.T, cam_pose).T
    return view_frust_pts


if __name__ == '__main__':
    # roi = np.array([11, 30, 80, 90])
    # pts = np.random.random((1000, 2)) * 50  # randomly sample top left points of bboxes
    # proposals = np.hstack([pts, pts + 150])
    # timed_batch_compute_iou = timeit(batch_compute_iou, n=1, need_compile=True)
    # timed_batch_compute_iou(roi, proposals)

    pcd = o3d.io.read_point_cloud('demo.pcd')
    clusters = timeit(extract_euclidean_clusters)(pcd, search_radius=0.05)
    print(len(clusters))
    pcds = []
    for cluster in clusters:
        cluster_pcd = pcd.select_by_index(cluster)
        color = np.random.random((3,))
        cluster_pcd.paint_uniform_color(color)
        pcds.append(cluster_pcd)
    o3d.visualization.draw_geometries(pcds)
