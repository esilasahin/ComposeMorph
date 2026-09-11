# Experiment 5 -- Docker Compose Validation

Dataset A (controlled corpus) files tested: **38**

## Input validity (evaluated separately per the task spec)

- **33/38 (86.84%)** of the input files are already valid per `docker compose config` before any editor touches them. The rest fail for reasons unrelated to the editors (missing `.env` files, undefined interpolation variables, deprecated or malformed syntax, ...); see the stage=`input` rows in the raw CSV. They are excluded from the rates below.

## Docker Compose Validation Success Rate (RQ1, main metric)

| Output | ComposeMorph | yaml-cpp baseline (= ComposeMorph before the quote fix) |
|---|---|---|
| Identity round-trip (Experiment 1) | 33/33 (100.00%) | 32/33 (96.97%) |
| Targeted `image` edit (Experiment 2) | 31/31 (100.00%) | 30/31 (96.77%) |
| **Combined** | **64/64 (100.00%)** | **62/64 (96.88%)** |

## Marker fixtures: x-* vs. non-x- unknown properties (RQ4 nuance)

| Fixture | ComposeMorph | yaml-cpp baseline (= ComposeMorph before the quote fix) |
|---|---|---|
| x-* extension fields only | 31/31 (100.00%) | 30/31 (96.77%) |
| x-* plus non-x- "future property" unknown fields | 0/31 (0.00%) | 0/31 (0.00%) |

The Compose Specification schema only admits unrecognized top-level or service keys when they are `x-*`-prefixed. A non-`x-` field that an editor preserves faithfully still makes docker compose reject the file, so the second row measures the schema, not the editor.

## ComposeMorph: outputs that became invalid despite a valid input (0)

None observed.

## yaml-cpp baseline (= ComposeMorph before the quote fix): outputs that became invalid despite a valid input (2)

### schema-type: a string field came back as a number/bool (quoted scalar lost its quotes) -- 2 case(s)

- `roundtrip_output` / `quoted-scalar-types.yml`: validating /home/user/ComposeMorph/results/raw/validation/dataset-a-output/yamlcpp-baseline/roundtrip/quoted-scalar-types.yml: services.app.command.2 must be a string
- `modification_output` / `quoted-scalar-types.yml`: validating /home/user/ComposeMorph/results/raw/validation/dataset-a-output/yamlcpp-baseline/modification/quoted-scalar-types.yml: services.app.command.2 must be a string
