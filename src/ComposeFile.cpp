#include "compose/ComposeFile.hpp"
#include <fstream>

namespace compose {

ComposeFile::ComposeFile() : rootNode_(YAML::Node(YAML::NodeType::Map)) {}

ComposeFile::ComposeFile(const std::string& filepath) {
    load(filepath);
}

void ComposeFile::load(const std::string& filepath) {
    filepath_ = filepath;
    rootNode_ = YAML::LoadFile(filepath);
}

void ComposeFile::save() {
    save(filepath_);
}

void ComposeFile::save(const std::string& filepath) {
    std::string target = filepath.empty() ? filepath_ : filepath;
    std::ofstream fout(target);
    fout << rootNode_ << std::endl;
}

Service ComposeFile::service(const std::string& name) {
    if (!rootNode_["services"] || !rootNode_["services"][name]) {
        return addService(name);
    }
    return Service(rootNode_["services"][name]);
}

bool ComposeFile::hasService(const std::string& name) const {
    return rootNode_["services"] && rootNode_["services"][name].IsDefined();
}

Service ComposeFile::addService(const std::string& name) {
    if (!rootNode_["services"]) {
        rootNode_["services"] = YAML::Node(YAML::NodeType::Map);
    }
    if (!rootNode_["services"][name]) {
        rootNode_["services"][name] = YAML::Node(YAML::NodeType::Map);
    }
    return Service(rootNode_["services"][name]);
}

void ComposeFile::removeService(const std::string& name) {
    if (rootNode_["services"] && rootNode_["services"][name]) {
        rootNode_["services"].remove(name);
    }
}

std::vector<std::string> ComposeFile::serviceNames() const {
    std::vector<std::string> names;
    if (rootNode_["services"] && rootNode_["services"].IsMap()) {
        for (auto it = rootNode_["services"].begin(); it != rootNode_["services"].end(); ++it) {
            names.push_back(it->first.as<std::string>());
        }
    }
    return names;
}

NetworkCollection ComposeFile::networks() {
    return NetworkCollection(rootNode_);
}

VolumeCollection ComposeFile::volumes() {
    return VolumeCollection(rootNode_);
}

SecretCollection ComposeFile::secrets() {
    return SecretCollection(rootNode_);
}

ConfigCollection ComposeFile::configs() {
    return ConfigCollection(rootNode_);
}

} // namespace compose