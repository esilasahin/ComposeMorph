// Bir servise extra_hosts kaydı ekler ya da mevcut kaydı günceller.
// Dosyadaki kısa (liste) ya da uzun (eşleme) sözdizimi korunur.
//
//   change-extra-host docker-compose.yml api hsm-server 10.10.10.20
#include <compose/ComposeFile.hpp>
#include <iostream>

int main(int argc, char** argv) {
    if (argc < 5) {
        std::cerr << "Usage: change-extra-host <file.yml> <service> <host> <address>\n";
        return 2;
    }

    try {
        compose::ComposeFile file(argv[1]);
        file.service(argv[2]).extraHosts().set(argv[3], argv[4]);
        file.validate();
        file.save();
        std::cout << "extra host set: " << argv[3] << " -> " << argv[4] << "\n";
    } catch (const compose::ComposeException& e) {
        std::cerr << "error: " << e.what() << "\n";
        return 1;
    }
    return 0;
}
