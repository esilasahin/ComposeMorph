#pragma once

#include <string>
#include <optional>
#include <yaml-cpp/yaml.h>
#include "compose/Environment.hpp"
#include "compose/ExtraHosts.hpp"
#include "compose/Ports.hpp"
#include "compose/Volumes.hpp"
#include "compose/Networks.hpp"
#include "compose/BuildConfig.hpp"

namespace compose {

class Environment;
class ExtraHosts;
class Ports;
class Volumes;
class Networks;
class BuildConfig;

class Service {
public:
    explicit Service(YAML::Node node);

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

    Environment environment();
    ExtraHosts extraHosts();
    Ports ports();
    Volumes volumes();
    Networks networks();
    BuildConfig build();

private:
    YAML::Node node_;
};

} // namespace compose