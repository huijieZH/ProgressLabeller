import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from parse import offlineParam
from render import offlineRender
from offlineRecon import offlineRecon


if __name__ == "__main__":
    param = offlineParam("/home/huijie/Desktop/newtestdata/configuration.json")
    offlineRecon(param)
    offlineRender(param, "output")