#pragma once
#include <yaml-cpp/yaml.h>
#include <string>
#include <vector>

namespace compose {

class HealthCheck {
public:
    explicit HealthCheck(YAML::Node serviceNode);

    void setCommand(const std::vector<std::string>& cmd);
    std::vector<std::string> command() const;

    void setInterval(const std::string& interval);
    std::string interval() const;

    void setTimeout(const std::string& timeout);
    std::string timeout() const;

    void setRetries(int retries);
    int retries() const;

    void setStartPeriod(const std::string& startPeriod);
    std::string startPeriod() const;

    void disable();

private:
    YAML::Node serviceNode_;
};

}