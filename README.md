# ComposeMorph

A modern, robust, and lightweight C++20 library designed to programmatically parse, inspect, modify, and serialize Docker Compose configuration files while preserving custom metadata and schema structures.


---

## Project Description

ComposeMorph simplifies automated orchestration workflows by providing a strongly-typed, intuitive C++ API over Docker Compose specifications. Instead of manually manipulating raw YAML trees, developers can safely query services, update container properties, adjust resource constraints, manage networks and volumes, and safely emit valid Compose YAML files.

---

## Dependencies

The project relies on standard, modern C++ tooling and libraries:
- C++ Compiler: GCC 11+ or Clang 13+ (Must support C++20)
- Build System: CMake (>= 3.16) and Make / Ninja
- YAML Engine: yaml-cpp (>= 0.7.0)
- Testing Framework: GoogleTest (GTest)

Installing Dependencies (Debian / Ubuntu):
sudo apt-get update
sudo apt-get install -y build-essential cmake libyaml-cpp-dev libgtest-dev

---

## Build Instructions

Follow the standard CMake workflow:

git clone [https://github.com/esilasahin/ComposeMorph.git](https://github.com/esilasahin/ComposeMorph.git)
cd ComposeMorph
mkdir -p build && cd build
cmake ..
make -j$(nproc)

---

## Installation

Linking via CMake (Recommended):
add_subdirectory(path/to/ComposeMorph)
target_link_libraries(your_application PRIVATE composemorph)

System-wide Install:
cd build
sudo make install

---

## Basic API Usage

Load and Save Example:

#include <iostream>
#include "compose/ComposeFile.hpp"

int main() {
    compose::ComposeFile compose("docker-compose.yml");

    compose::SaveOptions opts;
    opts.atomic = true;
    opts.backup = true;
    compose.save("docker-compose.updated.yml", opts);

    return 0;
}

---

## Service Modification Example

#include "compose/ComposeFile.hpp"

compose::ComposeFile compose("docker-compose.yml");
auto api = compose.service("api");

api.setImage("python:3.11-slim");
api.setHostname("api-prod");
api.setContainerName("custody_api");
api.setRestart("unless-stopped");
api.setWorkingDir("/app");
api.setUser("1000:1000");
api.setPrivileged(false);
api.set("logging.driver", "json-file");

---

## Environment Example

auto service = compose.service("web");

service.environment().set("DB_PORT", "5432");
service.environment().set("APP_ENV", "production");

if (service.environment().has("DB_PORT")) {
    std::string port = service.environment().get("DB_PORT").value_or("5000");
}

service.environment().remove("TEMP_KEY");

---

## extra_hosts Example

auto service = compose.service("web");

service.extraHosts().set("hsm01", "10.10.10.20");
service.extraHosts().set("db-internal", "192.168.1.100");

if (service.extraHosts().has("hsm01")) {
    std::string ip = service.extraHosts().get("hsm01").value();
}

---

## Volume Example

auto service = compose.service("api");

service.volumes().add("/opt/storage/v1", "/app/data");
service.volumes().add("./logs", "/var/log", "ro");

service.volumes().setSource("/app/data", "/opt/storage/v2");
service.volumes().removeByTarget("/var/log");

---

## Network Example

compose.networks().add("isolated-backend").setExternal(true);

auto service = compose.service("api");
service.networks().add("isolated-backend");

---

## Error Handling

#include "compose/ComposeFile.hpp"
#include "compose/Exceptions.hpp"

try {
    compose::ComposeFile compose("invalid-path.yml");
    auto service = compose.service("non_existent_service");
} catch (const compose::FileNotFoundException& ex) {
    std::cerr << "File error: " << ex.what() << std::endl;
} catch (const compose::ServiceNotFoundException& ex) {
    std::cerr << "Service error: " << ex.what() << std::endl;
} catch (const compose::ValidationException& ex) {
    std::cerr << "Schema error: " << ex.what() << std::endl;
}

---

## Testing

The library includes an automated test suite implemented via GoogleTest and managed through CTest.

cd build
make
ctest --output-on-failure

Verified Test Cases:
- ServiceBasicProperties: Attribute getters, setters, and state persistence.
- EnvironmentAndLabels: Key-value map operations for environment variables and labels.
- VolumesAdvancedOperations: Path bindings, dynamic source mutation, and target deletion.
- TopLevelAndDeployConfigs: Replicas, resource constraints (CPU/Memory), and root networks/volumes.
- GenericPropertiesAndSafeSave: Dynamic dot-notation properties, atomic write, and backup (.bak) creation.
- ExceptionsAndValidation: Exception triggering on invalid service lookups and schema faults.
- RoundTripPreservationAndModification: Preserving unrecognized tags (e.g., x-* custom metadata extensions) during full load/modify/save cycles.

---

## Limitations

- Comment Preservation: Like standard yaml-cpp emitters, structural and inline YAML comments are not preserved during file re-serialization.
- Anchor & Alias Expansion: YAML anchors (&) and aliases (*) are expanded to concrete values upon parsing and may not retain reference aliases when re-emitted.
- Strict Compose V2 Spec: Designed primarily around modern Compose V2 specification standards.