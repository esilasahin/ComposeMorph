#include "compose/Volumes.hpp"
#include "ScalarQuoting.hpp"
#include <sstream>

namespace compose {
namespace {

// Kısa sözdizimli girdiyi ("kaynak:hedef[:mod]") parçalarına ayırır.
struct ShortSyntax {
    std::string source;
    std::string target;
    std::string mode;
};

ShortSyntax splitShort(const std::string& mapping) {
    std::stringstream ss(mapping);
    ShortSyntax parts;
    std::getline(ss, parts.source, ':');
    std::getline(ss, parts.target, ':');
    std::getline(ss, parts.mode, ':');
    return parts;
}

// Uzun sözdizimli girdi bir eşlemedir:
//   - type: bind
//     source: /host/path
//     target: /container/path
// Hedef yol her iki biçimde de bu işlevle okunur.
std::string volumeTarget(const YAML::Node& entry) {
    if (entry.IsScalar()) {
        return splitShort(entry.as<std::string>()).target;
    }
    if (entry.IsMap() && entry["target"] && entry["target"].IsScalar()) {
        return entry["target"].as<std::string>();
    }
    return {};
}

std::string volumeToString(const YAML::Node& entry) {
    if (entry.IsScalar()) {
        return entry.as<std::string>();
    }
    if (!entry.IsMap() || !entry["target"] || !entry["target"].IsScalar()) {
        return {};
    }
    std::string target = entry["target"].as<std::string>();
    if (entry["source"] && entry["source"].IsScalar()) {
        return entry["source"].as<std::string>() + ":" + target;
    }
    return target;
}

}  // namespace

Volumes::Volumes(YAML::Node serviceNode) : serviceNode_(serviceNode) {}

void Volumes::add(const std::string& volumeMapping) {
    if (!serviceNode_["volumes"]) {
        serviceNode_["volumes"] = YAML::Node(YAML::NodeType::Sequence);
    }

    if (!has(volumeMapping)) {
        serviceNode_["volumes"].push_back(detail::makeString(volumeMapping));
    }
}

void Volumes::add(const std::string& source, const std::string& target, const std::string& mode) {
    std::string mapping = source + ":" + target;
    if (!mode.empty()) {
        mapping += ":" + mode;
    }
    add(mapping);
}

void Volumes::removeByTarget(const std::string& target) {
    if (!serviceNode_["volumes"] || !serviceNode_["volumes"].IsSequence()) {
        return;
    }

    YAML::Node newVolumes(YAML::NodeType::Sequence);
    for (std::size_t i = 0; i < serviceNode_["volumes"].size(); ++i) {
        if (volumeTarget(serviceNode_["volumes"][i]) != target) {
            newVolumes.push_back(serviceNode_["volumes"][i]);
        }
    }
    serviceNode_["volumes"] = newVolumes;
}

void Volumes::setSource(const std::string& target, const std::string& newSource) {
    if (!serviceNode_["volumes"] || !serviceNode_["volumes"].IsSequence()) {
        return;
    }

    for (std::size_t i = 0; i < serviceNode_["volumes"].size(); ++i) {
        YAML::Node entry = serviceNode_["volumes"][i];
        if (volumeTarget(entry) != target) {
            continue;
        }

        if (entry.IsMap()) {
            // Uzun sözdizimi: yalnızca source alanı yerinde güncellenir.
            detail::assignString(entry["source"], newSource);
        } else {
            ShortSyntax parts = splitShort(entry.as<std::string>());
            std::string updated = newSource + ":" + parts.target;
            if (!parts.mode.empty()) {
                updated += ":" + parts.mode;
            }
            detail::assignString(entry, updated);
        }
        return;
    }

    // Eğer hedef henüz yoksa yeni ekle
    add(newSource, target);
}

void Volumes::remove(const std::string& volumeMapping) {
    if (!serviceNode_["volumes"] || !serviceNode_["volumes"].IsSequence()) {
        return;
    }

    YAML::Node newVolumes(YAML::NodeType::Sequence);
    for (std::size_t i = 0; i < serviceNode_["volumes"].size(); ++i) {
        if (volumeToString(serviceNode_["volumes"][i]) != volumeMapping) {
            newVolumes.push_back(serviceNode_["volumes"][i]);
        }
    }
    serviceNode_["volumes"] = newVolumes;
}

bool Volumes::has(const std::string& volumeMapping) const {
    if (!serviceNode_["volumes"] || !serviceNode_["volumes"].IsSequence()) {
        return false;
    }

    for (std::size_t i = 0; i < serviceNode_["volumes"].size(); ++i) {
        if (volumeToString(serviceNode_["volumes"][i]) == volumeMapping) {
            return true;
        }
    }
    return false;
}

void Volumes::clear() {
    if (serviceNode_["volumes"]) {
        serviceNode_.remove("volumes");
    }
}

std::vector<std::string> Volumes::toVector() const {
    std::vector<std::string> result;
    if (serviceNode_["volumes"] && serviceNode_["volumes"].IsSequence()) {
        for (std::size_t i = 0; i < serviceNode_["volumes"].size(); ++i) {
            std::string text = volumeToString(serviceNode_["volumes"][i]);
            if (!text.empty()) {
                result.push_back(text);
            }
        }
    }
    return result;
}

}
