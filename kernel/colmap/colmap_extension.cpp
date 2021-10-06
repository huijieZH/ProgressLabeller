#include <colmap_extension.h>


void colmap_reconstruction( std::string database_path, std::string image_path, std::string camera_params, std::string output_path){
    colmap::CreateDirIfNotExists(output_path);     
    // create database
    colmap::Database database(database_path);

    // // Feature extraction
    colmap::ImageReaderOptions reader_options;
    reader_options.image_path = image_path;
    reader_options.database_path = database_path;
    reader_options.single_camera = true;
    reader_options.camera_model = "PINHOLE";
    reader_options.camera_params = camera_params;
    reader_options.default_focal_length_factor = 1.0;

    colmap::SiftExtractionOptions sift_extraction;

    colmap::SiftFeatureExtractor feature_extractor(reader_options, sift_extraction);

    feature_extractor.Start();
    feature_extractor.Wait();

    // Feature matching
    colmap::SiftMatchingOptions sift_matching;
    colmap::SequentialMatchingOptions sequential_matching;
    colmap::SequentialFeatureMatcher feature_matcher(sequential_matching,
                                                     sift_matching,
                                                     database_path);
    feature_matcher.Start();
    feature_matcher.Wait();   

    // Reconstruction
    colmap::ReconstructionManager reconstruction_manager;

    colmap::IncrementalMapperOptions mapper_options;
    mapper_options.ba_refine_focal_length = false;
    mapper_options.ba_refine_extra_params = false;

    colmap::IncrementalMapperController mapper(&mapper_options, 
                                               image_path,
                                               database_path,
                                               &reconstruction_manager);   

    size_t prev_num_reconstructions = 0;
    mapper.AddCallback(
        colmap::IncrementalMapperController::LAST_IMAGE_REG_CALLBACK, [&]() {
        // If the number of reconstructions has not changed, the last model
        // was discarded for some reason.
        if (reconstruction_manager.Size() > prev_num_reconstructions) {
            const std::string reconstruction_path = colmap::JoinPaths(
                output_path, std::to_string(prev_num_reconstructions));
            const auto& reconstruction =
                reconstruction_manager.Get(prev_num_reconstructions);
            colmap::CreateDirIfNotExists(reconstruction_path);
            reconstruction.Write(reconstruction_path);
            prev_num_reconstructions = reconstruction_manager.Size();
        }
        });

    mapper.Start();
    mapper.Wait();
}

void parseReconstruction(std::string output_path){
    colmap::Reconstruction reconstruction;
    reconstruction.Read(colmap::JoinPaths(output_path, "0"));
    reconstruction.ExportPLY(colmap::JoinPaths(output_path, "fused.ply"));
    reconstruction.WriteText(output_path);
    _camfile_transform(colmap::JoinPaths(output_path, "images.txt"), colmap::JoinPaths(output_path, "campose.txt"));
}


bool _is_number(const std::string& s)
{
    return !s.empty() && std::find_if(s.begin(), 
        s.end(), [](unsigned char c) { return !std::isdigit(c); }) == s.end();
}

bool _start_with_int(const std::string& text){
    std::string first_word = "";
    for (int index = 0; index < text.length(); index ++){
        if (text[index] != ' '){
            first_word.push_back(text[index]);
        } else{
            break;
        }
    }
    return _is_number(first_word);
}

bool _end_with_png(const std::string& text){
    bool state = text.substr(text.length()- 4) == ".png";
    return state;
}

void _camfile_transform(const std::string& ifile, const std::string& outfile){
    std::string line;
    std::ifstream infile(ifile);
    std::ofstream out(outfile);

    out << "# IMAGE_ID, QW, QX, QY, QZ, TX, TY, TZ, CAMERA_ID, NAME" << std::endl;
    out << " " << std::endl;
    
    while (std::getline(infile, line))
    {
        std::istringstream iss(line);
        if(_start_with_int(line) && _end_with_png(line)){
            out << line << std::endl;
        }
    }
}

PYBIND11_MODULE(colmap_extension, m) {
    m.doc() = "colmap reconstruction extension to python"; // optional module docstring
    m.def("colmap_reconstruction", &colmap_reconstruction, "Reconstruction from colmap");
    m.def("parseReconstruction", &parseReconstruction, "parse reconstruction result");
}