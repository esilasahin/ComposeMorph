# Quoted-Scalar Type Stability (follow-up to Experiment 5)

## 1. Canonical scalar-shape reference table

- yaml-cpp baseline (before fix): quoted top-level `version: "3.9"` came back as **float**
- ComposeMorph: quoted top-level `version: "3.9"` came back as **str**

Each cell gives the resolved type after the round-trip in an `environment:` value / a `command:` element / an `x-*` map. `str` everywhere means the quotes held.

| Shape | Quoted value | Pattern | yaml-cpp baseline (before fix) | ComposeMorph |
|---|---|---|---|---|
| integer_zero | '0' | integer-like | int / int / int | str / str / str |
| integer_positive | '8080' | integer-like | int / int / int | str / str / str |
| integer_leading_zero | '007' | integer-like | int / int / int | str / str / str |
| integer_negative | '-1' | integer-like | int / int / int | str / str / str |
| float_simple | '2.0' | float-like | float / float / float | str / str / str |
| float_version_like | '3.8' | float-like | float / float / float | str / str / str |
| float_scientific | '1.5e10' | float-like | str / str / str | str / str / str |
| semver_two_dots | '1.0.0' | plain-text (safe) | str / str / str | str / str / str |
| bool_true_lower | 'true' | bool-word | bool / bool / bool | str / str / str |
| bool_false_lower | 'false' | bool-word | bool / bool / bool | str / str / str |
| bool_yes | 'yes' | bool-word | bool / bool / bool | str / str / str |
| bool_on | 'on' | bool-word | bool / bool / bool | str / str / str |
| bool_y | 'y' | bool-word | str / str / str | str / str / str |
| null_word | 'null' | null-word | str / str / str | str / str / str |
| null_tilde | '~' | null-word | str / str / str | str / str / str |
| empty_string | '' | null-word | str / str / str | str / str / str |
| sexagesimal | '1:30' | sexagesimal | int / int / int | str / str / str |
| special_float_inf | '.inf' | special-float | float / float / float | str / str / str |
| special_float_nan | '.nan' | special-float | float / float / float | str / str / str |
| hex_like | '0x1A' | octal-or-hex-like | int / int / int | str / str / str |
| octal_like | '0o17' | octal-or-hex-like | str / str / str | str / str / str |
| timestamp_date | '2024-01-01' | timestamp-like | date / date / date | str / str / str |
| timestamp_datetime | '2024-01-01T00:00:00Z' | timestamp-like | datetime / datetime / datetime | str / str / str |
| plain_text | 'hello-world' | plain-text (safe) | str / str / str | str / str / str |
| plain_text_with_dash | 'my-service' | plain-text (safe) | str / str / str | str / str / str |

## 2. Dataset B corpus scan: real quoted-scalar occurrences

- Quoted-scalar occurrences checked: **9807** in **617** files
- yaml-cpp baseline (before fix): **2570** occurrences changed type, in **452** files (73.3% of files with quoted scalars)
- ComposeMorph: **0** occurrences changed type, in **0** files (0.0% of files with quoted scalars)

"Corrupted" = the value at the same path no longer resolves to `str` under PyYAML (YAML 1.1 resolution rules). "Files docker-invalid" joins Experiment 5's `docker compose config` result for that editor's output of the same file; go-yaml, Compose's parser, resolves some shapes differently (e.g. no sexagesimal ints), so not every PyYAML-level type change is rejected by Docker.

### By YAML scalar pattern

| Pattern | Occurrences | yaml-cpp baseline (before fix): corrupted | yaml-cpp baseline (before fix): files docker-invalid* | ComposeMorph: corrupted | ComposeMorph: files docker-invalid* |
|---|---|---|---|---|---|
| null-word | 264 | 0 (0.0%) | n/a | 0 (0.0%) | n/a |
| bool-word | 994 | 989 (99.5%) | 25/57 | 0 (0.0%) | n/a |
| sexagesimal | 145 | 6 (4.1%) | 3/4 | 0 (0.0%) | n/a |
| integer-like | 1251 | 1250 (99.9%) | 114/141 | 0 (0.0%) | n/a |
| float-like | 323 | 323 (100.0%) | 204/214 | 0 (0.0%) | n/a |
| timestamp-like | 2 | 2 (100.0%) | 0/2 | 0 (0.0%) | n/a |
| plain-text (safe) | 6828 | 0 (0.0%) | n/a | 0 (0.0%) | n/a |

### By Compose field location

| Field | Occurrences | yaml-cpp baseline (before fix): corrupted | yaml-cpp baseline (before fix): files docker-invalid* | ComposeMorph: corrupted | ComposeMorph: files docker-invalid* |
|---|---|---|---|---|---|
| labels value | 2072 | 531 (25.6%) | 3/6 | 0 (0.0%) | n/a |
| healthcheck | 1797 | 5 (0.3%) | 1/1 | 0 (0.0%) | n/a |
| environment value | 1707 | 934 (54.7%) | 21/52 | 0 (0.0%) | n/a |
| ports element | 1629 | 84 (5.2%) | 8/17 | 0 (0.0%) | n/a |
| other/unclassified | 1309 | 553 (42.2%) | 21/37 | 0 (0.0%) | n/a |
| command/entrypoint element | 824 | 39 (4.7%) | 11/15 | 0 (0.0%) | n/a |
| version | 368 | 367 (99.7%) | 292/292 | 0 (0.0%) | n/a |
| deploy resources (cpus/memory/replicas) | 69 | 57 (82.6%) | 4/8 | 0 (0.0%) | n/a |
| build args/context | 32 | 0 (0.0%) | n/a | 0 (0.0%) | n/a |

\* Distinct files with a corrupted occurrence in that group whose docker validity is known from Experiment 5 (validity is per file, not per occurrence).

### yaml-cpp baseline (before fix): sample of corrupted occurrences (2570 total)

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

## Mechanism

yaml-cpp's parser marks every quoted scalar with the non-specific tag `!` (plain scalars get `?`), but its emitter ignores that tag: `IsValidPlainScalar` in yaml-cpp 0.8.0's `src/emitterutils.cpp` writes a string without quotes unless it is null-like (`IsNullString`) or syntactically unsafe. That is why only the null-word shapes keep their quotes in the baseline column. ComposeMorph's serializer writes every `!`-tagged scalar double-quoted and leaves `?`-tagged (plain) scalars plain; see `src/ScalarQuoting.cpp`.
