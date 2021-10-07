import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from parse import offlineParam


if __name__ == "__main__":
    param = offlineParam("/home/huijie/Desktop/testdataset/configuration.json")
    
    pass