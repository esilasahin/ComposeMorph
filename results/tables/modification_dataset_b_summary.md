# Experiment 2 -- Targeted Modification / Change Locality -- Dataset B

Total (op, file) cases evaluated: **1467**

Change Locality Ratio = Expected Changed Lines (1) / Actual Changed Lines. Adjusted ratio further divides by (Actual - that file's own identity-round-trip noise from Experiment 1), isolating the edit's footprint from the library's baseline re-serialization noise (quote/flow-style normalization, blank-line loss).

## Per-property results

| Op | N | Success | Median actual changed lines | Median locality ratio | Median adjusted ratio |
|---|---|---|---|---|---|
| image | 200 | 200/200 | 13.0 | 0.0769 | 1.0000 |
| hostname | 39 | 39/39 | 31.0 | 0.0323 | 1.0000 |
| restart | 200 | 200/200 | 14.0 | 0.0714 | 1.0000 |
| env | 200 | 200/200 | 15.0 | 0.0667 | 1.0000 |
| port | 200 | 199/200 | 12.0 | 0.0833 | 1.0000 |
| volume-source | 200 | 200/200 | 13.0 | 0.0769 | 1.0000 |
| extra-host | 34 | 34/34 | 105.0 | 0.0095 | 1.0000 |
| network | 200 | 169/200 | 19.0 | 0.0526 | 1.0000 |
| healthcheck-retries | 185 | 185/185 | 19.0 | 0.0526 | 1.0000 |
| deploy-cpus | 9 | 9/9 | 25.0 | 0.0400 | 1.0000 |

## Notes

- `port`, `extra-host`, `network`: the library's API only exposes `add`/`remove` (no in-place setter), so the single targeted change modelled here is *adding one entry* to an existing list, not replacing an existing value.
- `volume-source`: only short-syntax volume entries (`source:target[:mode]`) are eligible -- `Volumes::setSource` calls `.as<std::string>()` on each entry and throws on long-syntax (mapping) volume definitions, so files using only long syntax are skipped.
- `port`: `Ports::has` (called by `add` to avoid duplicates) runs `.as<std::string>()` over every existing entry, so a service whose `ports` list mixes short-syntax strings with a long-syntax (mapping) port definition throws a yaml-cpp bad-conversion error -- the same short-syntax-only assumption seen in `Volumes` and `Networks`.
- `network`: eligibility only requires a `networks` key to exist, but `Networks::add` pushes onto it without checking the node is a sequence. Services using the long (mapping) `networks:` syntax cause `add` to throw ("appending to a non-sequence") -- a real library bug surfaced by this experiment, left visible below rather than filtered out.

## Failures (32)

- `port` / `ToolboxAid__Docker-Assistant__templates_portainer_docker-compose.yml.yml` (service `agent`): APPLY_FAILED: yaml-cpp: error at line 37, column 9: bad conversion
- `network` / `4linux__540__mentoria_compose_frontend2_docker-compose.yml.yml` (service `app-frontend2`): APPLY_FAILED: appending to a non-sequence
- `network` / `DigneZzZ__dwg__docker-compose.yml.CLI.yml` (service `adguardhome`): APPLY_FAILED: appending to a non-sequence
- `network` / `DigneZzZ__dwg__docker-compose.yml.DARK.yml` (service `adwireguard`): APPLY_FAILED: appending to a non-sequence
- `network` / `EnigmaCurry__d.rymcg.tech__jitsi-meet_docker-compose.yaml.yml` (service `jicofo`): APPLY_FAILED: appending to a non-sequence
- `network` / `Gustav0Prado__trab-seguranca__docker-compose.yml.yml` (service `trusted-server`): APPLY_FAILED: appending to a non-sequence
- `network` / `Hamada-khairi__Hamada-HomeLab__docker-compose.yml.yml` (service `adguardhome-sync`): APPLY_FAILED: appending to a non-sequence
- `network` / `PacktPublishing__PHP-8-Programming-Cookbook__docker-compose.yml.bak.yml` (service `mysql`): APPLY_FAILED: appending to a non-sequence
- `network` / `botAGI__AGmind__tests_golden_expected_cluster_peer_docker-compose.rendered.yml.yml` (service `api`): APPLY_FAILED: appending to a non-sequence
- `network` / `botAGI__AGmind__tests_golden_expected_full_lan_docker-compose.rendered.yml.yml` (service `api`): APPLY_FAILED: appending to a non-sequence
- `network` / `botAGI__AGmind__tests_golden_expected_minimal_lan_docker-compose.rendered.yml.yml` (service `api`): APPLY_FAILED: appending to a non-sequence
- `network` / `botAGI__AGmind__tests_golden_expected_rag_milvus_docker-compose.rendered.yml.yml` (service `api`): APPLY_FAILED: appending to a non-sequence
- `network` / `botAGI__AGmind__tests_golden_expected_ragflow_docker-compose.rendered.yml.yml` (service `api`): APPLY_FAILED: appending to a non-sequence
- `network` / `codename-co__stack__hub_jitsi_compose.yaml.yml` (service `jicofo`): APPLY_FAILED: appending to a non-sequence
- `network` / `codename-co__stack__hub_mailcow_compose.yaml.yml` (service `clamd-mailcow`): APPLY_FAILED: appending to a non-sequence
- `network` / `cvaghela__service-dash__appstore_Apps_ServiceDash_docker-compose.yml.yml` (service `claude-usage`): APPLY_FAILED: appending to a non-sequence
- `network` / `deeztek__Hermes-Secure-Email-Gateway__docker-compose.yml.yml` (service `hermes_authelia`): APPLY_FAILED: appending to a non-sequence
- `network` / `deployable-sh__stacks__supabase_upstream-docker-compose.yml.yml` (service `kong`): APPLY_FAILED: appending to a non-sequence
- `network` / `donato-marcos__homelab-containers__container_docker_standalone_storage_alarik_docker-compose.cluster.yaml.yml` (service `api01`): APPLY_FAILED: appending to a non-sequence
- `network` / `eyadsibai__machine-learning-docker-image__docker-compose.yml_bak.yml` (service `modeldb_backend`): APPLY_FAILED: appending to a non-sequence
- `network` / `garutilorenzo__mysql-ha-docker__.docker-compose.yml-ci.yml` (service `heartbeat`): APPLY_FAILED: appending to a non-sequence
- `network` / `ghe16__SD_IoT__docker-compose.yml.yml` (service `kafdrop`): APPLY_FAILED: appending to a non-sequence
- `network` / `hiqdev__billing-hiapi__docker-compose.yml.dist.yml` (service `nginx`): APPLY_FAILED: appending to a non-sequence
- `network` / `hiqdev__hisite__docker-compose.yml.dist.yml` (service `nginx`): APPLY_FAILED: appending to a non-sequence
- `network` / `ishayyemini__wpa3_attack__admin_CTFd_docker-compose.yml.yml` (service `cache`): APPLY_FAILED: appending to a non-sequence
- `network` / `jmquigley__dotfiles__conf_containers_base_docker-compose.yml.yml` (service `database`): APPLY_FAILED: appending to a non-sequence
- `network` / `kryman0__find_ip__docker-compose.yml.yml` (service `client`): APPLY_FAILED: appending to a non-sequence
- `network` / `lachouettecoop__chouette-odoo__docker-compose.yml.dev.yml` (service `db`): APPLY_FAILED: appending to a non-sequence
- `network` / `lmnaslimited__lmnas-next__docker_development_docker-compose.yml.yml` (service `frontend`): APPLY_FAILED: appending to a non-sequence
- `network` / `me-cedric__htpc-box-docker__docker-compose.yml.yml` (service `bazarr`): APPLY_FAILED: appending to a non-sequence
- `network` / `mgarralda__hadoop-spark-cluster__docker-compose.yml.bck.yml` (service `master`): APPLY_FAILED: appending to a non-sequence
- `network` / `nxmatic__gha-runner__gha_docker-compose.yml.yml` (service `gha-kms`): APPLY_FAILED: appending to a non-sequence
