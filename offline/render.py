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
                                               znear=0.001, zfar=100.0, name=None)
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
            ins_segimg = np.zeros_like(segimg)
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
                ins_segimg[mask] = obj_idx + 1
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
            Image.fromarray(ins_segimg).save(os.path.join(self.outputpath, "{0:06d}-instance_label.png".format(idx)))

    def renderTransparent_YCBV(self):
        self._createpkg(self.outputpath)
        H, W = self.param.camera["resolution"][1], self.param.camera["resolution"][0]
        # U, V = np.tile(np.arange(W), (H, 1)), np.tile(np.arange(H), (W, 1)).T
        fx, fy, cx, cy = self.intrinsic[0, 0], self.intrinsic[1, 1], self.intrinsic[0, 2], self.intrinsic[1, 2]
        flags = pyrender.constants.RenderFlags.DEPTH_ONLY
        Axis_align = np.array([[1, 0, 0, 0],
                            [0, -1, 0, 0],
                            [0, 0, -1, 0],
                            [0, 0, 0, 1],])          
        normalspeed_distance_threshold = 100000
        normalspeed_difference_threshold = 100000
        normalspeed_k_size = 1
        rescale = True # from  1280*720 to 640*480  
        render_table = False
        render_backface = True # save multi-layer depth and mask image of objects, .mat file containing multi-layer bounding box, and all object poses 
        '''
        need following changes in pyrender library:
        add a constant in class RenderFlags(object) in constants.py: BACKFACE = 16384
        change rendering logic to be
        
        glViewport(0, 0, self.viewport_width, self.viewport_height)
        glEnable(GL_DEPTH_TEST)
        glDepthMask(GL_TRUE)
        glDepthFunc(GL_LESS)
        glDepthRange(0.0, 1.0)
        glClearDepth(1.0)

        # enable rendering other surfaces
        if flags & RenderFlags.BACKFACE:
            # print('rendering backface')
            glClear(GL_DEPTH_BUFFER_BIT)
            # face-cullback
            glFrontFace(GL_CW)

            # backface
            glClearDepth(0.0)
            glDepthFunc(GL_GREATER)
        in function def _configure_forward_pass_viewport(self, flags) in renderer.py
        '''
        save_rgbd = False
        save_mat = False
        save_bbox = False
        render_normal = False
        render_seg = False
        render_depthtrue = False
        max_depth_layer = 6
        large_depth_const = 1000
        depth_samelayer_filter = 0.002

        if render_backface: # one mat file for all frames in a scene
            bbox_mat = {}
            pose_mat = {} # all object poses, no matter directly visible or not

        for idx, cam_name in tqdm(enumerate(self.camposes)):
            if save_rgbd:
                img_depth = self.move_rgbd(idx, cam_name, rescale)
            # ## render
            # render tableplane
            camT = self.camposes[cam_name].dot(Axis_align)
            self.scene.set_pose(self.nc, pose=camT)

            if render_table:
                for node in self.objectmap:
                    if self.objectmap[node]['name'] == 'round_table.instance001':
                        node.mesh.is_visible = True
                    else:
                        node.mesh.is_visible = False
                table_depth = self.render.render(self.scene, flags=flags)
                Image.fromarray((table_depth*1000).astype('uint16')).save(os.path.join(self.outputpath, "{0:06d}-tableplane_depth.png".format(idx)))
                
            if render_seg:
                segimg = np.zeros((self.param.camera["resolution"][1], self.param.camera["resolution"][0]), dtype=np.uint8)
            
            for node in self.objectmap:
                if self.objectmap[node]['name'] == 'round_table.instance001':
                    node.mesh.is_visible = False
                else:
                    node.mesh.is_visible = True
            obj_depth = self.render.render(self.scene, flags=flags)
            
            if save_bbox:
                txtfile = open(os.path.join(self.outputpath, "{0:06d}-box.txt".format(idx)), "w+")

            ## create -meta.mat
            if save_mat:
                mat = {}
                mat['cls_indexes'] = np.empty((0, 1), dtype=np.uint8)
                mat['center'] = np.empty((0, 2))
                mat['factor_depth'] = np.array([[np.around(1/self.param.data['depth_scale'])]], dtype = np.uint16)
                mat['intrinsic_matrix'] = self.intrinsic
                mat['poses'] = np.empty((3, 4, 0))
                mat['rotation_translation_matrix'] = self.camposes[cam_name][:3, :]
            
            camT_inv = np.linalg.inv(self.camposes[cam_name])
            
            if render_backface:
                depth_buffer = {}
            for node in self.objectmap:
                node.mesh.is_visible = False
            
            if render_backface:
                id_list = []
                bbox_mat[cam_name] = {}
                pose_mat[cam_name] = {}
            
            # time1 = time.time()
            for node in self.objectmap:
                if self.objectmap[node]['name'] == 'round_table.instance001':
                    continue
                obj_id = self.object_label[self.objectmap[node]["name"].split(".")[0]]
                node.mesh.is_visible = True
                modelT = self.objectmap[node]["trans"]
                model_camT = camT_inv.dot(modelT)
                depth = self.render.render(self.scene, flags=flags)

                if render_backface:
                    depth_buffer[model_camT[2, 3] - 0.0001] = depth
                    depth1 = self.render.render(self.scene, flags=flags | pyrender.constants.RenderFlags.BACKFACE)
                    depth1[np.abs(depth1 - depth) < depth_samelayer_filter] = large_depth_const
                    depth_buffer[model_camT[2, 3] + 0.0001] = depth1
                    id_list.append(obj_id)
                    pose_mat[cam_name][obj_id] = model_camT
                    # Image.fromarray((depth * 1000).astype(np.uint16)).save(os.path.join(self.outputpath, "{:06d}-depth_front_{}.png".format(idx, obj_idx)))
                    # Image.fromarray((depth1 * 1000).astype(np.uint16)).save(os.path.join(self.outputpath, "{:06d}-depth_back_{}.png".format(idx, obj_idx)))
                if render_seg:
                    mask = np.logical_and(
                        (np.abs(depth - obj_depth) < 1e-6), np.abs(obj_depth) > 0
                    )
                    mask_visible = (mask * 255).astype('uint8')
                    segimg[mask] = obj_id
                if save_mat and self._getbbxycb(mask_visible)[0]:
                    bbx = self._getbbxycb(mask_visible)[1]
                    txtfile.write(self.objectmap[node]["name"].split(".")[0] + f' {bbx[0]} {bbx[1]} {bbx[2]} {bbx[3]}\n')
                    mat['cls_indexes'] = np.vstack((mat['cls_indexes'], np.array([[obj_id]], dtype = np.uint8)))
                    center_homo = self.intrinsic @ model_camT[:3, 3]
                    center = center_homo[:2]/center_homo[2]
                    mat['center'] = np.vstack((mat['center'], center))
                    mat['poses'] = np.concatenate((mat['poses'], model_camT[:3, :, np.newaxis]), axis = 2)
                
                node.mesh.is_visible = False
            # print('time for rendering individual obj', time.time() - time1)

            if save_bbox:
                txtfile.close()

            # time1 = time.time()
            if render_backface:
                # depth_layers = np.zeros((max_depth_layer, H, W))
                # depth_current_max = np.zeros((H, W))
                # depth_layer_n = -np.ones((H, W), dtype=np.int)
                depth_layers = np.zeros((H, W, len(depth_buffer.keys())))
                for i, key in enumerate(depth_buffer.keys()):
                    tmp = depth_buffer[key].copy()
                    tmp[tmp <= 0.001] = large_depth_const
                    depth_layers[:, :, i] = tmp
                depth_layers_sorted = np.sort(depth_layers, axis=2)[:, :, :max_depth_layer]
                bg_mask = depth_layers_sorted == large_depth_const
                depth_layers_sorted[bg_mask] = 0
                depth_layers_sorted = (depth_layers_sorted * 1000).astype(np.uint16)
                # print('time for calculating depth layers', time.time() - time1)
                # time1 = time.time()
                index_layers_sorted = np.argsort(depth_layers, axis=2)[:, :, :max_depth_layer] // 2
                index_layers_sorted[bg_mask] = -1
                objid_layers = np.zeros_like(index_layers_sorted).astype('uint8')
                for i, id in enumerate(id_list):
                    objid_layers[index_layers_sorted == i] = id
                # for layer_n in range(max_depth_layer):
                #     # rgbimg = cv2.imread(os.path.join(self.outputpath, "{0:06d}-color.png".format(idx)))
                #     bbox_mat[cam_name][layer_n] = {}
                #     for id in id_list:
                #         index_mask = np.zeros((H, W), dtype=np.uint)
                #         for i in range(layer_n + 1): # 
                #             index_mask[objid_layers[:, :, i] == id] = id
                #         result = self._getbbxycb(index_mask)
                #         if result[0]:
                #             bbox_mat[cam_name][layer_n][id] = result[1]
                # print('time for calculating bounding box layers', time.time() - time1)
                    #         color = np.random.randint(0, 256, (3,))
                    #         color = ( int (color [ 0 ]), int (color [ 1 ]), int (color [ 2 ]))
                    #         rgbimg = cv2.rectangle(rgbimg, (result[1][0], result[1][1]), (result[1][2], result[1][3]), color)
                    #         rgbimg = cv2.putText(rgbimg, list(self.object_label.keys())[list(self.object_label.values()).index(id)], (result[1][0], result[1][1]), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                    # cv2.imwrite(os.path.join(self.outputpath, "{:06d}-bb_mask_check_{:d}.png".format(idx, layer_n)), rgbimg)
                # time1 = time.time()
                for i in range(max_depth_layer):
                    Image.fromarray((depth_layers_sorted[:, :, i])).save(os.path.join(self.outputpath, "{:06d}-depth_layer{:d}.png".format(idx, i)))
                    Image.fromarray((objid_layers[:, :, i])).save(os.path.join(self.outputpath, "{:06d}-mask_layer{:d}.png".format(idx, i)))
                # print('time for saving depth and mask layer images', time.time() - time1)
                # np.save(os.path.join(self.outputpath, "{}-depthlayer_{}.npy".format(idx, max_depth_layer)), depth_layers_sorted) # size too large compared to layered depth images
                # for key in sorted(depth_buffer.keys(), reverse=False):
                #     # depth_max_before = depth_current_max.copy()
                #     obj_d = depth_buffer[key]
                #     depth_layer_n[obj_d > 0.001] += 1
                #     obj_d[depth_layer_n >= max_depth_layer] = 0 # do not update if already over max_depth_layer
                #     depth_layer_n[depth_layer_n >= max_depth_layer] = max_depth_layer - 1
                #     layers = np.unique(depth_layer_n[obj_d > 0.001])
                #     for l in layers:
                #         if l == -1: continue
                #         mask = np.bitwise_and(obj_d > 0.001, depth_layers[l] == 0)
                #         depth_layers[l][mask] = obj_d[mask]
                #     # depth_current_max = np.maximum(depth_current_max, obj_d)
                # assert np.array_equal(depth_layers[0], obj_depth)
                # depth_layers = (depth_layers * 1000).astype(np.uint16)
                # np.save(os.path.join(self.outputpath, "{}-depthlayer_{}.npy".format(idx, max_depth_layer)), depth_layers)

            if save_mat:
                savemat(os.path.join(self.outputpath, "{0:06d}-meta.mat".format(idx)), mat)
            
            if render_seg:
                Image.fromarray(segimg).save(os.path.join(self.outputpath, "{0:06d}-label.png".format(idx)))

            if render_depthtrue:
                obj_true_depth = (obj_depth * 1000).astype(np.uint16)
                img_depth[obj_true_depth!=0] = obj_true_depth[obj_true_depth!=0]
                Image.fromarray(img_depth).save(os.path.join(self.outputpath, "{0:06d}-depth_true.png".format(idx)))

            if render_normal:
                # use normalSpeed library from github: (same result as cv2 Sobel/Scharr + medianblur, 3x faster)
                vn = normalSpeed.depth_normal(img_depth, fx, fy, normalspeed_k_size, normalspeed_distance_threshold, normalspeed_difference_threshold, True)
                # vn = normalSpeed.depth_normal(img_depth, fx, fy, k_size, distance_threshold, difference_threshold, False)
                normal = ((vn + 1)*255/2).astype(np.uint8)
                Image.fromarray(normal).save(os.path.join(self.outputpath, "{0:06d}-normal_true.png".format(idx)))
        
        if render_backface:
            savemat(os.path.join(self.outputpath, "bbox.mat"), bbox_mat)

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
    
    def move_rgbd(self, idx, cam_name, rescale, savefile=True):
        # copy/crop-reshape rgb-d
        if rescale:
            img_rgb = cv2.imread(os.path.join(self.datasrc, "rgb", cam_name))
            img_depth = cv2.imread(os.path.join(self.datasrc, "depth", cam_name), -1)
            img_rgb = cv2.resize(img_rgb[:, 160:-160], (640, 480))
            img_depth = cv2.resize(img_depth[:, 160:-160], (640, 480), interpolation=cv2.INTER_NEAREST)
            if savefile:
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
            if savefile:
                os.system('cp ' + os.path.join(self.datasrc, "rgb", cam_name) + ' ' + os.path.join(self.outputpath, "{0:06d}-color.png".format(idx)))
                os.system('cp ' + os.path.join(self.datasrc, "depth", cam_name) + ' ' + os.path.join(self.outputpath, "{0:06d}-depth.png".format(idx)))
        return img_depth