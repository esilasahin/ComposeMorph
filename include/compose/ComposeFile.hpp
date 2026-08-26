#pragma once
#include <yaml-cpp/yaml.h>
#include <string>
#include <vector>
#include "compose/Service.hpp"

namespace compose {

class ComposeFile {
public:
    ComposeFile() = default;
    explicit ComposeFile(const std::string& filePath);

    void load(const std::string& filePath);
    void save(const std::string& outputPath = "");

    Service service(const std::string& name);
    bool hasService(const std::string& name) const;
    Service addService(const std::string& name);
    void removeService(const std::string& name);
    std::vector<std::string> serviceNames() const;

private:
    std::string path_;
    YAML::Node root_;
};

}