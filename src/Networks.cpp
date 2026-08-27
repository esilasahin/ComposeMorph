#include "compose/Networks.hpp"

namespace compose {

Networks::Networks(YAML::Node serviceNode) : serviceNode_(serviceNode) {}

void Networks::add(const std::string& networkName) {
    if (!serviceNode_["networks"]) {
        serviceNode_["networks"] = YAML::Node(YAML::NodeType::Sequence);
    }

    if (!has(networkName)) {
        serviceNode_["networks"].push_back(networkName);
    }
}

void Networks::remove(const std::string& networkName) {
    if (!serviceNode_["networks"] || !serviceNode_["networks"].IsSequence()) {
        return;
    }

    YAML::Node newNetworks(YAML::NodeType::Sequence);
    for (std::size_t i = 0; i < serviceNode_["networks"].size(); ++i) {
        std::string current = serviceNode_["networks"][i].as<std::string>();
        if (current != networkName) {
            newNetworks.push_back(current);
        }
    }
    serviceNode_["networks"] = newNetworks;
}

bool Networks::has(const std::string& networkName) const {
    if (!serviceNode_["networks"] || !serviceNode_["networks"].IsSequence()) {
        return false;
    }

    for (std::size_t i = 0; i < serviceNode_["networks"].size(); ++i) {
        if (serviceNode_["networks"][i].as<std::string>() == networkName) {
            return true;
        }
    }
    return false;
}

void Networks::clear() {
    if (serviceNode_["networks"]) {
        serviceNode_.remove("networks");
    }
}

std::vector<std::string> Networks::toVector() const {
    std::vector<std::string> result;
    if (serviceNode_["networks"] && serviceNode_["networks"].IsSequence()) {
        for (std::size_t i = 0; i < serviceNode_["networks"].size(); ++i) {
            result.push_back(serviceNode_["networks"][i].as<std::string>());
        }
    }
    return result;
}

}