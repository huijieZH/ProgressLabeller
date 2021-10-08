import os
import sys
import time

def split_obj(filepath):
    with open(filepath) as f:
        lines = f.readlines()
    obj_files = []
    o_index_list = [] 
    index_l = 0
    while index_l < len(lines):
        l = lines[index_l]
        if l[:2] == "o ":
            o_index_list.append(index_l)
        index_l += 1

    o_index = 1
    while o_index < len(o_index_list):
        obj_files.append(lines[o_index_list[o_index - 1]:o_index_list[o_index]])
        o_index += 1

    obj_files.append(lines[o_index_list[-1]:])    
    obj_start = lines[:o_index_list[0]]
    total_v = 0
    total_from_last = 0
    for file in obj_files:
        file_name = file[0][2:-1] + ".obj"
        f = open(os.path.join(os.path.dirname(filepath), file_name), "w")
        all_file = obj_start+file
        for l in all_file:

            if l[:2] == "v ":
                total_v += 1
                l_new = l
            elif l[:2] == "f ":
                point_pairs = l.split(" ")[1:]
                l_new = "f "
                for point_p in point_pairs:
                    if "//" in point_p:
                        p_num_pair = point_p.split("//")
                        for p_num in p_num_pair:
                            l_new += str(int(p_num) - total_from_last)
                            l_new += "//"
                        l_new = l_new[:-2]
                        l_new += " "
                    elif "/" in point_p:
                        p_num_pair = point_p.split("/")
                        for p_num in p_num_pair:
                            l_new += str(int(p_num) - total_from_last)
                            l_new += "/"
                        l_new = l_new[:-2]
                        l_new += " "                            

                l_new = l_new[:-1]
                l_new += "\n" 
            else:
                l_new = l
            f.write(l_new)
        print("Successfully split {0}".format(file_name))
        f.close()
        total_from_last = total_v

if __name__ == "__main__":
    # print("Starting split .obj file in directory {0}\n".format(sys.argv[1]))
    # package = os.listdir(sys.argv[1])
    # package.sort()
    # for p in package:
    #     print("Starting split .obj file for {0}\n".format(p))
    #     path = os.path.join(sys.argv[1], p, "split")
    #     files = os.listdir(path)
    #     for f in files:
    #         if f[-4:] == ".obj":
    #             split_obj(os.path.join(sys.argv[1], p, "split", f))
    split_obj("/home/huijie/research/ACF/data/models_w_parts/ACFmodel/blue_mug/split/blue_mug_split.obj")
