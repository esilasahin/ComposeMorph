#include <iostream>
#include <fstream>
#include <cassert>
#include "compose/ComposeFile.hpp"
#include "compose/Environment.hpp"
#include "compose/ExtraHosts.hpp"
#include "compose/Ports.hpp"
#include "compose/Volumes.hpp"
#include "compose/Networks.hpp"
#include "compose/BuildConfig.hpp"
#include "compose/HealthCheck.hpp"
#include "compose/DependsOn.hpp"
#include "compose/DeployConfig.hpp"
#include "compose/TopLevelCollections.hpp"

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
    web.volumes().setSource("/usr/app/executable", "/opt/custody/v2");
    web.volumes().removeByTarget("/var/log/nginx");

    // Networks testleri
    web.networks().add("frontend-net");
    web.networks().add("backend-net");

    // BuildConfig testleri
    auto app = compose.addService("app");
    app.build().setContext(".");
    app.build().setDockerfile("Dockerfile.prod");
    app.build().setTarget("builder");
    app.build().args().set("VERSION", "0.17.0");

    // HealthCheck testleri
    app.healthcheck().setCommand({"CMD", "curl", "-f", "http://localhost:8080/health"});
    app.healthcheck().setInterval("30s");
    app.healthcheck().setTimeout("10s");
    app.healthcheck().setRetries(3);
    app.healthcheck().setStartPeriod("20s");

    // DeployConfig testleri
    app.deploy().setReplicas(3);
    app.deploy().setMode("replicated");
    app.deploy().resources().limits().setCpus("2.0");
    app.deploy().resources().limits().setMemory("2G");
    app.deploy().resources().reservations().setMemory("512M");

    auto redis = compose.addService("redis");
    redis.setImage("redis:7-alpine");
    redis.ports().add("6379:6379");
    redis.networks().add("backend-net");

    // DependsOn testleri
    web.dependsOn().add("redis");
    web.dependsOn().add("app", compose::DependCondition::ServiceHealthy);

    // Top-Level Koleksiyon Testleri (Networks, Volumes, Secrets, Configs)
    auto net = compose.networks().add("frontend-net");
    net.setExternal(true);
    assert(compose.networks().has("frontend-net"));
    assert(compose.networks().get("frontend-net").external() == true);

    auto vol = compose.volumes().add("crypto-data");
    vol.setDriver("local");
    assert(compose.volumes().has("crypto-data"));
    assert(compose.volumes().get("crypto-data").driver() == "local");

    compose.secrets().add("tls_cert").setFile("./certs/server.crt");
    assert(compose.secrets().has("tls_cert"));
    assert(compose.secrets().get("tls_cert").file() == "./certs/server.crt");

    compose.configs().add("nginx_cfg").setFile("./nginx.conf");
    assert(compose.configs().has("nginx_cfg"));
    assert(compose.configs().get("nginx_cfg").file() == "./nginx.conf");

    compose.save("output.yml");

    // Kaydedilen dosyayı yeniden yükleyip doğrula
    compose::ComposeFile reloaded("output.yml");
    assert(reloaded.service("web").image() == "nginx:alpine");
    assert(reloaded.service("app").deploy().replicas() == 3);
    assert(reloaded.networks().get("frontend-net").external() == true);
    assert(reloaded.volumes().get("crypto-data").driver() == "local");
    assert(reloaded.secrets().get("tls_cert").file() == "./certs/server.crt");
    assert(reloaded.configs().get("nginx_cfg").file() == "./nginx.conf");

    std::cout << "Top-Level yapilar ve tum testler basariyla gecti!" << std::endl;
    return 0;
}