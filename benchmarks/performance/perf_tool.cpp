// Experiment 7 (Performance Benchmark) instrument: measures Load/Modify/
// Save/Total wall time for repeated in-process iterations against a single
// file, and the process's peak resident set size (Linux /proc/self/status
// VmHWM) after all iterations. Repeated in-process (rather than spawning a
// fresh process per measurement, as the other benchmarks/ tools do) so
// process-launch overhead doesn't dominate the small/medium-file numbers.
#include "compose/ComposeFile.hpp"
#include <chrono>
#include <cstdio>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

namespace {
using Clock = std::chrono::steady_clock;

double msSince(Clock::time_point a, Clock::time_point b) {
    return std::chrono::duration<double, std::milli>(b - a).count();
}

// Same op vocabulary as benchmarks/modification/modify_tool.cpp.
void applyOp(compose::ComposeFile& file, const std::string& op, const std::vector<std::string>& args) {
    if (op == "noop") return;
    auto svc = file.service(args.at(0));
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

long peakRssKb() {
    std::ifstream status("/proc/self/status");
    std::string line;
    while (std::getline(status, line)) {
        if (line.rfind("VmHWM:", 0) == 0) {
            long kb = -1;
            std::sscanf(line.c_str(), "VmHWM: %ld kB", &kb);
            return kb;
        }
    }
    return -1;
}
}

int main(int argc, char** argv) {
    if (argc < 5) {
        std::cerr << "Usage: perf_tool <input.yml> <iterations> <op> <service> [args...]" << std::endl;
        return 2;
    }
    const std::string input = argv[1];
    const int iterations = std::stoi(argv[2]);
    const std::string op = argv[3];
    std::vector<std::string> args;
    for (int i = 4; i < argc; ++i) args.emplace_back(argv[i]);

    const std::string tmpOut = input + ".perf-tmp.yml";

    std::cout << "iteration,load_ms,modify_ms,save_ms,total_ms" << std::endl;
    for (int i = 0; i < iterations; ++i) {
        auto t0 = Clock::now();
        compose::ComposeFile file;
        try {
            file.load(input);
        } catch (const std::exception& e) {
            std::cerr << "LOAD_FAILED: " << e.what() << std::endl;
            return 10;
        }
        auto t1 = Clock::now();
        try {
            applyOp(file, op, args);
        } catch (const std::exception& e) {
            std::cerr << "APPLY_FAILED: " << e.what() << std::endl;
            return 11;
        }
        auto t2 = Clock::now();
        try {
            file.save(tmpOut);
        } catch (const std::exception& e) {
            std::cerr << "SAVE_FAILED: " << e.what() << std::endl;
            return 12;
        }
        auto t3 = Clock::now();
        std::cout << i << "," << msSince(t0, t1) << "," << msSince(t1, t2) << ","
                  << msSince(t2, t3) << "," << msSince(t0, t3) << std::endl;
    }

    std::remove(tmpOut.c_str());
    std::cerr << "PEAK_RSS_KB=" << peakRssKb() << std::endl;
    return 0;
}
