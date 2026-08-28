#pragma once

#include <string>
#include <vector>
#include <optional>
#include <sstream>
#include <yaml-cpp/yaml.h>
#include "compose/Environment.hpp"
#include "compose/ExtraHosts.hpp"
#include "compose/Ports.hpp"
#include "compose/Volumes.hpp"
#include "compose/Networks.hpp"
#include "compose/BuildConfig.hpp"
#include "compose/HealthCheck.hpp"
#include "compose/DependsOn.hpp"
#include "compose/DeployConfig.hpp"
#include "compose/Exceptions.hpp"

namespace compose {

class Environment;
class ExtraHosts;
class Ports;
class Volumes;
class Networks;
class BuildConfig;
class HealthCheck;
class DependsOn;
class DeployConfig;

class Service {
public:
    explicit Service(YAML::Node node);

    // Temel Alanlar
    void setImage(const std::string& image);
    std::string image() const;

    void setHostname(const std::string& hostname);
    std::string hostname() const;
    void removeHostname();

    void setContainerName(const std::string& name);
    std::string containerName() const;
    void removeContainerName();

    void setRestart(const std::string& restart);
    std::string restart() const;
    void removeRestart();

    void setPrivileged(bool priv);
    bool privileged() const;

    void setWorkingDir(const std::string& dir);
    std::string workingDir() const;
    void removeWorkingDir();

    void setUser(const std::string& user);
    std::string user() const;
    void removeUser();

    // Komut ve Entrypoint
    void setCommand(const std::string& cmd);
    void setCommand(const std::vector<std::string>& cmdSeq);
    std::string command() const;

    void setEntrypoint(const std::string& entrypoint);
    void setEntrypoint(const std::vector<std::string>& entrypointSeq);
    std::string entrypoint() const;

    // Alt Koleksiyonlar
    Environment environment();
    Environment labels();
    ExtraHosts extraHosts();
    Ports ports();
    Volumes volumes();
    Networks networks();
    BuildConfig build();
    HealthCheck healthcheck();
    DependsOn dependsOn();
    DeployConfig deploy();

    // Generic Property API (Pointer & Address Hatasi Icerermeyen Temiz Node Referans Mantigi)
    template <typename T>
    void set(const std::string& keyPath, const T& value) {
        std::vector<std::string> keys = splitKeyPath(keyPath);
        if (keys.empty()) return;

        YAML::Node current = node_;
        for (std::size_t i = 0; i < keys.size() - 1; ++i) {
            if (!current[keys[i]] || !current[keys[i]].IsMap()) {
                current[keys[i]] = YAML::Node(YAML::NodeType::Map);
            }
            current.reset(current[keys[i]]);
        }
        current[keys.back()] = value;
    }

    template <typename T>
    std::optional<T> get(const std::string& keyPath) const {
        std::vector<std::string> keys = splitKeyPath(keyPath);
        if (keys.empty()) return std::nullopt;

        YAML::Node current = node_;
        for (const auto& key : keys) {
            if (!current[key] || !current[key].IsDefined()) {
                return std::nullopt;
            }
            current.reset(current[key]);
        }
        try {
            return current.as<T>();
        } catch (...) {
            return std::nullopt;
        }
    }

    void remove(const std::string& keyPath) {
        std::vector<std::string> keys = splitKeyPath(keyPath);
        if (keys.empty()) return;

        YAML::Node current = node_;
        for (std::size_t i = 0; i < keys.size() - 1; ++i) {
            if (!current[keys[i]]) return;
            current.reset(current[keys[i]]);
        }
        current.remove(keys.back());
    }

private:
    YAML::Node node_;

    static std::vector<std::string> splitKeyPath(const std::string& path) {
        std::vector<std::string> tokens;
        std::stringstream ss(path);
        std::string token;
        while (std::getline(ss, token, '.')) {
            if (!token.empty()) tokens.push_back(token);
        }
        return tokens;
    }
};

} // namespace compose