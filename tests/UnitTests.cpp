#include <gtest/gtest.h>
#include <fstream>
#include <filesystem>
#include "compose/ComposeFile.hpp"
#include "compose/Exceptions.hpp"

namespace fs = std::filesystem;

class ComposeEditorTest : public ::testing::Test {
protected:
    void SetUp() override {
        std::ofstream out("test_sample.yml");
        out << "services:\n"
            << "  api:\n"
            << "    image: python:3.11-slim\n"
            << "    restart: always\n";
        out.close();
    }

    void TearDown() override {
        if (fs::exists("test_sample.yml")) fs::remove("test_sample.yml");
        if (fs::exists("test_output.yml")) fs::remove("test_output.yml");
        if (fs::exists("test_output.yml.bak")) fs::remove("test_output.yml.bak");
    }
};

TEST_F(ComposeEditorTest, ServiceBasicProperties) {
    compose::ComposeFile compose("test_sample.yml");
    auto api = compose.service("api");

    EXPECT_EQ(api.image(), "python:3.11-slim");
    EXPECT_EQ(api.restart(), "always");

    api.setHostname("api-prod");
    api.setContainerName("custody_api");
    api.setWorkingDir("/app");
    api.setUser("1000:1000");
    api.setPrivileged(true);

    EXPECT_EQ(api.hostname(), "api-prod");
    EXPECT_EQ(api.containerName(), "custody_api");
    EXPECT_EQ(api.workingDir(), "/app");
    EXPECT_EQ(api.user(), "1000:1000");
    EXPECT_TRUE(api.privileged());
}

TEST_F(ComposeEditorTest, EnvironmentAndLabels) {
    compose::ComposeFile compose("test_sample.yml");
    auto api = compose.service("api");

    api.environment().set("DB_PORT", "5432");
    api.labels().set("version", "1.0.0");

    EXPECT_TRUE(api.environment().has("DB_PORT"));
    EXPECT_EQ(api.environment().get("DB_PORT").value(), "5432");
    EXPECT_EQ(api.labels().get("version").value(), "1.0.0");
}

TEST_F(ComposeEditorTest, VolumesAdvancedOperations) {
    compose::ComposeFile compose("test_sample.yml");
    auto api = compose.service("api");

    api.volumes().add("/opt/v1", "/app/data");
    api.volumes().add("./logs", "/var/log", "ro");

    EXPECT_TRUE(api.volumes().has("/opt/v1:/app/data"));
    EXPECT_TRUE(api.volumes().has("./logs:/var/log:ro"));

    api.volumes().setSource("/app/data", "/opt/v2");
    EXPECT_TRUE(api.volumes().has("/opt/v2:/app/data"));
    EXPECT_FALSE(api.volumes().has("/opt/v1:/app/data"));

    api.volumes().removeByTarget("/var/log");
    EXPECT_FALSE(api.volumes().has("./logs:/var/log:ro"));
}

TEST_F(ComposeEditorTest, TopLevelAndDeployConfigs) {
    compose::ComposeFile compose("test_sample.yml");
    auto api = compose.service("api");

    api.deploy().setReplicas(2);
    api.deploy().resources().limits().setCpus("1.5");
    api.deploy().resources().limits().setMemory("1G");

    compose.networks().add("isolated-net").setExternal(true);
    compose.volumes().add("app-storage").setDriver("local");

    EXPECT_EQ(api.deploy().replicas(), 2);
    EXPECT_EQ(api.deploy().resources().limits().cpus(), "1.5");
    EXPECT_TRUE(compose.networks().has("isolated-net"));
    EXPECT_TRUE(compose.networks().get("isolated-net").external());
    EXPECT_EQ(compose.volumes().get("app-storage").driver(), "local");
}

TEST_F(ComposeEditorTest, GenericPropertiesAndSafeSave) {
    compose::ComposeFile compose("test_sample.yml");
    auto api = compose.service("api");

    api.set("logging.driver", "json-file");
    EXPECT_EQ(api.get<std::string>("logging.driver").value(), "json-file");

    compose::SaveOptions opts;
    opts.backup = true;
    opts.atomic = true;
    compose.save("test_output.yml", opts);

    EXPECT_TRUE(fs::exists("test_output.yml"));

    compose::ComposeFile reloaded("test_output.yml");
    EXPECT_EQ(reloaded.service("api").get<std::string>("logging.driver").value(), "json-file");
}

TEST_F(ComposeEditorTest, ExceptionsAndValidation) {
    compose::ComposeFile compose("test_sample.yml");
    
    EXPECT_THROW(compose.service("non_existent_service"), compose::ServiceNotFoundException);
    EXPECT_NO_THROW(compose.validate());
}

TEST_F(ComposeEditorTest, RoundTripPreservationAndModification) {
    // 1. Load full-compose
    compose::ComposeFile compose("../test-data/full-compose.yml");
    ASSERT_TRUE(compose.hasService("custody-crypto"));

    auto crypto = compose.service("custody-crypto");
    
    // 2. Modify
    crypto.setImage("registry/custody-crypto:0.17.0");
    crypto.volumes().setSource("/usr/app/executable", "/opt/custody/executable-0.17.0");
    crypto.environment().set("SPRING_PROFILES_ACTIVE", "production");

    // 3. Save
    compose.save("generated-compose.yml");

    // 4. Reload & Verify
    compose::ComposeFile reloaded("generated-compose.yml");
    auto reloadedCrypto = reloaded.service("custody-crypto");

    EXPECT_EQ(reloadedCrypto.image(), "registry/custody-crypto:0.17.0");
    EXPECT_TRUE(reloadedCrypto.volumes().has("/opt/custody/executable-0.17.0:/usr/app/executable"));
    EXPECT_EQ(reloadedCrypto.environment().get("SPRING_PROFILES_ACTIVE").value(), "production");
    
    // x-* preservation
    EXPECT_EQ(reloadedCrypto.get<std::string>("x-company-security.hsm").value(), "enabled");
}