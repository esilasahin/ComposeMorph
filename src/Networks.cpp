#include "compose/Networks.hpp"
#include "ScalarQuoting.hpp"

namespace compose {

Networks::Networks(YAML::Node serviceNode) : serviceNode_(serviceNode) {}

// Servis düzeyindeki networks alanı iki biçimde yazılabilir:
//   networks: [frontend, backend]            (kısa sözdizimi, dizi)
//   networks:                                 (uzun sözdizimi, eşleme)
//     frontend:
//       aliases: [api]
// Her iki biçim de yerinde korunur: eşleme biçimindeki bir dosyaya ağ
// eklenirken dosya diziye çevrilmez, eşlemeye boş değerli anahtar eklenir.
void Networks::add(const std::string& networkName) {
    if (!serviceNode_["networks"]) {
        serviceNode_["networks"] = YAML::Node(YAML::NodeType::Sequence);
    }

    if (has(networkName)) {
        return;
    }

    if (serviceNode_["networks"].IsMap()) {
        serviceNode_["networks"][networkName] = YAML::Node(YAML::NodeType::Null);
    } else {
        serviceNode_["networks"].push_back(detail::makeString(networkName));
    }
}

void Networks::remove(const std::string& networkName) {
    if (!serviceNode_["networks"]) {
        return;
    }

    if (serviceNode_["networks"].IsMap()) {
        serviceNode_["networks"].remove(networkName);
        return;
    }
    if (!serviceNode_["networks"].IsSequence()) {
        return;
    }

    YAML::Node newNetworks(YAML::NodeType::Sequence);
    for (std::size_t i = 0; i < serviceNode_["networks"].size(); ++i) {
        const YAML::Node entry = serviceNode_["networks"][i];
        if (!entry.IsScalar() || entry.as<std::string>() != networkName) {
            newNetworks.push_back(entry);
        }
    }
    serviceNode_["networks"] = newNetworks;
}

bool Networks::has(const std::string& networkName) const {
    if (!serviceNode_["networks"]) {
        return false;
    }

    if (serviceNode_["networks"].IsMap()) {
        return static_cast<bool>(serviceNode_["networks"][networkName]);
    }
    if (!serviceNode_["networks"].IsSequence()) {
        return false;
    }

    for (std::size_t i = 0; i < serviceNode_["networks"].size(); ++i) {
        const YAML::Node entry = serviceNode_["networks"][i];
        if (entry.IsScalar() && entry.as<std::string>() == networkName) {
            return true;
        }
    }
    return false;
}

void Networks::clear() {
    if (serviceNode_["networks"]) {
        serviceNode_.remove("networks");
    }
}

std::vector<std::string> Networks::toVector() const {
    std::vector<std::string> result;
    if (!serviceNode_["networks"]) {
        return result;
    }

    if (serviceNode_["networks"].IsMap()) {
        for (const auto& kv : serviceNode_["networks"]) {
            result.push_back(kv.first.as<std::string>());
        }
    } else if (serviceNode_["networks"].IsSequence()) {
        for (std::size_t i = 0; i < serviceNode_["networks"].size(); ++i) {
            const YAML::Node entry = serviceNode_["networks"][i];
            if (entry.IsScalar()) {
                result.push_back(entry.as<std::string>());
            }
        }
    }
    return result;
}

}
