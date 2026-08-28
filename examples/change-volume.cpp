#include "compose/ComposeFile.hpp"
#include <iostream>

int main() {
    try {
        compose::ComposeFile file("test-data/full-compose.yml");
        auto crypto = file.service("custody-crypto");

        crypto.setImage("harbor.example/custody/cus-crypto:0.17.0");
        crypto.setHostname("custody-crypto");
        crypto.extraHosts().set("hsm01", "10.10.10.20");
        crypto.environment().set("HSM_HOST", "hsm01");
        crypto.volumes().setSource("/usr/app/executable", "/opt/custody/executable-0.17.0");

        file.validate();
        file.save("docker-compose.modified.yml");
        std::cout << "Successfully updated custody-crypto configuration!" << std::endl;
    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
        return 1;
    }
    return 0;
}