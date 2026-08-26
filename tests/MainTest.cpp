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

    // Environment testleri
    web.environment().set("PORT", "8080");
    web.environment().set("APP_ENV", "production");
    assert(web.environment().has("PORT"));
    assert(web.environment().get("PORT").value() == "8080");

    auto redis = compose.addService("redis");
    redis.setImage("redis:7-alpine");

    compose.save("output.yml");

    // Kaydedilen dosyayı yeniden yükleyip Environment'ı da doğrula
    compose::ComposeFile reloaded("output.yml");
    assert(reloaded.service("web").image() == "nginx:alpine");
    assert(reloaded.service("web").restart() == "always");
    assert(reloaded.service("web").environment().get("PORT").value() == "8080");
    assert(reloaded.service("web").environment().get("APP_ENV").value() == "production");
    assert(reloaded.service("redis").image() == "redis:7-alpine");

    std::cout << "Tum temel testler ve Environment testleri basariyla gecti!" << std::endl;
    return 0;
}