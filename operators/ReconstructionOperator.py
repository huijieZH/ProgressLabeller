from typing import DefaultDict
import bpy
from bpy.props import StringProperty, EnumProperty, FloatProperty
from bpy.types import Operator
import os
import multiprocessing
import subprocess
import sys

from kernel.exporter import configuration_export

from kernel.logging_utility import log_report
from kernel.loader import load_reconstruction_result, load_pc
from kernel.blender_utility import _get_configuration, _align_reconstruction, _clear_recon_output, _initreconpose
from kernel.orb_slam3.orbslam3_utility import _load_stereo_calib

try: 
    from kernel.reconstruction import KinectfusionRecon, poseFusion
except Exception as e:
    log_report(
        "Error", e, None
    )        

class Reconstruction(Operator):
    """This appears in the tooltip of the operator and in the generated docs"""
    bl_idname = "reconstruction.methodselect"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "3D Reconstruction from data (Depth, RGB or both)"

    # bl_options = {'REGISTER', 'INTERNAL'}

    ReconstructionType: EnumProperty(
        name="Reconstruction Method",
        description="Choose a reconstruction method",
        items=(
            ('KinectFusion', "KinectFusion", "Need depth & rgb data information"),
            ('COLMAP', "COLMAP", "Need depth & rgb data information"),
            ('ORB_SLAM2', "ORB_SLAM2", "Need depth & rgb data information"),
            ('ORB_SLAM3', "ORB_SLAM3", "Need depth & rgb data information"),
            ('VGGT_SLAM', "VGGT-SLAM", "Feed-forward dense reconstruction (VGGT-SLAM 2.0), monocular or stereo")
        ),
        default='ORB_SLAM3',
    )

    PerfixList = list()

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        scene = context.scene
        config_id, config = _get_configuration(context.object)
        if self.ReconstructionType == "KinectFusion":      
            _clear_recon_output(config.reconstructionsrc)    
            KinectfusionRecon(
                data_folder = config.datasrc,
                save_folder = config.reconstructionsrc,
                prefix_list = self.PerfixList,
                resX = config.resX, 
                resY = config.resY, 
                fx = config.fx, 
                fy = config.fy, 
                cx = config.cx, 
                cy = config.cy,
                tsdf_voxel_size = scene.kinectfusionparas.tsdf_voxel_size, 
                tsdf_trunc_margin = scene.kinectfusionparas.tsdf_trunc_margin, 
                pcd_voxel_size = scene.kinectfusionparas.pcd_voxel_size, 
                depth_scale = config.depth_scale, 
                depth_ignore = config.depth_ignore, 
                DISPLAY = scene.kinectfusionparas.DISPLAY,  
                frame_per_display = scene.kinectfusionparas.frame_per_display, 
            )
            config.inverse_pose = False
            _initreconpose(config)
            load_reconstruction_result(filepath = config.reconstructionsrc, 
                                        pointcloudscale = 1.0, 
                                        datasrc = config.datasrc,
                                        config_id = config_id,
                                        camera_display_scale = config.cameradisplayscale,
                                        CAMPOSE_INVERSE= config.inverse_pose
                                        )
            dir = os.path.dirname(config.reconstructionsrc)
            configuration_export(config, os.path.join(dir, "configuration.json"))
        elif self.ReconstructionType == "COLMAP":
            is_stereo = config.sensor_mode == "STEREO"
            stereo_calib = None
            if is_stereo:
                try:
                    stereo_calib = _load_stereo_calib(scene.orbslamparas.stereo_calib_path)
                except Exception as e:
                    log_report("Error", "Stereo calibration load failed: {0}".format(e), None)
                    return {'FINISHED'}

            _clear_recon_output(config.reconstructionsrc)
            source = os.path.dirname(os.path.dirname(__file__))
            code_path = os.path.join(source, "kernel", "colmap", "colmap_runner.py")
            venv_py = os.environ.get("COLMAP_PY", "/opt/colmap-venv/bin/python")

            if is_stereo:
                # Parent dir; image names are `left/X.png` / `right/X.png`.
                image_dir = config.datasrc
            else:
                image_dir = os.path.join(config.datasrc, "rgb")

            cmd = [
                venv_py, code_path,
                "--database_path", os.path.join(config.reconstructionsrc, "reconstruction.db"),
                "--image_dir", image_dir,
                "--image_list_path", os.path.join(config.reconstructionsrc, "image-list.txt"),
                "--camera_params", "{0},{1},{2},{3}".format(config.fx, config.fy, config.cx, config.cy),
                "--output_path", config.reconstructionsrc,
                "--matcher", scene.colmapparas.matcher,
                "--num_threads", str(scene.colmapparas.num_threads),
                "--overlap", str(scene.colmapparas.overlap),
            ]
            if is_stereo:
                cmd += [
                    "--stereo",
                    "--right_camera_params", "{0},{1},{2},{3}".format(
                        stereo_calib["fx2"], stereo_calib["fy2"],
                        stereo_calib["cx2"], stereo_calib["cy2"]),
                    "--baseline", "{0}".format(stereo_calib["baseline"]),
                ]
            if scene.colmapparas.refine_focal_length:
                cmd += ["--refine_focal_length"]

            rc = subprocess.call(cmd)
            if rc != 0:
                log_report("Error", "COLMAP runner failed (rc={0}); is pycolmap installed at {1}?".format(rc, venv_py), None)
                return {'FINISHED'}
            config.inverse_pose = True
            if is_stereo:
                # Runner already applied a metric Sim3 scale derived from
                # the known stereo baseline; loader just passes through.
                scale = 1.0
            else:
                scale = _align_reconstruction(config, scene, scene.scalealign.THRESHOLD, scene.scalealign.NUM_THRESHOLD)
            config.reconstructionscale = scale
            _initreconpose(config)
            load_reconstruction_result(filepath = config.reconstructionsrc,
                                pointcloudscale = scale,
                                datasrc = config.datasrc,
                                config_id = config_id,
                                camera_display_scale = config.cameradisplayscale,
                                IMPORT_RATIO = 1.0,
                                CAMPOSE_INVERSE= config.inverse_pose
                                )
            dir = os.path.dirname(config.reconstructionsrc)
            configuration_export(config, os.path.join(dir, "configuration.json"))
        elif self.ReconstructionType == "ORB_SLAM2":
            try: 
                from kernel.orb_slam.build import orb_extension
                from kernel.orb_slam.orbslam_utility import orbslam_yaml, orbslam_associatefile
            except:
                log_report(
                    "Error", "Please successfully install ORB_SLAM2, pybind11 and complie orb_extension", None
                )            
            else:
                _clear_recon_output(config.reconstructionsrc)    
                orbslam_yaml(os.path.join(config.reconstructionsrc, "orb_slam.yaml"), 
                             config.fx, config.fy, config.cx, config.cy, 
                             config.resX, config.resY, config.depth_scale, 
                             scene.orbslamparas.timestampfrenquency)
                orbslam_associatefile(os.path.join(config.reconstructionsrc, "associate.txt"), 
                                      config.datasrc, 
                                      scene.orbslamparas.timestampfrenquency)
                source = os.path.dirname(os.path.dirname(__file__))
                code_path = os.path.join(source, "kernel", "orb_slam", "orb_slam.py")
                os.system(sys.executable + " {0} {1} {2} {3} {4} {5} {6} {7}".format(code_path, 
                    scene.orbslamparas.orb_vocabularysrc, 
                    os.path.join(config.reconstructionsrc,"orb_slam.yaml"),
                    config.datasrc,
                    os.path.join(config.reconstructionsrc, "associate.txt"),
                    config.reconstructionsrc,
                    scene.orbslamparas.timestampfrenquency,
                    float(scene.orbslamparas.display)
                    ))
                config.inverse_pose = False
                config.reconstructionscale = 1.0
                _initreconpose(config)
                load_reconstruction_result(filepath = config.reconstructionsrc, 
                                           pointcloudscale = 1.0, 
                                           datasrc = config.datasrc,
                                           config_id = config_id,
                                           camera_display_scale = config.cameradisplayscale,
                                           IMPORT_RATIO = config.sample_rate,
                                           CAMPOSE_INVERSE= config.inverse_pose
                                           )
                dir = os.path.dirname(config.reconstructionsrc)
                configuration_export(config, os.path.join(dir, "configuration.json"))

        elif self.ReconstructionType == "ORB_SLAM3":
            try:
                from kernel.orb_slam3.build import orb3_extension
                from kernel.orb_slam3.orbslam3_utility import orbslam3_yaml, orbslam3_associatefile
            except:
                log_report(
                    "Error", "Please successfully install ORB_SLAM3, pybind11 and complie orb_extension", None
                )
            else:
                sensor_mode = config.sensor_mode
                mode_int = {"MONOCULAR": 0, "RGBD": 1, "STEREO": 2}[sensor_mode]

                stereo_calib = None
                if sensor_mode == "STEREO":
                    try:
                        stereo_calib = _load_stereo_calib(scene.orbslamparas.stereo_calib_path)
                    except Exception as e:
                        log_report("Error", "Stereo calibration load failed: {0}".format(e), None)
                        return {'FINISHED'}

                _clear_recon_output(config.reconstructionsrc)
                orbslam3_yaml(os.path.join(config.reconstructionsrc, "orb_slam3.yaml"),
                             config.fx, config.fy, config.cx, config.cy,
                             config.resX, config.resY, config.depth_scale,
                             scene.orbslamparas.timestampfrenquency,
                             sensor_mode=sensor_mode,
                             stereo_calib=stereo_calib,
                             stereo_th_depth=scene.orbslamparas.stereo_th_depth)
                orbslam3_associatefile(os.path.join(config.reconstructionsrc, "associate.txt"),
                                      config.datasrc,
                                      scene.orbslamparas.timestampfrenquency,
                                      sensor_mode=sensor_mode)
                source = os.path.dirname(os.path.dirname(__file__))
                code_path = os.path.join(source, "kernel", "orb_slam3", "orb_slam3.py")
                os.system(sys.executable + " {0} {1} {2} {3} {4} {5} {6} {7} {8}".format(code_path,
                    scene.orbslamparas.orb_vocabularysrc,
                    os.path.join(config.reconstructionsrc,"orb_slam3.yaml"),
                    config.datasrc,
                    os.path.join(config.reconstructionsrc, "associate.txt"),
                    config.reconstructionsrc,
                    scene.orbslamparas.timestampfrenquency,
                    float(scene.orbslamparas.display),
                    mode_int,
                    ))
                config.inverse_pose = False
                config.reconstructionscale = 1.0
                _initreconpose(config)
                load_reconstruction_result(filepath = config.reconstructionsrc,
                                           pointcloudscale = 1.0,
                                           datasrc = config.datasrc,
                                           config_id = config_id,
                                           camera_display_scale = config.cameradisplayscale,
                                           IMPORT_RATIO = config.sample_rate,
                                           CAMPOSE_INVERSE= config.inverse_pose
                                           )
                dir = os.path.dirname(config.reconstructionsrc)
                configuration_export(config, os.path.join(dir, "configuration.json"))

        elif self.ReconstructionType == "VGGT_SLAM":
            is_stereo = config.sensor_mode == "STEREO"
            stereo_calib = None
            if is_stereo:
                try:
                    stereo_calib = _load_stereo_calib(scene.orbslamparas.stereo_calib_path)
                except Exception as e:
                    log_report("Error", "Stereo calibration load failed: {0}".format(e), None)
                    return {'FINISHED'}

            _clear_recon_output(config.reconstructionsrc)
            source = os.path.dirname(os.path.dirname(__file__))
            code_path = os.path.join(source, "kernel", "vggt_slam", "vggt_slam_runner.py")
            venv_py = os.environ.get("VGGT_PY", "/opt/vggt-venv/bin/python")

            # Stereo feeds left/ + right/ together (parent dir); monocular uses rgb/.
            image_dir = config.datasrc if is_stereo else os.path.join(config.datasrc, "rgb")

            cmd = [
                venv_py, code_path,
                "--image_dir", image_dir,
                "--output_path", config.reconstructionsrc,
                "--image_list_path", os.path.join(config.reconstructionsrc, "image-list.txt"),
                "--vggt_slam_dir", os.environ.get("VGGT_SLAM_DIR", "/opt/VGGT-SLAM"),
                "--weights_dir", os.environ.get("VGGT_WEIGHTS", os.path.join(source, "weights")),
                "--submap_size", str(scene.vggtslamparas.submap_size),
                "--max_loops", str(scene.vggtslamparas.max_loops),
                "--conf_threshold", str(scene.vggtslamparas.conf_threshold),
                "--min_disparity", str(scene.vggtslamparas.min_disparity),
                "--vis_voxel_size", str(scene.vggtslamparas.vis_voxel_size),
            ]
            if scene.vggtslamparas.use_keyframe_downsample:
                cmd += ["--use_keyframe_downsample"]
            if scene.vggtslamparas.keyframe_filter:
                cmd += [
                    "--kf_filter",
                    "--kf_max_delta_trans", str(scene.vggtslamparas.kf_max_delta_trans),
                    "--kf_max_delta_rot", str(scene.vggtslamparas.kf_max_delta_rot),
                    "--kf_max_frames", str(scene.vggtslamparas.kf_max_frames),
                ]
            if is_stereo:
                cmd += ["--stereo", "--baseline", "{0}".format(stereo_calib["baseline"])]

            rc = subprocess.call(cmd)
            if rc != 0:
                log_report("Error", "VGGT-SLAM runner failed (rc={0}); is VGGT-SLAM installed at {1}?".format(rc, venv_py), None)
                return {'FINISHED'}

            # Runner writes camera-to-world poses; stereo already baked in the
            # metric scale, monocular is up-to-scale (adjust in Blender).
            config.inverse_pose = False
            config.reconstructionscale = 1.0
            _initreconpose(config)
            load_reconstruction_result(filepath = config.reconstructionsrc,
                                       pointcloudscale = 1.0,
                                       datasrc = config.datasrc,
                                       config_id = config_id,
                                       camera_display_scale = config.cameradisplayscale,
                                       IMPORT_RATIO = config.sample_rate,
                                       CAMPOSE_INVERSE = config.inverse_pose
                                       )
            dir = os.path.dirname(config.reconstructionsrc)
            configuration_export(config, os.path.join(dir, "configuration.json"))

        ### whatever pose reconstruction method, estimate an volume
        # if self.ReconstructionType == "ORB_SLAM2" or self.ReconstructionType == "ORB_SLAM3":

        #     poseFusion(
        #         os.path.join(dir, "configuration.json"),
        #         tsdf_voxel_size = scene.kinectfusionparas.tsdf_voxel_size,
        #         tsdf_trunc_margin = scene.kinectfusionparas.tsdf_trunc_margin, 
        #         pcd_voxel_size = scene.kinectfusionparas.pcd_voxel_size, 
        #         depth_ignore = config.depth_ignore
        #         )
        #     load_pc(os.path.join(config.reconstructionsrc, "depthfused.ply"), 1.0, config_id, "reconstruction_depthfusion")
        return {'FINISHED'}


    def invoke(self, context, event):
        current_object = bpy.context.object.name
        workspace_name = current_object.split(":")[0]
        config_id = context.object["config_id"]
        config = bpy.context.scene.configuration[config_id]
        needs_depth = config.sensor_mode != "STEREO"
        for obj in bpy.data.objects:
            if obj.name.startswith(workspace_name) and obj['type'] == "camera":
                perfix = (obj.name.split(":")[1]).replace("view", "")
                has_rgb = (workspace_name + ":rgb" + perfix) in bpy.data.images
                has_depth = (workspace_name + ":depth" + perfix) in bpy.data.images
                ready = has_rgb and (has_depth or not needs_depth)
                if ready and perfix not in self.PerfixList:
                    self.PerfixList.append(perfix)
        self.PerfixList.sort(key = lambda x:int(x))

        if len(self.PerfixList) == 0:
            if needs_depth:
                msg = "You should upload the rgb and depth data before doing reconstruction"
            else:
                msg = "You should upload the rgb (left) data before doing reconstruction"
            log_report("Error", msg, None)
            return {'FINISHED'}
        elif config.reconstructionsrc == "":
            log_report(
                "Error", "You should specify your reconstruction path first", None
            )
            return {'FINISHED'}
        else:
            return context.window_manager.invoke_props_dialog(self, width = 400)

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        config_id = bpy.context.object["config_id"]
        config = scene.configuration[config_id]
        layout.prop(self, "ReconstructionType", text="Reconstruction Method")
        if self.ReconstructionType == "KinectFusion":
            layout.label(text="Set Camera Parameters:")
            box = layout.box() 
            row = box.row(align=True)
            row.prop(config, "fx")
            row.prop(config, "fy")
            row = box.row(align=True)
            row.prop(config, "cx")
            row.prop(config, "cy")
            row = box.row(align=True)
            row.prop(config, "resX")
            row.prop(config, "resY")
            layout.label(text="Set KinectFusion Parameters:")
            row = layout.row() 
            row.prop(config, "depth_scale")
            row = layout.row() 
            row.prop(scene.kinectfusionparas, "tsdf_voxel_size")
            row = layout.row() 
            row.prop(scene.kinectfusionparas, "tsdf_trunc_margin")
            row = layout.row() 
            row.prop(scene.kinectfusionparas, "pcd_voxel_size")
            row = layout.row() 
            row.prop(config, "depth_ignore")
            box = layout.box() 
            row = box.row(align=True)
            row.prop(scene.kinectfusionparas, "DISPLAY")       
            
        elif self.ReconstructionType == "COLMAP":
            sensor_mode = config.sensor_mode
            layout.label(text="Sensor Mode: {0}".format(sensor_mode))
            layout.label(text="Set Camera Parameters:")
            box = layout.box()
            row = box.row(align=True)
            row.prop(config, "fx")
            row.prop(config, "fy")
            row = box.row(align=True)
            row.prop(config, "cx")
            row.prop(config, "cy")
            row = box.row(align=True)
            row.prop(config, "resX")
            row.prop(config, "resY")
            layout.label(text="Set Reconstruction Loading Parameters:")
            layout.label(text="Set Plane Alignment (ICP) Parameters:")
            box = layout.box()
            row = box.row()
            row.prop(scene.planalignmentparas, "threshold")
            row = box.row()
            row.prop(scene.planalignmentparas, "n")
            row = box.row()
            row.prop(scene.planalignmentparas, "iteration")
            if sensor_mode == "STEREO":
                layout.label(text="Set Stereo Parameters:")
                box = layout.box()
                row = box.row()
                row.prop(scene.orbslamparas, "stereo_calib_path")
                box = layout.box()
                box.label(text="Scale is recovered from the stereo baseline.")
            else:
                box = layout.box()
                box.label(text="Point Cloud Scale:")
                row = box.row()
                row.prop(config, "depth_scale")
            row = layout.row()
            row.prop(config, "cameradisplayscale")
            if sensor_mode != "STEREO":
                row = layout.row()
                row.prop(scene.scalealign, "THRESHOLD")
                row = layout.row()
                row.prop(scene.scalealign, "NUM_THRESHOLD")
            layout.label(text="Set COLMAP Parameters:")
            box = layout.box()
            row = box.row()
            row.prop(scene.colmapparas, "matcher")
            if scene.colmapparas.matcher == "sequential":
                row = box.row()
                row.prop(scene.colmapparas, "overlap")
            row = box.row()
            row.prop(scene.colmapparas, "num_threads")
            row = box.row()
            row.prop(scene.colmapparas, "refine_focal_length")
        
        elif self.ReconstructionType == "ORB_SLAM2":
            layout.label(text="Set Camera Parameters:")
            box = layout.box() 
            row = box.row(align=True)
            row.prop(config, "fx")
            row.prop(config, "fy")
            row = box.row(align=True)
            row.prop(config, "cx")
            row.prop(config, "cy")
            row = box.row(align=True)
            row.prop(config, "resX")
            row.prop(config, "resY")
            layout.label(text="Set Reconstruction Loading Parameters:")        
            layout.label(text="Set Plane Alignment (ICP) Parameters:")
            box = layout.box() 
            row = box.row()
            row.prop(scene.planalignmentparas, "threshold") 
            row = box.row()
            row.prop(scene.planalignmentparas, "n") 
            row = box.row()
            row.prop(scene.planalignmentparas, "iteration") 
            box = layout.box() 
            box.label(text="Point Cloud Scale:")
            row = box.row()
            row.prop(config, "depth_scale")
            row = layout.row()
            row.prop(config, "cameradisplayscale")
            row = layout.row()
            row.prop(scene.scalealign, "THRESHOLD")
            row = layout.row()
            row.prop(scene.scalealign, "NUM_THRESHOLD") 
            layout.label(text="Set ORB_SLAM2 Parameters:")   
            box = layout.box() 
            row = box.row()
            row.prop(scene.orbslamparas, "orb_vocabularysrc") 
            row = box.row()
            row.prop(scene.orbslamparas, "timestampfrenquency")   
            row = box.row()
            row.prop(scene.orbslamparas, "display")            

        elif self.ReconstructionType == "ORB_SLAM3":
            sensor_mode = config.sensor_mode
            layout.label(text="Sensor Mode: {0}".format(sensor_mode))

            layout.label(text="Set Camera Parameters:")
            box = layout.box()
            row = box.row(align=True)
            row.prop(config, "fx")
            row.prop(config, "fy")
            row = box.row(align=True)
            row.prop(config, "cx")
            row.prop(config, "cy")
            row = box.row(align=True)
            row.prop(config, "resX")
            row.prop(config, "resY")
            layout.label(text="Set Reconstruction Loading Parameters:")
            layout.label(text="Set Plane Alignment (ICP) Parameters:")
            box = layout.box()
            row = box.row()
            row.prop(scene.planalignmentparas, "threshold")
            row = box.row()
            row.prop(scene.planalignmentparas, "n")
            row = box.row()
            row.prop(scene.planalignmentparas, "iteration")
            if sensor_mode == 'RGBD':
                box = layout.box()
                box.label(text="Point Cloud Scale:")
                row = box.row()
                row.prop(config, "depth_scale")
            row = layout.row()
            row.prop(config, "cameradisplayscale")
            if sensor_mode == 'RGBD':
                row = layout.row()
                row.prop(scene.scalealign, "THRESHOLD")
                row = layout.row()
                row.prop(scene.scalealign, "NUM_THRESHOLD")
            if sensor_mode == 'STEREO':
                layout.label(text="Set Stereo Parameters:")
                box = layout.box()
                row = box.row()
                row.prop(scene.orbslamparas, "stereo_calib_path")
                row = box.row()
                row.prop(scene.orbslamparas, "stereo_th_depth")
            layout.label(text="Set ORB_SLAM3 Parameters:")
            box = layout.box()
            row = box.row()
            row.prop(scene.orbslamparas, "orb_vocabularysrc")
            row = box.row()
            row.prop(scene.orbslamparas, "timestampfrenquency")
            row = box.row()
            row.prop(scene.orbslamparas, "display")
            # layout.label(text="Set Depth Fusion Parameters:")
            # row = layout.row() 
            # row.prop(scene.kinectfusionparas, "tsdf_voxel_size")
            # row = layout.row() 
            # row.prop(scene.kinectfusionparas, "tsdf_trunc_margin")
            # row = layout.row() 
            # row.prop(scene.kinectfusionparas, "pcd_voxel_size")
            # row = layout.row() 
            # row.prop(config, "depth_ignore")
            # box = layout.box()

        elif self.ReconstructionType == "VGGT_SLAM":
            sensor_mode = config.sensor_mode
            layout.label(text="Sensor Mode: {0}".format(sensor_mode))
            layout.label(text="Set Camera Parameters:")
            box = layout.box()
            row = box.row(align=True)
            row.prop(config, "fx")
            row.prop(config, "fy")
            row = box.row(align=True)
            row.prop(config, "cx")
            row.prop(config, "cy")
            row = box.row(align=True)
            row.prop(config, "resX")
            row.prop(config, "resY")
            row = layout.row()
            row.prop(config, "cameradisplayscale")
            if sensor_mode == "STEREO":
                layout.label(text="Set Stereo Parameters:")
                box = layout.box()
                row = box.row()
                row.prop(scene.orbslamparas, "stereo_calib_path")
                box = layout.box()
                box.label(text="Metric scale is recovered from the stereo baseline.")
            else:
                box = layout.box()
                box.label(text="Monocular reconstruction is up-to-scale; adjust scale in Blender.")
            layout.label(text="Set VGGT-SLAM Parameters:")
            box = layout.box()
            row = box.row()
            row.prop(scene.vggtslamparas, "submap_size")
            row = box.row()
            row.prop(scene.vggtslamparas, "conf_threshold")
            row = box.row()
            row.prop(scene.vggtslamparas, "max_loops")
            row = box.row()
            row.prop(scene.vggtslamparas, "use_keyframe_downsample")
            if scene.vggtslamparas.use_keyframe_downsample:
                row = box.row()
                row.prop(scene.vggtslamparas, "min_disparity")
            row = box.row()
            row.prop(scene.vggtslamparas, "vis_voxel_size")
            row = box.row()
            row.prop(scene.vggtslamparas, "keyframe_filter")
            if scene.vggtslamparas.keyframe_filter:
                row = box.row()
                row.prop(scene.vggtslamparas, "kf_max_delta_trans")
                row = box.row()
                row.prop(scene.vggtslamparas, "kf_max_delta_rot")
                row = box.row()
                row.prop(scene.vggtslamparas, "kf_max_frames")


