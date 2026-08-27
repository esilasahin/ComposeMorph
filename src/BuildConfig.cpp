#include "compose/BuildConfig.hpp"

namespace compose {

BuildConfig::BuildConfig(YAML::Node serviceNode) : serviceNode_(serviceNode) {}

void BuildConfig::setContext(const std::string& context) {
    if (!serviceNode_["build"]) {
        serviceNode_["build"] = YAML::Node(YAML::NodeType::Map);
    }
    serviceNode_["build"]["context"] = context;
}

std::string BuildConfig::context() const {
    if (serviceNode_["build"] && serviceNode_["build"]["context"]) {
        return serviceNode_["build"]["context"].as<std::string>();
    }
    return "";
}

void BuildConfig::setDockerfile(const std::string& dockerfile) {
    if (!serviceNode_["build"]) {
        serviceNode_["build"] = YAML::Node(YAML::NodeType::Map);
    }
    serviceNode_["build"]["dockerfile"] = dockerfile;
}

std::string BuildConfig::dockerfile() const {
    if (serviceNode_["build"] && serviceNode_["build"]["dockerfile"]) {
        return serviceNode_["build"]["dockerfile"].as<std::string>();
    }
    return "";
}

void BuildConfig::setTarget(const std::string& target) {
    if (!serviceNode_["build"]) {
        serviceNode_["build"] = YAML::Node(YAML::NodeType::Map);
    }
    serviceNode_["build"]["target"] = target;
}

std::string BuildConfig::target() const {
    if (serviceNode_["build"] && serviceNode_["build"]["target"]) {
        return serviceNode_["build"]["target"].as<std::string>();
    }
    return "";
}

Environment BuildConfig::args() {
    if (!serviceNode_["build"]) {
        serviceNode_["build"] = YAML::Node(YAML::NodeType::Map);
    }
    if (!serviceNode_["build"]["args"]) {
        serviceNode_["build"]["args"] = YAML::Node(YAML::NodeType::Map);
    }
    return Environment(serviceNode_["build"]["args"]);
}

}