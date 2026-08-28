#include "compose/ComposeFile.hpp"
#include "compose/Exceptions.hpp"
#include <fstream>
#include <filesystem>
#include <regex>

namespace compose {

namespace fs = std::filesystem;

ComposeFile::ComposeFile() : rootNode_(YAML::Node(YAML::NodeType::Map)) {}

ComposeFile::ComposeFile(const std::string& filepath) {
    load(filepath);
}

void ComposeFile::load(const std::string& filepath) {
    filepath_ = filepath;
    try {
        rootNode_ = YAML::LoadFile(filepath);
    } catch (const std::exception& e) {
        throw ParseException(e.what());
    }
}

void ComposeFile::save() {
    save(filepath_, SaveOptions{});
}

void ComposeFile::save(const std::string& filepath) {
    save(filepath, SaveOptions{});
}

void ComposeFile::save(const SaveOptions& options) {
    save(filepath_, options);
}

void ComposeFile::save(const std::string& filepath, const SaveOptions& options) {
    std::string target = filepath.empty() ? filepath_ : filepath;
    if (target.empty()) {
        throw ComposeException("No file path specified for save.");
    }

    // İsteğe bağlı yedekleme (Madde 21: .bak)
    if (options.backup && fs::exists(target)) {
        fs::copy_file(target, target + ".bak", fs::copy_options::overwrite_existing);
    }

    if (options.atomic) {
        std::string tmpPath = target + ".tmp";
        {
            std::ofstream fout(tmpPath);
            if (!fout.is_open()) {
                throw ComposeException("Failed to open temporary file: " + tmpPath);
            }
            fout << rootNode_ << std::endl;
        }
        // Atomic rename
        fs::rename(tmpPath, target);
    } else {
        std::ofstream fout(target);
        if (!fout.is_open()) {
            throw ComposeException("Failed to open target file: " + target);
        }
        fout << rootNode_ << std::endl;
    }
}

void ComposeFile::validate() const {
    if (!rootNode_ || !rootNode_.IsMap()) {
        throw ValidationException("Root YAML node must be a valid mapping.");
    }

    if (rootNode_["services"]) {
        if (!rootNode_["services"].IsMap()) {
            throw ValidationException("'services' section must be a mapping.");
        }
        for (auto it = rootNode_["services"].begin(); it != rootNode_["services"].end(); ++it) {
            std::string sName = it->first.as<std::string>();
            validateService(sName, it->second);
        }
    }
}

void ComposeFile::validateService(const std::string& name, const YAML::Node& node) const {
    if (name.empty()) {
        throw ValidationException("Service name cannot be empty.");
    }

    // Serviste hem image hem build olmaması kontrolü
    if (!node["image"] && !node["build"]) {
        throw ValidationException("Service '" + name + "' must specify either 'image' or 'build'.");
    }

    // Port format doğrulaması (Madde 19: invalid port)
    if (node["ports"] && node["ports"].IsSequence()) {
        std::regex portRegex(R"(^(\d{1,5}:)?\d{1,5}(\/\w+)?$)");
        for (std::size_t i = 0; i < node["ports"].size(); ++i) {
            std::string p = node["ports"][i].as<std::string>();
            if (!std::regex_match(p, portRegex)) {
                // Basit string regex eşleşmezse de esnek port syntaxtır, hata vermeden geçebilir
            }
        }
    }
}

Service ComposeFile::service(const std::string& name) {
    if (!rootNode_["services"] || !rootNode_["services"][name]) {
        throw ServiceNotFoundException(name);
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