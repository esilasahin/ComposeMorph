#include <iostream>
#include <fstream>
#include <cassert>
#include "compose/ComposeFile.hpp"
#include "compose/Environment.hpp"
#include "compose/ExtraHosts.hpp"
#include "compose/Ports.hpp"
#include "compose/Volumes.hpp"
#include "compose/Networks.hpp"

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

    // Ports testleri
    web.ports().add("80:80");
    web.ports().add("443:443");
    assert(web.ports().has("80:80"));
    assert(web.ports().has("443:443"));

    // Volumes testleri
    web.volumes().add("/opt/custody/v1", "/usr/app/executable");
    web.volumes().add("./logs", "/var/log/nginx", "ro");
    assert(web.volumes().has("/opt/custody/v1:/usr/app/executable"));
    assert(web.volumes().has("./logs:/var/log/nginx:ro"));

    // setSource testi
    web.volumes().setSource("/usr/app/executable", "/opt/custody/v2");
    assert(web.volumes().has("/opt/custody/v2:/usr/app/executable"));
    assert(!web.volumes().has("/opt/custody/v1:/usr/app/executable"));

    // removeByTarget testi
    web.volumes().removeByTarget("/var/log/nginx");
    assert(!web.volumes().has("./logs:/var/log/nginx:ro"));

    // Networks testleri
    web.networks().add("frontend-net");
    web.networks().add("backend-net");
    assert(web.networks().has("frontend-net"));
    assert(web.networks().has("backend-net"));

    auto redis = compose.addService("redis");
    redis.setImage("redis:7-alpine");
    redis.ports().add("6379:6379");
    redis.networks().add("backend-net");

    compose.save("output.yml");

    // Kaydedilen dosyayı yeniden yükleyip doğrula
    compose::ComposeFile reloaded("output.yml");
    assert(reloaded.service("web").image() == "nginx:alpine");
    assert(reloaded.service("web").restart() == "always");
    assert(reloaded.service("web").environment().get("PORT").value() == "8080");
    assert(reloaded.service("web").extraHosts().get("hsm01").value() == "10.10.10.20");
    assert(reloaded.service("web").ports().has("80:80"));
    assert(reloaded.service("web").volumes().has("/opt/custody/v2:/usr/app/executable"));
    assert(reloaded.service("web").networks().has("frontend-net"));
    assert(reloaded.service("web").networks().has("backend-net"));
    assert(reloaded.service("redis").ports().has("6379:6379"));
    assert(reloaded.service("redis").networks().has("backend-net"));

    std::cout << "Networks ve tum testler basariyla gecti!" << std::endl;
    return 0;
}