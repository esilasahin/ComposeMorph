// Doğrulama kuralları (görev tanımı Madde 19) ve round-trip akışı
// (Madde 18, 23) için testler.
#include <gtest/gtest.h>
#include <compose/ComposeFile.hpp>
#include <filesystem>
#include <fstream>

namespace {

class ValidationTest : public ::testing::Test {
protected:
    compose::ComposeFile fromYaml(const std::string& content) {
        const std::string path = "validation_test.yml";
        std::ofstream out(path);
        out << content;
        out.close();
        files_.push_back(path);
        return compose::ComposeFile(path);
    }
    void TearDown() override {
        for (const std::string& file : files_) {
            std::filesystem::remove(file);
        }
    }
    std::vector<std::string> files_;
};

TEST_F(ValidationTest, ValidFilePasses) {
    auto file = fromYaml(R"(services:
  api:
    image: "company/api:1.0"
    hostname: api-01
    ports:
      - "8080:80"
      - ":9000"
      - "8000-8010:8000-8010/udp"
    volumes:
      - /opt/app:/usr/app:ro
    networks:
      - frontend
    environment:
      - "A=1"
      - "B=2"
networks:
  frontend: {}
)");
    EXPECT_NO_THROW(file.validate());
}

TEST_F(ValidationTest, TestDataFilesValidate) {
    compose::ComposeFile simple(TEST_DATA_DIR "/simple-compose.yml");
    EXPECT_NO_THROW(simple.validate());

    compose::ComposeFile full(TEST_DATA_DIR "/full-compose.yml");
    EXPECT_NO_THROW(full.validate());
}

TEST_F(ValidationTest, ServiceMustHaveImageOrBuild) {
    auto file = fromYaml(R"(services:
  api:
    hostname: api-01
)");
    EXPECT_THROW(file.validate(), compose::ValidationException);
}

TEST_F(ValidationTest, ExtendsServiceIsExemptFromImageRequirement) {
    auto file = fromYaml(R"(services:
  api:
    extends:
      service: base
    hostname: api-01
)");
    EXPECT_NO_THROW(file.validate());
}

TEST_F(ValidationTest, WrongTypesAreRejected) {
    auto ports = fromYaml(R"(services:
  api:
    image: "nginx"
    ports: "8080:80"
)");
    EXPECT_THROW(ports.validate(), compose::ValidationException);

    auto healthcheck = fromYaml(R"(services:
  api:
    image: "nginx"
    healthcheck:
      - CMD
)");
    EXPECT_THROW(healthcheck.validate(), compose::ValidationException);

    auto services = fromYaml("services:\n  - api\n");
    EXPECT_THROW(services.validate(), compose::ValidationException);
}

TEST_F(ValidationTest, InvalidHostnameIsRejected) {
    auto file = fromYaml(R"(services:
  api:
    image: "nginx"
    hostname: "-not a hostname-"
)");
    EXPECT_THROW(file.validate(), compose::ValidationException);
}

TEST_F(ValidationTest, InvalidAndDuplicatePortsAreRejected) {
    auto invalid = fromYaml(R"(services:
  api:
    image: "nginx"
    ports:
      - "not-a-port"
)");
    EXPECT_THROW(invalid.validate(), compose::ValidationException);

    auto duplicate = fromYaml(R"(services:
  api:
    image: "nginx"
    ports:
      - "8080:80"
      - "8080:80"
)");
    EXPECT_THROW(duplicate.validate(), compose::ValidationException);

    auto longSyntax = fromYaml(R"(services:
  api:
    image: "nginx"
    ports:
      - published: "8080"
)");
    EXPECT_THROW(longSyntax.validate(), compose::ValidationException);
}

TEST_F(ValidationTest, InvalidAndDuplicateVolumesAreRejected) {
    auto mode = fromYaml(R"(services:
  api:
    image: "nginx"
    volumes:
      - /opt/app:/usr/app:readonly
)");
    EXPECT_THROW(mode.validate(), compose::ValidationException);

    auto duplicate = fromYaml(R"(services:
  api:
    image: "nginx"
    volumes:
      - /opt/a:/usr/app
      - /opt/b:/usr/app
)");
    EXPECT_THROW(duplicate.validate(), compose::ValidationException);

    auto longSyntax = fromYaml(R"(services:
  api:
    image: "nginx"
    volumes:
      - type: bind
        source: /opt/app
)");
    EXPECT_THROW(longSyntax.validate(), compose::ValidationException);
}

TEST_F(ValidationTest, DuplicateEnvironmentKeyIsRejected) {
    auto file = fromYaml(R"(services:
  api:
    image: "nginx"
    environment:
      - "APP_ENV=production"
      - "APP_ENV=staging"
)");
    EXPECT_THROW(file.validate(), compose::ValidationException);
}

TEST_F(ValidationTest, UndefinedNetworkReferenceIsRejected) {
    auto file = fromYaml(R"(services:
  api:
    image: "nginx"
    networks:
      - missing
networks:
  frontend: {}
)");
    EXPECT_THROW(file.validate(), compose::ValidationException);
}

TEST_F(ValidationTest, InterpolatedValuesAreNotValidated) {
    auto file = fromYaml(R"(services:
  api:
    image: "nginx"
    hostname: "${HOSTNAME}"
    ports:
      - "$HOST_PORT:80"
    volumes:
      - "${DATA_DIR}:/data:rw"
)");
    EXPECT_NO_THROW(file.validate());
}

TEST_F(ValidationTest, RoundTripKeepsUnknownAndExtensionFields) {
    auto file = fromYaml(R"(x-company-security:
  hsm: enabled
services:
  api:
    image: "company/api:1.0"
    future_compose_property:
      enabled: true
      mode: experimental
    x-service-meta:
      owner: team
)");
    file.service("api").setImage("company/api:2.0");
    file.save("validation_roundtrip.yml");
    files_.push_back("validation_roundtrip.yml");

    compose::ComposeFile reloaded("validation_roundtrip.yml");
    auto svc = reloaded.service("api");
    EXPECT_EQ(svc.image(), "company/api:2.0");
    EXPECT_EQ(svc.get<std::string>("future_compose_property.mode").value(), "experimental");
    EXPECT_EQ(svc.get<std::string>("x-service-meta.owner").value(), "team");

    YAML::Node root = YAML::LoadFile("validation_roundtrip.yml");
    EXPECT_TRUE(root["x-company-security"]);
    EXPECT_EQ(root["x-company-security"]["hsm"].as<std::string>(), "enabled");
}

}  // namespace

