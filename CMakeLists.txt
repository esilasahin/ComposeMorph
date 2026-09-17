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
    src/ScalarQuoting.cpp
)

# Statik kütüphane hedefi
add_library(composemorph STATIC ${COMPOSE_SOURCES})
target_include_directories(composemorph PUBLIC include)
target_link_libraries(composemorph PUBLIC yaml-cpp)

# Geriye dönük uyumluluk: eski hedef adıyla (compose-editor) referans veren
# dış projeler için alias (Milestone 2 sonrası eklenen tüketiciler kırılmasın diye).
add_library(compose-editor ALIAS composemorph)

# Kapsam ölçümü (Madde 25): -DCOMPOSEMORPH_COVERAGE=ON ile gcov verisi üretilir.
option(COMPOSEMORPH_COVERAGE "Enable gcov instrumentation for coverage reports" OFF)
if(COMPOSEMORPH_COVERAGE)
    target_compile_options(composemorph PUBLIC --coverage -O0 -g)
    target_link_options(composemorph PUBLIC --coverage)
endif()

# Testleri etkinleştir
enable_testing()

# Google Test çalıştırılabilir hedefi
file(GLOB COMPOSE_TEST_SOURCES CONFIGURE_DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/tests/*.cpp)
add_executable(unit_tests ${COMPOSE_TEST_SOURCES})
target_link_libraries(unit_tests PRIVATE composemorph GTest::GTest GTest::Main)
# Test verisinin mutlak yolu: testler hangi derleme dizininden çalışırsa çalışsın bulunur.
target_compile_definitions(unit_tests PRIVATE
    TEST_DATA_DIR="${CMAKE_CURRENT_SOURCE_DIR}/test-data")

include(GoogleTest)
gtest_discover_tests(unit_tests)

# Deney 1 (Identity Round-Trip) için benchmark aracı
add_executable(roundtrip_tool benchmarks/roundtrip/roundtrip_tool.cpp)
target_link_libraries(roundtrip_tool PRIVATE composemorph)

# Deney 2 (Targeted Modification / Change Locality) için benchmark aracı
add_executable(modify_tool benchmarks/modification/modify_tool.cpp)
target_link_libraries(modify_tool PRIVATE composemorph)

# Deney 6 (Karşılaştırmalı Benchmark) için çıplak yaml-cpp temel çizgileri.
# Not: composemorph'a değil, doğrudan yaml-cpp'ye bağlanır.
add_executable(yamlcpp_careful_tool benchmarks/comparison/yamlcpp_careful_tool.cpp)
target_link_libraries(yamlcpp_careful_tool PRIVATE yaml-cpp)

add_executable(yamlcpp_naive_tool benchmarks/comparison/yamlcpp_naive_tool.cpp)
target_link_libraries(yamlcpp_naive_tool PRIVATE yaml-cpp)

# Deney 7 (Performance Benchmark) için ölçüm aracı
add_executable(perf_tool benchmarks/performance/perf_tool.cpp)
target_link_libraries(perf_tool PRIVATE composemorph)
# Serializer-only overhead measurement needs the library's internal header.
target_include_directories(perf_tool PRIVATE src)
# Görev tanımı Madde 26: örnek kullanım programları
file(GLOB COMPOSE_EXAMPLES CONFIGURE_DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/examples/*.cpp)
foreach(example_file ${COMPOSE_EXAMPLES})
    get_filename_component(example_name ${example_file} NAME_WE)
    add_executable(${example_name} ${example_file})
    target_link_libraries(${example_name} PRIVATE composemorph)
endforeach()
