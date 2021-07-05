cmake_minimum_required(VERSION 2.8.11)

project(colmap_extension)

find_package(COLMAP REQUIRED)
find_package(pybind11 REQUIRED)

# set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -std=c++14")

include_directories(${COLMAP_INCLUDE_DIRS})
link_directories(${COLMAP_LINK_DIRS})

set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

pybind11_add_module(colmap_extension colmap_extension.cpp)
target_link_libraries(colmap_extension ${COLMAP_LIBRARIES})