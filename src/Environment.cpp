#include "compose/Environment.hpp"

namespace compose {

Environment::Environment(YAML::Node node) : m_node(node) {}

void Environment::set(const std::string& key, const std::string& value) {
    if (!m_node) {
        m_node = YAML::Node(YAML::NodeType::Map);
    }
    m_node[key] = value;
}

std::optional<std::string> Environment::get(const std::string& key) const {
    if (m_node && m_node.IsMap() && m_node[key]) {
        return m_node[key].as<std::string>();
    }
    return std::nullopt;
}

bool Environment::has(const std::string& key) const {
    return m_node && m_node.IsMap() && m_node[key].IsDefined();
}

void Environment::remove(const std::string& key) {
    if (m_node && m_node.IsMap() && m_node[key]) {
        m_node.remove(key);
    }
}

std::unordered_map<std::string, std::string> Environment::getAll() const {
    std::unordered_map<std::string, std::string> result;
    if (m_node && m_node.IsMap()) {
        for (const auto& kv : m_node) {
            result[kv.first.as<std::string>()] = kv.second.as<std::string>();
        }
    }
    return result;
}

} // namespace compose