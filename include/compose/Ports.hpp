#pragma once
#include <yaml-cpp/yaml.h>
#include <string>
#include <vector>

namespace compose {

class Ports {
public:
    explicit Ports(YAML::Node serviceNode);

    void add(const std::string& portMapping);
    void remove(const std::string& portMapping);
    bool has(const std::string& portMapping) const;
    void clear();

    std::vector<std::string> toVector() const;

private:
    YAML::Node serviceNode_;
};

}