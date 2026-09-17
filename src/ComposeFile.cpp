#include "compose/ComposeFile.hpp"
#include "compose/Exceptions.hpp"
#include "ScalarQuoting.hpp"
#include <fstream>
#include <filesystem>
#include <regex>
#include <set>
#include <sstream>

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
            detail::emitPreservingQuotes(fout, rootNode_);
            fout << std::endl;
        }
        // Atomic rename
        fs::rename(tmpPath, target);
    } else {
        std::ofstream fout(target);
        if (!fout.is_open()) {
            throw ComposeException("Failed to open target file: " + target);
        }
        detail::emitPreservingQuotes(fout, rootNode_);
        fout << std::endl;
    }
}

namespace {

// Görev tanımı Madde 19'daki kontroller için yardımcılar. Interpolasyon
// içeren değerler ("${PORT}:80") çalışma zamanında çözüldüğü için denetim
// dışında bırakılır.
bool hasInterpolation(const std::string& value) {
    // Compose hem ${VAR} hem de $VAR yazımını destekler.
    return value.find('$') != std::string::npos;
}

const std::regex& portPattern() {
    static const std::regex pattern(
        R"(^(?:(?:\d{1,3}(?:\.\d{1,3}){3}|\[[0-9A-Fa-f:]+\]):)?)"
        R"((?:\d{0,5}(?:-\d{1,5})?:)?\d{1,5}(?:-\d{1,5})?(?:/(?:tcp|udp|sctp))?$)");
    return pattern;
}

const std::regex& hostnamePattern() {
    // Docker, RFC 1123'ten farklı olarak alt çizgiye de izin verdiğinden
    // desen bu karakteri kapsar.
    static const std::regex pattern(
        R"(^[A-Za-z0-9]([A-Za-z0-9_-]{0,61}[A-Za-z0-9])?)"
        R"((\.[A-Za-z0-9]([A-Za-z0-9_-]{0,61}[A-Za-z0-9])?)*$)");
    return pattern;
}

bool isVolumeMode(const std::string& mode) {
    static const std::set<std::string> known = {
        "ro", "rw", "z", "Z", "cached", "delegated", "consistent", "nocopy", "rprivate",
        "private", "rshared", "shared", "rslave", "slave"};
    std::stringstream ss(mode);
    std::string token;
    while (std::getline(ss, token, ',')) {
        if (known.find(token) == known.end()) {
            return false;
        }
    }
    return true;
}

void requireType(const YAML::Node& node, const std::string& field, const std::string& service,
                 std::initializer_list<YAML::NodeType::value> allowed) {
    if (!node) {
        return;
    }
    for (YAML::NodeType::value type : allowed) {
        if (node.Type() == type) {
            return;
        }
    }
    throw ValidationException("Service '" + service + "': '" + field + "' has the wrong type.");
}

}  // namespace

void ComposeFile::validate() const {
    if (!rootNode_ || !rootNode_.IsMap()) {
        throw ValidationException("Root YAML node must be a valid mapping.");
    }

    // Üst seviyede tanımlı ağlar, servislerin ağ referanslarını denetlemek
    // için toplanır (Madde 19: invalid network reference).
    std::set<std::string> declaredNetworks;
    bool networksDeclared = false;
    if (rootNode_["networks"]) {
        if (!rootNode_["networks"].IsMap() && !rootNode_["networks"].IsNull()) {
            throw ValidationException("Top-level 'networks' section must be a mapping.");
        }
        networksDeclared = rootNode_["networks"].IsMap();
        if (networksDeclared) {
            for (const auto& kv : rootNode_["networks"]) {
                declaredNetworks.insert(kv.first.as<std::string>());
            }
        }
    }

    if (rootNode_["services"]) {
        if (!rootNode_["services"].IsMap()) {
            throw ValidationException("'services' section must be a mapping.");
        }
        for (auto it = rootNode_["services"].begin(); it != rootNode_["services"].end(); ++it) {
            std::string sName = it->first.as<std::string>();
            validateService(sName, it->second,
                            networksDeclared ? &declaredNetworks : nullptr);
        }
    }
}

