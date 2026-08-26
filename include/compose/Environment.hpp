#pragma once

#include <string>
#include <unordered_map>
#include <optional>
#include <yaml-cpp/yaml.h>

namespace compose {

class Environment {
public:
    explicit Environment(YAML::Node node);

    void set(const std::string& key, const std::string& value);
    std::optional<std::string> get(const std::string& key) const;
    bool has(const std::string& key) const;
    void remove(const std::string& key);
    std::unordered_map<std::string, std::string> getAll() const;

private:
    YAML::Node node_;
};

} // namespace compose