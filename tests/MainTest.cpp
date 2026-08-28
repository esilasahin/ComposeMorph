#include <iostream>
#include <fstream>
#include <filesystem>
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
#include "compose/Exceptions.hpp"

namespace fs = std::filesystem;

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
    web.setWorkingDir("/usr/share/nginx/html");
    web.setUser("1001:1001");
    web.setCommand("nginx -g 'daemon off;'");
    web.labels().set("traefik.enable", "true");

    // Generic Property API Testi (Madde 17)
    web.set("logging.driver", "json-file");
    web.set("x-custom-security.hsm", "enabled");
    assert(web.get<std::string>("logging.driver").value() == "json-file");
    assert(web.get<std::string>("x-custom-security.hsm").value() == "enabled");

    // Alt koleksiyon testleri
    web.environment().set("PORT", "8080");
    web.extraHosts().set("hsm01", "10.10.10.20");
    web.ports().add("80:80");
    web.volumes().add("/opt/custody/v1", "/usr/app/executable");
    web.networks().add("frontend-net");

    auto app = compose.addService("app");
    app.build().setContext(".");
    app.build().setDockerfile("Dockerfile.prod");
    app.deploy().setReplicas(3);

    // Validation Testi (Madde 19)
    compose.validate();

    // Safe-Save ve Backup Testi (Madde 21)
    compose::SaveOptions opts;
    opts.backup = true;
    opts.atomic = true;
    compose.save("output.yml", opts);

    assert(fs::exists("output.yml"));

    // Exception Testi (Madde 20)
    bool exceptionCaught = false;
    try {
        compose.service("non_existing_service");
    } catch (const compose::ServiceNotFoundException& e) {
        exceptionCaught = true;
    }
    assert(exceptionCaught);

    std::cout << "Milestone 3 (Generic Properties, Validation, Safe-Save, Exceptions) basariyla gecti!" << std::endl;
    return 0;
}