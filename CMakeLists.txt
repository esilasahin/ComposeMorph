cmake_minimum_required(VERSION 3.16)
project(cpp-compose-editor VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Gerekli dış kütüphane
find_package(yaml-cpp REQUIRED)

# Çekirdek kaynak kodlar
set(COMPOSE_SOURCES
    src/ComposeFile.cpp
    src/Service.cpp
    src/Environment.cpp
    src/ExtraHosts.cpp
    src/Ports.cpp
    src/Volumes.cpp
    src/Networks.cpp
    src/BuildConfig.cpp
)

# Statik kütüphane hedefi
add_library(compose-editor STATIC ${COMPOSE_SOURCES})

# Modern target bazlı include ve linkleme
target_include_directories(compose-editor PUBLIC include)
target_link_libraries(compose-editor PUBLIC yaml-cpp)

# Test çalıştırılabilir dosyası
add_executable(run_test tests/MainTest.cpp)
target_link_libraries(run_test PRIVATE compose-editor)