#include <iostream>
#include <fstream>
#include <cassert>
#include "compose/ComposeFile.hpp"
#include "compose/Environment.hpp"
#include "compose/ExtraHosts.hpp"

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

    // Environment testleri
    web.environment().set("PORT", "8080");
    web.environment().set("APP_ENV", "production");
    assert(web.environment().has("PORT"));
    assert(web.environment().get("PORT").value() == "8080");

    // ExtraHosts testleri
    web.extraHosts().set("hsm01", "10.10.10.20");
    web.extraHosts().set("db-host", "192.168.1.50");
    assert(web.extraHosts().has("hsm01"));
    assert(web.extraHosts().get("hsm01").value() == "10.10.10.20");

    auto redis = compose.addService("redis");
    redis.setImage("redis:7-alpine");

    compose.save("output.yml");

    // Kaydedilen dosyayı yeniden yükleyip doğrula
    compose::ComposeFile reloaded("output.yml");
    assert(reloaded.service("web").image() == "nginx:alpine");
    assert(reloaded.service("web").restart() == "always");
    assert(reloaded.service("web").environment().get("PORT").value() == "8080");
    assert(reloaded.service("web").extraHosts().get("hsm01").value() == "10.10.10.20");
    assert(reloaded.service("redis").image() == "redis:7-alpine");

    std::cout << "Tum temel, Environment ve ExtraHosts testleri basariyla gecti!" << std::endl;
    return 0;
}