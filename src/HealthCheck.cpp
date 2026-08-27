#include "compose/HealthCheck.hpp"

namespace compose {

HealthCheck::HealthCheck(YAML::Node serviceNode) : serviceNode_(serviceNode) {}

void HealthCheck::setCommand(const std::vector<std::string>& cmd) {
    if (!serviceNode_["healthcheck"]) {
        serviceNode_["healthcheck"] = YAML::Node(YAML::NodeType::Map);
    }
    YAML::Node cmdSeq(YAML::NodeType::Sequence);
    for (const auto& arg : cmd) {
        cmdSeq.push_back(arg);
    }
    serviceNode_["healthcheck"]["test"] = cmdSeq;
}

std::vector<std::string> HealthCheck::command() const {
    std::vector<std::string> result;
    if (serviceNode_["healthcheck"] && serviceNode_["healthcheck"]["test"] && serviceNode_["healthcheck"]["test"].IsSequence()) {
        for (std::size_t i = 0; i < serviceNode_["healthcheck"]["test"].size(); ++i) {
            result.push_back(serviceNode_["healthcheck"]["test"][i].as<std::string>());
        }
    }
    return result;
}

void HealthCheck::setInterval(const std::string& interval) {
    if (!serviceNode_["healthcheck"]) {
        serviceNode_["healthcheck"] = YAML::Node(YAML::NodeType::Map);
    }
    serviceNode_["healthcheck"]["interval"] = interval;
}

std::string HealthCheck::interval() const {
    if (serviceNode_["healthcheck"] && serviceNode_["healthcheck"]["interval"]) {
        return serviceNode_["healthcheck"]["interval"].as<std::string>();
    }
    return "";
}

void HealthCheck::setTimeout(const std::string& timeout) {
    if (!serviceNode_["healthcheck"]) {
        serviceNode_["healthcheck"] = YAML::Node(YAML::NodeType::Map);
    }
    serviceNode_["healthcheck"]["timeout"] = timeout;
}

std::string HealthCheck::timeout() const {
    if (serviceNode_["healthcheck"] && serviceNode_["healthcheck"]["timeout"]) {
        return serviceNode_["healthcheck"]["timeout"].as<std::string>();
    }
    return "";
}

void HealthCheck::setRetries(int retries) {
    if (!serviceNode_["healthcheck"]) {
        serviceNode_["healthcheck"] = YAML::Node(YAML::NodeType::Map);
    }
    serviceNode_["healthcheck"]["retries"] = retries;
}

int HealthCheck::retries() const {
    if (serviceNode_["healthcheck"] && serviceNode_["healthcheck"]["retries"]) {
        return serviceNode_["healthcheck"]["retries"].as<int>();
    }
    return 0;
}

void HealthCheck::setStartPeriod(const std::string& startPeriod) {
    if (!serviceNode_["healthcheck"]) {
        serviceNode_["healthcheck"] = YAML::Node(YAML::NodeType::Map);
    }
    serviceNode_["healthcheck"]["start_period"] = startPeriod;
}

std::string HealthCheck::startPeriod() const {
    if (serviceNode_["healthcheck"] && serviceNode_["healthcheck"]["start_period"]) {
        return serviceNode_["healthcheck"]["start_period"].as<std::string>();
    }
    return "";
}

void HealthCheck::disable() {
    if (!serviceNode_["healthcheck"]) {
        serviceNode_["healthcheck"] = YAML::Node(YAML::NodeType::Map);
    }
    serviceNode_["healthcheck"]["disable"] = true;
}

}