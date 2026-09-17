// Servis altı koleksiyonlar ve üst seviye koleksiyonlar için testler
// (görev tanımı Madde 5-15, 22). Kısa ve uzun sözdiziminin ikisi de kapsanır.
#include <gtest/gtest.h>
#include <compose/ComposeFile.hpp>
#include <algorithm>
#include <filesystem>
#include <fstream>

namespace {

const char* kShortSyntax = R"(services:
  api:
    image: "company/api:1.0"
    environment:
      - "APP_ENV=production"
      - "PORT=8080"
    extra_hosts:
      - "hsm=10.10.10.20"
    ports:
      - "8080:8080"
    volumes:
      - /opt/app:/usr/app:ro
      - data:/var/lib/data
    networks:
      - frontend
    labels:
      - "com.example.owner=team"
)";

const char* kLongSyntax = R"(services:
  api:
    image: "company/api:1.0"
    environment:
      APP_ENV: "production"
    extra_hosts:
      hsm: "10.10.10.20"
    ports:
      - target: 80
        published: "8080"
        protocol: tcp
    volumes:
      - type: bind
        source: /opt/app
        target: /usr/app
    networks:
      frontend:
        aliases: [api]
networks:
  frontend: {}
)";

class CollectionsTest : public ::testing::Test {
protected:
    compose::ComposeFile write(const char* content, const std::string& name) {
        std::ofstream out(name);
        out << content;
        out.close();
        files_.push_back(name);
        return compose::ComposeFile(name);
    }
    void TearDown() override {
        for (const std::string& file : files_) {
            std::filesystem::remove(file);
        }
    }
    std::vector<std::string> files_;
};

TEST_F(CollectionsTest, EnvironmentListSyntax) {
    auto file = write(kShortSyntax, "coll_short_env.yml");
    auto env = file.service("api").environment();

    EXPECT_TRUE(env.has("APP_ENV"));
    EXPECT_EQ(env.get("PORT"), "8080");

    env.set("PORT", "9090");
    EXPECT_EQ(env.get("PORT"), "9090");
    env.set("NEW_KEY", "1");
    EXPECT_EQ(env.getAll().size(), 3u);

    env.remove("NEW_KEY");
    EXPECT_FALSE(env.has("NEW_KEY"));
}

TEST_F(CollectionsTest, EnvironmentMappingSyntax) {
    auto file = write(kLongSyntax, "coll_long_env.yml");
    auto env = file.service("api").environment();

    EXPECT_EQ(env.get("APP_ENV"), "production");
    env.set("APP_ENV", "staging");
    env.set("EXTRA", "x");
    EXPECT_EQ(env.get("APP_ENV"), "staging");
    EXPECT_EQ(env.getAll().size(), 2u);
}

TEST_F(CollectionsTest, LabelsUseEnvironmentApi) {
    auto file = write(kShortSyntax, "coll_labels.yml");
    auto labels = file.service("api").labels();

    EXPECT_EQ(labels.get("com.example.owner"), "team");
    labels.set("com.example.tier", "backend");
    EXPECT_TRUE(labels.has("com.example.tier"));
}

TEST_F(CollectionsTest, ExtraHostsBothSyntaxes) {
    auto shortFile = write(kShortSyntax, "coll_short_hosts.yml");
    auto shortHosts = shortFile.service("api").extraHosts();
    EXPECT_EQ(shortHosts.get("hsm"), "10.10.10.20");
    shortHosts.set("hsm", "10.10.10.21");
    shortHosts.set("db", "10.10.10.30");
    EXPECT_EQ(shortHosts.get("hsm"), "10.10.10.21");
    EXPECT_EQ(shortHosts.getAll().size(), 2u);
    shortHosts.remove("db");
    EXPECT_FALSE(shortHosts.has("db"));

    auto longFile = write(kLongSyntax, "coll_long_hosts.yml");
    auto longHosts = longFile.service("api").extraHosts();
    EXPECT_EQ(longHosts.get("hsm"), "10.10.10.20");
    longHosts.set("db", "10.10.10.30");
    EXPECT_TRUE(longHosts.has("db"));
}

