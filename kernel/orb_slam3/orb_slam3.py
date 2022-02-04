if __name__ == "__main__":
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from build.orb3_extension import orb3_slam_recon
    # orb3_slam_recon(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5], float(sys.argv[6]), float(sys.argv[7]))
    orb3_slam_recon(sys.argv[1], "/home/huijie/research/progresslabeller/ORB_SLAM3/Examples/RGB-D/test.yaml", sys.argv[3], sys.argv[4], sys.argv[5], float(sys.argv[6]), float(sys.argv[7]))
