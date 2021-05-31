import bpy
import numpy as np
from PIL import Image
import os
import itertools
from kernel.logging_utility import log_report

def save_img(img_render, img_origin, img_segment, img_segment_inverse, name):
    renderim = Image.fromarray(img_render)
    renderim.save(os.path.join("tmp", name + "_render.png"))
    originim = Image.fromarray(img_origin)
    originim.save(os.path.join("tmp", name + "_origin.png"))
    segmentim = Image.fromarray(img_segment)
    segmentim.save(os.path.join("tmp", name + "_segment.png"))
    segmentim_inverse = Image.fromarray(img_segment_inverse)
    segmentim_inverse.save(os.path.join("tmp", name + "_segmentinverse.png"))


def metric_test():
    dx_list = [-0.002, -0.001, 0, 0.001, 0.002]
    dy_list = [-0.002, -0.001, 0, 0.001, 0.002]
    dz_list = [-0.002, -0.001, 0, 0.001, 0.002]
    dt_list = [-0.02, -0.01, 0, 0.01, 0.02]
    x, y, z = bpy.data.objects["mustard_bottle"].location
    _, tx, ty, _ = bpy.data.objects["mustard_bottle"].rotation_quaternion
    t = np.arctan2(tx, ty)

    current_object = bpy.context.object.name
    pair_image_name = bpy.data.objects[current_object]["image"].name
    img_rgb = np.array(bpy.data.images[pair_image_name].pixels).reshape(bpy.context.scene.configuration.resY, bpy.context.scene.configuration.resX, 4)
    
    for dx, dy, dz, dt in list(itertools.product(dx_list, dy_list, dz_list, dt_list)):
        log_report("INFO", f"On view {pair_image_name} : dx = {dx:.3f}, dy = {dy:.3f}, dz = {dz:.3f}, dt = {dt:.3f}", None)        
        bpy.data.objects["mustard_bottle"].location = [x + dx, y + dy, z + dz]
        t_test = t + dt
        bpy.data.objects["mustard_bottle"].rotation_quaternion = [0, np.sin(t_test), np.cos(t_test), 0]
        
        tmpimgname_render = './tmp/tmp.png'
        bpy.context.scene.render.filepath = tmpimgname_render
        bpy.context.scene.render.image_settings.file_format='PNG' 
        bpy.context.scene.render.image_settings.color_mode ='RGBA'
        bpy.context.scene.render.film_transparent = True
        bpy.context.scene.render.resolution_x = bpy.context.scene.configuration.resX
        bpy.context.scene.render.resolution_y = bpy.context.scene.configuration.resY
        res = bpy.ops.render.render(write_still = True)
        img_render = np.array(Image.open(tmpimgname_render))
        os.system('rm ' + tmpimgname_render)
        foreground_mask = img_render[:, :, 3] == 0
        img_origin = (img_rgb[::-1, :, :3]*255).astype(np.uint8)
        img_segment = img_origin.copy()
        img_segment[foreground_mask, :3] = 0
        img_segment_inverse = img_origin.copy()
        img_segment_inverse[~foreground_mask, :3] = 0
        save_img(img_render[:, :, :3], img_origin, img_segment, img_segment_inverse,pair_image_name + f"dx{dx:.3f}dy{dy:.3f}dz{dz:.3f}dt{dt:.3f}")