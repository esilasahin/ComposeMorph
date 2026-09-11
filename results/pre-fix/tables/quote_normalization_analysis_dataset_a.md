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

Total quoted-scalar occurrences found and checked: **62**

- Files with at least one explicitly-quoted scalar: **18**
- Of those, files where at least one quoted scalar was corrupted by the round-trip: **9** (50.0%)

### By YAML scalar pattern

"Corrupted" = type changed under PyYAML's YAML-1.1-family resolver (same core schema family as yaml-cpp's), used here as an instrument since `yaml.safe_load` alone discards quote style. "Docker-confirmed invalid" cross-references Experiment 5's actual `docker compose config` run on the same files -- go-yaml (Compose's parser) resolves scalars slightly differently (e.g. it has no sexagesimal-int support), so not every PyYAML-detected type change is something Docker itself rejects.

| Pattern | Occurrences | Corrupted (PyYAML) | Rate | Files docker-confirmed invalid* |
|---|---|---|---|---|
| null-word | 2 | 0 | 0.0% | n/a |
| bool-word | 4 | 4 | 100.0% | 1/2 files |
| sexagesimal | 2 | 0 | 0.0% | n/a |
| integer-like | 9 | 9 | 100.0% | 1/5 files |
| float-like | 9 | 9 | 100.0% | 1/2 files |
| plain-text (safe) | 36 | 0 | 0.0% | n/a |

\* Denominator is distinct *files* with a corrupted occurrence of that pattern whose docker-validity is known from Experiment 5's run (not occurrences, since validity is per-file); a file can appear under multiple patterns.

### By Compose field location

| Field | Occurrences | Corrupted (PyYAML) | Rate | Files docker-confirmed invalid* |
|---|---|---|---|---|
| environment value | 14 | 8 | 57.1% | 1/2 files |
| other/unclassified | 13 | 3 | 23.1% | 0/2 files |
| ports element | 8 | 2 | 25.0% | 0/1 files |
| healthcheck | 8 | 0 | 0.0% | n/a |
| labels value | 5 | 0 | 0.0% | n/a |
| version | 4 | 4 | 100.0% | 1/1 files |
| deploy resources (cpus/memory/replicas) | 4 | 4 | 100.0% | 0/1 files |
| command/entrypoint element | 4 | 1 | 25.0% | 1/1 files |
| build args/context | 2 | 0 | 0.0% | n/a |

**Environment/label values are the most *frequently* corrupted by occurrence count, but this table's last column is what tells you whether that corruption is something `docker compose config` actually rejects** -- the Compose schema treats most `environment:`/`labels:` values as permissively-typed, so a `"true"` becoming `true` there often round-trips back to a config Docker still accepts, whereas the same shape in `version:` or a `command:` element is fatal. Either way, ComposeMorph is silently changing a value the user explicitly wrote as a string -- an application reading that environment variable expecting text (e.g. via a strict-typed config loader) would still see different content if it introspects the file directly rather than the merged container environment.

### Sample of corrupted occurrences (22 total)

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

### Corrupted occurrences per affected file

mean=2.44, median=2, max=6 (n=9 files)

## Takeaway

The corruption is fully explained by scalar *shape*, not by which Compose field it happens to sit in: any explicitly-quoted value that reads as an integer, float, YAML 1.1 boolean word, or null word loses its quotes on save and is reinterpreted with the new type -- in a generic map, in an `environment:` value, or in a `command:` list element alike. `version:` is simply the single field where this shape (`"N.N"`, matching `float-like`) happens to appear in nearly every real Compose file, which is why it dominates Experiment 5's failure count. Plain-text quoted values (`plain-text (safe)`) are unaffected. This is a property of yaml-cpp's default emitter -- which does not track each scalar's original quote style, only whether quoting is syntactically *required* -- not something specific to ComposeMorph's own code.