class DepthFusion(Operator):
    """This appears in the tooltip of the operator and in the generated docs"""
    bl_idname = "reconstruction.depthfusion"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "Fusion the depth and rgb from reconstructed camera poses"

    # bl_options = {'REGISTER', 'INTERNAL'}

    PerfixList = list()

    @classmethod
    def poll(cls, context):
        return True

    def execute(self, context):
        scene = context.scene
        config_id, config = _get_configuration(context.object)    
        dir = os.path.dirname(config.reconstructionsrc)    
        poseFusion(
            os.path.join(dir, "configuration.json"),
            tsdf_voxel_size = scene.kinectfusionparas.tsdf_voxel_size,
            tsdf_trunc_margin = scene.kinectfusionparas.tsdf_trunc_margin, 
            pcd_voxel_size = scene.kinectfusionparas.pcd_voxel_size, 
            depth_ignore = config.depth_ignore
            )
        load_pc(os.path.join(config.reconstructionsrc, "depthfused.ply"), 1.0, config_id, "reconstruction_depthfusion")
        return {'FINISHED'}

    def invoke(self, context, event):
        current_object = bpy.context.object.name
        workspace_name = current_object.split(":")[0]        
        for obj in bpy.data.objects:
            if obj.name.startswith(workspace_name) and obj['type'] == "camera":
                perfix = (obj.name.split(":")[1]).replace("view", "")
                if (workspace_name + ":" + "depth" + perfix in bpy.data.images) and (workspace_name + ":" + "rgb" + perfix in bpy.data.images) and (perfix not in self.PerfixList):
                    self.PerfixList.append(perfix)
        self.PerfixList.sort(key = lambda x:int(x))

        config_id = context.object["config_id"]
        config = bpy.context.scene.configuration[config_id]  

        if len(self.PerfixList) == 0:
            log_report(
                "Error", "You should upload the rgb and depth data before doing reconstruction", None
            )     
            return {'FINISHED'}
        elif config.reconstructionsrc == "":
            log_report(
                "Error", "You should specify your reconstruction path first", None
            )     
            return {'FINISHED'}            
        else:
            files = os.listdir(config.reconstructionsrc)
            if "campose.txt" not in files or "fused.ply" not in files:
                log_report(
                    "Error", "You should do the reconstruction before fusion", None
                )     
                return {'FINISHED'}    
            else:
                return context.window_manager.invoke_props_dialog(self, width = 400)

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        config_id = bpy.context.object["config_id"]
        config = scene.configuration[config_id]
        layout.label(text="Set Camera Parameters:")
        box = layout.box() 
        row = box.row(align=True)
        row.prop(config, "fx")
        row.prop(config, "fy")
        row = box.row(align=True)
        row.prop(config, "cx")
        row.prop(config, "cy")
        row = box.row(align=True)
        row.prop(config, "resX")
        row.prop(config, "resY")
        layout.label(text="Set Fusion Parameters:")
        row = layout.row() 
        row.prop(config, "depth_scale")
        row = layout.row() 
        row.prop(scene.kinectfusionparas, "tsdf_voxel_size")
        row = layout.row() 
        row.prop(scene.kinectfusionparas, "tsdf_trunc_margin")
        row = layout.row() 
        row.prop(scene.kinectfusionparas, "pcd_voxel_size")
        row = layout.row() 
        row.prop(config, "depth_ignore")   


