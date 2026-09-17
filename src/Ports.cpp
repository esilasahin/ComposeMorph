#include "compose/Ports.hpp"
#include "compose/Exceptions.hpp"
#include "ScalarQuoting.hpp"

namespace compose {
namespace {

// Compose ports girdisi kısa ("8080:80") ya da uzun sözdizimli olabilir:
//   - target: 80
//     published: "8080"
//     protocol: tcp
// Her iki biçimi de tek bir kısa sözdizimi dizgisine indirger; böylece
// karşılaştırma ve listeleme biçimden bağımsız çalışır.
std::string portToString(const YAML::Node& entry) {
    if (entry.IsScalar()) {
        return entry.as<std::string>();
    }
    if (!entry.IsMap() || !entry["target"] || !entry["target"].IsScalar()) {
        return {};
    }

    std::string text;
    if (entry["host_ip"] && entry["host_ip"].IsScalar()) {
        text += entry["host_ip"].as<std::string>() + ":";
    }
    if (entry["published"] && entry["published"].IsScalar()) {
        text += entry["published"].as<std::string>() + ":";
    }
    text += entry["target"].as<std::string>();
    if (entry["protocol"] && entry["protocol"].IsScalar()) {
        text += "/" + entry["protocol"].as<std::string>();
    }
    return text;
}

}  // namespace

Ports::Ports(YAML::Node serviceNode) : serviceNode_(serviceNode) {}

void Ports::add(const std::string& portMapping) {
    if (!serviceNode_["ports"]) {
        serviceNode_["ports"] = YAML::Node(YAML::NodeType::Sequence);
    } else if (!serviceNode_["ports"].IsSequence()) {
        throw InvalidPropertyException("'ports' must be a sequence.");
    }

    if (!has(portMapping)) {
        serviceNode_["ports"].push_back(detail::makeString(portMapping));
    }
}

void Ports::remove(const std::string& portMapping) {
    if (!serviceNode_["ports"] || !serviceNode_["ports"].IsSequence()) {
        return;
    }

    YAML::Node newPorts(YAML::NodeType::Sequence);
    for (std::size_t i = 0; i < serviceNode_["ports"].size(); ++i) {
        if (portToString(serviceNode_["ports"][i]) != portMapping) {
            newPorts.push_back(serviceNode_["ports"][i]);
        }
    }
    serviceNode_["ports"] = newPorts;
}

bool Ports::has(const std::string& portMapping) const {
    if (!serviceNode_["ports"] || !serviceNode_["ports"].IsSequence()) {
        return false;
    }

    for (std::size_t i = 0; i < serviceNode_["ports"].size(); ++i) {
        if (portToString(serviceNode_["ports"][i]) == portMapping) {
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
            std::string text = portToString(serviceNode_["ports"][i]);
            if (!text.empty()) {
                result.push_back(text);
            }
        }
    }
    return result;
}

}
