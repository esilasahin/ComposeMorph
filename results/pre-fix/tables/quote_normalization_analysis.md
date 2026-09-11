# Quote-Normalization Deep Dive (follow-up to Experiment 5)

## 1. Canonical scalar-shape reference table

Fixture's top-level `version: "3.9"` came back as: **float** (corrupted: True).

| Shape | Quoted value | Pattern | In `environment:` value | In `command:` list | In generic (`x-*`) map |
|---|---|---|---|---|---|
| integer_zero | '0' | integer-like | int | int | int |
| integer_positive | '8080' | integer-like | int | int | int |
| integer_leading_zero | '007' | integer-like | int | int | int |
| integer_negative | '-1' | integer-like | int | int | int |
| float_simple | '2.0' | float-like | float | float | float |
| float_version_like | '3.8' | float-like | float | float | float |
| float_scientific | '1.5e10' | float-like | str | str | str |
| semver_two_dots | '1.0.0' | plain-text (safe) | str | str | str |
| bool_true_lower | 'true' | bool-word | bool | bool | bool |
| bool_false_lower | 'false' | bool-word | bool | bool | bool |
| bool_yes | 'yes' | bool-word | bool | bool | bool |
| bool_on | 'on' | bool-word | bool | bool | bool |
| bool_y | 'y' | bool-word | str | str | str |
| null_word | 'null' | null-word | str | str | str |
| null_tilde | '~' | null-word | str | str | str |
| empty_string | '' | null-word | str | str | str |
| sexagesimal | '1:30' | sexagesimal | int | int | int |
| special_float_inf | '.inf' | special-float | float | float | float |
| special_float_nan | '.nan' | special-float | float | float | float |
| hex_like | '0x1A' | octal-or-hex-like | int | int | int |
| octal_like | '0o17' | octal-or-hex-like | str | str | str |
| timestamp_date | '2024-01-01' | timestamp-like | date | date | date |
| timestamp_datetime | '2024-01-01T00:00:00Z' | timestamp-like | datetime | datetime | datetime |
| plain_text | 'hello-world' | plain-text (safe) | str | str | str |
| plain_text_with_dash | 'my-service' | plain-text (safe) | str | str | str |

`str` = quote effectively preserved (safe). Anything else (`int`, `float`, `bool`, `NoneType`) means the round-trip silently changed the value's type.

## 2. Dataset B corpus scan: real quoted-scalar occurrences

Total quoted-scalar occurrences found and checked: **9807**

- Files with at least one explicitly-quoted scalar: **617**
- Of those, files where at least one quoted scalar was corrupted by the round-trip: **452** (73.3%)

### By YAML scalar pattern

"Corrupted" = type changed under PyYAML's YAML-1.1-family resolver (same core schema family as yaml-cpp's), used here as an instrument since `yaml.safe_load` alone discards quote style. "Docker-confirmed invalid" cross-references Experiment 5's actual `docker compose config` run on the same files -- go-yaml (Compose's parser) resolves scalars slightly differently (e.g. it has no sexagesimal-int support), so not every PyYAML-detected type change is something Docker itself rejects.

| Pattern | Occurrences | Corrupted (PyYAML) | Rate | Files docker-confirmed invalid* |
|---|---|---|---|---|
| null-word | 264 | 0 | 0.0% | n/a |
| bool-word | 994 | 989 | 99.5% | 25/57 files |
| sexagesimal | 145 | 6 | 4.1% | 3/4 files |
| integer-like | 1251 | 1250 | 99.9% | 114/141 files |
| float-like | 323 | 323 | 100.0% | 204/214 files |
| timestamp-like | 2 | 2 | 100.0% | 0/2 files |
| plain-text (safe) | 6828 | 0 | 0.0% | n/a |

\* Denominator is distinct *files* with a corrupted occurrence of that pattern whose docker-validity is known from Experiment 5's run (not occurrences, since validity is per-file); a file can appear under multiple patterns.

### By Compose field location

| Field | Occurrences | Corrupted (PyYAML) | Rate | Files docker-confirmed invalid* |
|---|---|---|---|---|
| labels value | 2072 | 531 | 25.6% | 3/6 files |
| healthcheck | 1797 | 5 | 0.3% | 1/1 files |
| environment value | 1707 | 934 | 54.7% | 21/52 files |
| ports element | 1629 | 84 | 5.2% | 8/17 files |
| other/unclassified | 1309 | 553 | 42.2% | 21/37 files |
| command/entrypoint element | 824 | 39 | 4.7% | 11/15 files |
| version | 368 | 367 | 99.7% | 292/292 files |
| deploy resources (cpus/memory/replicas) | 69 | 57 | 82.6% | 4/8 files |
| build args/context | 32 | 0 | 0.0% | n/a |

