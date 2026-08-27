#pragma once
#include <yaml-cpp/yaml.h>
#include <string>
#include "compose/Environment.hpp"

namespace compose {

class BuildConfig {
public:
    explicit BuildConfig(YAML::Node serviceNode);

    void setContext(const std::string& context);
    std::string context() const;

    void setDockerfile(const std::string& dockerfile);
    std::string dockerfile() const;

    void setTarget(const std::string& target);
    std::string target() const;

    Environment args();

private:
    YAML::Node serviceNode_;
};

}