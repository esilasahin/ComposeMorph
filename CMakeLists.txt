cmake_minimum_required(VERSION 3.16)
project(cpp-compose-editor VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(yaml-cpp REQUIRED)

include_directories(include)

set(COMPOSE_SOURCES
    src/ComposeFile.cpp
    src/Service.cpp
)

add_library(compose-editor STATIC ${COMPOSE_SOURCES})
target_link_libraries(compose-editor PUBLIC yaml-cpp)

add_executable(run_test tests/MainTest.cpp)
target_link_libraries(run_test PRIVATE compose-editor)