// Experiment 6 (Comparative Benchmark) baseline: a *correctly written*
// direct yaml-cpp usage of the same single-property edits ComposeMorph's
// benchmarks/modification/modify_tool.cpp performs, but without any of
// ComposeMorph's typed Service/Environment/... classes -- just raw
// YAML::Node indexing, mutating only the target leaf/sequence in place,
// including the short (list) syntax of environment and extra_hosts.
//
// It serializes with yaml-cpp's default emitter, so it also stands in for
// ComposeMorph before the quote-preserving serializer (src/ScalarQuoting.cpp)
// in Experiment 5 and the quoted-scalar analysis: before that change,
// ComposeMorph's round-trip output was byte-identical to this tool's noop
// output (Experiment 6, results/pre-fix/tables/comparison_summary.md: 100/100
// files), and its image edit follows the same Node write. Contrast with
// yamlcpp_naive_tool.cpp, which implements the same edits the way an
// unguided caller plausibly would, and loses data.
#include <yaml-cpp/yaml.h>
#include <fstream>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

namespace {
constexpr int kExitUsage = 2;
constexpr int kExitLoadFailed = 10;
constexpr int kExitApplyFailed = 11;
constexpr int kExitSaveFailed = 12;

YAML::Node getService(YAML::Node root, const std::string& name) {
    if (!root["services"] || !root["services"][name]) {
        throw std::runtime_error("Service not found: " + name);
    }
    return root["services"][name];
}

bool sequenceHas(YAML::Node seq, const std::string& value) {
    if (!seq || !seq.IsSequence()) return false;
    for (std::size_t i = 0; i < seq.size(); ++i) {
        if (seq[i].as<std::string>() == value) return true;
    }
    return false;
}

void applyOp(YAML::Node root, const std::string& op, const std::vector<std::string>& args) {
    const std::string& serviceName = args.at(0);
    YAML::Node svc = getService(root, serviceName);

    if (op == "noop") {
        // Identity round-trip baseline: intentionally do nothing.
    } else if (op == "image") {
        svc["image"] = args.at(1);
    } else if (op == "hostname") {
        svc["hostname"] = args.at(1);
    } else if (op == "restart") {
        svc["restart"] = args.at(1);
    } else if (op == "env") {
        const std::string& key = args.at(1);
        YAML::Node env = svc["environment"];
        if (env && env.IsSequence()) {
            const std::string entry = key + "=" + args.at(2);
            bool found = false;
            for (std::size_t i = 0; i < env.size(); ++i) {
                const std::string current = env[i].as<std::string>();
                if (current.substr(0, current.find('=')) == key) {
                    env[i] = entry;
                    found = true;
                    break;
                }
            }
            if (!found) env.push_back(entry);
        } else {
            if (!env) svc["environment"] = YAML::Node(YAML::NodeType::Map);
            svc["environment"][key] = args.at(2);
        }
    } else if (op == "port") {
        if (!svc["ports"]) svc["ports"] = YAML::Node(YAML::NodeType::Sequence);
        if (!sequenceHas(svc["ports"], args.at(1))) svc["ports"].push_back(args.at(1));
    } else if (op == "volume-source") {
        const std::string& target = args.at(1);
        const std::string& newSource = args.at(2);
        bool found = false;
        if (svc["volumes"] && svc["volumes"].IsSequence()) {
            for (std::size_t i = 0; i < svc["volumes"].size(); ++i) {
                std::string current = svc["volumes"][i].as<std::string>();
                std::stringstream ss(current);
                std::string src, tgt, mode;
                std::getline(ss, src, ':');
                std::getline(ss, tgt, ':');
                std::getline(ss, mode, ':');
                if (tgt == target) {
                    std::string updated = newSource + ":" + tgt;
                    if (!mode.empty()) updated += ":" + mode;
                    svc["volumes"][i] = updated;
                    found = true;
                    break;
                }
            }
        }
        if (!found) {
            if (!svc["volumes"]) svc["volumes"] = YAML::Node(YAML::NodeType::Sequence);
            svc["volumes"].push_back(newSource + ":" + target);
        }
    } else if (op == "extra-host") {
        const std::string& host = args.at(1);
        YAML::Node hosts = svc["extra_hosts"];
        if (hosts && hosts.IsSequence()) {
            bool found = false;
            char sep = '=';
            for (std::size_t i = 0; i < hosts.size(); ++i) {
                const std::string current = hosts[i].as<std::string>();
                const auto eq = current.find('=');
                const auto pos = eq != std::string::npos ? eq : current.find(':');
                if (pos == std::string::npos) continue;
                if (i == 0) sep = current[pos];
                if (current.substr(0, pos) == host) {
                    hosts[i] = host + current[pos] + args.at(2);
                    found = true;
                    break;
                }
            }
            if (!found) hosts.push_back(host + sep + args.at(2));
        } else {
            if (!hosts) svc["extra_hosts"] = YAML::Node(YAML::NodeType::Map);
            svc["extra_hosts"][host] = args.at(2);
        }
    } else if (op == "network") {
        if (!svc["networks"]) svc["networks"] = YAML::Node(YAML::NodeType::Sequence);
        if (!sequenceHas(svc["networks"], args.at(1))) svc["networks"].push_back(args.at(1));
    } else if (op == "healthcheck-retries") {
        if (!svc["healthcheck"]) svc["healthcheck"] = YAML::Node(YAML::NodeType::Map);
        svc["healthcheck"]["retries"] = std::stoi(args.at(1));
    } else if (op == "deploy-cpus") {
        if (!svc["deploy"]) svc["deploy"] = YAML::Node(YAML::NodeType::Map);
        if (!svc["deploy"]["resources"]) svc["deploy"]["resources"] = YAML::Node(YAML::NodeType::Map);
        if (!svc["deploy"]["resources"]["limits"]) svc["deploy"]["resources"]["limits"] = YAML::Node(YAML::NodeType::Map);
        svc["deploy"]["resources"]["limits"]["cpus"] = args.at(1);
    } else {
        throw std::runtime_error("Unknown op: " + op);
    }
}
}

int main(int argc, char** argv) {
    if (argc < 5) {
        std::cerr << "Usage: yamlcpp_careful_tool <input.yml> <output.yml> <op> <service> [args...]" << std::endl;
        return kExitUsage;
    }
    const std::string input = argv[1];
    const std::string output = argv[2];
    const std::string op = argv[3];
    std::vector<std::string> args;
    for (int i = 4; i < argc; ++i) args.emplace_back(argv[i]);

    YAML::Node root;
    try {
        root = YAML::LoadFile(input);
    } catch (const std::exception& e) {
        std::cerr << "LOAD_FAILED: " << e.what() << std::endl;
        return kExitLoadFailed;
    }

    try {
        applyOp(root, op, args);
    } catch (const std::exception& e) {
        std::cerr << "APPLY_FAILED: " << e.what() << std::endl;
        return kExitApplyFailed;
    }

    // Deliberately NOT atomic (no temp file + rename) -- this is what most
    // direct yaml-cpp usage looks like; contrast with ComposeMorph's
    // SaveOptions::atomic (see src/ComposeFile.cpp).
    try {
        std::ofstream fout(output);
        if (!fout.is_open()) throw std::runtime_error("cannot open output file: " + output);
        fout << root << std::endl;
    } catch (const std::exception& e) {
        std::cerr << "SAVE_FAILED: " << e.what() << std::endl;
        return kExitSaveFailed;
    }

    std::cout << "OK" << std::endl;
    return 0;
}
