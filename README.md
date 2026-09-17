# ComposeMorph

Docker Compose yapılandırma dosyalarını programatik olarak ayrıştırmak, incelemek, değiştirmek ve serileştirmek için tasarlanmış; özel metadata'ları ve şema yapılarını koruyan, modern, sağlam ve hafif bir C++20 kütüphanesi.

---

## Proje Tanımı

ComposeMorph, Docker Compose spesifikasyonları üzerinde tip güvenli ve sezgisel bir C++ API sunarak otomasyon iş akışlarını basitleştirir. Ham YAML ağaçlarını elle işlemek yerine, geliştiriciler servisleri güvenli şekilde sorgulayabilir, konteyner özelliklerini güncelleyebilir, kaynak sınırlarını ayarlayabilir, ağları ve volume'ları yönetebilir ve geçerli Compose YAML dosyalarını güvenle üretebilir.

---

## Research

Bu repository, C++ uygulamalarından Docker Compose YAML dosyalarının güvenli, geri uyumlu ve minimum yan etkiyle programatik olarak değiştirilmesi üzerine hazırlanmakta olan bir bilimsel bildiriye eşlik etmektedir.

Title: TBD
Authors: ...
Conference: ...
Paper: ...
Artifact: bu repository (`benchmarks/`, `datasets/`, `scripts/`, `results/`)

Tüm deneyleri tek komutla yeniden çalıştırmak için:

    ./scripts/run-all-experiments.sh

Sonuçlar için `results/tables/` ve `results/figures/`, ilgili literatür taraması için `docs/related-work.md` dizinine bakınız.

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

Test paketi 55 testten oluşur ve dört dosyaya ayrılmıştır:

- `tests/UnitTests.cpp` — temel API, round-trip ve bu çalışmada bulunan hatalar için gerileme testleri (tırnak koruma, kısa sözdizimi).
- `tests/ServiceApiTest.cpp` — servis ekleme/silme/listeleme, tüm skaler property getter/setter/remove üçlüleri, komut ve entrypoint, genel (dot-path) property API'si, kaydetme seçenekleri, istisnalar.
- `tests/CollectionsTest.cpp` — environment, labels, extra_hosts, ports, volumes, networks, build, healthcheck, depends_on, deploy ve üst seviye koleksiyonlar; kısa ve uzun sözdiziminin ikisi de.
- `tests/ValidationTest.cpp` — Madde 19'daki doğrulama kuralları ve round-trip'te bilinmeyen/`x-*` alanların korunması.

### Kapsam (coverage)

```
./scripts/coverage.sh        # eşik %80 (aşılmazsa çıkış kodu 1)
```

Betik ayrı bir `build-coverage/` dizininde gcov ile ölçüm yapar; ek araç
gerektirmez. Rapor `results/coverage/coverage.csv` dosyasına yazılır.
Son ölçüm: **toplam %92,4 satır kapsamı**; ayrıştırma/değiştirme çekirdeği
(`Service.cpp` %100, `ScalarQuoting.cpp` %96,8, `Volumes.cpp` %92,5,
`Ports.cpp` %90,6) %90'ın üzerindedir.

---

### Doğrulama kapsamı

`compose.validate()` şunları denetler: servis adı biçimi, `image`/`build`
zorunluluğu (`extends` kullanan servisler muaf), alan tipleri (ports/volumes
dizi, environment/labels/networks dizi veya eşleme, healthcheck/deploy eşleme),
hostname biçimi, port biçimi ve yinelenen portlar, volume tanımı ve yinelenen
hedefler, yinelenen ortam değişkenleri, üst seviyede tanımlı olmayan ağ
referansları. `${VAR}` ve `$VAR` içeren değerler çalışma zamanında
çözüldüğü için denetim dışıdır. Şema doğrulamasının tamamı için
`docker compose config` kullanılır.

## Kısıtlamalar

- Yorum Satırı Koruması: Standart yaml-cpp emitter'larında olduğu gibi, dosya yeniden serileştirilirken yapısal ve satır içi YAML yorumları korunmaz.
- Bayt Düzeyinde Aynılık: Yorumlar, boş satırlar ve girinti tercihleri korunmadığı için round-trip bayt düzeyinde aynı dosyayı üretmez (Dataset B'de %4,0) — bkz. `results/tables/roundtrip_dataset_b_summary.md`. Değerlerin YAML tipleri ise korunur: kaynakta tırnaklı yazılmış skalerler tırnaklı olarak yeniden üretilir (`src/ScalarQuoting.cpp`), tek tırnak kullanımı çift tırnağa dönüşür.
- Anchor & Alias Etiket Kaybı: YAML anchor (&) / alias (*) / merge-key (`<<`) yapıları round-trip sırasında referans bağı korunarak (somut değerlere genişletilmeden) yeniden yazılır, ancak orijinal anchor adı korunmaz — yaml-cpp bunun yerine otomatik üretilmiş sayısal bir etiket (örn. `&1`) atar (bkz. `datasets/controlled/corner-cases/anchors-and-aliases.yml`).
- Katı Compose V2 Spesifikasyonu: Öncelikli olarak modern Compose V2 spesifikasyon standartları etrafında tasarlanmıştır.
- Uzun (long) Sözdizimi: `ports`, `volumes` ve `networks` için hem kısa hem uzun (mapping) sözdizimi okunur, yerinde güncellenir ve dosyadaki biçim korunur; uzun sözdizimli girdiler kısa gösterime indirgenerek karşılaştırılır (`8080:80/tcp`). Yeni girdi eklerken kısa sözdizimi kullanılır: eşleme biçimli `networks` bölümüne eklenen ağ, eşlemeye boş değerli anahtar olarak yazılır.
- x- Öneki Olmayan Bilinmeyen Alanlar: Kütüphane bu alanları sadakatle korur, ancak Compose Specification şeması yalnızca `x-` önekli uzantılara izin verdiği için böyle bir alan içeren dosya `docker compose config` tarafından reddedilir — bu, kütüphaneden bağımsız bir şema kısıtıdır.