namespace {

// Kapsam boşluklarını kapatan ek doğrulama durumları.
TEST_F(ValidationTest, RootAndSectionTypeErrors) {
    auto scalarRoot = fromYaml("just-a-string\n");
    EXPECT_THROW(scalarRoot.validate(), compose::ValidationException);

    auto badNetworks = fromYaml(R"(services:
  api:
    image: "nginx"
networks:
  - frontend
)");
    EXPECT_THROW(badNetworks.validate(), compose::ValidationException);

    auto scalarService = fromYaml("services:\n  api: \"nginx\"\n");
    EXPECT_THROW(scalarService.validate(), compose::ValidationException);
}

TEST_F(ValidationTest, InvalidServiceNameIsRejected) {
    auto file = fromYaml(R"(services:
  "-api":
    image: "nginx"
)");
    EXPECT_THROW(file.validate(), compose::ValidationException);
}

TEST_F(ValidationTest, MalformedEntriesAreRejected) {
    auto emptyVolume = fromYaml(R"(services:
  api:
    image: "nginx"
    volumes:
      - ""
)");
    EXPECT_THROW(emptyVolume.validate(), compose::ValidationException);

    auto tooManyParts = fromYaml(R"(services:
  api:
    image: "nginx"
    volumes:
      - a:b:c:d
)");
    EXPECT_THROW(tooManyParts.validate(), compose::ValidationException);

    auto nestedPort = fromYaml(R"(services:
  api:
    image: "nginx"
    ports:
      - - 8080
)");
    EXPECT_THROW(nestedPort.validate(), compose::ValidationException);
}

TEST_F(ValidationTest, MappingFormNetworksAreChecked) {
    auto undefined = fromYaml(R"(services:
  api:
    image: "nginx"
    networks:
      missing:
        aliases: [api]
networks:
  frontend: {}
)");
    EXPECT_THROW(undefined.validate(), compose::ValidationException);

    auto defined = fromYaml(R"(services:
  api:
    image: "nginx"
    networks:
      frontend:
        aliases: [api]
networks:
  frontend: {}
)");
    EXPECT_NO_THROW(defined.validate());
}

TEST_F(ValidationTest, SaveOptionsOverloadWritesInPlace) {
    auto file = fromYaml("services:\n  api:\n    image: \"nginx\"\n");
    file.service("api").setImage("nginx:1.27");
    EXPECT_NO_THROW(file.save(compose::SaveOptions{.backup = false, .atomic = true}));

    compose::ComposeFile reloaded("validation_test.yml");
    EXPECT_EQ(reloaded.service("api").image(), "nginx:1.27");
}

TEST_F(ValidationTest, AddServiceCreatesServicesSection) {
    compose::ComposeFile file;
    file.addService("api").setImage("nginx");
    EXPECT_TRUE(file.hasService("api"));
    EXPECT_NO_THROW(file.validate());
}

}  // namespace
