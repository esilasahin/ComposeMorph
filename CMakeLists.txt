cmake_minimum_required(VERSION 3.16)
project(ComposeMorph VERSION 1.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

# Gerekli dış kütüphaneler
find_package(yaml-cpp REQUIRED)
find_package(GTest REQUIRED)

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
    src/HealthCheck.cpp
    src/DependsOn.cpp
    src/DeployConfig.cpp
    src/TopLevelCollections.cpp
)

# Statik kütüphane hedefi
add_library(composemorph STATIC ${COMPOSE_SOURCES})
target_include_directories(composemorph PUBLIC include)
target_link_libraries(composemorph PUBLIC yaml-cpp)

# Geriye dönük uyumluluk: eski hedef adıyla (compose-editor) referans veren
# dış projeler için alias (Milestone 2 sonrası eklenen tüketiciler kırılmasın diye).
add_library(compose-editor ALIAS composemorph)

# Testleri etkinleştir
enable_testing()

# Google Test çalıştırılabilir hedefi
add_executable(unit_tests tests/UnitTests.cpp)
target_link_libraries(unit_tests PRIVATE composemorph GTest::GTest GTest::Main)

include(GoogleTest)
gtest_discover_tests(unit_tests)