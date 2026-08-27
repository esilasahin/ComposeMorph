#include "compose/DeployConfig.hpp"

namespace compose {

// ResourceSpecs Implementation
ResourceSpecs::ResourceSpecs(YAML::Node node) : node_(node) {}

void ResourceSpecs::setCpus(const std::string& cpus) {
    node_["cpus"] = cpus;
}

std::string ResourceSpecs::cpus() const {
    return node_["cpus"] ? node_["cpus"].as<std::string>() : "";
}

void ResourceSpecs::setMemory(const std::string& memory) {
    node_["memory"] = memory;
}

std::string ResourceSpecs::memory() const {
    return node_["memory"] ? node_["memory"].as<std::string>() : "";
}

// Resources Implementation
Resources::Resources(YAML::Node deployNode) : deployNode_(deployNode) {}

ResourceSpecs Resources::limits() {
    if (!deployNode_["resources"]) {
        deployNode_["resources"] = YAML::Node(YAML::NodeType::Map);
    }
    if (!deployNode_["resources"]["limits"]) {
        deployNode_["resources"]["limits"] = YAML::Node(YAML::NodeType::Map);
    }
    return ResourceSpecs(deployNode_["resources"]["limits"]);
}

ResourceSpecs Resources::reservations() {
    if (!deployNode_["resources"]) {
        deployNode_["resources"] = YAML::Node(YAML::NodeType::Map);
    }
    if (!deployNode_["resources"]["reservations"]) {
        deployNode_["resources"]["reservations"] = YAML::Node(YAML::NodeType::Map);
    }
    return ResourceSpecs(deployNode_["resources"]["reservations"]);
}

// DeployConfig Implementation
DeployConfig::DeployConfig(YAML::Node serviceNode) : serviceNode_(serviceNode) {}

void DeployConfig::setReplicas(int count) {
    if (!serviceNode_["deploy"]) {
        serviceNode_["deploy"] = YAML::Node(YAML::NodeType::Map);
    }
    serviceNode_["deploy"]["replicas"] = count;
}

int DeployConfig::replicas() const {
    if (serviceNode_["deploy"] && serviceNode_["deploy"]["replicas"]) {
        return serviceNode_["deploy"]["replicas"].as<int>();
    }
    return 0;
}

void DeployConfig::setMode(const std::string& mode) {
    if (!serviceNode_["deploy"]) {
        serviceNode_["deploy"] = YAML::Node(YAML::NodeType::Map);
    }
    serviceNode_["deploy"]["mode"] = mode;
}

std::string DeployConfig::mode() const {
    if (serviceNode_["deploy"] && serviceNode_["deploy"]["mode"]) {
        return serviceNode_["deploy"]["mode"].as<std::string>();
    }
    return "";
}

Resources DeployConfig::resources() {
    if (!serviceNode_["deploy"]) {
        serviceNode_["deploy"] = YAML::Node(YAML::NodeType::Map);
    }
    return Resources(serviceNode_["deploy"]);
}

}