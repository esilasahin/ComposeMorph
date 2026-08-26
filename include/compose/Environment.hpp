#pragma once

#include <string>
#include <unordered_map>
#include <optional>
#include <yaml-cpp/yaml.h>

namespace compose {

class Environment {
public:
    explicit Environment(YAML::Node node);

    // Değişken ekle veya güncelle
    void set(const std::string& key, const std::string& value);

    // Değişken oku (varsa değeri döner, yoksa std::nullopt)
    std::optional<std::string> get(const std::string& key) const;

    // Değişken var mı kontrol et
    bool has(const std::string& key) const;

    // Değişkeni sil
    void remove(const std::string& key);

    // Tüm değişkenleri map olarak getir
    std::unordered_map<std::string, std::string> getAll() const;

private:
    YAML::Node m_node;
};

} // namespace compose