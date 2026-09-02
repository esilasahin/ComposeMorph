# ComposeMorph

Docker Compose yapılandırma dosyalarını programatik olarak ayrıştırmak, incelemek, değiştirmek ve serileştirmek için tasarlanmış; özel metadata'ları ve şema yapılarını koruyan, modern, sağlam ve hafif bir C++20 kütüphanesi.

---

## Proje Tanımı

ComposeMorph, Docker Compose spesifikasyonları üzerinde tip güvenli ve sezgisel bir C++ API sunarak otomasyon iş akışlarını basitleştirir. Ham YAML ağaçlarını elle işlemek yerine, geliştiriciler servisleri güvenli şekilde sorgulayabilir, konteyner özelliklerini güncelleyebilir, kaynak sınırlarını ayarlayabilir, ağları ve volume'ları yönetebilir ve geçerli Compose YAML dosyalarını güvenle üretebilir.

---

## Bağımlılıklar

Proje, standart ve modern C++ araç ve kütüphanelerine dayanır:
- C++ Derleyicisi: GCC 11+ veya Clang 13+ (C++20 desteklemeli)
- Derleme Sistemi: CMake (>= 3.16) ve Make / Ninja
- YAML Motoru: yaml-cpp (>= 0.7.0)
- Test Framework'ü: GoogleTest (GTest)

Bağımlılıkların Kurulumu (Debian / Ubuntu):
sudo apt-get update
sudo apt-get install -y build-essential cmake libyaml-cpp-dev libgtest-dev

---

## Derleme Talimatları

Standart CMake iş akışını takip edin:

git clone [https://github.com/esilasahin/ComposeMorph.git](https://github.com/esilasahin/ComposeMorph.git)
cd ComposeMorph
mkdir -p build && cd build
cmake ..
make -j$(nproc)

---

## Kurulum

CMake ile Bağlama (Önerilen):
add_subdirectory(path/to/ComposeMorph)
target_link_libraries(your_application PRIVATE composemorph)

Sistem Geneline Kurulum:
cd build
sudo make install

---

## Temel API Kullanımı

Yükleme ve Kaydetme Örneği:

#include <iostream>
#include "compose/ComposeFile.hpp"

int main() {
    compose::ComposeFile compose("docker-compose.yml");

    compose::SaveOptions opts;
    opts.atomic = true;
    opts.backup = true;
    compose.save("docker-compose.updated.yml", opts);

    return 0;
}

---

## Servis Değiştirme Örneği

#include "compose/ComposeFile.hpp"

compose::ComposeFile compose("docker-compose.yml");
auto api = compose.service("api");

api.setImage("python:3.11-slim");
api.setHostname("api-prod");
api.setContainerName("custody_api");
api.setRestart("unless-stopped");
api.setWorkingDir("/app");
api.setUser("1000:1000");
api.setPrivileged(false);
api.set("logging.driver", "json-file");

---

## Environment (Ortam Değişkeni) Örneği

auto service = compose.service("web");

service.environment().set("DB_PORT", "5432");
service.environment().set("APP_ENV", "production");

if (service.environment().has("DB_PORT")) {
    std::string port = service.environment().get("DB_PORT").value_or("5000");
}

service.environment().remove("TEMP_KEY");

---

## extra_hosts Örneği

auto service = compose.service("web");

service.extraHosts().set("hsm01", "10.10.10.20");
service.extraHosts().set("db-internal", "192.168.1.100");

if (service.extraHosts().has("hsm01")) {
    std::string ip = service.extraHosts().get("hsm01").value();
}

---

## Volume Örneği

auto service = compose.service("api");

service.volumes().add("/opt/storage/v1", "/app/data");
service.volumes().add("./logs", "/var/log", "ro");

service.volumes().setSource("/app/data", "/opt/storage/v2");
service.volumes().removeByTarget("/var/log");

---

## Network Örneği

compose.networks().add("isolated-backend").setExternal(true);

auto service = compose.service("api");
service.networks().add("isolated-backend");

---

## Hata Yönetimi

#include "compose/ComposeFile.hpp"
#include "compose/Exceptions.hpp"

try {
    compose::ComposeFile compose("invalid-path.yml");
    auto service = compose.service("non_existent_service");
} catch (const compose::FileNotFoundException& ex) {
    std::cerr << "File error: " << ex.what() << std::endl;
} catch (const compose::ServiceNotFoundException& ex) {
    std::cerr << "Service error: " << ex.what() << std::endl;
} catch (const compose::ValidationException& ex) {
    std::cerr << "Schema error: " << ex.what() << std::endl;
}

---

## Test

Kütüphane, GoogleTest ile yazılmış ve CTest üzerinden yönetilen otomatik bir test paketi içerir.

cd build
make
ctest --output-on-failure

Doğrulanmış Test Senaryoları:
- ServiceBasicProperties: Özellik getter/setter'ları ve durumun kalıcılığı.
- EnvironmentAndLabels: Ortam değişkenleri ve etiketler için anahtar-değer map işlemleri.
- VolumesAdvancedOperations: Path bağlamaları, dinamik kaynak (source) değişimi ve hedef (target) silme.
- TopLevelAndDeployConfigs: Replica sayısı, kaynak sınırları (CPU/Memory) ve üst seviye networks/volumes.
- GenericPropertiesAndSafeSave: Dinamik dot-notation property'leri, atomic yazma ve yedek (.bak) oluşturma.
- ExceptionsAndValidation: Geçersiz servis aramalarında ve şema hatalarında istisna (exception) fırlatılması.
- RoundTripPreservationAndModification: Tam yükleme/değiştirme/kaydetme döngüsünde tanınmayan etiketlerin (örn. x-* özel metadata uzantıları) korunması.

---

## Kısıtlamalar

- Yorum Satırı Koruması: Standart yaml-cpp emitter'larında olduğu gibi, dosya yeniden serileştirilirken yapısal ve satır içi YAML yorumları korunmaz.
- Anchor & Alias Genişletmesi: YAML anchor (&) ve alias (*) yapıları parse sırasında somut değerlere genişletilir ve yeniden yazılırken referans bağı korunmayabilir.
- Katı Compose V2 Spesifikasyonu: Öncelikli olarak modern Compose V2 spesifikasyon standartları etrafında tasarlanmıştır.