#include "compose/Ports.hpp"

namespace compose {

Ports::Ports(YAML::Node serviceNode) : serviceNode_(serviceNode) {}

void Ports::add(const std::string& portMapping) {
    if (!serviceNode_["ports"]) {
        serviceNode_["ports"] = YAML::Node(YAML::NodeType::Sequence);
    }

    if (!has(portMapping)) {
        serviceNode_["ports"].push_back(portMapping);
    }
}

void Ports::remove(const std::string& portMapping) {
    if (!serviceNode_["ports"] || !serviceNode_["ports"].IsSequence()) {
        return;
    }

    YAML::Node newPorts(YAML::NodeType::Sequence);
    for (std::size_t i = 0; i < serviceNode_["ports"].size(); ++i) {
        std::string current = serviceNode_["ports"][i].as<std::string>();
        if (current != portMapping) {
            newPorts.push_back(current);
        }
    }
    serviceNode_["ports"] = newPorts;
}

bool Ports::has(const std::string& portMapping) const {
    if (!serviceNode_["ports"] || !serviceNode_["ports"].IsSequence()) {
        return false;
    }

    for (std::size_t i = 0; i < serviceNode_["ports"].size(); ++i) {
        if (serviceNode_["ports"][i].as<std::string>() == portMapping) {
            return true;
        }
    }
    return false;
}

void Ports::clear() {
    if (serviceNode_["ports"]) {
        serviceNode_.remove("ports");
    }
}

std::vector<std::string> Ports::toVector() const {
    std::vector<std::string> result;
    if (serviceNode_["ports"] && serviceNode_["ports"].IsSequence()) {
        for (std::size_t i = 0; i < serviceNode_["ports"].size(); ++i) {
            result.push_back(serviceNode_["ports"][i].as<std::string>());
        }
    }
    return result;
}

}