// Experiment 6 (Comparative Benchmark) baseline: a *plausible but
// destructive* direct yaml-cpp usage pattern -- building a fresh node
// with just the field(s) the caller cares about and assigning it over the
// existing subtree, instead of mutating the existing node in place. This
// is a common real-world mistake (it "looks right" and compiles fine)
// that silently discards every sibling field.
//
// Only `image`, `hostname`, and `env` are modelled (the most common
// single-field edits); other ops report NOT_IMPLEMENTED rather than
// guessing at a plausible mistake for every op.
#include <yaml-cpp/yaml.h>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

namespace {
constexpr int kExitUsage = 2;
constexpr int kExitLoadFailed = 10;
constexpr int kExitApplyFailed = 11;
constexpr int kExitSaveFailed = 12;
constexpr int kExitNotImplemented = 21;

void applyOp(YAML::Node root, const std::string& op, const std::vector<std::string>& args) {
    const std::string& serviceName = args.at(0);
    if (!root["services"] || !root["services"][serviceName]) {
        throw std::runtime_error("Service not found: " + serviceName);
    }

    if (op == "noop") {
        // Identity round-trip baseline: intentionally do nothing.
    } else if (op == "image") {
        // Destructive: replaces the ENTIRE service definition, losing
        // hostname/ports/environment/etc. that were already there.
        YAML::Node newService;
        newService["image"] = args.at(1);
        root["services"][serviceName] = newService;
    } else if (op == "hostname") {
        YAML::Node newService;
        newService["hostname"] = args.at(1);
        root["services"][serviceName] = newService;
    } else if (op == "env") {
        // Narrower mistake: only the environment section is rebuilt from
        // scratch, so other service fields survive but sibling env vars
        // do not.
        YAML::Node newEnv;
        newEnv[args.at(1)] = args.at(2);
        root["services"][serviceName]["environment"] = newEnv;
    } else {
        throw std::domain_error("NOT_IMPLEMENTED: naive baseline does not model op '" + op + "'");
    }
}
}

int main(int argc, char** argv) {
    if (argc < 5) {
        std::cerr << "Usage: yamlcpp_naive_tool <input.yml> <output.yml> <op> <service> [args...]" << std::endl;
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
    } catch (const std::domain_error& e) {
        std::cerr << e.what() << std::endl;
        return kExitNotImplemented;
    } catch (const std::exception& e) {
        std::cerr << "APPLY_FAILED: " << e.what() << std::endl;
        return kExitApplyFailed;
    }

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