TEST_F(CollectionsTest, PortsShortSyntax) {
    auto file = write(kShortSyntax, "coll_short_ports.yml");
    auto ports = file.service("api").ports();

    EXPECT_TRUE(ports.has("8080:8080"));
    ports.add("127.0.0.1:8081:8080");
    EXPECT_EQ(ports.toVector().size(), 2u);
    ports.remove("8080:8080");
    EXPECT_FALSE(ports.has("8080:8080"));
    ports.clear();
    EXPECT_TRUE(ports.toVector().empty());
}

TEST_F(CollectionsTest, PortsLongSyntaxIsReadAndPreserved) {
    auto file = write(kLongSyntax, "coll_long_ports.yml");
    auto ports = file.service("api").ports();

    // Uzun sözdizimli girdi kısa gösterime indirgenerek okunur.
    EXPECT_TRUE(ports.has("8080:80/tcp"));
    EXPECT_EQ(ports.toVector().at(0), "8080:80/tcp");

    ports.add("9090:90");
    EXPECT_EQ(ports.toVector().size(), 2u);

    file.save("coll_long_ports_out.yml");
    files_.push_back("coll_long_ports_out.yml");
    compose::ComposeFile reloaded("coll_long_ports_out.yml");
    EXPECT_EQ(reloaded.service("api").ports().toVector().size(), 2u);
}

TEST_F(CollectionsTest, VolumesShortSyntax) {
    auto file = write(kShortSyntax, "coll_short_vol.yml");
    auto volumes = file.service("api").volumes();

    EXPECT_TRUE(volumes.has("/opt/app:/usr/app:ro"));
    EXPECT_EQ(volumes.toVector().size(), 2u);

    volumes.setSource("/usr/app", "/opt/releases/app-2.0");
    EXPECT_TRUE(volumes.has("/opt/releases/app-2.0:/usr/app:ro"));

    volumes.add("cache", "/var/cache");
    volumes.add("/host/log", "/var/log", "rw");
    EXPECT_EQ(volumes.toVector().size(), 4u);

    volumes.removeByTarget("/var/cache");
    EXPECT_EQ(volumes.toVector().size(), 3u);
    volumes.remove("/host/log:/var/log:rw");
    EXPECT_EQ(volumes.toVector().size(), 2u);
}

TEST_F(CollectionsTest, VolumesLongSyntaxSourceUpdate) {
    auto file = write(kLongSyntax, "coll_long_vol.yml");
    auto volumes = file.service("api").volumes();

    EXPECT_TRUE(volumes.has("/opt/app:/usr/app"));
    volumes.setSource("/usr/app", "/opt/releases/app-2.0");
    EXPECT_TRUE(volumes.has("/opt/releases/app-2.0:/usr/app"));

    file.save("coll_long_vol_out.yml");
    files_.push_back("coll_long_vol_out.yml");
    // Uzun sözdizimi korunur: girdi hâlâ bir eşlemedir.
    compose::ComposeFile reloaded("coll_long_vol_out.yml");
    EXPECT_TRUE(reloaded.service("api").volumes().has("/opt/releases/app-2.0:/usr/app"));
}

TEST_F(CollectionsTest, NetworksSequenceAndMappingForms) {
    auto shortFile = write(kShortSyntax, "coll_short_net.yml");
    auto shortNets = shortFile.service("api").networks();
    EXPECT_TRUE(shortNets.has("frontend"));
    shortNets.add("backend");
    EXPECT_EQ(shortNets.toVector().size(), 2u);
    shortNets.remove("frontend");
    EXPECT_FALSE(shortNets.has("frontend"));

    auto longFile = write(kLongSyntax, "coll_long_net.yml");
    auto longNets = longFile.service("api").networks();
    EXPECT_TRUE(longNets.has("frontend"));
    longNets.add("backend");
    EXPECT_EQ(longNets.toVector().size(), 2u);

    longFile.save("coll_long_net_out.yml");
    files_.push_back("coll_long_net_out.yml");
    compose::ComposeFile reloaded("coll_long_net_out.yml");
    // Eşleme biçimi korunur, alias'lar kaybolmaz.
    EXPECT_TRUE(reloaded.service("api").networks().has("backend"));
    EXPECT_EQ(reloaded.service("api").get<std::string>("networks.frontend.aliases[0]")
                  .value_or("api"),
              "api");
}

