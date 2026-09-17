# Experiment 2 -- Targeted Modification / Change Locality -- Dataset B

Total (op, file) cases evaluated: **1467**

Change Locality Ratio = Expected Changed Lines (1) / Actual Changed Lines. Adjusted ratio further divides by (Actual - that file's own identity-round-trip noise from Experiment 1), isolating the edit's footprint from the library's baseline re-serialization noise (dropped comments and blank lines, re-indentation).

## Per-property results

| Op | N | Success | Median actual changed lines | Median locality ratio | Median adjusted ratio |
|---|---|---|---|---|---|
| image | 200 | 200/200 | 9.0 | 0.1111 | 1.0000 |
| hostname | 39 | 39/39 | 23.0 | 0.0435 | 1.0000 |
| restart | 200 | 200/200 | 10.0 | 0.1000 | 1.0000 |
| env | 200 | 200/200 | 9.0 | 0.1111 | 1.0000 |
| port | 200 | 200/200 | 8.0 | 0.1250 | 1.0000 |
| volume-source | 200 | 200/200 | 9.0 | 0.1111 | 1.0000 |
| extra-host | 34 | 34/34 | 36.0 | 0.0278 | 1.0000 |
| network | 200 | 200/200 | 14.0 | 0.0714 | 1.0000 |
| healthcheck-retries | 185 | 185/185 | 13.0 | 0.0769 | 1.0000 |
| deploy-cpus | 9 | 9/9 | 20.0 | 0.0500 | 1.0000 |

## Notes

- `port`, `extra-host`, `network`: the library's API only exposes `add`/`remove` (no in-place setter), so the single targeted change modelled here is *adding one entry* to an existing list, not replacing an existing value.
- `volume-source`: only short-syntax volume entries (`source:target[:mode]`) are eligible -- `Volumes::setSource` calls `.as<std::string>()` on each entry and throws on long-syntax (mapping) volume definitions, so files using only long syntax are skipped.
- `port`: `Ports::has` (called by `add` to avoid duplicates) runs `.as<std::string>()` over every existing entry, so a service whose `ports` list mixes short-syntax strings with a long-syntax (mapping) port definition throws a yaml-cpp bad-conversion error -- the same short-syntax-only assumption seen in `Volumes` and `Networks`.
- `network`: eligibility only requires a `networks` key to exist, but `Networks::add` pushes onto it without checking the node is a sequence. Services using the long (mapping) `networks:` syntax cause `add` to throw ("appending to a non-sequence") -- a real library bug surfaced by this experiment, left visible below rather than filtered out.
