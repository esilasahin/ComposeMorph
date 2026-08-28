#pragma once

#include <string>
#include <vector>
#include <yaml-cpp/yaml.h>
#include "compose/Service.hpp"
#include "compose/TopLevelCollections.hpp"
#include "compose/Exceptions.hpp"

namespace compose {

struct SaveOptions {
    bool backup = false;
    bool atomic = true;
};

class ComposeFile {
public:
    ComposeFile();
    explicit ComposeFile(const std::string& filepath);

    void load(const std::string& filepath);
    void save();
    void save(const std::string& filepath);
    void save(const SaveOptions& options);
    void save(const std::string& filepath, const SaveOptions& options);

    // Validation (Madde 19)
    void validate() const;

    Service service(const std::string& name);
    bool hasService(const std::string& name) const;
    Service addService(const std::string& name);
    void removeService(const std::string& name);
    std::vector<std::string> serviceNames() const;

    // Top-Level Koleksiyonlar
    NetworkCollection networks();
    VolumeCollection volumes();
    SecretCollection secrets();
    ConfigCollection configs();

private:
    std::string filepath_;
    YAML::Node rootNode_;

    void validateService(const std::string& name, const YAML::Node& node) const;
};

} // namespace compose