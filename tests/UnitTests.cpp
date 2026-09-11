#include <gtest/gtest.h>
#include <fstream>
#include <filesystem>
#include "compose/ComposeFile.hpp"
#include "compose/Exceptions.hpp"

namespace fs = std::filesystem;

class ComposeMorphTest : public ::testing::Test {
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

TEST_F(ComposeMorphTest, ServiceBasicProperties) {
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

TEST_F(ComposeMorphTest, EnvironmentAndLabels) {
    compose::ComposeFile compose("test_sample.yml");
    auto api = compose.service("api");

    api.environment().set("DB_PORT", "5432");
    api.labels().set("version", "1.0.0");

    EXPECT_TRUE(api.environment().has("DB_PORT"));
    EXPECT_EQ(api.environment().get("DB_PORT").value(), "5432");
    EXPECT_EQ(api.labels().get("version").value(), "1.0.0");
}

TEST_F(ComposeMorphTest, VolumesAdvancedOperations) {
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

TEST_F(ComposeMorphTest, TopLevelAndDeployConfigs) {
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

TEST_F(ComposeMorphTest, GenericPropertiesAndSafeSave) {
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

TEST_F(ComposeMorphTest, ExceptionsAndValidation) {
    compose::ComposeFile compose("test_sample.yml");
    
    EXPECT_THROW(compose.service("non_existent_service"), compose::ServiceNotFoundException);
    EXPECT_NO_THROW(compose.validate());
}

TEST_F(ComposeMorphTest, RoundTripPreservationAndModification) {
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

namespace {
std::string readFile(const std::string& path) {
    std::ifstream in(path);
    return std::string((std::istreambuf_iterator<char>(in)), std::istreambuf_iterator<char>());
}

void writeFile(const std::string& path, const std::string& content) {
    std::ofstream out(path);
    out << content;
}
}

TEST_F(ComposeMorphTest, QuotedScalarsKeepTheirQuotesOnSave) {
    writeFile("test_sample.yml",
              "version: \"3.8\"\n"
              "x-base: &base\n"
              "  restart: always\n"
              "services:\n"
              "  api:\n"
              "    <<: *base\n"
              "    image: nginx:latest\n"
              "    environment:\n"
              "      DEBUG: \"true\"\n"
              "      RETRIES: '3'\n"
              "    command: [\"caddy\", \"--listen\", \":80\", \"4\"]\n"
              "    healthcheck:\n"
              "      retries: 3\n");

    compose::ComposeFile compose("test_sample.yml");
    compose.save("test_output.yml");
    const std::string out = readFile("test_output.yml");

    EXPECT_NE(out.find("version: \"3.8\""), std::string::npos) << out;
    EXPECT_NE(out.find("DEBUG: \"true\""), std::string::npos) << out;
    EXPECT_NE(out.find("RETRIES: \"3\""), std::string::npos) << out;
    EXPECT_NE(out.find("\":80\""), std::string::npos) << out;
    EXPECT_NE(out.find("\"4\""), std::string::npos) << out;
    // Plain scalars were typed on purpose and must stay plain.
    EXPECT_NE(out.find("retries: 3\n"), std::string::npos) << out;
    EXPECT_NE(out.find("image: nginx:latest\n"), std::string::npos) << out;
    // Anchors and aliases survive (yaml-cpp renumbers the anchor name).
    EXPECT_NE(out.find("x-base: &1"), std::string::npos) << out;
    EXPECT_NE(out.find("<<: *1"), std::string::npos) << out;

    YAML::Node reloaded = YAML::LoadFile("test_output.yml");
    EXPECT_EQ(reloaded["version"].Tag(), "!");
    EXPECT_EQ(reloaded["services"]["api"]["healthcheck"]["retries"].as<int>(), 3);
}

TEST_F(ComposeMorphTest, ApiWrittenStringsThatLookTypedAreQuoted) {
    compose::ComposeFile compose("test_sample.yml");
    auto api = compose.service("api");
    api.setCommand(std::vector<std::string>{"run", "--workers", "4"});
    api.environment().set("FEATURE_FLAG", "yes");
    api.environment().set("APP_ENV", "production");
    api.set("x-meta.version", std::string("1.0"));
    api.set("deploy.replicas", 2);
    compose.save("test_output.yml");
    const std::string out = readFile("test_output.yml");

    EXPECT_NE(out.find("\"4\""), std::string::npos) << out;
    EXPECT_NE(out.find("FEATURE_FLAG: \"yes\""), std::string::npos) << out;
    EXPECT_NE(out.find("APP_ENV: production\n"), std::string::npos) << out;
    EXPECT_NE(out.find("version: \"1.0\""), std::string::npos) << out;
    EXPECT_NE(out.find("replicas: 2\n"), std::string::npos) << out;
}

TEST_F(ComposeMorphTest, OverwritingAQuotedValueKeepsItQuoted) {
    writeFile("test_sample.yml",
              "services:\n"
              "  api:\n"
              "    image: \"nginx:1.0\"\n"
              "    ports:\n"
              "      - \"8080:80\"\n"
              "      - \"3000\"\n");

    compose::ComposeFile compose("test_sample.yml");
    auto api = compose.service("api");
    api.setImage("nginx:2.0");
    api.ports().remove("8080:80");
    compose.save("test_output.yml");
    const std::string out = readFile("test_output.yml");

    EXPECT_NE(out.find("image: \"nginx:2.0\""), std::string::npos) << out;
    EXPECT_NE(out.find("- \"3000\""), std::string::npos) << out;
    EXPECT_EQ(out.find("8080:80"), std::string::npos) << out;
}

TEST_F(ComposeMorphTest, ShortSyntaxEnvironmentLabelsAndExtraHostsStayLists) {
    writeFile("test_sample.yml",
              "services:\n"
              "  api:\n"
              "    image: nginx\n"
              "    environment:\n"
              "      - A=1\n"
              "      - B=2\n"
              "      - FROM_HOST\n"
              "    labels:\n"
              "      - \"tier=backend\"\n"
              "    extra_hosts:\n"
              "      - \"db:10.0.0.5\"\n");

    compose::ComposeFile compose("test_sample.yml");
    auto api = compose.service("api");
    EXPECT_EQ(api.environment().get("B").value(), "2");
    EXPECT_TRUE(api.environment().has("FROM_HOST"));
    EXPECT_FALSE(api.environment().get("FROM_HOST").has_value());
    EXPECT_EQ(api.extraHosts().get("db").value(), "10.0.0.5");

    api.environment().set("A", "changed");
    api.environment().set("C", "true");
    api.environment().remove("B");
    api.labels().set("owner", "team-a");
    api.extraHosts().set("db", "10.0.0.6");
    api.extraHosts().set("hsm", "10.0.0.7");
    compose.save("test_output.yml");
    const std::string out = readFile("test_output.yml");

    YAML::Node env = YAML::LoadFile("test_output.yml")["services"]["api"]["environment"];
    ASSERT_TRUE(env.IsSequence()) << out;
    ASSERT_EQ(env.size(), 3u) << out;
    EXPECT_EQ(env[0].as<std::string>(), "A=changed");
    EXPECT_EQ(env[1].as<std::string>(), "FROM_HOST");
    EXPECT_EQ(env[2].as<std::string>(), "C=true");
    EXPECT_NE(out.find("- owner=team-a"), std::string::npos) << out;
    EXPECT_NE(out.find("\"db:10.0.0.6\""), std::string::npos) << out;
    EXPECT_NE(out.find("- hsm:10.0.0.7"), std::string::npos) << out;
}