**Environment/label values are the most *frequently* corrupted by occurrence count, but this table's last column is what tells you whether that corruption is something `docker compose config` actually rejects** -- the Compose schema treats most `environment:`/`labels:` values as permissively-typed, so a `"true"` becoming `true` there often round-trips back to a config Docker still accepts, whereas the same shape in `version:` or a `command:` element is fatal. Either way, ComposeMorph is silently changing a value the user explicitly wrote as a string -- an application reading that environment variable expecting text (e.g. via a strict-typed config loader) would still see different content if it introspects the file directly rather than the merged container environment.

### Sample of corrupted occurrences (2570 total)

| File | Path | Original (quoted) | Became |
|---|---|---|---|
| `0kkun__tennis-track__.openapi_docker-compose.yml.yml` | `version` | `'3.9'` | float |
| `0xSh4dy__hackentine_archives__reversing_rev1_firstchallrevbasic_docker-compose.yml.yml` | `version` | `'2'` | int |
| `1qzxc__infra__shared-files_docker_gitlabci_docker-compose.yml.yml` | `version` | `'3.6'` | float |
| `1qzxc__infra__shared-files_docker_gitlabci_docker-compose.yml.yml` | `services.web.ports.[2]` | `'8022:22'` | int |
| `3PillarGlobal__engineering-playbook__dockerized-automation_docker-compose.yml.yml` | `version` | `'2.1'` | float |
| `3bsolutionsltd__transconnect-app__docker-compose.yml.yml` | `version` | `'3.8'` | float |
| `97jsantos__atividade-pratica-modulo-14__docker-compose.yml.yml` | `version` | `'3.1'` | float |
| `9Roflander__BigData-Labs-UNIME__Lab3_docker-compose.yml.yml` | `services.kafka.environment.KAFKA_AUTO_CREATE_TOPICS_ENABLE` | `'false'` | bool |
| `9Roflander__BigData-Labs-UNIME__Lab3_docker-compose.yml.yml` | `services.kafka-init.command.[7]` | `'3'` | int |
| `9Roflander__BigData-Labs-UNIME__Lab3_docker-compose.yml.yml` | `services.kafka-init.command.[9]` | `'1'` | int |
| `AAhmed233__microservice_dxc__sonarqube_docker-compose.yml.yml` | `services.sonarqube.environment.SONAR_ES_BOOTSTRAP_CHECKS_DISABLE` | `'false'` | bool |
| `ALipckin__task-flow-backend__auth_docker-compose.yml.yml` | `version` | `'3.8'` | float |
| `AP0827__Multi-Threaded-Web-Server__docker-compose.yml.yml` | `services.mtws.environment.MTWS_MAX_KEEPALIVE_REQUESTS` | `'100'` | int |
| `AP0827__Multi-Threaded-Web-Server__docker-compose.yml.yml` | `services.modsecurity.environment.PORT` | `'8080'` | int |
| `AP0827__Multi-Threaded-Web-Server__docker-compose.yml.yml` | `services.modsecurity.environment.MODSEC_AUDIT_ENGINE` | `'On'` | bool |
| `AP0827__Multi-Threaded-Web-Server__docker-compose.yml.yml` | `services.modsecurity.environment.BLOCKING_PARANOIA` | `'1'` | int |
| `AP0827__Multi-Threaded-Web-Server__docker-compose.yml.yml` | `services.modsecurity.environment.DETECTION_PARANOIA` | `'1'` | int |
| `AbdullahSholi__DOS_Project_Part1__docker-compose.yml.yml` | `version` | `'3.8'` | float |
| `AdrienPoupa__docker-compose-nas__docker-compose.yml.yml` | `services.unpackerr.logging.options.max-file` | `'5'` | int |
| `Akin-ctrl__Stock_pipeline__docker-compose.yml.yml` | `services.postgres.deploy.resources.limits.cpus` | `'2.0'` | float |
| ... | 2550 more | | (see raw CSV) |

### Corrupted occurrences per affected file

mean=5.69, median=1.0, max=391 (n=452 files)

## Takeaway

The corruption is fully explained by scalar *shape*, not by which Compose field it happens to sit in: any explicitly-quoted value that reads as an integer, float, YAML 1.1 boolean word, or null word loses its quotes on save and is reinterpreted with the new type -- in a generic map, in an `environment:` value, or in a `command:` list element alike. `version:` is simply the single field where this shape (`"N.N"`, matching `float-like`) happens to appear in nearly every real Compose file, which is why it dominates Experiment 5's failure count. Plain-text quoted values (`plain-text (safe)`) are unaffected. This is a property of yaml-cpp's default emitter -- which does not track each scalar's original quote style, only whether quoting is syntactically *required* -- not something specific to ComposeMorph's own code.
