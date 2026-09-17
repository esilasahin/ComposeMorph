// Servis yaşam döngüsü, temel property API'si ve genel (generic) property
// API'si için testler (görev tanımı Madde 3, 4, 17, 22).
#include <gtest/gtest.h>
#include <compose/ComposeFile.hpp>
#include <filesystem>
#include <fstream>

namespace {

const char* kSample = R"(services:
  api:
    image: "company/api:1.0"
    hostname: api01
    container_name: api-container
    restart: unless-stopped
    working_dir: /usr/app
    user: "1000:1000"
    command: ["run", "--workers", "4"]
)";

class ServiceApiTest : public ::testing::Test {
protected:
    void SetUp() override {
        std::ofstream out("service_api_test.yml");
        out << kSample;
    }
    void TearDown() override {
        std::filesystem::remove("service_api_test.yml");
        std::filesystem::remove("service_api_out.yml");
    }
    compose::ComposeFile open() { return compose::ComposeFile("service_api_test.yml"); }
};

TEST_F(ServiceApiTest, ServiceLifecycle) {
    auto file = open();
    EXPECT_TRUE(file.hasService("api"));
    EXPECT_FALSE(file.hasService("redis"));

    file.addService("redis").setImage("redis:7");
    EXPECT_TRUE(file.hasService("redis"));

    std::vector<std::string> names = file.serviceNames();
    EXPECT_EQ(names.size(), 2u);
    EXPECT_NE(std::find(names.begin(), names.end(), "redis"), names.end());

    file.removeService("redis");
    EXPECT_FALSE(file.hasService("redis"));
    EXPECT_EQ(file.serviceNames().size(), 1u);
}

TEST_F(ServiceApiTest, MissingServiceThrows) {
    auto file = open();
    EXPECT_THROW(file.service("nope"), compose::ServiceNotFoundException);
}

TEST_F(ServiceApiTest, InvalidYamlThrowsParseException) {
    EXPECT_THROW(compose::ComposeFile(TEST_DATA_DIR "/invalid-compose.yml"),
                 compose::ParseException);
}

TEST_F(ServiceApiTest, MissingFileThrowsParseException) {
    EXPECT_THROW(compose::ComposeFile("no-such-file.yml"), compose::ParseException);
}

TEST_F(ServiceApiTest, ScalarPropertiesRoundTrip) {
    auto file = open();
    auto svc = file.service("api");

    EXPECT_EQ(svc.image(), "company/api:1.0");
    EXPECT_EQ(svc.hostname(), "api01");
    EXPECT_EQ(svc.containerName(), "api-container");
    EXPECT_EQ(svc.restart(), "unless-stopped");
    EXPECT_EQ(svc.workingDir(), "/usr/app");
    EXPECT_EQ(svc.user(), "1000:1000");

    svc.setImage("company/api:2.0");
    svc.setHostname("api02");
    svc.setContainerName("api2");
    svc.setRestart("always");
    svc.setPrivileged(true);
    svc.setWorkingDir("/srv");
    svc.setUser("0:0");

    EXPECT_EQ(svc.image(), "company/api:2.0");
    EXPECT_EQ(svc.hostname(), "api02");
    EXPECT_EQ(svc.containerName(), "api2");
    EXPECT_EQ(svc.restart(), "always");
    EXPECT_TRUE(svc.privileged());
    EXPECT_EQ(svc.workingDir(), "/srv");
    EXPECT_EQ(svc.user(), "0:0");
}

TEST_F(ServiceApiTest, RemoveScalarProperties) {
    auto file = open();
    auto svc = file.service("api");

    svc.removeHostname();
    svc.removeContainerName();
    svc.removeRestart();
    svc.removeWorkingDir();
    svc.removeUser();

    EXPECT_TRUE(svc.hostname().empty());
    EXPECT_TRUE(svc.containerName().empty());
    EXPECT_TRUE(svc.restart().empty());
    EXPECT_TRUE(svc.workingDir().empty());
    EXPECT_TRUE(svc.user().empty());
}

TEST_F(ServiceApiTest, CommandAndEntrypoint) {
    auto file = open();
    auto svc = file.service("api");

    EXPECT_FALSE(svc.command().empty());
    svc.setCommand(std::vector<std::string>{"serve", "--port", "8080"});
    EXPECT_NE(svc.command().find("8080"), std::string::npos);
    svc.setCommand(std::string("serve"));
    EXPECT_EQ(svc.command(), "serve");

    svc.setEntrypoint("/entrypoint.sh");
    EXPECT_EQ(svc.entrypoint(), "/entrypoint.sh");
    svc.setEntrypoint(std::vector<std::string>{"/bin/sh", "-c"});
    EXPECT_FALSE(svc.entrypoint().empty());
}

TEST_F(ServiceApiTest, GenericPropertyApi) {
    auto file = open();
    auto svc = file.service("api");

    svc.set("future_compose_property", std::string("value"));
    svc.set("custom.section.value", std::string("test"));
    svc.set("deploy.replicas", 3);

    EXPECT_EQ(svc.get<std::string>("custom.section.value").value(), "test");
    EXPECT_EQ(svc.get<int>("deploy.replicas").value(), 3);
    EXPECT_FALSE(svc.get<std::string>("custom.missing.key").has_value());

    svc.remove("custom.section.value");
    EXPECT_FALSE(svc.get<std::string>("custom.section.value").has_value());
}

TEST_F(ServiceApiTest, SaveWithBackupAndNonAtomic) {
    auto file = open();
    file.service("api").setImage("company/api:3.0");

    file.save("service_api_out.yml", compose::SaveOptions{.backup = false, .atomic = false});
    EXPECT_TRUE(std::filesystem::exists("service_api_out.yml"));

    compose::ComposeFile reloaded("service_api_out.yml");
    EXPECT_EQ(reloaded.service("api").image(), "company/api:3.0");

    reloaded.save("service_api_out.yml", compose::SaveOptions{.backup = true, .atomic = true});
    EXPECT_TRUE(std::filesystem::exists("service_api_out.yml.bak"));
    std::filesystem::remove("service_api_out.yml.bak");
}

TEST_F(ServiceApiTest, EmptyFileHasNoServices) {
    compose::ComposeFile empty;
    EXPECT_TRUE(empty.serviceNames().empty());
    EXPECT_THROW(empty.save(), compose::ComposeException);
}

}  // namespace
