// Targeted single-property modification harness for Experiment 2 (RQ3 --
// Change Locality). Loads a Compose file, applies exactly one property
// change through the typed API, and saves. The Python driver diffs
// input vs. output to measure how much of the file changed beyond the
// targeted property.
#include "compose/ComposeFile.hpp"
#include <iostream>
#include <string>
#include <vector>

namespace {
constexpr int kExitUsage = 2;
constexpr int kExitLoadFailed = 10;
constexpr int kExitApplyFailed = 11;
constexpr int kExitSaveFailed = 12;

void applyOp(compose::ComposeFile& file, const std::string& op,
             const std::vector<std::string>& args) {
    const std::string& serviceName = args.at(0);
    auto svc = file.service(serviceName);

    if (op == "image") {
        svc.setImage(args.at(1));
    } else if (op == "hostname") {
        svc.setHostname(args.at(1));
    } else if (op == "restart") {
        svc.setRestart(args.at(1));
    } else if (op == "env") {
        svc.environment().set(args.at(1), args.at(2));
    } else if (op == "port") {
        svc.ports().add(args.at(1));
    } else if (op == "volume-source") {
        svc.volumes().setSource(args.at(1), args.at(2));
    } else if (op == "extra-host") {
        svc.extraHosts().set(args.at(1), args.at(2));
    } else if (op == "network") {
        svc.networks().add(args.at(1));
    } else if (op == "healthcheck-retries") {
        svc.healthcheck().setRetries(std::stoi(args.at(1)));
    } else if (op == "deploy-cpus") {
        svc.deploy().resources().limits().setCpus(args.at(1));
    } else {
        throw compose::ComposeException("Unknown op: " + op);
    }
}
}

int main(int argc, char** argv) {
    if (argc < 5) {
        std::cerr << "Usage: modify_tool <input.yml> <output.yml> <op> <service> [args...]" << std::endl;
        return kExitUsage;
    }

    const std::string input = argv[1];
    const std::string output = argv[2];
    const std::string op = argv[3];
    std::vector<std::string> args;
    for (int i = 4; i < argc; ++i) args.emplace_back(argv[i]);

    compose::ComposeFile file;
    try {
        file.load(input);
    } catch (const std::exception& e) {
        std::cerr << "LOAD_FAILED: " << e.what() << std::endl;
        return kExitLoadFailed;
    }

    try {
        applyOp(file, op, args);
    } catch (const std::exception& e) {
        std::cerr << "APPLY_FAILED: " << e.what() << std::endl;
        return kExitApplyFailed;
    }

    try {
        file.save(output);
    } catch (const std::exception& e) {
        std::cerr << "SAVE_FAILED: " << e.what() << std::endl;
        return kExitSaveFailed;
    }

    std::cout << "OK" << std::endl;
    return 0;
}
