#pragma once

#include <string>
#include <unordered_map>
#include <optional>
#include <yaml-cpp/yaml.h>

namespace compose {

class ExtraHosts {
public:
    explicit ExtraHosts(YAML::Node node);

    // Host ve IP ekle / güncelle
    void set(const std::string& host, const std::string& ip);

    // IP bilgisini getir
    std::optional<std::string> get(const std::string& host) const;

    // Host tanımlı mı kontrol et
    bool has(const std::string& host) const;

    // Host sil
    void remove(const std::string& host);

    // Tüm host-ip ikililerini getir
    std::unordered_map<std::string, std::string> getAll() const;

private:
    YAML::Node node_;
};

} // namespace compose