#pragma once
#include <yaml-cpp/yaml.h>
#include <string>
#include <vector>

namespace compose {

class Networks {
public:
    explicit Networks(YAML::Node serviceNode);

    void add(const std::string& networkName);
    void remove(const std::string& networkName);
    bool has(const std::string& networkName) const;
    void clear();

    std::vector<std::string> toVector() const;

private:
    YAML::Node serviceNode_;
};

}