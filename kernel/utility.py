import numpy as np
import math
import os

def _transstring2trans(transstring):
    vectorstring = transstring.split(';')[:-1]
    vectorstring = [v.split(',') for v in vectorstring]
    return np.array(vectorstring).astype(np.float32)

def _trans2transstring(trans):
    trans_u1 = trans.astype(dtype='<U8')
    transstring = ''
    for i in range(trans_u1.shape[0]):
        for j in range(trans_u1.shape[1]):
            transstring+=trans_u1[i, j]
            if j == trans_u1.shape[1] - 1:
                transstring+=';'
            else:
                transstring+=','
    return transstring

def _select_sample_files(files, sample_rate):
    ii = 0
    selected_files = []
    while ii < len(files):
        selected_files.append(files[math.floor(ii)])
        ii += 1/sample_rate
    if files[-1] not in selected_files:
        selected_files.append(files[-1])
    return selected_files

def _generate_image_list(path, files):
    f= open(os.path.join(path, "image-list.txt"),"w+")
    for file in files:
        f.write(file + "\n")

def _parse_camfile(camera_rgb_file):
    camera_lines = []
    file = open(camera_rgb_file, "r")
    lines = file.read().split("\n")
    for l in lines:
        data = l.split(" ")
        if data[0].isnumeric():
            camera_lines.append(l)
    return camera_lines
