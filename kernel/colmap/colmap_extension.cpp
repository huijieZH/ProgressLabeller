#include <iostream>


#include "colmap/base/database.h"
#include "colmap/base/camera_models.h"
#include "colmap/base/image_reader.h"
#include "colmap/base/reconstruction_manager.h"
#include "colmap/base/reconstruction.h"

#include "colmap/controllers/incremental_mapper.h"

#include "colmap/feature/sift.h"
#include "colmap/feature/extraction.h"
#include "colmap/feature/matching.h"

#include "colmap/util/misc.h"

#include <pybind11/pybind11.h>


void colmap_reconstruction( std::string database_path, std::string image_path, std::string camera_params, std::string output_path){
    colmap::CreateDirIfNotExists(output_path);     
    // create database
    colmap::Database database(database_path);

    // // Feature extraction
    colmap::ImageReaderOptions reader_options;
    reader_options.image_path = image_path;
    reader_options.database_path = database_path;
    reader_options.single_camera = true;
    reader_options.camera_model = "SIMPLE_PINHOLE";
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

PYBIND11_MODULE(colmap_extension, m) {
    m.doc() = "colmap reconstruction extension to python"; // optional module docstring
    m.def("colmap_reconstruction", &colmap_reconstruction, "Reconstruction from colmap");
}