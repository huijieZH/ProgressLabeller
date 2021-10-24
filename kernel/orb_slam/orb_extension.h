#include<iostream>
#include<algorithm>
#include<fstream>
#include<chrono>
#include <unistd.h>

#include<opencv2/core/core.hpp>
#include<opencv2/imgcodecs/legacy/constants_c.h>

#include<System.h>
#include<MapPoint.h>

#include <pybind11/pybind11.h>

int orb_slam_recon(string ORBvoc_path, string ORB_slam_config, string datasrc, string strAssociationFilename, string recon_path, float image_frequence);

void LoadImages(const string &strAssociationFilename, vector<string> &vstrImageFilenamesRGB,
                vector<string> &vstrImageFilenamesD, vector<double> &vTimestamps);

void savePly(const string &path, const std::vector<cv::Mat> points);