#include "compose/Service.hpp"

namespace compose {

Service::Service(YAML::Node node) : node_(node) {}

void Service::setImage(const std::string& img) {
    node_["image"] = img;
}

std::string Service::image() const {
    return node_["image"] ? node_["image"].as<std::string>() : "";
}

void Service::setHostname(const std::string& host) {
    node_["hostname"] = host;
}

std::string Service::hostname() const {
    return node_["hostname"] ? node_["hostname"].as<std::string>() : "";
}

void Service::removeHostname() {
    node_.remove("hostname");
}

void Service::setContainerName(const std::string& name) {
    node_["container_name"] = name;
}

std::string Service::containerName() const {
    return node_["container_name"] ? node_["container_name"].as<std::string>() : "";
}

void Service::removeContainerName() {
    node_.remove("container_name");
}

void Service::setRestart(const std::string& restartPolicy) {
    node_["restart"] = restartPolicy;
}

std::string Service::restart() const {
    return node_["restart"] ? node_["restart"].as<std::string>() : "";
}

void Service::removeRestart() {
    node_.remove("restart");
}

void Service::setPrivileged(bool priv) {
    node_["privileged"] = priv;
}

bool Service::privileged() const {
    return node_["privileged"] ? node_["privileged"].as<bool>() : false;
}

Environment Service::environment() {
    if (!node_["environment"]) {
        node_["environment"] = YAML::Node(YAML::NodeType::Map);
    }
    return Environment(node_["environment"]);
}

ExtraHosts Service::extraHosts() {
    if (!node_["extra_hosts"]) {
        node_["extra_hosts"] = YAML::Node(YAML::NodeType::Map);
    }
    return ExtraHosts(node_["extra_hosts"]);
}

Ports Service::ports() {
    return Ports(node_);
}

Volumes Service::volumes() {
    return Volumes(node_);
}

Networks Service::networks() {
    return Networks(node_);
}

} // namespace compose