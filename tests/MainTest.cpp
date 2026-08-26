#include <iostream>
#include <fstream>
#include <cassert>
#include "compose/ComposeFile.hpp"

int main() {
    std::ofstream sample("sample.yml");
    sample << "services:\n"
           << "  web:\n"
           << "    image: nginx:1.14\n"
           << "    hostname: web01\n";
    sample.close();

    compose::ComposeFile compose("sample.yml");
    assert(compose.hasService("web"));

    auto web = compose.service("web");
    web.setImage("nginx:alpine");
    web.setRestart("always");

    auto redis = compose.addService("redis");
    redis.setImage("redis:7-alpine");

    compose.save("output.yml");

    compose::ComposeFile reloaded("output.yml");
    assert(reloaded.service("web").image() == "nginx:alpine");
    assert(reloaded.service("web").restart() == "always");
    assert(reloaded.service("redis").image() == "redis:7-alpine");

    std::cout << "Tum temel testler basariyla gecti!" << std::endl;
    return 0;
}