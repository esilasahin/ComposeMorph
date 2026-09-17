// Bir servisin imaj etiketini yükseltir.
//
//   change-image docker-compose.yml api company/api:2.0
#include <compose/ComposeFile.hpp>
#include <iostream>

int main(int argc, char** argv) {
    if (argc < 4) {
        std::cerr << "Usage: change-image <file.yml> <service> <image>\n";
        return 2;
    }

    try {
        compose::ComposeFile file(argv[1]);
        file.service(argv[2]).setImage(argv[3]);
        file.validate();
        file.save();
        std::cout << "image updated: " << argv[2] << " -> " << argv[3] << "\n";
    } catch (const compose::ComposeException& e) {
        std::cerr << "error: " << e.what() << "\n";
        return 1;
    }
    return 0;
}
