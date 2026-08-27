#include "compose/TopLevelCollections.hpp"

namespace compose {

// NetworkDefinition
NetworkDefinition::NetworkDefinition(YAML::Node node) : node_(node) {}

void NetworkDefinition::setExternal(bool external) {
    node_["external"] = external;
}

bool NetworkDefinition::external() const {
    return (node_["external"]) ? node_["external"].as<bool>() : false;
}

void NetworkDefinition::setDriver(const std::string& driver) {
    node_["driver"] = driver;
}

std::string NetworkDefinition::driver() const {
    return (node_["driver"]) ? node_["driver"].as<std::string>() : "";
}

// NetworkCollection
NetworkCollection::NetworkCollection(YAML::Node rootNode) : rootNode_(rootNode) {}

NetworkDefinition NetworkCollection::add(const std::string& name) {
    if (!rootNode_["networks"]) {
        rootNode_["networks"] = YAML::Node(YAML::NodeType::Map);
    }
    if (!rootNode_["networks"][name]) {
        rootNode_["networks"][name] = YAML::Node(YAML::NodeType::Map);
    }
    return NetworkDefinition(rootNode_["networks"][name]);
}

NetworkDefinition NetworkCollection::get(const std::string& name) {
    return add(name);
}

void NetworkCollection::remove(const std::string& name) {
    if (rootNode_["networks"]) {
        rootNode_["networks"].remove(name);
    }
}

bool NetworkCollection::has(const std::string& name) const {
    return rootNode_["networks"] && rootNode_["networks"][name].IsDefined();
}

std::vector<std::string> NetworkCollection::names() const {
    std::vector<std::string> result;
    if (rootNode_["networks"] && rootNode_["networks"].IsMap()) {
        for (auto it = rootNode_["networks"].begin(); it != rootNode_["networks"].end(); ++it) {
            result.push_back(it->first.as<std::string>());
        }
    }
    return result;
}

// VolumeDefinition
VolumeDefinition::VolumeDefinition(YAML::Node node) : node_(node) {}

void VolumeDefinition::setExternal(bool external) {
    node_["external"] = external;
}

bool VolumeDefinition::external() const {
    return (node_["external"]) ? node_["external"].as<bool>() : false;
}

void VolumeDefinition::setDriver(const std::string& driver) {
    node_["driver"] = driver;
}

std::string VolumeDefinition::driver() const {
    return (node_["driver"]) ? node_["driver"].as<std::string>() : "";
}

// VolumeCollection
VolumeCollection::VolumeCollection(YAML::Node rootNode) : rootNode_(rootNode) {}

VolumeDefinition VolumeCollection::add(const std::string& name) {
    if (!rootNode_["volumes"]) {
        rootNode_["volumes"] = YAML::Node(YAML::NodeType::Map);
    }
    if (!rootNode_["volumes"][name]) {
        rootNode_["volumes"][name] = YAML::Node(YAML::NodeType::Map);
    }
    return VolumeDefinition(rootNode_["volumes"][name]);
}

VolumeDefinition VolumeCollection::get(const std::string& name) {
    return add(name);
}

void VolumeCollection::remove(const std::string& name) {
    if (rootNode_["volumes"]) {
        rootNode_["volumes"].remove(name);
    }
}

bool VolumeCollection::has(const std::string& name) const {
    return rootNode_["volumes"] && rootNode_["volumes"][name].IsDefined();
}

std::vector<std::string> VolumeCollection::names() const {
    std::vector<std::string> result;
    if (rootNode_["volumes"] && rootNode_["volumes"].IsMap()) {
        for (auto it = rootNode_["volumes"].begin(); it != rootNode_["volumes"].end(); ++it) {
            result.push_back(it->first.as<std::string>());
        }
    }
    return result;
}

// FileConfigDefinition
FileConfigDefinition::FileConfigDefinition(YAML::Node node) : node_(node) {}

void FileConfigDefinition::setFile(const std::string& filePath) {
    node_["file"] = filePath;
}

std::string FileConfigDefinition::file() const {
    return (node_["file"]) ? node_["file"].as<std::string>() : "";
}

void FileConfigDefinition::setExternal(bool external) {
    node_["external"] = external;
}

bool FileConfigDefinition::external() const {
    return (node_["external"]) ? node_["external"].as<bool>() : false;
}

// SecretCollection
SecretCollection::SecretCollection(YAML::Node rootNode) : rootNode_(rootNode) {}

FileConfigDefinition SecretCollection::add(const std::string& name) {
    if (!rootNode_["secrets"]) {
        rootNode_["secrets"] = YAML::Node(YAML::NodeType::Map);
    }
    if (!rootNode_["secrets"][name]) {
        rootNode_["secrets"][name] = YAML::Node(YAML::NodeType::Map);
    }
    return FileConfigDefinition(rootNode_["secrets"][name]);
}

FileConfigDefinition SecretCollection::get(const std::string& name) {
    return add(name);
}

void SecretCollection::remove(const std::string& name) {
    if (rootNode_["secrets"]) {
        rootNode_["secrets"].remove(name);
    }
}

bool SecretCollection::has(const std::string& name) const {
    return rootNode_["secrets"] && rootNode_["secrets"][name].IsDefined();
}

// ConfigCollection
ConfigCollection::ConfigCollection(YAML::Node rootNode) : rootNode_(rootNode) {}

FileConfigDefinition ConfigCollection::add(const std::string& name) {
    if (!rootNode_["configs"]) {
        rootNode_["configs"] = YAML::Node(YAML::NodeType::Map);
    }
    if (!rootNode_["configs"][name]) {
        rootNode_["configs"][name] = YAML::Node(YAML::NodeType::Map);
    }
    return FileConfigDefinition(rootNode_["configs"][name]);
}

FileConfigDefinition ConfigCollection::get(const std::string& name) {
    return add(name);
}

void ConfigCollection::remove(const std::string& name) {
    if (rootNode_["configs"]) {
        rootNode_["configs"].remove(name);
    }
}

bool ConfigCollection::has(const std::string& name) const {
    return rootNode_["configs"] && rootNode_["configs"][name].IsDefined();
}

}