class KinectfusionConfig(bpy.types.PropertyGroup):

    tsdf_voxel_size: bpy.props.FloatProperty(name="TSDF Voxel Size (m)", 
                                            description="Voxel size for truncated signed distance function, in meter", 
                                            default=0.0025, 
                                            min=0.00, 
                                            max=10.00, 
                                            step=4, 
                                            precision=4)
    tsdf_trunc_margin: bpy.props.FloatProperty(name="TSDF Truncated Margin (m)", 
                                            description="Truncated margin for truncated signed distance function, in meter", 
                                            default=0.015, 
                                            min=0.00, 
                                            max=10.00, 
                                            step=4, 
                                            precision=4)
    pcd_voxel_size: bpy.props.FloatProperty(name="Model Voxel Size (m)", 
                                            description="Voxel size for rendered model, in meter", 
                                            default=0.005, 
                                            min=0.00, 
                                            max=10.00, 
                                            step=4, 
                                            precision=4)  
    DISPLAY: bpy.props.BoolProperty(
        name="Display during reconstruction",
        description="During reconstruction simutaneously display the reconstruction result in Blender",
        default=False,
    )       

    frame_per_display: bpy.props.IntProperty(name="Frames per display", 
                                                description="Frame interval between two displays", 
                                                default=5)                                                                           

