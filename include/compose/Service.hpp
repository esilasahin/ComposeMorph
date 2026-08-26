#pragma once
#include <yaml-cpp/yaml.h>
#include <string>

namespace compose {

class Service {
public:
    explicit Service(YAML::Node node);

    void setImage(const std::string& img);
    std::string image() const;

    void setHostname(const std::string& host);
    std::string hostname() const;
    void removeHostname();

    void setContainerName(const std::string& name);
    std::string containerName() const;
    void removeContainerName();

    void setRestart(const std::string& restartPolicy);
    std::string restart() const;
    void removeRestart();

    void setPrivileged(bool priv);
    bool privileged() const;

private:
    YAML::Node node_;
};

}