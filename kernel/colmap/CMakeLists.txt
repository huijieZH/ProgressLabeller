cmake_minimum_required(VERSION 2.8.11)

project(colmap_extension)

find_package(COLMAP REQUIRED)
set(PYBIND11_PYTHON_VERSION 3.7)
set(pybind11_DIR "/home/cxt/Documents/softwares/blender-2.92.0-linux64/2.92/python/lib/python3.7/site-packages/pybind11/share/cmake/pybind11")
find_package(pybind11 REQUIRED)

include_directories(${COLMAP_INCLUDE_DIRS} ${CMAKE_CURRENT_SOURCE_DIR})
link_directories(${COLMAP_LINK_DIRS})

set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

pybind11_add_module(colmap_extension colmap_extension.cpp)
target_link_libraries(colmap_extension ${COLMAP_LIBRARIES})
