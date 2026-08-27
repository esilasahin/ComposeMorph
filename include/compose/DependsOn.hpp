#pragma once
#include <yaml-cpp/yaml.h>
#include <string>
#include <vector>

namespace compose {

enum class DependCondition {
    ServiceStarted,
    ServiceHealthy,
    ServiceCompletedSuccessfully
};

class DependsOn {
public:
    explicit DependsOn(YAML::Node serviceNode);

    void add(const std::string& serviceName);
    void add(const std::string& serviceName, DependCondition condition);
    void remove(const std::string& serviceName);
    bool has(const std::string& serviceName) const;

    std::vector<std::string> toVector() const;

private:
    YAML::Node serviceNode_;
    static std::string conditionToString(DependCondition condition);
};

}