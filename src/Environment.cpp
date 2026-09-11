#include "compose/Environment.hpp"
#include "ScalarQuoting.hpp"

namespace compose {

namespace {
// Short (list) syntax entries are "KEY=VALUE", or a bare "KEY" whose value
// comes from the host environment.
std::string entryKey(const std::string& entry) {
    return entry.substr(0, entry.find('='));
}

std::optional<std::string> entryValue(const std::string& entry) {
    const auto eq = entry.find('=');
    if (eq == std::string::npos) return std::nullopt;
    return entry.substr(eq + 1);
}

bool entryHasKey(const YAML::Node& item, const std::string& key) {
    return item.IsScalar() && entryKey(item.Scalar()) == key;
}
}

Environment::Environment(YAML::Node node) : node_(node) {}

void Environment::set(const std::string& key, const std::string& value) {
    if (node_ && node_.IsSequence()) {
        const std::string entry = key + "=" + value;
        for (std::size_t i = 0; i < node_.size(); ++i) {
            if (entryHasKey(node_[i], key)) {
                detail::assignString(node_[i], entry);
                return;
            }
        }
        node_.push_back(detail::makeString(entry));
        return;
    }
    if (!node_) {
        node_ = YAML::Node(YAML::NodeType::Map);
    }
    detail::assignString(node_[key], value);
}

std::optional<std::string> Environment::get(const std::string& key) const {
    if (node_ && node_.IsSequence()) {
        for (const auto& item : node_) {
            if (entryHasKey(item, key)) return entryValue(item.Scalar());
        }
        return std::nullopt;
    }
    if (node_ && node_.IsMap() && node_[key] && node_[key].IsScalar()) {
        return node_[key].as<std::string>();
    }
    return std::nullopt;
}

bool Environment::has(const std::string& key) const {
    if (node_ && node_.IsSequence()) {
        for (const auto& item : node_) {
            if (entryHasKey(item, key)) return true;
        }
        return false;
    }
    return node_ && node_.IsMap() && node_[key].IsDefined();
}

void Environment::remove(const std::string& key) {
    if (node_ && node_.IsSequence()) {
        YAML::Node kept(YAML::NodeType::Sequence);
        for (const auto& item : node_) {
            if (!entryHasKey(item, key)) kept.push_back(item);
        }
        node_ = kept;
        return;
    }
    if (node_ && node_.IsMap() && node_[key]) {
        node_.remove(key);
    }
}

std::unordered_map<std::string, std::string> Environment::getAll() const {
    std::unordered_map<std::string, std::string> result;
    if (node_ && node_.IsSequence()) {
        for (const auto& item : node_) {
            if (!item.IsScalar()) continue;
            if (auto value = entryValue(item.Scalar())) result[entryKey(item.Scalar())] = *value;
        }
    } else if (node_ && node_.IsMap()) {
        for (const auto& kv : node_) {
            if (kv.second.IsScalar()) result[kv.first.as<std::string>()] = kv.second.as<std::string>();
        }
    }
    return result;
}

} // namespace compose
