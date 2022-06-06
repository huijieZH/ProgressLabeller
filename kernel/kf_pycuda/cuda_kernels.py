import numpy as np
# import matplotlib.pyplot as plt
# import matplotlib.animation as animation

import pycuda
import pycuda.autoinit
import pycuda.driver as cuda
from pycuda import gpuarray
from pycuda.compiler import SourceModule

source_module = SourceModule(
    """
    #define _X (threadIdx.x + blockDim.x * blockIdx.x)
    #define _Y (threadIdx.y + blockDim.y * blockIdx.y)
    #define _Z (threadIdx.z + blockDim.z * blockIdx.z)
    #define _ColorConst 65536

    __device__
    size_t getVoxelIndex(int x, int y, int z, int *dim)
    {
        return z*dim[0]*dim[1] + y*dim[0] + x;
    }

    __device__
    float serializeColor(float r, float g, float b)
    {
        return b*_ColorConst + g*256 + r;
    }

    __device__
    void deserializeColor(float color, float *r, float *g, float *b)
    {
        *b = floorf(color / _ColorConst);
        *g = floorf((color - (*b)*_ColorConst) / 256);
        *r = color - (*b)*_ColorConst - (*g)*256;
    }

    __device__
    void matmul(float *A, float *B, float *out, int m, int n, int l)
    {
        /*
            A is a matrix of shape m * n
            B is a matrix of shape n * l
            out is a matrix of shape m * l
            All these three matrix are stored in a row-wise 1D array
        */
        for (int i = 0; i < m; i++) {
            for (int j = 0; j < l; ++j) {
                int sum = 0;
                for (int k = 0; k < n; ++k) {
                    sum += A[i*n + k] * B[k*l + j];
                }
                out[i*l + j] = sum;
            }
        }
    }

    __device__
    void inv_T(float *A, float *out)
    {
        /*
           inverse a transformation matrix
           [[R, t]   -->  [[R.T, -R.T @ t]
            [0, 1]]        [0,       1]]
        */
        out[0] = A[0];
        out[1] = A[4];
        out[2] = A[8];
        out[3] = -(out[0]*A[3] + out[1]*A[7] + out[2]*A[11]);
        out[4] = A[1];
        out[5] = A[5];
        out[6] = A[9];
        out[7] = -(out[4]*A[3] + out[5]*A[7] + out[6]*A[11]);
        out[8] = A[2];
        out[9] = A[6];
        out[10] = A[10];
        out[11] = -(out[8]*A[3] + out[9]*A[7] + out[10]*A[11]);
        out[12] = 0;
        out[13] = 0;
        out[14] = 0;
        out[15] = 1;
    }

    __global__
    void integrate(float *tsdf_vol, float *weight_vol, float *color_vol, int *dim, float *vol_origin,
                   float voxel_size, float *cam_intr, float *cam_pose, int im_h, int im_w,
                   float *color_im, float *depth_im, float trunc_margin, float weight)
    {
        const int x = _X;
        const int y = _Y;
        const int z = _Z;

        if (x >= dim[0] || y >= dim[1] || z >= dim[2]) {
            return;
        }

        size_t voxel_idx = getVoxelIndex(x, y, z, dim);

        // voxel grid coordinates to world coordinates
        float pt_x = vol_origin[0] + x * voxel_size;
        float pt_y = vol_origin[1] + y * voxel_size;
        float pt_z = vol_origin[2] + z * voxel_size;

        // world coordinates to camera coordinates
        float tmp_pt_x = pt_x - cam_pose[0*4+3];
        float tmp_pt_y = pt_y - cam_pose[1*4+3];
        float tmp_pt_z = pt_z - cam_pose[2*4+3];
        float cam_pt_x = cam_pose[0*4+0]*tmp_pt_x + cam_pose[1*4+0]*tmp_pt_y + cam_pose[2*4+0]*tmp_pt_z;
        float cam_pt_y = cam_pose[0*4+1]*tmp_pt_x + cam_pose[1*4+1]*tmp_pt_y + cam_pose[2*4+1]*tmp_pt_z;
        float cam_pt_z = cam_pose[0*4+2]*tmp_pt_x + cam_pose[1*4+2]*tmp_pt_y + cam_pose[2*4+2]*tmp_pt_z;

        // camera coordinates to image pixels
        // cam_intr = [[fx, 0, cx], [0, fy, cy], [0, 0, 1]]
        float fx = cam_intr[0];
        float fy = cam_intr[4];
        float cx = cam_intr[2];
        float cy = cam_intr[5];

        int pixel_x = __float2int_rn(fx*(cam_pt_x/cam_pt_z) + cx);
        int pixel_y = __float2int_rn(fy*(cam_pt_y/cam_pt_z) + cy);
        int pixel_idx = pixel_y*im_w + pixel_x;

        // skip if outside view frustum
        if (pixel_x < 0 || pixel_x >= im_w || pixel_y < 0 || pixel_y >= im_h) return;
        if (cam_pt_z < 0) return;

        float depth_value = depth_im[pixel_idx];
        if (depth_value == 0) return;

        // skip voxels that are beyond truncated value
        float depth_diff = depth_value - cam_pt_z;
        if (depth_diff < -trunc_margin) return;

        // update weights
        float w_old = weight_vol[voxel_idx];
        float w_new = w_old + weight;
        weight_vol[voxel_idx] = w_new;

        // integrate TSDF
        float dist = fminf(1.0f, depth_diff / trunc_margin);
        tsdf_vol[voxel_idx] = (tsdf_vol[voxel_idx]*w_old + weight*dist) / w_new;

        // integrate color
        float old_color = color_vol[voxel_idx];
        float old_r, old_g, old_b;
        deserializeColor(old_color, &old_r, &old_g, &old_b);

        float new_color = color_im[pixel_idx];
        float new_r, new_g, new_b;
        deserializeColor(new_color, &new_r, &new_g, &new_b);

        new_b = fminf(roundf((old_b*w_old + weight*new_b) / w_new), 255.0f);
        new_g = fminf(roundf((old_g*w_old + weight*new_g) / w_new), 255.0f);
        new_r = fminf(roundf((old_r*w_old + weight*new_r) / w_new), 255.0f);
        color_vol[voxel_idx] = serializeColor(new_r, new_g, new_b);
    }

    __device__
    float getMinTime(float3 &min_range, float3 &max_range, float3 &cam_pos, float3 &ray)
    {
        float txmin = ((ray.x > 0 ? min_range.x : max_range.x) - cam_pos.x) / ray.x;
        float tymin = ((ray.y > 0 ? min_range.y : max_range.y) - cam_pos.y) / ray.y;
        float tzmin = ((ray.z > 0 ? min_range.z : max_range.z) - cam_pos.z) / ray.z;
        return fmaxf(fmaxf(txmin, tymin), tzmin);
    }

    __device__
    float getMaxTime(float3 &min_range, float3 &max_range, float3 &cam_pos, float3 &ray)
    {
        float txmax = ((ray.x > 0 ? max_range.x : min_range.x) - cam_pos.x) / ray.x;
        float tymax = ((ray.y > 0 ? max_range.y : min_range.y) - cam_pos.y) / ray.y;
        float tzmax = ((ray.z > 0 ? max_range.z : min_range.z) - cam_pos.z) / ray.z;
        return fminf(fminf(txmax, tymax), tzmax);
    }

    __global__
    void batchInlierMetric(int im_h, int im_w, int batch_size, float *batch_depth_im, float *depth_im,
                           float *weights, float inlier_thresh)
    {
        const int x = _X;
        if (x >= batch_size) return;

        int num_pixels = im_h * im_w;
        size_t start_idx = x * num_pixels;

        float num_inliers = 0;
        float num_total = 0;
        float num_obs = 0;
        for (int i = 0; i < num_pixels; ++i) {
            if (depth_im[i] != 0) num_obs += 1;

            float depth_render = batch_depth_im[i + start_idx];
            if (depth_render != 0) num_total += 1;
            else continue;

            if (fabsf(depth_render - depth_im[i]) < inlier_thresh) {
                num_inliers += 1;
            }
        }
        float ratio = 0.8;
        if (num_total == 0 || num_obs == 0) {
            weights[x] = 0;
        } else {
            // weights[x] = num_inliers;
            // weights[x] = 2 * num_inliers  / (num_total + num_obs);
            // weights[x] = num_inliers * num_inliers / (num_total * num_obs);
            weights[x] = ratio * (num_inliers / num_total) + (1 - ratio) * (num_inliers / num_obs);
        }
        return;
    }

    __global__
    void batchRayCasting(float *tsdf_vol, float *color_vol, float *weight_vol, int *dim, float* vol_origin, float voxel_size,
                         float *cam_intr, float *cam_pose, float *inv_cam_pose,
                         int start_row, int start_col, int im_h, int im_w,
                         char *batch_color_im, float *batch_depth_im, int batch_size)
    {
        const int x = _X;
        const int y = _Y;
        const int z = _Z;

        if (x >= im_w || y >= im_h || z > batch_size) {
            return;
        }

        int cam_pose_const = 16;  // 4x4 matrix
        cam_pose = cam_pose + z*cam_pose_const;
        inv_cam_pose = inv_cam_pose + z*cam_pose_const;

        int im_size_const = im_h * im_w;
        size_t pixel_idx = y*im_w + x + z*im_size_const;
        batch_depth_im[pixel_idx] = 0;

        size_t r_pixel_idx = y*im_w + x + 3*z*im_size_const;
        size_t g_pixel_idx = r_pixel_idx + im_size_const;
        size_t b_pixel_idx = g_pixel_idx + im_size_const;
        batch_color_im[r_pixel_idx] = 0;
        batch_color_im[g_pixel_idx] = 0;
        batch_color_im[b_pixel_idx] = 0;

        float3 min_range = make_float3(vol_origin[0], vol_origin[1], vol_origin[2]);
        float3 max_range = make_float3(vol_origin[0] + voxel_size * dim[0],
                                       vol_origin[1] + voxel_size * dim[1],
                                       vol_origin[2] + voxel_size * dim[2]);

        // camera coordinates to image pixels
        // cam_intr = [[fx, 0, cx], [0, fy, cy], [0, 0, 1]]
        float fx = cam_intr[0];
        float fy = cam_intr[4];
        float cx = cam_intr[2];
        float cy = cam_intr[5];

        float3 pixel_pos = make_float3((start_col + x - cx) / fx, (start_row + y - cy) / fy, 1);
        float3 ray = make_float3(
            cam_pose[0]*pixel_pos.x + cam_pose[1]*pixel_pos.y + cam_pose[2]*pixel_pos.z,
            cam_pose[4]*pixel_pos.x + cam_pose[5]*pixel_pos.y + cam_pose[6]*pixel_pos.z,
            cam_pose[8]*pixel_pos.x + cam_pose[9]*pixel_pos.y + cam_pose[10]*pixel_pos.z
        );
        float normalize_const = sqrtf(ray.x*ray.x + ray.y*ray.y + ray.z*ray.z);
        ray.x = voxel_size * ray.x / normalize_const;
        ray.y = voxel_size * ray.y / normalize_const;
        ray.z = voxel_size * ray.z / normalize_const;

        float3 cam_pos = make_float3(cam_pose[3], cam_pose[7], cam_pose[11]);
        int t_min = __float2int_rd(fmaxf(getMinTime(min_range, max_range, cam_pos, ray), 0));
        int t_max = __float2int_ru(getMaxTime(min_range, max_range, cam_pos, ray));
        if (t_min >= t_max) {
            return;
        }

        float dist_x = cam_pos.x - vol_origin[0];
        float dist_y = cam_pos.y - vol_origin[1];
        float dist_z = cam_pos.z - vol_origin[2];
        
        int3 prev_voxel = make_int3(
            __float2int_rn((dist_x + ray.x * t_min) / voxel_size),
            __float2int_rn((dist_y + ray.y * t_min) / voxel_size),
            __float2int_rn((dist_z + ray.z * t_min) / voxel_size)
        );

        bool ray_inside_box = false;
        int t_step = 5;  // 5 is relatively safe. 10 is much faster but may miss the crossing point.
        for (int t = t_min + 1; t < t_max - 1; t += t_step) {
            int3 curr_voxel = make_int3(
                __float2int_rn((dist_x + ray.x * t) / voxel_size),
                __float2int_rn((dist_y + ray.y * t) / voxel_size),
                __float2int_rn((dist_z + ray.z * t) / voxel_size)
            );

            if (!ray_inside_box) {
                if (prev_voxel.x >= 0 && prev_voxel.x < dim[0] && 
                    prev_voxel.y >= 0 && prev_voxel.y < dim[1] &&
                    prev_voxel.z >= 0 && prev_voxel.z < dim[2])
                {
                    ray_inside_box = true;
                } else {
                    prev_voxel = curr_voxel;
                    continue;
                }
            }

            // Box has a convex shape. A ray cannot re-enter a box after leaving it.
            if (ray_inside_box &&
                (curr_voxel.x < 0 || curr_voxel.x >= dim[0] ||
                 curr_voxel.y < 0 || curr_voxel.y >= dim[1] ||
                 curr_voxel.z < 0 || curr_voxel.z >= dim[2]))
            {
                return;
            }

            size_t prev_voxel_idx = getVoxelIndex(prev_voxel.x, prev_voxel.y, prev_voxel.z, dim);
            size_t curr_voxel_idx = getVoxelIndex(curr_voxel.x, curr_voxel.y, curr_voxel.z, dim);

            float prev_tsdf = tsdf_vol[prev_voxel_idx];
            float curr_tsdf = tsdf_vol[curr_voxel_idx];

            // zero crossing
            if (prev_tsdf > 0 && curr_tsdf < 0) {

                // find the exact zero crossing time
                for (int i = max(t_min + 1, t - t_step); i <= t; ++i) {
                    int3 voxel = make_int3(
                        __float2int_rn((dist_x + ray.x * i) / voxel_size),
                        __float2int_rn((dist_y + ray.y * i) / voxel_size),
                        __float2int_rn((dist_z + ray.z * i) / voxel_size)
                    );
                    size_t voxel_index = getVoxelIndex(voxel.x, voxel.y, voxel.z, dim);

                    if (tsdf_vol[voxel_index] < 0) {
                        if (tsdf_vol[voxel_index] > -1) {
                            float3 p = make_float3(
                                vol_origin[0] + voxel.x * voxel_size,
                                vol_origin[1] + voxel.y * voxel_size,
                                vol_origin[2] + voxel.z * voxel_size
                            );

                            float depth = inv_cam_pose[8]*p.x + inv_cam_pose[9]*p.y + inv_cam_pose[10]*p.z + inv_cam_pose[11];
                            batch_depth_im[pixel_idx] = depth;

                            float r, g, b;
                            deserializeColor(color_vol[voxel_index], &r, &g, &b);
                            batch_color_im[r_pixel_idx] = (char)r;
                            batch_color_im[g_pixel_idx] = (char)g;
                            batch_color_im[b_pixel_idx] = (char)b;
                            return;
                        } else {
                            break;  // false surface
                        }
                    }
                }
            }
            prev_voxel = curr_voxel;
        }
    }

    __global__
    void rayCasting(float *tsdf_vol, float *color_vol, float *weight_vol, int *dim, float* vol_origin, float voxel_size,
                    float *cam_intr, float *cam_pose, float *inv_cam_pose,
                    int start_row, int start_col, int im_h, int im_w,
                    char *color_im, float *depth_im)
    {
        const int x = _X;
        const int y = _Y;

        if (x >= im_w || y >= im_h) {
            return;
        }
        
        size_t pixel_idx = y*im_w + x;
        depth_im[pixel_idx] = 0;

        size_t r_pixel_idx = pixel_idx;
        size_t g_pixel_idx = im_w * im_h + pixel_idx;
        size_t b_pixel_idx = 2 * im_w * im_h + pixel_idx;
        color_im[r_pixel_idx] = 0;
        color_im[g_pixel_idx] = 0;
        color_im[b_pixel_idx] = 0;

        float3 min_range = make_float3(vol_origin[0], vol_origin[1], vol_origin[2]);
        float3 max_range = make_float3(vol_origin[0] + voxel_size * dim[0],
                                       vol_origin[1] + voxel_size * dim[1],
                                       vol_origin[2] + voxel_size * dim[2]);

        // camera coordinates to image pixels
        // cam_intr = [[fx, 0, cx], [0, fy, cy], [0, 0, 1]]
        float fx = cam_intr[0];
        float fy = cam_intr[4];
        float cx = cam_intr[2];
        float cy = cam_intr[5];

        float3 pixel_pos = make_float3((start_col + x - cx) / fx, (start_row + y - cy) / fy, 1);
        float3 ray = make_float3(
            cam_pose[0]*pixel_pos.x + cam_pose[1]*pixel_pos.y + cam_pose[2]*pixel_pos.z,
            cam_pose[4]*pixel_pos.x + cam_pose[5]*pixel_pos.y + cam_pose[6]*pixel_pos.z,
            cam_pose[8]*pixel_pos.x + cam_pose[9]*pixel_pos.y + cam_pose[10]*pixel_pos.z
        );
        float normalize_const = sqrtf(ray.x*ray.x + ray.y*ray.y + ray.z*ray.z);

        // ray contains information of both direction and magnitute
        ray.x = voxel_size * ray.x / normalize_const;
        ray.y = voxel_size * ray.y / normalize_const;
        ray.z = voxel_size * ray.z / normalize_const;

        float3 cam_pos = make_float3(cam_pose[3], cam_pose[7], cam_pose[11]);
        int t_min = __float2int_ru(fmaxf(getMinTime(min_range, max_range, cam_pos, ray), 0));
        int t_max = __float2int_rd(getMaxTime(min_range, max_range, cam_pos, ray));
        if (t_min >= t_max) {
            return;
        }

        float dist_x = cam_pos.x - vol_origin[0];
        float dist_y = cam_pos.y - vol_origin[1];
        float dist_z = cam_pos.z - vol_origin[2];

        int3 prev_voxel = make_int3(
            __float2int_rn((dist_x + ray.x * t_min) / voxel_size),
            __float2int_rn((dist_y + ray.y * t_min) / voxel_size),
            __float2int_rn((dist_z + ray.z * t_min) / voxel_size)
        );

        bool ray_inside_box = false;
        for (int t = t_min + 1; t < t_max; t += 1) {
            int3 curr_voxel = make_int3(
                __float2int_rn((dist_x + ray.x * t) / voxel_size),
                __float2int_rn((dist_y + ray.y * t) / voxel_size),
                __float2int_rn((dist_z + ray.z * t) / voxel_size)
            );

            if (!ray_inside_box) {
                if (prev_voxel.x >= 0 && prev_voxel.x < dim[0] && 
                    prev_voxel.y >= 0 && prev_voxel.y < dim[1] &&
                    prev_voxel.z >= 0 && prev_voxel.z < dim[2])
                {
                    ray_inside_box = true;
                } else {
                    prev_voxel = curr_voxel;
                    continue;
                }
            }

            // Box has a convex shape. A ray cannot re-enter a box after leaving it.
            if (ray_inside_box &&
                (curr_voxel.x < 0 || curr_voxel.x >= dim[0] ||
                 curr_voxel.y < 0 || curr_voxel.y >= dim[1] ||
                 curr_voxel.z < 0 || curr_voxel.z >= dim[2]))
            {
                return;
            }

            size_t prev_voxel_idx = getVoxelIndex(prev_voxel.x, prev_voxel.y, prev_voxel.z, dim);
            size_t curr_voxel_idx = getVoxelIndex(curr_voxel.x, curr_voxel.y, curr_voxel.z, dim);

            float prev_tsdf = tsdf_vol[prev_voxel_idx];
            float curr_tsdf = tsdf_vol[curr_voxel_idx];

            // zero crossing from front
            if (prev_tsdf > 0 && curr_tsdf < 0 && curr_tsdf > -1) {
                float3 p = make_float3(
                    vol_origin[0] + curr_voxel.x * voxel_size,
                    vol_origin[1] + curr_voxel.y * voxel_size,
                    vol_origin[2] + curr_voxel.z * voxel_size
                );
                float depth = inv_cam_pose[8]*p.x + inv_cam_pose[9]*p.y + inv_cam_pose[10]*p.z + inv_cam_pose[11];
                depth_im[pixel_idx] = depth;

                float r, g, b;
                deserializeColor(color_vol[curr_voxel_idx], &r, &g, &b);
                color_im[r_pixel_idx] = (char)r;
                color_im[g_pixel_idx] = (char)g;
                color_im[b_pixel_idx] = (char)b;
                return;
            }

            prev_voxel = curr_voxel;
        }
    }

    __device__
    bool checkInBox(float3 p, float *origin, float *vectors, float *dims)
    {
        /*
            bbox is represented using an origin and three normalized vectors from this origin, and dims
            origin: [x, y, z]
            vectors: [x1, y1, z1, x2, y2, z2, x3, y3, z3]
            dims: [dim_x, dim_y, dim_z]
        */

        float3 v = make_float3(p.x - origin[0], p.y - origin[1], p.z - origin[2]);

        // calculate dot products of v with v1, v2, v3
        float prod1 = v.x*vectors[0] + v.y*vectors[1] + v.z*vectors[2];
        float prod2 = v.x*vectors[3] + v.y*vectors[4] + v.z*vectors[5];
        float prod3 = v.x*vectors[6] + v.y*vectors[7] + v.z*vectors[8];

        // point is outside the oriented bbox
        if (prod1 < 0 || prod1 > dims[0]*dims[0] || prod2 < 0 || prod2 > dims[1]*dims[1] || prod3 < 0 || prod3 > dims[2]*dims[2]) {
            return false;
        }
        return true;
    }

    __global__
    void renderBoxes(float *depth_im, int im_h, int im_w, float *cam_intr,
                     int num_boxes, float *cam_poses, float *box_dims)
    {
        const int x = _X;
        const int y = _Y;

        if (x >= im_w || y >= im_h) {
            return;
        }

        size_t pixel_idx = y*im_w + x;
        depth_im[pixel_idx] = 0;

        for (int i = 0; i < num_boxes; ++i) {
            float dim_x = box_dims[3*i];
            float dim_y = box_dims[3*i + 1];
            float dim_z = box_dims[3*i + 2];
            float3 min_range = make_float3(-dim_x / 2, -dim_y / 2, -dim_z / 2);
            float3 max_range = make_float3(dim_x / 2, dim_y / 2, dim_z / 2);

            // camera coordinates to image pixels
            // cam_intr = [[fx, 0, cx], [0, fy, cy], [0, 0, 1]]
            float fx = cam_intr[0];
            float fy = cam_intr[4];
            float cx = cam_intr[2];
            float cy = cam_intr[5];

            float *cam_pose = cam_poses + 16*i;
            float3 pixel_pos = make_float3((x - cx) / fx, (y - cy) / fy, 1);
            float3 cam_pos = make_float3(cam_pose[3], cam_pose[7], cam_pose[11]);
            float3 ray = make_float3(
                cam_pose[0]*pixel_pos.x + cam_pose[1]*pixel_pos.y + cam_pose[2]*pixel_pos.z,
                cam_pose[4]*pixel_pos.x + cam_pose[5]*pixel_pos.y + cam_pose[6]*pixel_pos.z,
                cam_pose[8]*pixel_pos.x + cam_pose[9]*pixel_pos.y + cam_pose[10]*pixel_pos.z
            );

            float t_min = fmaxf(getMinTime(min_range, max_range, cam_pos, ray), 0);
            float t_max = getMaxTime(min_range, max_range, cam_pos, ray);
            if (t_min >= t_max) {
                continue;
            }

            if (depth_im[pixel_idx] == 0 || depth_im[pixel_idx] > t_min) {
                depth_im[pixel_idx] = t_min;
            }
        }
    }

    __global__
    void filterOcclusion(float *depth_im, float *occ_im, int im_h, int im_w)
    {
        const int x = _X;
        const int y = _Y;

        if (x >= im_w || y >= im_h) {
            return;
        }

        size_t pixel_idx = y*im_w + x;
        if (occ_im[pixel_idx] != 0 && depth_im[pixel_idx] > occ_im[pixel_idx]) {
            depth_im[pixel_idx] = 0;
        }
    }
    
    __global__
    void filterPointsInBoxes(float *depth_im, int im_w, int im_h, float *cam_intr,
                             int num_boxes, float *origins, float *vectors, float *dims, int *inverse)
    {
        /*
            cam_intr = [[fx, 0, cx], [0, fy, cy], [0, 0, 1]]

            bbox is represented using an origin and three normalized vectors from this origin, and dims
            origins: [[x1, y1, z1], ...]
            vectors: [[x1, y1, z1, x2, y2, z2, x3, y3, z3], ...]
            dims: [[dim_x, dim_y, dim_z], ...]
            inverse: a list of in integer, 0 means keep pts in box, 1 means filter pts in box
        */

        const int x = _X;
        const int y = _Y;

        if (x >= im_w || y >= im_h) {
            return;
        }

        size_t pixel_idx = y*im_w + x;
        float depth = depth_im[pixel_idx];
        if (depth == 0) return;

        float fx = cam_intr[0];
        float fy = cam_intr[4];
        float cx = cam_intr[2];
        float cy = cam_intr[5];

        float3 p = make_float3((x - cx)*depth/fx, (y - cy)*depth/fy, depth);

        for (int i = 0; i < num_boxes; ++i) {
            bool inBox = checkInBox(p, origins + 3*i, vectors + 9*i, dims + 3*i);
            if ((inBox && inverse[i] == 1) || (!inBox && inverse[i] == 0)) {
                depth_im[pixel_idx] = 0;
                return;
            }
        }
        return;
    }

    __global__
    void colorDistanceL2(char *rendered_color, char *obs_color, float* rendered_depth, float *diff, int im_w, int im_h)
    {
        const int x = _X;
        const int y = _Y;

        if (x >= im_w || y >= im_h) {
            return;
        }

        size_t pixel_idx = y*im_w + x;
        diff[pixel_idx] = 0;

        if (rendered_depth[pixel_idx] == 0) {
            return;
        }

        size_t r_pixel_idx = pixel_idx;
        size_t g_pixel_idx = im_w * im_h + pixel_idx;
        size_t b_pixel_idx = 2 * im_w * im_h + pixel_idx;

        float r_diff = (float)obs_color[r_pixel_idx] - (float)rendered_color[r_pixel_idx];
        float g_diff = (float)obs_color[g_pixel_idx] - (float)rendered_color[g_pixel_idx];
        float b_diff = (float)obs_color[b_pixel_idx] - (float)rendered_color[b_pixel_idx];
        diff[pixel_idx] = sqrt(r_diff*r_diff + g_diff*g_diff + b_diff*b_diff);
    }

    __global__
    void indexTest(float *output, int *dim)
    {
        const int x = _X;
        const int y = _Y;
        const int z = _Z;

        if (x >= dim[0] || y >= dim[1] || z >= dim[2]) {
            return;
        }

        size_t global_idx = getVoxelIndex(x, y, z, dim);

        output[global_idx] = z * dim[0] * dim[1] + y * dim[0] + x + 1;
        // output[global_idx] = x*x + y*y;
    }

    """
)
