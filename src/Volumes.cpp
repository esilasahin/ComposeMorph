#include "compose/Volumes.hpp"

namespace compose {

Volumes::Volumes(YAML::Node serviceNode) : serviceNode_(serviceNode) {}

void Volumes::add(const std::string& volumeMapping) {
    if (!serviceNode_["volumes"]) {
        serviceNode_["volumes"] = YAML::Node(YAML::NodeType::Sequence);
    }

    if (!has(volumeMapping)) {
        serviceNode_["volumes"].push_back(volumeMapping);
    }
}

void Volumes::remove(const std::string& volumeMapping) {
    if (!serviceNode_["volumes"] || !serviceNode_["volumes"].IsSequence()) {
        return;
    }

    YAML::Node newVolumes(YAML::NodeType::Sequence);
    for (std::size_t i = 0; i < serviceNode_["volumes"].size(); ++i) {
        std::string current = serviceNode_["volumes"][i].as<std::string>();
        if (current != volumeMapping) {
            newVolumes.push_back(current);
        }
    }
    serviceNode_["volumes"] = newVolumes;
}

bool Volumes::has(const std::string& volumeMapping) const {
    if (!serviceNode_["volumes"] || !serviceNode_["volumes"].IsSequence()) {
        return false;
    }

    for (std::size_t i = 0; i < serviceNode_["volumes"].size(); ++i) {
        if (serviceNode_["volumes"][i].as<std::string>() == volumeMapping) {
            return true;
        }
    }
    return false;
}

void Volumes::clear() {
    if (serviceNode_["volumes"]) {
        serviceNode_.remove("volumes");
    }
}

std::vector<std::string> Volumes::toVector() const {
    std::vector<std::string> result;
    if (serviceNode_["volumes"] && serviceNode_["volumes"].IsSequence()) {
        for (std::size_t i = 0; i < serviceNode_["volumes"].size(); ++i) {
            result.push_back(serviceNode_["volumes"][i].as<std::string>());
        }
    }
    return result;
}

}