class ORBSLAMConfig(bpy.types.PropertyGroup):
    dirpath = os.path.dirname(os.path.dirname(__file__))
    orb_vocabularysrc = os.path.join(dirpath, "kernel", "orb_slam", "ORBvoc.txt")
    orb_vocabularysrc: bpy.props.StringProperty(name = "orb_vocabulary path",
                                                subtype = "FILE_PATH",
                                                default = orb_vocabularysrc)
    timestampfrenquency: bpy.props.FloatProperty(name="Frequency for timestamp",
                                            description="Frequency of the images, realted to the speed of ORB-SLAM, set 20 for 1280X720 images and 30 for 640X480 ",
                                            default=20,
                                            min=0.0,
                                            max=100.0,
                                            step=1,
                                            precision=1)
    display:  bpy.props.BoolProperty(name="Display reconstruction",
                                      description="Display reconstruction using OPRB_SLAM2's UI",
                                      default=False)

    def sensor_mode_update(self, context):
        if context.object is not None:
            _, cfg = _get_configuration(context.object)
            if cfg is not None:
                cfg.sensor_mode = self.sensor_mode

    sensor_mode: bpy.props.EnumProperty(
        name="ORB-SLAM3 Sensor Mode",
        description="Choose ORB-SLAM3 sensor mode. MONOCULAR: RGB-only (data/rgb/). RGBD: RGB+depth (data/rgb/+data/depth/). STEREO: rectified stereo pair (data/left/+data/right/)",
        items=(
            ('MONOCULAR', "Monocular (RGB only)", "Run ORB-SLAM3 with a single RGB stream from data/rgb/"),
            ('RGBD', "RGB-D", "Run ORB-SLAM3 with RGB+depth from data/rgb/ and data/depth/"),
            ('STEREO', "Stereo", "Run ORB-SLAM3 with stereo pair from data/left/ and data/right/"),
        ),
        default='MONOCULAR',
        update=sensor_mode_update,
    )
    stereo_calib_path: bpy.props.StringProperty(
        name="Stereo Calibration File",
        description="Path to a YAML/JSON file with right-camera intrinsics, distortion, baseline (m), and 4x4 extrinsic T_c1_c2",
        subtype="FILE_PATH",
        default="")
    stereo_th_depth: bpy.props.FloatProperty(
        name="Stereo ThDepth",
        description="Close/far threshold for stereo features (in baseline units)",
        default=40.0,
        min=0.0,
        max=1000.0,
        step=1,
        precision=1)