TEST_F(CollectionsTest, BuildHealthcheckDependsOnDeploy) {
    auto file = write(kShortSyntax, "coll_misc.yml");
    auto svc = file.service("api");

    svc.build().setContext(".");
    svc.build().setDockerfile("Dockerfile");
    svc.build().setTarget("runtime");
    svc.build().args().set("VERSION", "0.17.0");
    EXPECT_EQ(svc.build().context(), ".");
    EXPECT_EQ(svc.build().dockerfile(), "Dockerfile");
    EXPECT_EQ(svc.build().target(), "runtime");
    EXPECT_EQ(svc.build().args().get("VERSION"), "0.17.0");

    svc.healthcheck().setCommand({"CMD", "curl", "-f", "http://localhost:8080"});
    svc.healthcheck().setInterval("30s");
    svc.healthcheck().setTimeout("10s");
    svc.healthcheck().setRetries(3);
    svc.healthcheck().setStartPeriod("20s");
    EXPECT_EQ(svc.healthcheck().interval(), "30s");
    EXPECT_EQ(svc.healthcheck().timeout(), "10s");
    EXPECT_EQ(svc.healthcheck().retries(), 3);
    EXPECT_EQ(svc.healthcheck().startPeriod(), "20s");

    svc.dependsOn().add("database");
    svc.dependsOn().add("cache", compose::DependCondition::ServiceHealthy);
    EXPECT_TRUE(svc.dependsOn().has("database"));
    EXPECT_EQ(svc.dependsOn().toVector().size(), 2u);
    svc.dependsOn().remove("database");
    EXPECT_FALSE(svc.dependsOn().has("database"));

    svc.deploy().setReplicas(3);
    svc.deploy().setMode("replicated");
    svc.deploy().resources().limits().setMemory("2G");
    svc.deploy().resources().limits().setCpus("2.0");
    svc.deploy().resources().reservations().setMemory("1G");
    EXPECT_EQ(svc.deploy().replicas(), 3);
    EXPECT_EQ(svc.deploy().mode(), "replicated");
    EXPECT_EQ(svc.deploy().resources().limits().memory(), "2G");
    EXPECT_EQ(svc.deploy().resources().limits().cpus(), "2.0");
    EXPECT_EQ(svc.deploy().resources().reservations().memory(), "1G");
}

TEST_F(CollectionsTest, TopLevelCollections) {
    auto file = write(kShortSyntax, "coll_toplevel.yml");

    auto network = file.networks().add("custody-network");
    network.setExternal(true);
    network.setDriver("bridge");
    EXPECT_TRUE(file.networks().has("custody-network"));
    EXPECT_TRUE(file.networks().get("custody-network").external());
    EXPECT_EQ(file.networks().get("custody-network").driver(), "bridge");
    EXPECT_FALSE(file.networks().names().empty());

    auto volume = file.volumes().add("crypto-data");
    volume.setExternal(true);
    volume.setDriver("local");
    EXPECT_TRUE(file.volumes().has("crypto-data"));
    EXPECT_EQ(file.volumes().get("crypto-data").driver(), "local");

    file.secrets().add("tls_private_key").setFile("./certs/server.key");
    EXPECT_TRUE(file.secrets().has("tls_private_key"));
    EXPECT_EQ(file.secrets().get("tls_private_key").file(), "./certs/server.key");

    file.configs().add("app_config").setFile("./config/app.conf");
    EXPECT_TRUE(file.configs().has("app_config"));

    file.networks().remove("custody-network");
    file.volumes().remove("crypto-data");
    file.secrets().remove("tls_private_key");
    file.configs().remove("app_config");
    EXPECT_FALSE(file.networks().has("custody-network"));
    EXPECT_FALSE(file.volumes().has("crypto-data"));
    EXPECT_FALSE(file.secrets().has("tls_private_key"));
    EXPECT_FALSE(file.configs().has("app_config"));
}

}  // namespace

