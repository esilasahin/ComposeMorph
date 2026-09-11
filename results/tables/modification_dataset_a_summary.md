# Experiment 2 -- Targeted Modification / Change Locality -- Dataset A (controlled corpus)

Total (op, file) cases evaluated: **70**

Change Locality Ratio = Expected Changed Lines (1) / Actual Changed Lines. Adjusted ratio further divides by (Actual - that file's own identity-round-trip noise from Experiment 1), isolating the edit's footprint from the library's baseline re-serialization noise (quote/flow-style normalization, blank-line loss).

## Per-property results

| Op | N | Success | Median actual changed lines | Median locality ratio | Median adjusted ratio |
|---|---|---|---|---|---|
| image | 36 | 36/36 | 3.0 | 0.3333 | 1.0000 |
| hostname | 1 | 1/1 | 29.0 | 0.0345 | 1.0000 |
| restart | 3 | 3/3 | 7.0 | 0.1429 | 1.0000 |
| env | 11 | 11/11 | 4.0 | 0.2500 | 1.0000 |
| port | 5 | 3/5 | 5.0 | 0.2000 | 1.0000 |
| volume-source | 4 | 3/4 | 3.0 | 0.3333 | 1.0000 |
| extra-host | 1 | 1/1 | 29.0 | 0.0345 | 1.0000 |
| network | 4 | 1/4 | 2.0 | 0.5000 | 1.0000 |
| healthcheck-retries | 2 | 2/2 | 15.5 | 0.2672 | 1.0000 |
| deploy-cpus | 3 | 3/3 | 9.0 | 0.1111 | 1.0000 |

## Notes

- `port`, `extra-host`, `network`: the library's API only exposes `add`/`remove` (no in-place setter), so the single targeted change modelled here is *adding one entry* to an existing list, not replacing an existing value.
- `volume-source`: only short-syntax volume entries (`source:target[:mode]`) are eligible -- `Volumes::setSource` calls `.as<std::string>()` on each entry and throws on long-syntax (mapping) volume definitions, so files using only long syntax are skipped.
- `port`: `Ports::has` (called by `add` to avoid duplicates) runs `.as<std::string>()` over every existing entry, so a service whose `ports` list mixes short-syntax strings with a long-syntax (mapping) port definition throws a yaml-cpp bad-conversion error -- the same short-syntax-only assumption seen in `Volumes` and `Networks`.
- `network`: eligibility only requires a `networks` key to exist, but `Networks::add` pushes onto it without checking the node is a sequence. Services using the long (mapping) `networks:` syntax cause `add` to throw ("appending to a non-sequence") -- a real library bug surfaced by this experiment, left visible below rather than filtered out.

## Failures (6)

- `port` / `full-featured.yml` (service `web`): APPLY_FAILED: yaml-cpp: error at line 23, column 9: bad conversion
- `port` / `ports-long.yml` (service `web`): APPLY_FAILED: yaml-cpp: error at line 5, column 9: bad conversion
- `volume-source` / `full-featured.yml` (service `api`): APPLY_FAILED: yaml-cpp: error at line 64, column 9: bad conversion
- `network` / `full-featured.yml` (service `api`): APPLY_FAILED: appending to a non-sequence
- `network` / `null-and-empty-values.yml` (service `app`): APPLY_FAILED: appending to a non-sequence
- `network` / `networks.yml` (service `backend`): APPLY_FAILED: appending to a non-sequence
