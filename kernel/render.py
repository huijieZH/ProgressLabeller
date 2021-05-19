import bpy
import numpy
from PIL import Image
import os

def save_img(img_render, img_origin, img_segment,  name):
    renderim = Image.fromarray(img_render)
    renderim.save(os.path.join("tmp", name + "_render.png"))
    originim = Image.fromarray(img_origin)
    originim.save(os.path.join("tmp", name + "_origin.png"))
    segmentim = Image.fromarray(img_segment)
    segmentim.save(os.path.join("tmp", name + "_segment.png"))