#include "compose/DependsOn.hpp"

namespace compose {

DependsOn::DependsOn(YAML::Node serviceNode) : serviceNode_(serviceNode) {}

std::string DependsOn::conditionToString(DependCondition condition) {
    switch (condition) {
        case DependCondition::ServiceHealthy:
            return "service_healthy";
        case DependCondition::ServiceCompletedSuccessfully:
            return "service_completed_successfully";
        case DependCondition::ServiceStarted:
        default:
            return "service_started";
    }
}

void DependsOn::add(const std::string& serviceName) {
    if (!serviceNode_["depends_on"]) {
        serviceNode_["depends_on"] = YAML::Node(YAML::NodeType::Sequence);
    }

    if (serviceNode_["depends_on"].IsSequence()) {
        if (!has(serviceName)) {
            serviceNode_["depends_on"].push_back(serviceName);
        }
    } else if (serviceNode_["depends_on"].IsMap()) {
        serviceNode_["depends_on"][serviceName]["condition"] = "service_started";
    }
}

void DependsOn::add(const std::string& serviceName, DependCondition condition) {
    // Condition varsa Map formatına çevrilir veya map olarak eklenir
    if (!serviceNode_["depends_on"] || serviceNode_["depends_on"].IsSequence()) {
        YAML::Node newMap(YAML::NodeType::Map);
        if (serviceNode_["depends_on"] && serviceNode_["depends_on"].IsSequence()) {
            for (std::size_t i = 0; i < serviceNode_["depends_on"].size(); ++i) {
                newMap[serviceNode_["depends_on"][i].as<std::string>()]["condition"] = "service_started";
            }
        }
        serviceNode_["depends_on"] = newMap;
    }
    serviceNode_["depends_on"][serviceName]["condition"] = conditionToString(condition);
}

void DependsOn::remove(const std::string& serviceName) {
    if (!serviceNode_["depends_on"]) return;

    if (serviceNode_["depends_on"].IsSequence()) {
        YAML::Node newSeq(YAML::NodeType::Sequence);
        for (std::size_t i = 0; i < serviceNode_["depends_on"].size(); ++i) {
            if (serviceNode_["depends_on"][i].as<std::string>() != serviceName) {
                newSeq.push_back(serviceNode_["depends_on"][i].as<std::string>());
            }
        }
        serviceNode_["depends_on"] = newSeq;
    } else if (serviceNode_["depends_on"].IsMap()) {
        serviceNode_["depends_on"].remove(serviceName);
    }
}

bool DependsOn::has(const std::string& serviceName) const {
    if (!serviceNode_["depends_on"]) return false;

    if (serviceNode_["depends_on"].IsSequence()) {
        for (std::size_t i = 0; i < serviceNode_["depends_on"].size(); ++i) {
            if (serviceNode_["depends_on"][i].as<std::string>() == serviceName) {
                return true;
            }
        }
    } else if (serviceNode_["depends_on"].IsMap()) {
        return serviceNode_["depends_on"][serviceName].IsDefined();
    }
    return false;
}

std::vector<std::string> DependsOn::toVector() const {
    std::vector<std::string> result;
    if (!serviceNode_["depends_on"]) return result;

    if (serviceNode_["depends_on"].IsSequence()) {
        for (std::size_t i = 0; i < serviceNode_["depends_on"].size(); ++i) {
            result.push_back(serviceNode_["depends_on"][i].as<std::string>());
        }
    } else if (serviceNode_["depends_on"].IsMap()) {
        for (auto it = serviceNode_["depends_on"].begin(); it != serviceNode_["depends_on"].end(); ++it) {
            result.push_back(it->first.as<std::string>());
        }
    }
    return result;
}

}