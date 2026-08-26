#include "compose/ExtraHosts.hpp"

namespace compose {

ExtraHosts::ExtraHosts(YAML::Node node) : node_(node) {}

void ExtraHosts::set(const std::string& host, const std::string& ip) {
    if (!node_) {
        node_ = YAML::Node(YAML::NodeType::Map);
    }
    node_[host] = ip;
}

std::optional<std::string> ExtraHosts::get(const std::string& host) const {
    if (node_ && node_.IsMap() && node_[host]) {
        return node_[host].as<std::string>();
    }
    return std::nullopt;
}

bool ExtraHosts::has(const std::string& host) const {
    return node_ && node_.IsMap() && node_[host].IsDefined();
}

void ExtraHosts::remove(const std::string& host) {
    if (node_ && node_.IsMap() && node_[host]) {
        node_.remove(host);
    }
}

std::unordered_map<std::string, std::string> ExtraHosts::getAll() const {
    std::unordered_map<std::string, std::string> result;
    if (node_ && node_.IsMap()) {
        for (const auto& kv : node_) {
            result[kv.first.as<std::string>()] = kv.second.as<std::string>();
        }
    }
    return result;
}

} // namespace compose