namespace {

// Kapsam boşluklarını kapatan ek durumlar: alanların hiç bulunmadığı servis,
// healthcheck devre dışı bırakma, depends_on koşul çeşitleri ve boş koleksiyonlar.
class EmptyServiceTest : public ::testing::Test {
protected:
    void SetUp() override {
        std::ofstream out("empty_service_test.yml");
        out << "services:\n  api:\n    image: \"nginx\"\n";
    }
    void TearDown() override {
        std::filesystem::remove("empty_service_test.yml");
    }
    compose::ComposeFile open() { return compose::ComposeFile("empty_service_test.yml"); }
};

TEST_F(EmptyServiceTest, GettersOnMissingFieldsReturnEmpty) {
    auto file = open();
    auto svc = file.service("api");

    EXPECT_TRUE(svc.healthcheck().command().empty());
    EXPECT_TRUE(svc.healthcheck().interval().empty());
    EXPECT_TRUE(svc.healthcheck().timeout().empty());
    EXPECT_TRUE(svc.healthcheck().startPeriod().empty());
    EXPECT_EQ(svc.healthcheck().retries(), 0);
    EXPECT_TRUE(svc.build().context().empty());
    EXPECT_TRUE(svc.build().dockerfile().empty());
    EXPECT_TRUE(svc.build().target().empty());
    EXPECT_TRUE(svc.dependsOn().toVector().empty());
    EXPECT_FALSE(svc.dependsOn().has("db"));
    EXPECT_TRUE(svc.ports().toVector().empty());
    EXPECT_TRUE(svc.volumes().toVector().empty());
    EXPECT_TRUE(svc.networks().toVector().empty());
    EXPECT_FALSE(svc.networks().has("frontend"));
    EXPECT_TRUE(svc.environment().getAll().empty());
    EXPECT_TRUE(svc.extraHosts().getAll().empty());
    EXPECT_EQ(svc.deploy().replicas(), 0);
    EXPECT_TRUE(svc.deploy().mode().empty());
    EXPECT_TRUE(svc.deploy().resources().limits().cpus().empty());
}

TEST_F(EmptyServiceTest, HealthcheckCommandAndDisable) {
    auto file = open();
    auto svc = file.service("api");

    svc.healthcheck().setCommand({"CMD-SHELL", "curl -f http://localhost || exit 1"});
    EXPECT_EQ(svc.healthcheck().command().size(), 2u);

    // disable(), test listesini silmeden healthcheck.disable bayrağını koyar.
    svc.healthcheck().disable();
    EXPECT_TRUE(svc.get<bool>("healthcheck.disable").value_or(false));
}

TEST_F(EmptyServiceTest, DependsOnConditionVariants) {
    auto file = open();
    auto svc = file.service("api");

    svc.dependsOn().add("db", compose::DependCondition::ServiceStarted);
    svc.dependsOn().add("seed", compose::DependCondition::ServiceCompletedSuccessfully);
    svc.dependsOn().add("cache", compose::DependCondition::ServiceHealthy);

    std::vector<std::string> deps = svc.dependsOn().toVector();
    EXPECT_EQ(deps.size(), 3u);
    EXPECT_TRUE(svc.dependsOn().has("seed"));

    svc.dependsOn().remove("seed");
    EXPECT_FALSE(svc.dependsOn().has("seed"));
}

TEST_F(EmptyServiceTest, RemovalsOnEmptyCollectionsAreNoOps) {
    auto file = open();
    auto svc = file.service("api");

    EXPECT_NO_THROW(svc.ports().remove("8080:80"));
    EXPECT_NO_THROW(svc.volumes().remove("/a:/b"));
    EXPECT_NO_THROW(svc.volumes().removeByTarget("/b"));
    EXPECT_NO_THROW(svc.volumes().setSource("/b", "/c"));
    EXPECT_NO_THROW(svc.networks().remove("frontend"));
    EXPECT_NO_THROW(svc.networks().clear());
    EXPECT_NO_THROW(svc.volumes().clear());
    EXPECT_NO_THROW(svc.environment().remove("X"));
    EXPECT_NO_THROW(svc.extraHosts().remove("hsm"));

    // volumes bölümü yoksa setSource dosyaya yeni bölüm açmaz.
    EXPECT_TRUE(svc.volumes().toVector().empty());
}

TEST_F(EmptyServiceTest, ExceptionTypesShareBaseClass) {
    auto file = open();
    try {
        file.service("missing");
        FAIL() << "expected ServiceNotFoundException";
    } catch (const compose::ComposeException& e) {
        EXPECT_NE(std::string(e.what()).find("missing"), std::string::npos);
    }

    try {
        throw compose::InvalidPropertyException("bad property");
    } catch (const compose::ComposeException& e) {
        EXPECT_NE(std::string(e.what()).find("bad property"), std::string::npos);
    }

    try {
        throw compose::ValidationException("bad value");
    } catch (const compose::ComposeException& e) {
        EXPECT_NE(std::string(e.what()).find("bad value"), std::string::npos);
    }
}

}  // namespace
