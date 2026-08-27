#pragma once
#include <yaml-cpp/yaml.h>
#include <string>
#include <vector>

namespace compose {

// Top-Level Network Tanımı
class NetworkDefinition {
public:
    explicit NetworkDefinition(YAML::Node node);

    void setExternal(bool external);
    bool external() const;

    void setDriver(const std::string& driver);
    std::string driver() const;

private:
    YAML::Node node_;
};

class NetworkCollection {
public:
    explicit NetworkCollection(YAML::Node rootNode);

    NetworkDefinition add(const std::string& name);
    NetworkDefinition get(const std::string& name);
    void remove(const std::string& name);
    bool has(const std::string& name) const;
    std::vector<std::string> names() const;

private:
    YAML::Node rootNode_;
};

// Top-Level Volume Tanımı
class VolumeDefinition {
public:
    explicit VolumeDefinition(YAML::Node node);

    void setExternal(bool external);
    bool external() const;

    void setDriver(const std::string& driver);
    std::string driver() const;

private:
    YAML::Node node_;
};

class VolumeCollection {
public:
    explicit VolumeCollection(YAML::Node rootNode);

    VolumeDefinition add(const std::string& name);
    VolumeDefinition get(const std::string& name);
    void remove(const std::string& name);
    bool has(const std::string& name) const;
    std::vector<std::string> names() const;

private:
    YAML::Node rootNode_;
};

// Top-Level Secret / Config Tanımı
class FileConfigDefinition {
public:
    explicit FileConfigDefinition(YAML::Node node);

    void setFile(const std::string& filePath);
    std::string file() const;

    void setExternal(bool external);
    bool external() const;

private:
    YAML::Node node_;
};

class SecretCollection {
public:
    explicit SecretCollection(YAML::Node rootNode);

    FileConfigDefinition add(const std::string& name);
    FileConfigDefinition get(const std::string& name);
    void remove(const std::string& name);
    bool has(const std::string& name) const;

private:
    YAML::Node rootNode_;
};

class ConfigCollection {
public:
    explicit ConfigCollection(YAML::Node rootNode);

    FileConfigDefinition add(const std::string& name);
    FileConfigDefinition get(const std::string& name);
    void remove(const std::string& name);
    bool has(const std::string& name) const;

private:
    YAML::Node rootNode_;
};

}