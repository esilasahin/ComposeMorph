// Identity round-trip harness for Experiment 1 (RQ1 / RQ2).
// Loads a Compose file, saves it back with no modification, then reloads
// the saved output to confirm it is itself parseable. Distinct exit codes
// let the benchmark driver attribute a failure to the right stage.
#include "compose/ComposeFile.hpp"
#include <iostream>

namespace {
constexpr int kExitOk = 0;
constexpr int kExitUsage = 2;
constexpr int kExitLoadFailed = 10;
constexpr int kExitSaveFailed = 11;
constexpr int kExitReparseFailed = 12;
}

int main(int argc, char** argv) {
    if (argc != 3) {
        std::cerr << "Usage: roundtrip_tool <input.yml> <output.yml>" << std::endl;
        return kExitUsage;
    }

    const std::string input = argv[1];
    const std::string output = argv[2];

    compose::ComposeFile file;
    try {
        file.load(input);
    } catch (const std::exception& e) {
        std::cerr << "LOAD_FAILED: " << e.what() << std::endl;
        return kExitLoadFailed;
    }

    try {
        file.save(output);
    } catch (const std::exception& e) {
        std::cerr << "SAVE_FAILED: " << e.what() << std::endl;
        return kExitSaveFailed;
    }

    compose::ComposeFile reloaded;
    try {
        reloaded.load(output);
    } catch (const std::exception& e) {
        std::cerr << "REPARSE_FAILED: " << e.what() << std::endl;
        return kExitReparseFailed;
    }

    std::cout << "OK" << std::endl;
    return kExitOk;
}
