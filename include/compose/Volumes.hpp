#pragma once
#include <yaml-cpp/yaml.h>
#include <string>
#include <vector>

namespace compose {

class Volumes {
public:
    explicit Volumes(YAML::Node serviceNode);

    // Düz string ekleme: "host:container:ro"
    void add(const std::string& volumeMapping);

    // Şartname Madde 7: 2 ve 3 parametreli add desteği
    void add(const std::string& source, const std::string& target, const std::string& mode = "");

    // Şartname Madde 7: Hedef yola göre silme
    void removeByTarget(const std::string& target);

    // Şartname Madde 7 & 30: Hedef yolun kaynağını değiştirme
    void setSource(const std::string& target, const std::string& newSource);

    void remove(const std::string& volumeMapping);
    bool has(const std::string& volumeMapping) const;
    void clear();

    std::vector<std::string> toVector() const;

private:
    YAML::Node serviceNode_;
};

}