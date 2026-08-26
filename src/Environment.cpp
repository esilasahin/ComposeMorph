#include "compose/Environment.hpp"

namespace compose {

Environment::Environment(YAML::Node node) : node_(node) {}

void Environment::set(const std::string& key, const std::string& value) {
    if (!node_) {
        node_ = YAML::Node(YAML::NodeType::Map);
    }
    node_[key] = value;
}

std::optional<std::string> Environment::get(const std::string& key) const {
    if (node_ && node_.IsMap() && node_[key]) {
        return node_[key].as<std::string>();
    }
    return std::nullopt;
}

bool Environment::has(const std::string& key) const {
    return node_ && node_.IsMap() && node_[key].IsDefined();
}

void Environment::remove(const std::string& key) {
    if (node_ && node_.IsMap() && node_[key]) {
        node_.remove(key);
    }
}

std::unordered_map<std::string, std::string> Environment::getAll() const {
    std::unordered_map<std::string, std::string> result;
    if (node_ && node_.IsMap()) {
        for (const auto& kv : node_) {
            result[kv.first.as<std::string>()] = kv.second.as<std::string>();
        }
    }
    return result;
}

} // namespace compose