void ComposeFile::validateService(const std::string& name, const YAML::Node& node,
                                  const std::set<std::string>* declaredNetworks) const {
    static const std::regex namePattern(R"(^[A-Za-z0-9][A-Za-z0-9_.-]*$)");
    if (name.empty()) {
        throw ValidationException("Service name cannot be empty.");
    }
    if (!std::regex_match(name, namePattern)) {
        throw ValidationException("Service name '" + name + "' is not a valid Compose name.");
    }
    if (!node.IsMap()) {
        throw ValidationException("Service '" + name + "' must be a mapping.");
    }

    // Zorunlu alanlar: image ya da build. extends kullanan servis bu alanları
    // devraldığı için muaftır.
    if (!node["image"] && !node["build"] && !node["extends"]) {
        throw ValidationException("Service '" + name + "' must specify either 'image' or 'build'.");
    }

    // Tip denetimi
    using T = YAML::NodeType;
    requireType(node["image"], "image", name, {T::Scalar});
    requireType(node["hostname"], "hostname", name, {T::Scalar});
    requireType(node["container_name"], "container_name", name, {T::Scalar});
    requireType(node["restart"], "restart", name, {T::Scalar});
    requireType(node["ports"], "ports", name, {T::Sequence});
    requireType(node["volumes"], "volumes", name, {T::Sequence});
    requireType(node["networks"], "networks", name, {T::Sequence, T::Map, T::Null});
    requireType(node["environment"], "environment", name, {T::Sequence, T::Map, T::Null});
    requireType(node["labels"], "labels", name, {T::Sequence, T::Map});
    requireType(node["depends_on"], "depends_on", name, {T::Sequence, T::Map});
    requireType(node["healthcheck"], "healthcheck", name, {T::Map});
    requireType(node["deploy"], "deploy", name, {T::Map});

    // Hostname biçimi
    if (node["hostname"] && node["hostname"].IsScalar()) {
        std::string hostname = node["hostname"].as<std::string>();
        if (!hasInterpolation(hostname) && !std::regex_match(hostname, hostnamePattern())) {
            throw ValidationException("Service '" + name + "': invalid hostname '" + hostname + "'.");
        }
    }

    // Port biçimi ve yinelenen port girdileri
    if (node["ports"] && node["ports"].IsSequence()) {
        std::set<std::string> seen;
        for (std::size_t i = 0; i < node["ports"].size(); ++i) {
            const YAML::Node entry = node["ports"][i];
            if (entry.IsMap()) {
                if (!entry["target"]) {
                    throw ValidationException("Service '" + name +
                                              "': long-syntax port entry requires 'target'.");
                }
                continue;
            }
            if (!entry.IsScalar()) {
                throw ValidationException("Service '" + name + "': invalid port entry.");
            }
            std::string port = entry.as<std::string>();
            if (!hasInterpolation(port) && !std::regex_match(port, portPattern())) {
                throw ValidationException("Service '" + name + "': invalid port '" + port + "'.");
            }
            if (!seen.insert(port).second) {
                throw ValidationException("Service '" + name + "': duplicate port '" + port + "'.");
            }
        }
    }

    // Volume tanımları ve yinelenen hedefler
    if (node["volumes"] && node["volumes"].IsSequence()) {
        std::set<std::string> targets;
        for (std::size_t i = 0; i < node["volumes"].size(); ++i) {
            const YAML::Node entry = node["volumes"][i];
            std::string target;
            if (entry.IsMap()) {
                if (!entry["target"]) {
                    throw ValidationException("Service '" + name +
                                              "': long-syntax volume entry requires 'target'.");
                }
                target = entry["target"].as<std::string>();
            } else if (entry.IsScalar()) {
                std::string mapping = entry.as<std::string>();
                if (mapping.empty()) {
                    throw ValidationException("Service '" + name + "': empty volume definition.");
                }
                if (hasInterpolation(mapping)) {
                    continue;
                }
                std::vector<std::string> parts;
                std::stringstream ss(mapping);
                std::string part;
                while (std::getline(ss, part, ':')) {
                    parts.push_back(part);
                }
                if (parts.size() > 3) {
                    throw ValidationException("Service '" + name + "': invalid volume definition '" +
                                              mapping + "'.");
                }
                // Üçüncü parça yol içeriyorsa mod değil, ikinci bir yoldur
                // (ör. "v:/host/path:/container/path"); yalnızca gerçek mod
                // belirteçleri denetlenir.
                if (parts.size() == 3 && parts[2].find('/') == std::string::npos &&
                    !isVolumeMode(parts[2])) {
                    throw ValidationException("Service '" + name + "': invalid volume mode '" +
                                              parts[2] + "'.");
                }
                target = parts.size() > 1 ? parts[1] : parts[0];
            } else {
                throw ValidationException("Service '" + name + "': invalid volume entry.");
            }

            if (!target.empty() && !targets.insert(target).second) {
                throw ValidationException("Service '" + name + "': duplicate volume target '" +
                                          target + "'.");
            }
        }
    }

    // Ortam değişkenlerinin liste biçiminde yinelenmesi
    if (node["environment"] && node["environment"].IsSequence()) {
        std::set<std::string> keys;
        for (std::size_t i = 0; i < node["environment"].size(); ++i) {
            const YAML::Node entry = node["environment"][i];
            if (!entry.IsScalar()) {
                continue;
            }
            std::string text = entry.as<std::string>();
            std::string key = text.substr(0, text.find('='));
            if (!key.empty() && !keys.insert(key).second) {
                throw ValidationException("Service '" + name +
                                          "': duplicate environment variable '" + key + "'.");
            }
        }
    }

    // Ağ referansları: üst seviyede tanımlı olmayan ağa atıf
    if (declaredNetworks && node["networks"]) {
        std::vector<std::string> referenced;
        if (node["networks"].IsSequence()) {
            for (std::size_t i = 0; i < node["networks"].size(); ++i) {
                if (node["networks"][i].IsScalar()) {
                    referenced.push_back(node["networks"][i].as<std::string>());
                }
            }
        } else if (node["networks"].IsMap()) {
            for (const auto& kv : node["networks"]) {
                referenced.push_back(kv.first.as<std::string>());
            }
        }

        std::set<std::string> seen;
        for (const std::string& network : referenced) {
            if (network != "default" && declaredNetworks->find(network) == declaredNetworks->end()) {
                throw ValidationException("Service '" + name + "': undefined network '" +
                                          network + "'.");
            }
            if (!seen.insert(network).second) {
                throw ValidationException("Service '" + name + "': duplicate network '" +
                                          network + "'.");
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