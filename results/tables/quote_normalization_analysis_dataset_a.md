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

## 2. Dataset A (controlled corpus) corpus scan: real quoted-scalar occurrences

- Quoted-scalar occurrences checked: **62** in **18** files
- yaml-cpp baseline (before fix): **22** occurrences changed type, in **9** files (50.0% of files with quoted scalars)
- ComposeMorph: **0** occurrences changed type, in **0** files (0.0% of files with quoted scalars)

"Corrupted" = the value at the same path no longer resolves to `str` under PyYAML (YAML 1.1 resolution rules). "Files docker-invalid" joins Experiment 5's `docker compose config` result for that editor's output of the same file; go-yaml, Compose's parser, resolves some shapes differently (e.g. no sexagesimal ints), so not every PyYAML-level type change is rejected by Docker.

### By YAML scalar pattern

| Pattern | Occurrences | yaml-cpp baseline (before fix): corrupted | yaml-cpp baseline (before fix): files docker-invalid* | ComposeMorph: corrupted | ComposeMorph: files docker-invalid* |
|---|---|---|---|---|---|
| null-word | 2 | 0 (0.0%) | n/a | 0 (0.0%) | n/a |
| bool-word | 4 | 4 (100.0%) | 1/2 | 0 (0.0%) | n/a |
| sexagesimal | 2 | 0 (0.0%) | n/a | 0 (0.0%) | n/a |
| integer-like | 9 | 9 (100.0%) | 1/5 | 0 (0.0%) | n/a |
| float-like | 9 | 9 (100.0%) | 1/2 | 0 (0.0%) | n/a |
| plain-text (safe) | 36 | 0 (0.0%) | n/a | 0 (0.0%) | n/a |

### By Compose field location

| Field | Occurrences | yaml-cpp baseline (before fix): corrupted | yaml-cpp baseline (before fix): files docker-invalid* | ComposeMorph: corrupted | ComposeMorph: files docker-invalid* |
|---|---|---|---|---|---|
| environment value | 14 | 8 (57.1%) | 1/2 | 0 (0.0%) | n/a |
| other/unclassified | 13 | 3 (23.1%) | 0/2 | 0 (0.0%) | n/a |
| healthcheck | 8 | 0 (0.0%) | n/a | 0 (0.0%) | n/a |
| ports element | 8 | 2 (25.0%) | 0/1 | 0 (0.0%) | n/a |
| labels value | 5 | 0 (0.0%) | n/a | 0 (0.0%) | n/a |
| version | 4 | 4 (100.0%) | 1/1 | 0 (0.0%) | n/a |
| deploy resources (cpus/memory/replicas) | 4 | 4 (100.0%) | 0/1 | 0 (0.0%) | n/a |
| command/entrypoint element | 4 | 1 (25.0%) | 1/1 | 0 (0.0%) | n/a |
| build args/context | 2 | 0 (0.0%) | n/a | 0 (0.0%) | n/a |

\* Distinct files with a corrupted occurrence in that group whose docker validity is known from Experiment 5 (validity is per file, not per occurrence).

### yaml-cpp baseline (before fix): sample of corrupted occurrences (22 total)

| File | Path | Original (quoted) | Became |
|---|---|---|---|
| `full-featured.yml` | `version` | `'3.9'` | float |
| `full-featured.yml` | `x-default-logging.options.max-file` | `'3'` | int |
| `full-featured.yml` | `services.web.ports.[1].published` | `'8443'` | int |
| `full-featured.yml` | `services.web.deploy.resources.limits.cpus` | `'1.0'` | float |
| `full-featured.yml` | `services.api.environment.PORT` | `'3000'` | int |
| `full-featured.yml` | `services.api.environment.DEBUG` | `'false'` | bool |
| `quoted-scalar-types.yml` | `version` | `'3.9'` | float |
| `quoted-scalar-types.yml` | `services.app.environment.FEATURE_FLAG` | `'true'` | bool |
| `quoted-scalar-types.yml` | `services.app.environment.RETRY_COUNT` | `'3'` | int |
| `quoted-scalar-types.yml` | `services.app.environment.TIMEOUT_SECONDS` | `'2.5'` | float |
| `quoted-scalar-types.yml` | `services.app.environment.DEBUG_MODE` | `'yes'` | bool |
| `quoted-scalar-types.yml` | `services.app.command.[2]` | `'4'` | int |
| `deploy.yml` | `services.worker.deploy.resources.limits.cpus` | `'2.0'` | float |
| `deploy.yml` | `services.worker.deploy.resources.reservations.cpus` | `'0.5'` | float |
| `environment-long.yml` | `services.api.environment.PORT` | `'3000'` | int |
| `environment-long.yml` | `services.api.environment.DEBUG` | `'false'` | bool |
| `logging.yml` | `services.app.logging.options.max-file` | `'3'` | int |
| `ports-long.yml` | `services.web.ports.[0].published` | `'8080'` | int |
| `sysctls.yml` | `services.app.sysctls.net.ipv4.tcp_syncookies` | `'0'` | int |
| `preservation-edge-cases.yml` | `version` | `'3.9'` | float |
| ... | 2 more | | (see raw CSV) |

## Mechanism

yaml-cpp's parser marks every quoted scalar with the non-specific tag `!` (plain scalars get `?`), but its emitter ignores that tag: `IsValidPlainScalar` in yaml-cpp 0.8.0's `src/emitterutils.cpp` writes a string without quotes unless it is null-like (`IsNullString`) or syntactically unsafe. That is why only the null-word shapes keep their quotes in the baseline column. ComposeMorph's serializer writes every `!`-tagged scalar double-quoted and leaves `?`-tagged (plain) scalars plain; see `src/ScalarQuoting.cpp`.
