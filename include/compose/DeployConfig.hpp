#pragma once
#include <yaml-cpp/yaml.h>
#include <string>

namespace compose {

class ResourceSpecs {
public:
    explicit ResourceSpecs(YAML::Node node);

    void setCpus(const std::string& cpus);
    std::string cpus() const;

    void setMemory(const std::string& memory);
    std::string memory() const;

private:
    YAML::Node node_;
};

class Resources {
public:
    explicit Resources(YAML::Node deployNode);

    ResourceSpecs limits();
    ResourceSpecs reservations();

private:
    YAML::Node deployNode_;
};

class DeployConfig {
public:
    explicit DeployConfig(YAML::Node serviceNode);

    void setReplicas(int count);
    int replicas() const;

    void setMode(const std::string& mode);
    std::string mode() const;

    Resources resources();

private:
    YAML::Node serviceNode_;
};

}