import pyrender
import numpy as np
import os
import json
import trimesh
import pyrender
from kernel.geometry import _pose2Rotation
from PIL import Image
from tqdm import tqdm

class offlineRender:
    def __init__(self, param, outputdir) -> None:
        self.param = param
        self.outputpath = os.path.join(self.param.dir, outputdir)
        self.modelsrc = self.param.modelsrc
        self.reconstructionsrc = self.param.reconstructionsrc
        self.datasrc = self.param.datasrc
        self.intrinsic = self.param.camera["intrinsic"]
        self.objects = self.param.objs
        self._prepare_scene()
        self._parsecamfile()
        self._applytrans2cam()
        self.render = pyrender.OffscreenRenderer(self.param.camera["resolution"][0], self.param.camera["resolution"][1])
        self._createallpkgs()
        self.renderAll()
    
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
        for obj in self.objects:
            ## for full model
            if self.objects[obj]['type'] == 'normal':
                tm = trimesh.load(os.path.join(self.modelsrc, obj, obj+".obj"))
                mesh = pyrender.Mesh.from_trimesh(tm)
                node = pyrender.Node(mesh=mesh, matrix=self.objects[obj]['trans'])
                self.objectmap[node] = {"index":object_index, "name":obj, "trans":self.objects[obj]['trans']}
                self.scene.add_node(node)
                object_index += 1
            ## for split model
            if self.objects[obj]['type'] == 'split':
                splitobjfiles = os.listdir(os.path.join(self.modelsrc, obj, "split"))
                for f in splitobjfiles:
                    if f.endswith(".obj"):
                        tm = trimesh.load(os.path.join(self.modelsrc, obj, "split", f))
                        mesh = pyrender.Mesh.from_trimesh(tm)
                        node = pyrender.Node(mesh=mesh, matrix=self.objects[obj]['trans'])
                        self.objectmap[node] = {"index":object_index, "name":f.split(".")[0], "trans":self.objects[obj]['trans']}
                        self.scene.add_node(node)
                        object_index += 1
    
    def _parsecamfile(self):
        self.camposes = {}
        f = open(os.path.join(self.reconstructionsrc, "campose.txt"))
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
            origin_pose = np.linalg.inv(origin_pose).dot(Axis_align)
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
        for cam in tqdm(self.camposes):
            camT = self.camposes[cam]
            segment = self._render(camT, self.scene)
            perfix = cam.split(".")[0]
            inputrgb = np.array(Image.open(os.path.join(self.datasrc, "rgb", cam)))

            for node in self.objectmap:
                posepath = os.path.join(self.outputpath, self.objectmap[node]["name"], "pose")
                rgbpath = os.path.join(self.outputpath, self.objectmap[node]["name"], "rgb")
                modelT = self.objectmap[node]["trans"]
                model_camT = np.linalg.inv(camT.dot(Axis_align)).dot(modelT)
                self._createpose(posepath, perfix, model_camT)
                self._createrbg(inputrgb, segment, os.path.join(rgbpath, cam), self.objectmap[node]["index"] + 1)



    def _createpose(self, path, perfix, T):
        posefileName = os.path.join(path, perfix + ".txt")
        # np.savetxt(posefileName, np.linalg.inv(T), fmt='%f', delimiter=' ')
        np.savetxt(posefileName, T, fmt='%f', delimiter=' ')

    def _createrbg(self, inputrgb, segment, outputpath, segment_index):
        rgb = inputrgb.copy()
        mask = np.repeat((segment != segment_index)[:, :, np.newaxis], 3, axis=2)
        rgb[mask] = 0
        img = Image.fromarray(rgb)
        img.save(outputpath)