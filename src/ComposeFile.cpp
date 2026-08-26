#include "compose/ComposeFile.hpp"
#include <fstream>
#include <stdexcept>

namespace compose {

ComposeFile::ComposeFile(const std::string& filePath) {
    load(filePath);
}

void ComposeFile::load(const std::string& filePath) {
    path_ = filePath;
    root_ = YAML::LoadFile(filePath);
}

Service ComposeFile::service(const std::string& name) {
    if (!hasService(name)) {
        throw std::runtime_error("Service not found: " + name);
    }
    return Service(root_["services"][name]);
}

bool ComposeFile::hasService(const std::string& name) const {
    return root_["services"] && root_["services"][name].IsDefined();
}

Service ComposeFile::addService(const std::string& name) {
    if (!root_["services"]) {
        root_["services"] = YAML::Node(YAML::NodeType::Map);
    }
    if (!root_["services"][name]) {
        root_["services"][name] = YAML::Node(YAML::NodeType::Map);
    }
    return Service(root_["services"][name]);
}

void ComposeFile::removeService(const std::string& name) {
    if (root_["services"] && root_["services"][name]) {
        root_["services"].remove(name);
    }
}

std::vector<std::string> ComposeFile::serviceNames() const {
    std::vector<std::string> names;
    if (root_["services"] && root_["services"].IsMap()) {
        for (const auto& kv : root_["services"]) {
            names.push_back(kv.first.as<std::string>());
        }
    }
    return names;
}

void ComposeFile::save(const std::string& outputPath) {
    std::string target = outputPath.empty() ? path_ : outputPath;
    std::ofstream fout(target);
    fout << root_ << std::endl;
}

}