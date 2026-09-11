#include "compose/ExtraHosts.hpp"
#include "ScalarQuoting.hpp"

namespace compose {

namespace {
// Short (list) syntax entries are "HOST=IP" or the older "HOST:IP". An IPv6
// address may contain ':', so '=' wins when present and otherwise only the
// first ':' separates host from address.
std::size_t separatorPos(const std::string& entry) {
    const auto eq = entry.find('=');
    return eq != std::string::npos ? eq : entry.find(':');
}

std::string entryHost(const std::string& entry) {
    return entry.substr(0, separatorPos(entry));
}

std::optional<std::string> entryAddress(const std::string& entry) {
    const auto sep = separatorPos(entry);
    if (sep == std::string::npos) return std::nullopt;
    return entry.substr(sep + 1);
}

bool entryHasHost(const YAML::Node& item, const std::string& host) {
    return item.IsScalar() && entryHost(item.Scalar()) == host;
}

char separatorFor(const YAML::Node& seq) {
    for (const auto& item : seq) {
        if (!item.IsScalar()) continue;
        const auto sep = separatorPos(item.Scalar());
        if (sep != std::string::npos) return item.Scalar()[sep];
    }
    return '=';
}
}

ExtraHosts::ExtraHosts(YAML::Node node) : node_(node) {}

void ExtraHosts::set(const std::string& host, const std::string& ip) {
    if (node_ && node_.IsSequence()) {
        for (std::size_t i = 0; i < node_.size(); ++i) {
            if (entryHasHost(node_[i], host)) {
                const std::string current = node_[i].Scalar();
                detail::assignString(node_[i], host + current[separatorPos(current)] + ip);
                return;
            }
        }
        node_.push_back(detail::makeString(host + separatorFor(node_) + ip));
        return;
    }
    if (!node_) {
        node_ = YAML::Node(YAML::NodeType::Map);
    }
    detail::assignString(node_[host], ip);
}

std::optional<std::string> ExtraHosts::get(const std::string& host) const {
    if (node_ && node_.IsSequence()) {
        for (const auto& item : node_) {
            if (entryHasHost(item, host)) return entryAddress(item.Scalar());
        }
        return std::nullopt;
    }
    if (node_ && node_.IsMap() && node_[host] && node_[host].IsScalar()) {
        return node_[host].as<std::string>();
    }
    return std::nullopt;
}

bool ExtraHosts::has(const std::string& host) const {
    if (node_ && node_.IsSequence()) {
        for (const auto& item : node_) {
            if (entryHasHost(item, host)) return true;
        }
        return false;
    }
    return node_ && node_.IsMap() && node_[host].IsDefined();
}

void ExtraHosts::remove(const std::string& host) {
    if (node_ && node_.IsSequence()) {
        YAML::Node kept(YAML::NodeType::Sequence);
        for (const auto& item : node_) {
            if (!entryHasHost(item, host)) kept.push_back(item);
        }
        node_ = kept;
        return;
    }
    if (node_ && node_.IsMap() && node_[host]) {
        node_.remove(host);
    }
}

std::unordered_map<std::string, std::string> ExtraHosts::getAll() const {
    std::unordered_map<std::string, std::string> result;
    if (node_ && node_.IsSequence()) {
        for (const auto& item : node_) {
            if (!item.IsScalar()) continue;
            if (auto address = entryAddress(item.Scalar())) result[entryHost(item.Scalar())] = *address;
        }
    } else if (node_ && node_.IsMap()) {
        for (const auto& kv : node_) {
            if (kv.second.IsScalar()) result[kv.first.as<std::string>()] = kv.second.as<std::string>();
        }
    }
    return result;
}

} // namespace compose
