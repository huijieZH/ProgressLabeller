#include "orb_extension.h"

using namespace std;

int orb_slam_recon(string ORBvoc_path, string ORB_slam_config, string datasrc, string strAssociationFilename, string recon_path, int image_frequence)
{

    // Retrieve paths to images
    vector<string> vstrImageFilenamesRGB;
    vector<string> vstrImageFilenamesD;
    vector<double> vTimestamps;
    // string strAssociationFilename = string(argv[4]);
    LoadImages(strAssociationFilename, vstrImageFilenamesRGB, vstrImageFilenamesD, vTimestamps);

    // Check consistency in the number of images and depthmaps
    int nImages = vstrImageFilenamesRGB.size();
    if(vstrImageFilenamesRGB.empty())
    {
        cerr << endl << "No images found in provided path." << endl;
        return 1;
    }
    else if(vstrImageFilenamesD.size()!=vstrImageFilenamesRGB.size())
    {
        cerr << endl << "Different number of images for rgb and depth." << endl;
        return 1;
    }

    // Create SLAM system. It initializes all system threads and gets ready to process frames.
    ORB_SLAM2::System SLAM(ORBvoc_path, ORB_slam_config, ORB_SLAM2::System::RGBD, true);

    // Vector for tracking time statistics
    vector<float> vTimesTrack;
    vTimesTrack.resize(nImages);

    cout << endl << "-------" << endl;
    cout << "Start processing sequence ..." << endl;
    cout << "Images in the sequence: " << nImages << endl << endl;

    // Main loop
    cv::Mat imRGB, imD;
    for(int ni=0; ni<nImages; ni++)
    {
        // Read image and depthmap from file
        imRGB = cv::imread(string(datasrc)+"/"+vstrImageFilenamesRGB[ni],CV_LOAD_IMAGE_UNCHANGED);
        imD = cv::imread(string(datasrc)+"/"+vstrImageFilenamesD[ni],CV_LOAD_IMAGE_UNCHANGED);
        double tframe = vTimestamps[ni];

        if(imRGB.empty())
        {
            cerr << endl << "Failed to load image at: "
                 << string(datasrc) << "/" << vstrImageFilenamesRGB[ni] << endl;
            return 1;
        }

// #ifdef COMPILEDWITHC11
//         std::chrono::steady_clock::time_point t1 = std::chrono::steady_clock::now();
// #else
//         std::chrono::monotonic_clock::time_point t1 = std::chrono::monotonic_clock::now();
// #endif
        auto t1 = std::chrono::system_clock::now();

        // Pass the image to the SLAM system
        SLAM.TrackRGBD(imRGB,imD,tframe);

        auto t2 = std::chrono::system_clock::now();

// #ifdef COMPILEDWITHC11
//         std::chrono::steady_clock::time_point t2 = std::chrono::steady_clock::now();
// #else
//         std::chrono::monotonic_clock::time_point t2 = std::chrono::monotonic_clock::now();
// #endif

        double ttrack= std::chrono::duration_cast<std::chrono::duration<double> >(t2 - t1).count();

        vTimesTrack[ni]=ttrack;

        // Wait to load the next frame
        double T=0;
        if(ni<nImages-1)
            T = vTimestamps[ni+1]-tframe;
        else if(ni>0)
            T = tframe-vTimestamps[ni-1];

        if(ttrack<T)
            usleep((T-ttrack)*1e6);
    }

    // Stop all threads
    SLAM.Shutdown();

    // Tracking time statistics
    sort(vTimesTrack.begin(),vTimesTrack.end());
    float totaltime = 0;
    for(int ni=0; ni<nImages; ni++)
    {
        totaltime+=vTimesTrack[ni];
    }
    cout << "-------" << endl << endl;
    cout << "median tracking time: " << vTimesTrack[nImages/2] << endl;
    cout << "mean tracking time: " << totaltime/nImages << endl;

    // Save camera trajectory
    
    // string recon_path = string(argv[5]);
    // SLAM.SaveTrajectoryTUM(recon_path + "/CameraTrajectory.txt");
    // SLAM.SaveKeyFrameTrajectoryTUM(recon_path + "/KeyFrameTrajectory.txt");  
    SLAM.SaveTrajectory_progresslabeler(recon_path + "/campose.txt", vstrImageFilenamesRGB, vTimestamps, image_frequence);
    std::vector<cv::Mat> mapping_points;
    mapping_points = SLAM.GetTrackedMapPoints_progresslabeler();
    savePly(recon_path, mapping_points);
    SLAM.SaveCameraFeature_progresslabeler(recon_path + "/images.txt", vstrImageFilenamesRGB);
    SLAM.SaveFeature3D_progresslabeler(recon_path + "/points3D.txt");
    return 0;
}

void savePly(const string &strreconpath, const std::vector<cv::Mat> points){
    pcl::PointCloud<pcl::PointXYZRGB>::Ptr newcloudPtr(new pcl::PointCloud<pcl::PointXYZRGB>);
    for(auto p:points){
        pcl::PointXYZRGB point;
        point.x = p.at<float>(0);
        point.y = p.at<float>(1);
        point.z = p.at<float>(2);
        std::uint32_t rgb = (static_cast<std::uint32_t>(255) << 16 |
                static_cast<std::uint32_t>(0) << 8 | static_cast<std::uint32_t>(0));
        point.rgb = *reinterpret_cast<float*>(&rgb);
        newcloudPtr->points.push_back(point);        
    }
    pcl::io::savePLYFileBinary(strreconpath + "/fused.ply", *newcloudPtr);
    cout << "successfully save fused.ply" << endl;
}

void LoadImages(const string &strAssociationFilename, vector<string> &vstrImageFilenamesRGB,
                vector<string> &vstrImageFilenamesD, vector<double> &vTimestamps)
{
    ifstream fAssociation;
    fAssociation.open(strAssociationFilename.c_str());
    while(!fAssociation.eof())
    {
        string s;
        getline(fAssociation,s);
        if(!s.empty())
        {
            stringstream ss;
            ss << s;
            double t;
            string sRGB, sD;
            ss >> t;
            vTimestamps.push_back(t);
            ss >> sRGB;
            vstrImageFilenamesRGB.push_back(sRGB);
            ss >> t;
            ss >> sD;
            vstrImageFilenamesD.push_back(sD);

        }
    }
}

PYBIND11_MODULE(orb_extension, m) {
    m.doc() = "orb_extension reconstruction extension to python"; // optional module docstring
    m.def("orb_slam_recon", &orb_slam_recon, "orb_slam reconconstruction");
}