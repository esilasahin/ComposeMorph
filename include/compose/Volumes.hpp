#pragma once
#include <yaml-cpp/yaml.h>
#include <string>
#include <vector>

namespace compose {

class Volumes {
public:
    explicit Volumes(YAML::Node serviceNode);

    void add(const std::string& volumeMapping);
    void remove(const std::string& volumeMapping);
    bool has(const std::string& volumeMapping) const;
    void clear();

    std::vector<std::string> toVector() const;

private:
    YAML::Node serviceNode_;
};

}