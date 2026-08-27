#pragma once

#include <string>
#include <vector>
#include <optional>
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

    // Temel Alanlar (Madde 4)
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

    // Komut ve Giriş Noktaları (Madde 16)
    void setCommand(const std::string& cmd);
    void setCommand(const std::vector<std::string>& cmdSeq);
    std::string command() const;

    void setEntrypoint(const std::string& entrypoint);
    void setEntrypoint(const std::vector<std::string>& entrypointSeq);
    std::string entrypoint() const;

    // Alt Koleksiyonlar (Madde 5-15)
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

private:
    YAML::Node node_;
};

} // namespace compose