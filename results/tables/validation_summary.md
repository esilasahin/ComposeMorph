# Experiment 5 -- Docker Compose Validation

Dataset B files tested: **647**

## Input validity (baseline, evaluated separately per the PDF)

- **491/647** (75.89%) of the raw GitHub Compose files are already valid per `docker compose config`, before ComposeMorph touches them. The rest fail for reasons unrelated to this library (missing `.env` files, undefined interpolation variables, deprecated/malformed syntax, etc.) -- see stage=`input` rows in the raw CSV for the specific errors. These files are excluded from the rates below.

## Docker Compose Validation Success Rate (RQ1, main metric)

- Identity round-trip output (Experiment 1, no modification): **187/491** (38.09%)
- Targeted `image` modification output (Experiment 2): **148/401** (36.91%)
- **Combined: 335/892 (37.56%)**

## Marker fixtures: x-* vs. non-x- unknown properties (RQ4 nuance)

- x-* extension fields only: **32/83** (38.55%) valid per docker compose config
- x-* extension fields *and* non-x- "future property" style unknown fields: **0/83** (0.00%)

**Interpretation:** Experiments 3/4 showed ComposeMorph preserves *both* kinds of unknown structure semantically at ~100%. This experiment shows that preservation alone isn't the same as validity: the Compose Specification schema only permits unrecognized top-level/service keys when they're `x-*`-prefixed. A non-`x-` "forward-compatible" field survives the round-trip but docker compose still rejects the *file*, independent of anything ComposeMorph did. This is a real constraint worth stating plainly in Limitations, not a bug in the library.

## Outputs that became invalid despite a valid input (557)

Categorized by root cause (see `classify_error()` in this script):

### schema-type: quoted numeric-looking scalar unquoted on save (e.g. version, command/entrypoint elements) -- 542 case(s)

- `roundtrip_output` / `0kkun__tennis-track__.openapi_docker-compose.yml.yml`: validating /home/user/ComposeMorph/results/raw/validation/output/roundtrip/0kkun__tennis-track__.openapi_docker-compose.yml.yml: version must be a string
- `roundtrip_output` / `0xSh4dy__hackentine_archives__reversing_rev1_firstchallrevbasic_docker-compose.yml.yml`: validating /home/user/ComposeMorph/results/raw/validation/output/roundtrip/0xSh4dy__hackentine_archives__reversing_rev1_firstchallrevbasic_docker-compose.yml.yml: version must be a string
- `roundtrip_output` / `1qzxc__infra__shared-files_docker_gitlabci_docker-compose.yml.yml`: validating /home/user/ComposeMorph/results/raw/validation/output/roundtrip/1qzxc__infra__shared-files_docker_gitlabci_docker-compose.yml.yml: version must be a string
- `roundtrip_output` / `3PillarGlobal__engineering-playbook__dockerized-automation_docker-compose.yml.yml`: validating /home/user/ComposeMorph/results/raw/validation/output/roundtrip/3PillarGlobal__engineering-playbook__dockerized-automation_docker-compose.yml.yml: version must be a string | time="2026-09-0
- `roundtrip_output` / `3bsolutionsltd__transconnect-app__docker-compose.yml.yml`: validating /home/user/ComposeMorph/results/raw/validation/output/roundtrip/3bsolutionsltd__transconnect-app__docker-compose.yml.yml: version must be a string | time="2026-09-08T16:23:40+03:00" level=w
- ... and 537 more (see raw CSV)

### benchmark-harness artifact: find_image() in run_modification_experiment.py splits the image string on its *last* ':', which lands inside a `${VAR:-default}` tag expression for images using compose interpolation syntax -- not a ComposeMorph defect -- 11 case(s)

- `modification_output` / `Amrue320__cicd-demo-app__docker-compose.yml.yml`: invalid interpolation format for services.app.image. | You may need to escape any $ with another $. | ${DOCKER_IMAGE:-cicd-demo-app}:${APP_VERSION:cm-test-9.9 | time="2026-09-08T16:24:05+03:00" level=
- `modification_output` / `CJLove__homelab__ArtifactKeeper_docker-compose.yml.yml`: invalid interpolation format for services.backend.image. | You may need to escape any $ with another $. | ghcr.io/artifact-keeper/artifact-keeper-backend:${ARTIFACT_KEEPER_VERSION:cm-test-9.9
- `modification_output` / `appwrite__appwrite__docker-compose.yml.yml`: invalid interpolation format for services.appwrite.image. | You may need to escape any $ with another $. | ${_APP_IMAGE:-appwrite/appwrite}:${_APP_VERSION:cm-test-9.9 | time="2026-09-08T16:24:12+03:00
- `modification_output` / `botAGI__AGmind__templates_docker-compose.yml.yml`: invalid interpolation format for services.alertmanager.image. | You may need to escape any $ with another $. | prom/alertmanager:${ALERTMANAGER_VERSION:cm-test-9.9 | time="2026-09-08T16:24:13+03:00" l
- `modification_output` / `codename-co__stack__hub_jitsi_compose.yaml.yml`: invalid interpolation format for services.jicofo.image. | You may need to escape any $ with another $. | jitsi/jicofo:${JITSI_IMAGE_VERSION:cm-test-9.9 | time="2026-09-08T16:24:14+03:00" level=warning
- ... and 6 more (see raw CSV)

### SYNTAX: output is not valid YAML for other parsers (yaml-cpp emitter quirk) -- 4 case(s)

- `roundtrip_output` / `CodesWhat__drydock__test_qa-compose.yml.yml`: yaml: line 273: did not find expected node content
- `roundtrip_output` / `jakejarvis__homelab__docker-compose.yml.yml`: yaml: line 334: did not find expected node content
- `modification_output` / `CodesWhat__drydock__test_qa-compose.yml.yml`: yaml: line 273: did not find expected node content
- `modification_output` / `jakejarvis__homelab__docker-compose.yml.yml`: yaml: line 334: did not find expected node content

**The dominant failure mode -- quoted numeric-looking scalars losing their quotes on save -- is the *same mechanism* Experiment 1 already flagged as a formatting-only issue (e.g. `"2.0"` -> `2.0`). This experiment shows it is not purely cosmetic: when that scalar is `version:`, a `command:`/`entrypoint:` list element, or any other field the Compose schema requires to be a string, the re-serialized file is outright rejected by `docker compose config`. In at least one observed case (`command: ["caddy", "respond", "--listen", ":80", "QA"]`), the unquoted `:80` inside a flow sequence is not just schema-invalid but syntactically unparseable YAML for other parsers (confirmed independently with PyYAML) -- yaml-cpp's own reader accepts its own output, but standards-compliant parsers do not. This is the single most consequential finding in this benchmark suite and should be reported prominently in Results/Limitations, not folded into the round-trip byte-diff numbers.
