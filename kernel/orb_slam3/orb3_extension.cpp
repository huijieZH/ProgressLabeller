#include "orb3_extension.h"

using namespace std;

int orb3_slam_recon(string ORBvoc_path, string ORB_slam_config, string datasrc, string strAssociationFilename, string recon_path, float image_frequence, float display, int sensor_mode)
{
    // Retrieve paths to images
    vector<string> vstrImageFilenamesRGB;
    vector<string> vstrImageFilenamesAux;
    vector<double> vTimestamps;

    if (sensor_mode == 0) {
        LoadImagesMonocular(strAssociationFilename, vstrImageFilenamesRGB, vTimestamps);
    } else {
        LoadImagesPaired(strAssociationFilename, vstrImageFilenamesRGB, vstrImageFilenamesAux, vTimestamps);
    }

    int nImages = vstrImageFilenamesRGB.size();
    if(vstrImageFilenamesRGB.empty())
    {
        cerr << endl << "No images found in provided path." << endl;
        return 1;
    }
    if(sensor_mode != 0 && vstrImageFilenamesAux.size() != vstrImageFilenamesRGB.size())
    {
        cerr << endl << "Different number of images for primary and auxiliary streams." << endl;
        return 1;
    }

    // Create SLAM system. It initializes all system threads and gets ready to process frames.
    bool DISPALY = (display == 1);

    ORB_SLAM3::System::eSensor sensor;
    if (sensor_mode == 0) {
        sensor = ORB_SLAM3::System::MONOCULAR;
    } else if (sensor_mode == 2) {
        sensor = ORB_SLAM3::System::STEREO;
    } else {
        sensor = ORB_SLAM3::System::RGBD;
    }
    ORB_SLAM3::System SLAM(ORBvoc_path, ORB_slam_config, sensor, DISPALY);

    // Vector for tracking time statistics
    vector<float> vTimesTrack;
    vTimesTrack.resize(nImages);

    cout << endl << "-------" << endl;
    cout << "Start processing sequence ..." << endl;
    cout << "Images in the sequence: " << nImages << endl << endl;

    // Main loop
    cv::Mat imRGB, imAux;
    for(int ni=0; ni<nImages; ni++)
    {
        imRGB = cv::imread(string(datasrc)+"/"+vstrImageFilenamesRGB[ni], CV_LOAD_IMAGE_UNCHANGED);
        if(sensor_mode != 0) {
            imAux = cv::imread(string(datasrc)+"/"+vstrImageFilenamesAux[ni], CV_LOAD_IMAGE_UNCHANGED);
        }
        double tframe = vTimestamps[ni];

        if(imRGB.empty())
        {
            cerr << endl << "Failed to load image at: "
                 << string(datasrc) << "/" << vstrImageFilenamesRGB[ni] << endl;
            return 1;
        }
        auto t1 = std::chrono::system_clock::now();

        cout << "Tracking " << vstrImageFilenamesRGB[ni] << " frame\n" << endl;
        if (sensor_mode == 0) {
            SLAM.TrackMonocular(imRGB, tframe);
        } else if (sensor_mode == 2) {
            SLAM.TrackStereo(imRGB, imAux, tframe);
        } else {
            SLAM.TrackRGBD(imRGB, imAux, tframe);
        }

        auto t2 = std::chrono::system_clock::now();

        double ttrack= std::chrono::duration_cast<std::chrono::duration<double> >(t2 - t1).count();

        vTimesTrack[ni]=ttrack;

        double T=0;
        if(ni<nImages-1)
            T = vTimestamps[ni+1]-tframe;
        else if(ni>0)
            T = tframe-vTimestamps[ni-1];

        if(ttrack<T)
            usleep((T-ttrack)*1e6);
    }

    SLAM.Shutdown();

    sort(vTimesTrack.begin(),vTimesTrack.end());
    float totaltime = 0;
    for(int ni=0; ni<nImages; ni++)
    {
        totaltime+=vTimesTrack[ni];
    }
    cout << "-------" << endl << endl;
    cout << "median tracking time: " << vTimesTrack[nImages/2] << endl;
    cout << "mean tracking time: " << totaltime/nImages << endl;

    SLAM.SaveTrajectory_progresslabeler(recon_path + "/campose.txt", vstrImageFilenamesRGB, vTimestamps, image_frequence);
    vector<Eigen::Vector3f> mapping_points;
    mapping_points = SLAM.GetTrackedMapPoints_progresslabeler();
    savePly(recon_path, mapping_points);
    return 0;
}

void savePly(const string &path, const vector<Eigen::Vector3f> points) {
    ofstream f(path + "/fused.ply");
    f << "ply\n"
        << "format ascii 1.0\n"
        << "element vertex " << points.size() << "\n"
        << "property float x\n"
        << "property float y\n"
        << "property float z\n"
        << "end_header\n";
    for (auto p : points)
    {
        f << p(0) << " " << p(1) << " " << p(2) << "\n";
    }
    f.close();
}

void LoadImagesMonocular(const string &strAssociationFilename, vector<string> &vstrImageFilenamesRGB,
                         vector<double> &vTimestamps)
{
    ifstream fAssociation;
    fAssociation.open(strAssociationFilename.c_str());
    while(!fAssociation.eof())
    {
        string s;
        getline(fAssociation,s);
        if(!s.empty())
        {
            stringstream ss(s);
            double t;
            string sRGB;
            ss >> t;
            ss >> sRGB;
            if(sRGB.empty())
                continue;
            vTimestamps.push_back(t);
            vstrImageFilenamesRGB.push_back(sRGB);
        }
    }
}

void LoadImagesPaired(const string &strAssociationFilename, vector<string> &vstrImageFilenamesRGB,
                     vector<string> &vstrImageFilenamesAux, vector<double> &vTimestamps)
{
    ifstream fAssociation;
    fAssociation.open(strAssociationFilename.c_str());
    while(!fAssociation.eof())
    {
        string s;
        getline(fAssociation,s);
        if(!s.empty())
        {
            stringstream ss(s);
            double t;
            string sRGB, sAux;
            ss >> t;
            vTimestamps.push_back(t);
            ss >> sRGB;
            vstrImageFilenamesRGB.push_back(sRGB);
            ss >> t;
            ss >> sAux;
            vstrImageFilenamesAux.push_back(sAux);
        }
    }
}

PYBIND11_MODULE(orb3_extension, m) {
    m.doc() = "orb3_extension reconstruction extension to python"; // optional module docstring
    m.def("orb3_slam_recon", &orb3_slam_recon, "orb3_slam reconconstruction");
}
