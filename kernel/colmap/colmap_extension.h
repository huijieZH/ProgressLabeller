#include <iostream>
#include <fstream>
#include <string>
#include <sstream>
#include <exception>
#include <algorithm>

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

void colmap_reconstruction( std::string database_path, std::string image_path, std::string image_list_path, std::string camera_params, std::string output_path);


void parseReconstruction(std::string output_path);


bool _is_number(const std::string& s);

bool _start_with_int(const std::string& text);

void _camfile_transform(const std::string& infile, const std::string& outfile);