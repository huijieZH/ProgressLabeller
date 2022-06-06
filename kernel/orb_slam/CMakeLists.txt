cmake_minimum_required(VERSION 2.8.11)

project(orb_extension)

set(PYBIND11_PYTHON_VERSION 3.7)
set(pybind11_DIR "$ENV{PROGRESSLABELLER_BLENDER_PATH}/2.92/python/lib/python3.7/site-packages/pybind11/share/cmake/pybind11")
find_package(pybind11 REQUIRED)
find_package(OpenCV 4 QUIET)
find_package(Eigen3 3.1.0 REQUIRED)
find_package(Pangolin REQUIRED)

set(ORB_INCLUDE_DIRS "$ENV{ORB_SOURCE_DIR}/include")
set(ORB_LIBRARIES "$ENV{ORB_SOURCE_DIR}/lib")

include_directories(
${ORB_INCLUDE_DIRS} 
$ENV{ORB_SOURCE_DIR}
${EIGEN3_INCLUDE_DIR}
${Pangolin_INCLUDE_DIRS}
${CMAKE_CURRENT_SOURCE_DIR}
)

set(CMAKE_CXX_STANDARD 11)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

pybind11_add_module(orb_extension orb_extension.cpp)

target_link_libraries(
orb_extension 
${ORB_LIBRARIES}/libORB_SLAM2.so
${OpenCV_LIBS}
${EIGEN3_LIBS}
${Pangolin_LIBRARIES}
$ENV{ORB_SOURCE_DIR}/Thirdparty/DBoW2/lib/libDBoW2.so
$ENV{ORB_SOURCE_DIR}/Thirdparty/g2o/lib/libg2o.so
)