class COLMAPConfig(bpy.types.PropertyGroup):
    matcher: bpy.props.EnumProperty(
        name="Matcher",
        description="Feature matcher used by COLMAP",
        items=(
            ('sequential', "Sequential", "Match consecutive frames; fastest for ordered video"),
            ('exhaustive', "Exhaustive", "Match every pair of frames; slower but more robust on unordered images"),
        ),
        default='sequential',
    )
    num_threads: bpy.props.IntProperty(
        name="Threads",
        description="CPU threads for SIFT extraction, matching, and bundle adjustment; -1 = auto",
        default=-1,
        min=-1,
        max=64,
    )
    overlap: bpy.props.IntProperty(
        name="Overlap",
        description="Sequential matcher: how many neighboring frames each image is "
                    "matched against (in stereo, left/right are interleaved so each "
                    "left pairs with its right). Ignored for exhaustive.",
        default=10,
        min=1,
        max=100,
    )
    refine_focal_length: bpy.props.BoolProperty(
        name="Refine Focal Length",
        description="Let COLMAP's bundle adjustment refine the focal length. "
                    "Off (default) locks the calibrated intrinsics you entered.",
        default=False,
    )


class VGGTSLAMConfig(bpy.types.PropertyGroup):
    submap_size: bpy.props.IntProperty(
        name="Submap Size",
        description="Number of new frames per VGGT submap (one VGGT forward pass)",
        default=16,
        min=2,
        max=64,
    )
    conf_threshold: bpy.props.FloatProperty(
        name="Confidence Filter (%)",
        description="Initial percentage of low-confidence points to filter out",
        default=25.0,
        min=0.0,
        max=99.0,
        step=10,
        precision=1,
    )
    max_loops: bpy.props.IntProperty(
        name="Max Loop Closures",
        description="Maximum loop closures per submap (0 disables loop closure)",
        default=1,
        min=0,
        max=1,
    )
    min_disparity: bpy.props.FloatProperty(
        name="Min Disparity",
        description="Minimum optical-flow disparity to keep a frame (only used "
                    "when keyframe downsampling is enabled)",
        default=50.0,
        min=0.0,
        max=1000.0,
        step=10,
        precision=1,
    )
    use_keyframe_downsample: bpy.props.BoolProperty(
        name="Keyframe Downsample",
        description="Drop low-disparity frames via optical flow. Off (default) "
                    "reconstructs every uploaded frame so each gets a pose.",
        default=False,
    )
    vis_voxel_size: bpy.props.FloatProperty(
        name="Display Voxel Size (m)",
        description="Voxel size for downsampling the displayed dense cloud. "
                    "Metric (meters) in stereo mode; reconstruction units in "
                    "monocular. 0 = full per-pixel density (may be heavy in Blender).",
        default=0.005,
        min=0.0,
        max=1.0,
        step=1,
        precision=4,
    )
    keyframe_filter: bpy.props.BoolProperty(
        name="Delta-Pose Keyframe Filter",
        description="Load only confident frames, ranked by how far each camera "
                    "moved between its initial and pose-graph-optimized pose. "
                    "Filters the loaded cameras only; the dense cloud stays full.",
        default=False,
    )
    kf_max_delta_trans: bpy.props.FloatProperty(
        name="Max Pose Shift (m)",
        description="Drop frames whose camera center moved more than this between "
                    "the initial and optimized pose. Meters in stereo; "
                    "reconstruction units in monocular.",
        default=0.02,
        min=0.0,
        max=10.0,
        step=1,
        precision=4,
    )
    kf_max_delta_rot: bpy.props.FloatProperty(
        name="Max Pose Rotation (deg)",
        description="Drop frames whose camera rotated more than this many degrees "
                    "during optimization.",
        default=2.0,
        min=0.0,
        max=180.0,
        step=10,
        precision=2,
    )
    kf_max_frames: bpy.props.IntProperty(
        name="Max Keyframes (0 = all)",
        description="Cap on kept frames; if more pass the thresholds, keep the "
                    "ones that moved least. 0 = no cap.",
        default=0,
        min=0,
        max=100000,
    )


