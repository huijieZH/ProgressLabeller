from cv2 import INTER_NEAREST
import pyrender
import numpy as np
import os
import json
import trimesh
import pyrender
from kernel.geometry import _pose2Rotation
from PIL import Image
from tqdm import tqdm
from scipy.io import savemat
import copy
import open3d as o3d
import cv2
import normalSpeed
import time
os.environ['PYOPENGL_PLATFORM'] = 'egl'

class offlineRender:
    def __init__(self, param, outputdir, interpolation_type, pkg_type = "BOP") -> None:
        assert(pkg_type in ["ProgressLabeller", "BOP", "YCBV", "Transparent_YCBV"])
        print("Start offline rendering")
        self.param = param
        self.interpolation_type = interpolation_type
        self.outputpath = outputdir
        self.modelsrc = self.param.modelsrc
        self.reconstructionsrc = self.param.reconstructionsrc
        self.datasrc = self.param.datasrc
        self.intrinsic = self.param.camera["intrinsic"]
        self.objects = self.param.objs
        self.objs_kp = self.param.objs_kp
        
        self._parsecamfile()
        if pkg_type == "ProgressLabeller":
            self._prepare_scene()
            self._createallpkgs()
            self.render = pyrender.OffscreenRenderer(self.param.camera["resolution"][0], self.param.camera["resolution"][1])
            self.renderAll()
        
        ## TODO only add key points to BOP
        elif pkg_type == "BOP":
            self.object_label = param.object_label
            self._prepare_scene_BOP()
            self.render = pyrender.OffscreenRenderer(self.param.camera["resolution"][0], self.param.camera["resolution"][1])
            self.renderBOP()
        elif pkg_type == "YCBV":    
            self.object_label = param.object_label
            self._prepare_scene()
            self.render = pyrender.OffscreenRenderer(self.param.camera["resolution"][0], self.param.camera["resolution"][1])
            self.renderYCBV()
        elif pkg_type == "Transparent_YCBV":    
            self.object_label = param.object_label
            self._prepare_scene()
            self.render = pyrender.OffscreenRenderer(self.param.camera["resolution"][0], self.param.camera["resolution"][1])
            self.normal_render = pyrender.OffscreenRenderer(self.param.camera["resolution"][0], self.param.camera["resolution"][1])

            # class CustomShaderCache():
            #     ## from https://github.com/mmatl/pyrender/issues/39
            #     def __init__(self):
            #         self.program = None

            #     def get_program(self, vertex_shader, fragment_shader, geometry_shader=None, defines=None):
            #         if self.program is None:
            #             self.program = pyrender.shader_program.ShaderProgram("./offline/shaders/mesh.vert", "./offline/shaders/mesh.frag", defines=defines)
            #         return self.program
            # self.normal_render._renderer._program_cache = CustomShaderCache()    
            # self.render._renderer._program_cache = CustomShaderCache()  
            # self.normal_render = o3d.visualization.rendering.OffscreenRenderer(self.param.camera['resolution'][0], self.param.camera['resolution'][1])      
            self.renderTransparent_YCBV()

    
    def data_export(self, target_dir):
        if not os.path.exists(target_dir):
            os.mkdir(target_dir)
        
    def _prepare_scene(self):
        self.objectmap = {}
        object_index = 0
        self.scene = pyrender.Scene()
        cam = pyrender.camera.IntrinsicsCamera(self.param.camera["intrinsic"][0, 0],
                                               self.param.camera["intrinsic"][1, 1], 
                                               self.param.camera["intrinsic"][0, 2], 
                                               self.param.camera["intrinsic"][1, 2], 
                                               znear=0.05, zfar=100.0, name=None)
        self.nc = pyrender.Node(camera=cam, matrix=np.eye(4))
        self.scene.add_node(self.nc)
        for obj_instancename in self.objects:
            obj = obj_instancename.split(".")[0]
            ## for full model
            if self.objects[obj_instancename]['type'] == 'normal':
                tm = trimesh.load(os.path.join(self.modelsrc, obj, obj+".obj"))
                mesh = pyrender.Mesh.from_trimesh(tm, smooth = False)
                node = pyrender.Node(mesh=mesh, matrix=self.objects[obj_instancename]['trans'])
                self.objectmap[node] = {"index":object_index, "name":obj_instancename, "trans":self.objects[obj_instancename]['trans']}
                self.scene.add_node(node)
                object_index += 1
            ## for split model
            # if self.objects[obj_instancename]['type'] == 'split':
            #     splitobjfiles = os.listdir(os.path.join(self.modelsrc, obj, "split"))
            #     for f in splitobjfiles:
            #         if f.endswith(".obj"):
            #             tm = trimesh.load(os.path.join(self.modelsrc, obj, "split", f))
            #             mesh = pyrender.Mesh.from_trimesh(tm)
            #             node = pyrender.Node(mesh=mesh, matrix=self.objects[obj]['trans'])
            #             self.objectmap[node] = {"index":object_index, "name":f.split(".")[0], "trans":self.objects[obj]['trans']}
            #             self.scene.add_node(node)
            #             object_index += 1
        # self.scenefornormal = copy.deepcopy(self.scene) 
    def _parsecamfile(self):
        self.camposes = {}
        f = open(os.path.join(self.reconstructionsrc, "campose_all_{0}.txt".format(self.interpolation_type)))
        # f = open(os.path.join(self.reconstructionsrc, "campose.txt"))
        lines = f.readlines()
        for l in lines:
            datas = l.split(" ")
            if datas[0].isnumeric():
                self.camposes[datas[-1].split("\n")[0]] = _pose2Rotation([[float(datas[5]), float(datas[6]), float(datas[7])],\
                                                           [float(datas[1]), float(datas[2]), float(datas[3]), float(datas[4])]])
    
    def _applytrans2cam(self):
        Axis_align = np.array([[1, 0, 0, 0],
                               [0, -1, 0, 0],
                               [0, 0, -1, 0],
                               [0, 0, 0, 1],]
            )
        scale = self.param.recon["scale"]
        trans = self.param.recon["trans"]
        for cam in self.camposes:
            origin_pose = self.camposes[cam]
            origin_pose[:3, 3] = origin_pose[:3, 3] * scale
            if self.CAM_INVERSE:
                origin_pose = np.linalg.inv(origin_pose).dot(Axis_align)
            else:
                origin_pose = origin_pose.dot(Axis_align)
            self.camposes[cam] = trans.dot(origin_pose)

    def _render(self, cam_pose, scene):
        ##segimg is the instance segmentation for each part(normal or each part for the split)
        scene.set_pose(self.nc, pose=cam_pose)
        flags = pyrender.constants.RenderFlags.DEPTH_ONLY
        segimg = np.zeros((self.param.camera["resolution"][1], self.param.camera["resolution"][0]), dtype=np.uint8)

        full_depth = self.render.render(scene, flags = flags)
        for node in self.objectmap:
            node.mesh.is_visible = False
        
        for node in self.objectmap:
            node.mesh.is_visible = True
            depth = self.render.render(scene, flags = flags)
            mask = np.logical_and(
                (np.abs(depth - full_depth) < 1e-6), np.abs(full_depth) > 0
            )
            segimg[mask] = self.objectmap[node]['index'] + 1
            node.mesh.is_visible = False
        
        for node in self.objectmap:
            node.mesh.is_visible = True
        return segimg

    def _createpkg(self, dir):
        if os.path.exists(dir):
            return True
        else:
            if self._createpkg(os.path.dirname(dir)):
                os.mkdir(dir)
                return self._createpkg(os.path.dirname(dir))

    def _createallpkgs(self):
        for node in self.objectmap:
            self._createpkg(os.path.join(self.outputpath, self.objectmap[node]["name"], "pose"))
            self._createpkg(os.path.join(self.outputpath, self.objectmap[node]["name"], "rgb"))
    
    def renderAll(self):
        ## generate whole output dataset
        Axis_align = np.array([[1, 0, 0, 0],
                               [0, -1, 0, 0],
                               [0, 0, -1, 0],
                               [0, 0, 0, 1],]
                                )
        i = 0             
        for cam in tqdm(self.camposes):
            if (i%100) == 0:
                camT = self.camposes[cam].dot(Axis_align)
                segment = self._render(camT, self.scene)
                perfix = cam.split(".")[0]
                inputrgb = np.array(Image.open(os.path.join(self.datasrc, "rgb", cam)))

                for node in self.objectmap:
                    posepath = os.path.join(self.outputpath, self.objectmap[node]["name"], "pose")
                    rgbpath = os.path.join(self.outputpath, self.objectmap[node]["name"], "rgb")
                    modelT = self.objectmap[node]["trans"]
                    # model_camT = np.linalg.inv(camT.dot(Axis_align)).dot(modelT)
                    model_camT = np.linalg.inv(self.camposes[cam]).dot(modelT)
                    self._createpose(posepath, perfix, model_camT)
                    self._createrbg(inputrgb, segment, os.path.join(rgbpath, cam), self.objectmap[node]["index"] + 1)
            i+=1



    def _createpose(self, path, perfix, T):
        posefileName = os.path.join(path, perfix + ".txt")
        # np.savetxt(posefileName, np.linalg.inv(T), fmt='%f', delimiter=' ')
        np.savetxt(posefileName, T, fmt='%f', delimiter=' ')

    def _createrbg(self, inputrgb, segment, outputpath, segment_index):
        rgb = inputrgb.copy()
        mask = np.repeat((segment != segment_index)[:, :, np.newaxis], 3, axis=2)
        mask[:,:,1] = False
        mask[:,:,2] = False
        rgb[mask] = 0
        img = Image.fromarray(rgb)
        img.save(outputpath)
    

    def renderBOP(self):
        ## should be change by user, 
        self._createpkg(os.path.join(self.outputpath, "depth"))
        self._createpkg(os.path.join(self.outputpath, "mask"))
        self._createpkg(os.path.join(self.outputpath, "mask_visib"))
        self._createpkg(os.path.join(self.outputpath, "rgb"))
        scene_camera = {}
        scene_gt = {}
        scene_gt_info = {}
        for idx, cam_name in tqdm(enumerate(self.camposes)):
            os.system('cp ' + os.path.join(self.datasrc, "rgb", cam_name) + ' ' + os.path.join(self.outputpath, "rgb", "{0:06d}.png".format(idx)))
            os.system('cp ' + os.path.join(self.datasrc, "depth", cam_name) + ' ' + os.path.join(self.outputpath, "depth", "{0:06d}.png".format(idx)))
            inputdepth = Image.open(os.path.join(self.datasrc, "depth", cam_name))
            ### 
            scene_camera[idx] = {
                "cam_K": self.intrinsic.flatten().tolist(),
                "cam_R_w2c": (self.camposes[cam_name][:3, :3]).flatten().tolist(),
                "cam_t_w2c": (self.camposes[cam_name][:3, 3]).flatten().tolist(),
                "depth_scale": np.round(self.param.data['depth_scale'], 5),
                "mode": 0
            }
            scene_gt[idx] = list()
            scene_gt_info[idx] = list()
            ## render
            Axis_align = np.array([[1, 0, 0, 0],
                               [0, -1, 0, 0],
                               [0, 0, -1, 0],
                               [0, 0, 0, 1],]
            )
            camT = self.camposes[cam_name].dot(Axis_align)
            self.scene.set_pose(self.nc, pose=camT)
            flags = pyrender.constants.RenderFlags.DEPTH_ONLY
            for node in self.objectmap:
                node.mesh.is_visible = True
            full_depth = self.render.render(self.scene, flags = flags)

            for node in self.objectmap:
                node.mesh.is_visible = False
            
            for obj_idx, node in enumerate(self.objectmap):
                node.mesh.is_visible = True
                depth = self.render.render(self.scene, flags = flags)
                mask = np.logical_and(
                    (np.abs(depth - full_depth) < 1e-6), np.abs(full_depth) > 0
                )

                ## calculate ketpoints location
                instance_name = self.objectmap[node]['name']
                kp = self.objs_kp[instance_name]
                cam_world_T = np.linalg.inv(self.camposes[cam_name])
                kp_pixel_homo = self.intrinsic.dot(cam_world_T[:3, :3].dot(kp.T) + cam_world_T[:3, [3]])
                kp_pixel = (kp_pixel_homo[:2]/kp_pixel_homo[2]).T

                mask_trim = (np.abs(depth) > 0)
                mask_visiable_trim = mask
                mask_pillow = Image.fromarray((mask_trim * 255).astype('uint8'))
                mask_pillow.save(os.path.join(self.outputpath, "mask", "{0:06d}_{1:06d}.png".format(idx ,obj_idx)))
                mask_visiable_pillow = Image.fromarray((mask_visiable_trim * 255).astype('uint8'))
                mask_visiable_pillow.save(os.path.join(self.outputpath, "mask_visib", "{0:06d}_{1:06d}.png".format(idx ,obj_idx)))
                node.mesh.is_visible = False
                if not self._getbbx(mask_trim)[0]:
                    continue
                scene_gt_info[idx].append({
                    "bbox_obj": self._getbbx(mask_trim)[1], 
                    "bbox_visib": self._getbbx(mask_visiable_trim)[1],
                    "px_count_all": int(np.sum(depth > 0)),
                    "px_count_valid": int(np.sum(np.array(inputdepth)[mask_trim] != 0)),
                    "px_count_visib": int(np.sum(mask_visiable_trim)),
                    "visib_fract": float(np.sum(mask_visiable_trim)/np.sum(depth > 0)),
                    "kps": kp_pixel.tolist(),
                })
                modelT = self.objectmap[node]["trans"]
                model_camT = np.linalg.inv(modelT).dot(self.camposes[cam_name])
                scene_gt[idx].append({
                    "cam_R_m2c": (model_camT[:3, :3]).flatten().tolist(),
                    "cam_t_m2c":(model_camT[:3, 3]).flatten().tolist(),
                    "obj_id": self.objectmap[node]['index']
                })
            # if idx == 1: # TODO: remove later, rerun entire scene
            #     break
        with open(os.path.join(self.outputpath, 'scene_camera.json'), 'w', encoding='utf-8') as f:
            json.dump(scene_camera, f, ensure_ascii=False, indent=1)
        with open(os.path.join(self.outputpath, 'scene_gt.json'), 'w', encoding='utf-8') as f:
            json.dump(scene_gt, f, ensure_ascii=False, indent=1)
        with open(os.path.join(self.outputpath, 'scene_gt_info.json'), 'w', encoding='utf-8') as f:
            json.dump(scene_gt_info, f, ensure_ascii=False, indent=1)

    def _prepare_scene_BOP(self):
        self.objectmap = {}
        self.scene = pyrender.Scene()
        cam = pyrender.camera.IntrinsicsCamera(self.param.camera["intrinsic"][0, 0],
                                            self.param.camera["intrinsic"][1, 1], 
                                            self.param.camera["intrinsic"][0, 2], 
                                            self.param.camera["intrinsic"][1, 2], 
                                            znear=0.05, zfar=100.0, name=None)
        self.nc = pyrender.Node(camera=cam, matrix=np.eye(4))
        self.scene.add_node(self.nc)
        for obj_instancename in self.objects:
            ## for full model
            obj = obj_instancename.split(".")[0]
            if self.objects[obj_instancename]['type'] == 'normal':
                tm = trimesh.load(os.path.join(self.modelsrc, obj, obj+".obj"))
                mesh = pyrender.Mesh.from_trimesh(tm)
                node = pyrender.Node(mesh=mesh, matrix=self.objects[obj_instancename]['trans'])
                self.objectmap[node] = {"index":self.object_label[obj], "name":obj_instancename , "trans":self.objects[obj_instancename ]['trans']}
                self.scene.add_node(node)
            if obj_instancename in self.objs_kp:
                trans = self.objects[obj_instancename]['trans']
                points = self.objs_kp[obj_instancename].T
                points_transed = trans[:3, :3].dot(points) + trans[:3, [3]]
                self.objs_kp[obj_instancename] = points_transed.T

    
    def _getbbx(self, mask):
        pixel_list = np.where(mask)
        if np.any(pixel_list):
            top = pixel_list[0].min()
            bottom = pixel_list[0].max()
            left = pixel_list[1].min()
            right = pixel_list[1].max()
            return True, [int(left), int(top), int(right - left), int(bottom - top)]
        else:
            return False, []
    
    def renderYCBV(self):
        self._createpkg(self.outputpath)
        for idx, cam_name in tqdm(enumerate(self.camposes)):
            os.system('cp ' + os.path.join(self.datasrc, "rgb", cam_name) + ' ' + os.path.join(self.outputpath, "{0:06d}-color.png".format(idx)))
            os.system('cp ' + os.path.join(self.datasrc, "depth", cam_name) + ' ' + os.path.join(self.outputpath, "{0:06d}-depth.png".format(idx)))
            ## render
            Axis_align = np.array([[1, 0, 0, 0],
                               [0, -1, 0, 0],
                               [0, 0, -1, 0],
                               [0, 0, 0, 1],]
            )
            camT = self.camposes[cam_name].dot(Axis_align)
            self.scene.set_pose(self.nc, pose=camT)
            flags = pyrender.constants.RenderFlags.DEPTH_ONLY

            segimg = np.zeros((self.param.camera["resolution"][1], self.param.camera["resolution"][0]), dtype=np.uint8)
            vertmap = np.zeros((self.param.camera["resolution"][1], self.param.camera["resolution"][0]), dtype=np.float32)
            for node in self.objectmap:
                node.mesh.is_visible = True
            full_depth = self.render.render(self.scene, flags = flags)

            for node in self.objectmap:
                node.mesh.is_visible = False
            
            ## create -label.txt
            txtfile = open(os.path.join(self.outputpath, "{0:06d}-box.txt".format(idx)),"w+")
            ## create -meta.mat
            mat = {}
            mat['cls_indexes'] = np.empty((0, 1), dtype = np.uint8)
            mat['center'] = np.empty((0, 2))
            mat['factor_depth'] = np.array([[np.around(1/self.param.data['depth_scale'])]], dtype = np.uint16)
            mat['intrinsic_matrix'] = self.intrinsic
            mat['poses'] = np.empty((3, 4, 0))
            mat['rotation_translation_matrix'] = self.camposes[cam_name][:3, :]
            for obj_idx, node in enumerate(self.objectmap):
                node.mesh.is_visible = True
                depth = self.render.render(self.scene, flags = flags)
                mask = np.logical_and(
                    (np.abs(depth - full_depth) < 1e-6), np.abs(full_depth) > 0
                )
                mask_visiable = (mask * 255).astype('uint8')
                segimg[mask] = self.object_label[self.objectmap[node]["name"].split(".")[0]]
                node.mesh.is_visible = False
                if not self._getbbxycb(mask_visiable)[0]:
                    continue
                else:
                    bbx = self._getbbxycb(mask_visiable)[1]
                    txtfile.write(self.objectmap[node]["name"].split(".")[0] + f' {bbx[0]} {bbx[1]} {bbx[2]} {bbx[3]}\n')
                    mat['cls_indexes'] = np.vstack((mat['cls_indexes'], np.array([[self.object_label[self.objectmap[node]["name"].split(".")[0]]]], dtype = np.uint8)))
                    
                    modelT = self.objectmap[node]["trans"]
                    model_camT = np.linalg.inv(self.camposes[cam_name]).dot(modelT)
                    center_homo = self.intrinsic @ model_camT[:3, 3]
                    center = center_homo[:2]/center_homo[2]
                    mat['center'] = np.vstack((mat['center'], center))
                    mat['poses'] = np.concatenate((mat['poses'], model_camT[:3, :, np.newaxis]), axis = 2)
                    pass

            txtfile.close()
            savemat(os.path.join(self.outputpath, "{0:06d}-meta.mat".format(idx)), mat)
            segimg_pillow = Image.fromarray(segimg)
            segimg_pillow.save(os.path.join(self.outputpath, "{0:06d}-label.png".format(idx)))

    def renderTransparent_YCBV(self):
        self._createpkg(self.outputpath)
        H, W = self.param.camera["resolution"][1], self.param.camera["resolution"][0]
        U, V = np.tile(np.arange(W), (H, 1)), np.tile(np.arange(H), (W, 1)).T
        fx, fy, cx, cy = self.intrinsic[0, 0], self.intrinsic[1, 1], self.intrinsic[0, 2], self.intrinsic[1, 2]
        flags = pyrender.constants.RenderFlags.DEPTH_ONLY
        Axis_align = np.array([[1, 0, 0, 0],
                            [0, -1, 0, 0],
                            [0, 0, -1, 0],
                            [0, 0, 0, 1],])
        rescale = True # from  1280*720 to 640*480            
        normalspeed_distance_threshold = 100000
        normalspeed_difference_threshold = 100000
        normalspeed_k_size = 1

        for idx, cam_name in tqdm(enumerate(self.camposes)):
            if rescale:
                img_rgb = cv2.imread(os.path.join(self.datasrc, "rgb", cam_name))
                img_depth = cv2.imread(os.path.join(self.datasrc, "depth", cam_name), -1)
                img_rgb = cv2.resize(img_rgb[:, 160:-160], (640, 480))
                img_depth = cv2.resize(img_depth[:, 160:-160], (640, 480), interpolation=cv2.INTER_NEAREST)
                cv2.imwrite(os.path.join(self.outputpath, "{0:06d}-color.png".format(idx)), img_rgb)
                cv2.imwrite(os.path.join(self.outputpath, "{0:06d}-depth.png".format(idx)), img_depth)
                # verify reshape intrinsics by projecting object point cloud and visualize on image
                # for obj in self.objectmap:
                #     obj_T = self.objectmap[obj]['trans']
                #     obj_name = self.objectmap[obj]['name'].split('.')[0]
                #     obj_points = np.array(trimesh.load_mesh(self.modelsrc + obj_name + '/' + obj_name + '.obj').vertices)
                #     camT = self.camposes[cam_name]
                #     obj_in_camT = np.linalg.inv(camT) @ obj_T
                #     r, t = obj_in_camT[:3, :3], obj_in_camT[:3, 3]
                #     obj_points_transform = obj_points @ r.T + t[np.newaxis, :]
                #     obj_points_transform /= obj_points_transform[:, [-1]]
                #     obj_points_on_image = obj_points_transform @ self.intrinsic.T
                #     for pt in obj_points_on_image:
                #         cv2.circle(img_rgb, (int(pt[0]), int(pt[1])), 1, (255, 0, 0), 1)
                # cv2.imwrite(os.path.join(self.outputpath, "{0:06d}-color_test_resize.png".format(idx)), img_rgb)
            else:
                img_depth = cv2.imread(os.path.join(self.datasrc, "depth", cam_name), -1)
                os.system('cp ' + os.path.join(self.datasrc, "rgb", cam_name) + ' ' + os.path.join(self.outputpath, "{0:06d}-color.png".format(idx)))
                os.system('cp ' + os.path.join(self.datasrc, "depth", cam_name) + ' ' + os.path.join(self.outputpath, "{0:06d}-depth.png".format(idx)))
            # t1 = time.time() - t
            # print('save rescale rgb + depth', t1)
            # t = time.time()
            ## render
            camT = self.camposes[cam_name].dot(Axis_align)
            self.scene.set_pose(self.nc, pose=camT)
            for node in self.objectmap:
                if self.objectmap[node]['name'] == 'round_table.instance001':
                    node.mesh.is_visible = True
                else:
                    node.mesh.is_visible = False
            table_depth = self.render.render(self.scene, flags=flags)
            Image.fromarray((table_depth*1000).astype('uint16')).save(os.path.join(self.outputpath, "{0:06d}-tableplane_depth.png".format(idx)))
            # t1 = time.time() - t
            # print('render big tableplane and save', t1)
            # t = time.time()
            segimg = np.zeros((self.param.camera["resolution"][1], self.param.camera["resolution"][0]), dtype=np.uint8)
            # vertmap = np.zeros((self.param.camera["resolution"][1], self.param.camera["resolution"][0]), dtype=np.float32)
            for node in self.objectmap:
                node.mesh.is_visible = not node.mesh.is_visible
            obj_depth = self.render.render(self.scene, flags=flags)
            
            # ## create -label.txt
            txtfile = open(os.path.join(self.outputpath, "{0:06d}-box.txt".format(idx)),"w+")
            ## create -meta.mat
            mat = {}
            mat['cls_indexes'] = np.empty((0, 1), dtype = np.uint8)
            mat['center'] = np.empty((0, 2))
            mat['factor_depth'] = np.array([[np.around(1/self.param.data['depth_scale'])]], dtype = np.uint16)
            mat['intrinsic_matrix'] = self.intrinsic
            mat['poses'] = np.empty((3, 4, 0))
            mat['rotation_translation_matrix'] = self.camposes[cam_name][:3, :]
            camT_inv = np.linalg.inv(self.camposes[cam_name])
            for node in self.objectmap:
                node.mesh.is_visible = False
            for obj_idx, node in enumerate(self.objectmap):
                if self.objectmap[node]['name'] == 'round_table.instance001':
                    continue
                node.mesh.is_visible = True
                depth = self.render.render(self.scene, flags = flags)
                mask = np.logical_and(
                    (np.abs(depth - obj_depth) < 1e-6), np.abs(obj_depth) > 0
                )
                mask_visiable = (mask * 255).astype('uint8')
                segimg[mask] = self.object_label[self.objectmap[node]["name"].split(".")[0]]
                node.mesh.is_visible = False
                if not self._getbbxycb(mask_visiable)[0]:
                    continue
                else:
                    bbx = self._getbbxycb(mask_visiable)[1]
                    txtfile.write(self.objectmap[node]["name"].split(".")[0] + f' {bbx[0]} {bbx[1]} {bbx[2]} {bbx[3]}\n')
                    mat['cls_indexes'] = np.vstack((mat['cls_indexes'], np.array([[self.object_label[self.objectmap[node]["name"].split(".")[0]]]], dtype = np.uint8)))
                    
                    modelT = self.objectmap[node]["trans"]
                    model_camT = camT_inv.dot(modelT)
                    center_homo = self.intrinsic @ model_camT[:3, 3]
                    center = center_homo[:2]/center_homo[2]
                    mat['center'] = np.vstack((mat['center'], center))
                    mat['poses'] = np.concatenate((mat['poses'], model_camT[:3, :, np.newaxis]), axis = 2)

            txtfile.close()
            savemat(os.path.join(self.outputpath, "{0:06d}-meta.mat".format(idx)), mat)
            Image.fromarray(segimg).save(os.path.join(self.outputpath, "{0:06d}-label.png".format(idx)))
            # t1 = time.time() - t
            # print('metadata and instance-label', t1)
            # t = time.time()

            obj_true_depth = (obj_depth * 1000).astype(np.uint16)
            img_depth[obj_true_depth!=0] = obj_true_depth[obj_true_depth!=0]
            Image.fromarray(img_depth).save(os.path.join(self.outputpath, "{0:06d}-depth_true.png".format(idx)))
            # t1 = time.time() - t
            # print('save depth true', t1)
            # t = time.time()

            # calculating normal, 3 ways
            # X, Y = img_depth * (U - cx) / fx, img_depth * (V - cy) / fy
            # way 1: use numpy to get neighbor difference
            # vx, vy, vz = np.gradient(X), np.gradient(Y), np.gradient(img_depth)
            # vu, vv = np.array([vx[0], vy[0], vz[0]]), np.array([vx[1], vy[1], vz[1]])

            # way 2: use cv2 Sobel/Scharr to get neighbor difference
            # vux = cv2.Scharr(X, cv2.CV_64F, 1, 0, borderType=cv2.BORDER_DEFAULT)
            # vuy = cv2.Scharr(Y, cv2.CV_64F, 1, 0, borderType=cv2.BORDER_DEFAULT)
            # vuz = cv2.Scharr(img_depth, cv2.CV_64F, 1, 0, borderType=cv2.BORDER_DEFAULT)
            # vvx = cv2.Scharr(X, cv2.CV_64F, 0, 1, borderType=cv2.BORDER_DEFAULT)
            # vvy = cv2.Scharr(Y, cv2.CV_64F, 0, 1, borderType=cv2.BORDER_DEFAULT)
            # vvz = cv2.Scharr(img_depth, cv2.CV_64F, 0, 1, borderType=cv2.BORDER_DEFAULT)
            # vu, vv = np.array([vux, vuy, vuz]), np.array([vvx, vvy, vvz])
            # vn = np.cross(vu, vv, axisa=0, axisb=0)
            # vn_norm = np.linalg.norm(vn, axis=2)
            # vn[:, :, 0] /= vn_norm
            # vn[:, :, 1] /= vn_norm
            # vn[:, :, 2] /= vn_norm

            # way 3: use normalSpeed library from github: (same result as way 2 + medianblur, 3x faster)

            vn = normalSpeed.depth_normal(img_depth, fx, fy, normalspeed_k_size, normalspeed_distance_threshold, normalspeed_difference_threshold, True)
            # vn = normalSpeed.depth_normal(img_depth, fx, fy, k_size, distance_threshold, difference_threshold, False)
            normal = ((vn + 1)*255/2).astype(np.uint8)
            Image.fromarray(normal).save(os.path.join(self.outputpath, "{0:06d}-normal_true.png".format(idx)))
            # print('calculate and save normal', time.time() - t)
            # print('total time', time.time() - t0)
            # break

    def _getbbxycb(self, mask):
        pixel_list = np.where(mask)
        if np.any(pixel_list):
            top = pixel_list[0].min()
            bottom = pixel_list[0].max()
            left = pixel_list[1].min()
            right = pixel_list[1].max()
            return True, [int(left), int(top), int(right), int(bottom)]
        else:
            return False, []
    
    def _getvertmap(self):
        ##TODO
        pass
