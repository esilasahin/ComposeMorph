# cpp-compose-editor

Modern C++20 standardında geliştirilmiş, `docker-compose.yml` dosyalarını programatik olarak okuma, düzenleme, doğrulama ve güvenli kaydetme imkanı sağlayan statik kütüphane.

## Özellikler

* **C++20 & yaml-cpp:** Tip güvenli, performanslı ve modern API tasarımı.
* **Kapsamlı Servis Yönetimi:** Servisler, ortam değişkenleri, extra hosts, portlar, volumes, build yapılandırmaları, healthcheck, depends_on ve deploy limitleri.
* **Top-Level Desteği:** Üst seviye `networks`, `volumes`, `secrets` ve `configs` koleksiyonları.
* **Generic Property API:** Gelecekteki veya standart dışı Compose alanları için dot-notation desteği (`logging.driver`, `x-*`).
* **Robustness & Safe-Save:** Atomic dosya yazma (`.tmp`), otomatik `.bak` yedekleme ve temel sözdizimi doğrulama (`validate()`).
* **Google Test:** CTest ile tam entegre birim test seti.

## Gereksinimler

* CMake 3.16+
* C++20 destekli derleyici (GCC 10+ / Clang 11+)
* `libyaml-cpp-dev`
* `libgtest-dev`

## Derleme ve Test

```bash
mkdir -p build && cd build
cmake ..
make
ctest --output-on-failure

```

## Örnek Kullanım
```cpp
#include "compose/ComposeFile.hpp"

int main() {
    compose::ComposeFile compose("docker-compose.yml");

    auto web = compose.service("web");
    web.setImage("nginx:alpine");
    web.environment().set("PORT", "8080");
    web.ports().add("80:80");

    compose::SaveOptions opts{.backup = true, .atomic = true};
    compose.save("docker-compose.yml", opts);

    return 0;
}
```