class ScaleAlignment(bpy.types.PropertyGroup):
    THRESHOLD: bpy.props.FloatProperty(name="variance threshold for scale alignment", 
                                        description="variance threshold for scale alignment", 
                                        default = 0.01, 
                                        min=0.0, 
                                        max=1.0, 
                                        step=2, 
                                        precision=2)   
    NUM_THRESHOLD: bpy.props.IntProperty(name="number threshold for scale alignment", 
                                        description="number threshold for scale alignment", 
                                        default = 8, 
                                        min=1, 
                                        max=20)   

def register():
    bpy.utils.register_class(Reconstruction)
    bpy.utils.register_class(DepthFusion)
    bpy.utils.register_class(KinectfusionConfig)
    bpy.utils.register_class(ORBSLAMConfig)
    bpy.utils.register_class(COLMAPConfig)
    bpy.utils.register_class(VGGTSLAMConfig)
    bpy.utils.register_class(ScaleAlignment)
    bpy.types.Scene.kinectfusionparas = bpy.props.PointerProperty(type=KinectfusionConfig)
    bpy.types.Scene.orbslamparas = bpy.props.PointerProperty(type=ORBSLAMConfig)
    bpy.types.Scene.colmapparas = bpy.props.PointerProperty(type=COLMAPConfig)
    bpy.types.Scene.vggtslamparas = bpy.props.PointerProperty(type=VGGTSLAMConfig)
    bpy.types.Scene.scalealign = bpy.props.PointerProperty(type=ScaleAlignment)

def unregister():
    bpy.utils.unregister_class(Reconstruction)
    bpy.utils.unregister_class(DepthFusion)
    bpy.utils.unregister_class(KinectfusionConfig)
    bpy.utils.unregister_class(ORBSLAMConfig)
    bpy.utils.unregister_class(COLMAPConfig)
    bpy.utils.unregister_class(VGGTSLAMConfig)
    bpy.utils.unregister_class(ScaleAlignment)