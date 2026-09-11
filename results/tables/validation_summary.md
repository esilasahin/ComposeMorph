# Experiment 5 -- Docker Compose Validation

Dataset B files tested: **647**

## Input validity (evaluated separately per the task spec)

- **491/647 (75.89%)** of the input files are already valid per `docker compose config` before any editor touches them. The rest fail for reasons unrelated to the editors (missing `.env` files, undefined interpolation variables, deprecated or malformed syntax, ...); see the stage=`input` rows in the raw CSV. They are excluded from the rates below.

## Docker Compose Validation Success Rate (RQ1, main metric)

| Output | ComposeMorph | yaml-cpp baseline (= ComposeMorph before the quote fix) |
|---|---|---|
| Identity round-trip (Experiment 1) | 491/491 (100.00%) | 187/491 (38.09%) |
| Targeted `image` edit (Experiment 2) | 401/401 (100.00%) | 153/401 (38.15%) |
| **Combined** | **892/892 (100.00%)** | **340/892 (38.12%)** |

## Marker fixtures: x-* vs. non-x- unknown properties (RQ4 nuance)

| Fixture | ComposeMorph | yaml-cpp baseline (= ComposeMorph before the quote fix) |
|---|---|---|
| x-* extension fields only | 83/83 (100.00%) | 33/83 (39.76%) |
| x-* plus non-x- "future property" unknown fields | 0/83 (0.00%) | 0/83 (0.00%) |

The Compose Specification schema only admits unrecognized top-level or service keys when they are `x-*`-prefixed. A non-`x-` field that an editor preserves faithfully still makes docker compose reject the file, so the second row measures the schema, not the editor.

## ComposeMorph: outputs that became invalid despite a valid input (0)

None observed.

## yaml-cpp baseline (= ComposeMorph before the quote fix): outputs that became invalid despite a valid input (552)

### schema-type: a string field came back as a number/bool (quoted scalar lost its quotes) -- 548 case(s)

- `roundtrip_output` / `0kkun__tennis-track__.openapi_docker-compose.yml.yml`: validating /home/user/ComposeMorph/results/raw/validation/output/yamlcpp-baseline/roundtrip/0kkun__tennis-track__.openapi_docker-compose.yml.yml: version must be a string
- `roundtrip_output` / `0xSh4dy__hackentine_archives__reversing_rev1_firstchallrevbasic_docker-compose.yml.yml`: validating /home/user/ComposeMorph/results/raw/validation/output/yamlcpp-baseline/roundtrip/0xSh4dy__hackentine_archives__reversing_rev1_firstchallrevbasic_docker-compose.yml.yml: version must be a st
- `roundtrip_output` / `1qzxc__infra__shared-files_docker_gitlabci_docker-compose.yml.yml`: validating /home/user/ComposeMorph/results/raw/validation/output/yamlcpp-baseline/roundtrip/1qzxc__infra__shared-files_docker_gitlabci_docker-compose.yml.yml: version must be a string
- `roundtrip_output` / `3PillarGlobal__engineering-playbook__dockerized-automation_docker-compose.yml.yml`: validating /home/user/ComposeMorph/results/raw/validation/output/yamlcpp-baseline/roundtrip/3PillarGlobal__engineering-playbook__dockerized-automation_docker-compose.yml.yml: version must be a string 
- `roundtrip_output` / `3bsolutionsltd__transconnect-app__docker-compose.yml.yml`: validating /home/user/ComposeMorph/results/raw/validation/output/yamlcpp-baseline/roundtrip/3bsolutionsltd__transconnect-app__docker-compose.yml.yml: version must be a string | time="2026-09-11T16:25:
- ... and 543 more (see raw CSV)

### syntax: output is not valid YAML for docker compose's parser -- 4 case(s)

- `roundtrip_output` / `CodesWhat__drydock__test_qa-compose.yml.yml`: yaml: line 273: did not find expected node content
- `roundtrip_output` / `jakejarvis__homelab__docker-compose.yml.yml`: yaml: line 334: did not find expected node content
- `modification_output` / `CodesWhat__drydock__test_qa-compose.yml.yml`: yaml: line 273: did not find expected node content
- `modification_output` / `jakejarvis__homelab__docker-compose.yml.yml`: yaml: line 334: did not find expected node content
