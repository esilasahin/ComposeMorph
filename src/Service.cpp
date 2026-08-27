#include "compose/Service.hpp"
#include "compose/BuildConfig.hpp"
#include "compose/HealthCheck.hpp"
#include "compose/DependsOn.hpp"
#include "compose/DeployConfig.hpp"

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

void Service::setWorkingDir(const std::string& dir) {
    node_["working_dir"] = dir;
}

std::string Service::workingDir() const {
    return node_["working_dir"] ? node_["working_dir"].as<std::string>() : "";
}

void Service::removeWorkingDir() {
    node_.remove("working_dir");
}

void Service::setUser(const std::string& user) {
    node_["user"] = user;
}

std::string Service::user() const {
    return node_["user"] ? node_["user"].as<std::string>() : "";
}

void Service::removeUser() {
    node_.remove("user");
}

void Service::setCommand(const std::string& cmd) {
    node_["command"] = cmd;
}

void Service::setCommand(const std::vector<std::string>& cmdSeq) {
    YAML::Node seq(YAML::NodeType::Sequence);
    for (const auto& item : cmdSeq) {
        seq.push_back(item);
    }
    node_["command"] = seq;
}

std::string Service::command() const {
    if (!node_["command"]) return "";
    if (node_["command"].IsScalar()) {
        return node_["command"].as<std::string>();
    }
    std::string res;
    for (std::size_t i = 0; i < node_["command"].size(); ++i) {
        if (i > 0) res += " ";
        res += node_["command"][i].as<std::string>();
    }
    return res;
}

void Service::setEntrypoint(const std::string& entrypoint) {
    node_["entrypoint"] = entrypoint;
}

void Service::setEntrypoint(const std::vector<std::string>& entrypointSeq) {
    YAML::Node seq(YAML::NodeType::Sequence);
    for (const auto& item : entrypointSeq) {
        seq.push_back(item);
    }
    node_["entrypoint"] = seq;
}

std::string Service::entrypoint() const {
    if (!node_["entrypoint"]) return "";
    if (node_["entrypoint"].IsScalar()) {
        return node_["entrypoint"].as<std::string>();
    }
    std::string res;
    for (std::size_t i = 0; i < node_["entrypoint"].size(); ++i) {
        if (i > 0) res += " ";
        res += node_["entrypoint"][i].as<std::string>();
    }
    return res;
}

Environment Service::environment() {
    if (!node_["environment"]) {
        node_["environment"] = YAML::Node(YAML::NodeType::Map);
    }
    return Environment(node_["environment"]);
}

Environment Service::labels() {
    if (!node_["labels"]) {
        node_["labels"] = YAML::Node(YAML::NodeType::Map);
    }
    return Environment(node_["labels"]);
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

BuildConfig Service::build() {
    return BuildConfig(node_);
}

HealthCheck Service::healthcheck() {
    return HealthCheck(node_);
}

DependsOn Service::dependsOn() {
    return DependsOn(node_);
}

DeployConfig Service::deploy() {
    return DeployConfig(node_);
}

} // namespace compose