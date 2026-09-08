# Experiment 6 -- Comparative Benchmark: ComposeMorph vs. raw yaml-cpp

## 1. Identity round-trip: ComposeMorph vs. careful raw yaml-cpp

Files compared: **100**

- Byte-identical output between the two tools: **100/100** (100.00%)
- ComposeMorph mean changed lines vs. input: 33.68
- yaml-cpp (careful) mean changed lines vs. input: 33.68
- **Interpretation:** ComposeMorph's round-trip preservation (or lack of it, per Experiment 1) is inherited entirely from yaml-cpp -- it is not a distinguishing feature of this library.

## 2. Targeted modification: change locality and collateral loss

| Tool | Op | N | Success | Median changed lines | Collateral preserved |
|---|---|---|---|---|---|
| composemorph | image | 150 | 150/150 | 13.0 | 130/149 |
| composemorph | hostname | 39 | 39/39 | 31.0 | 23/39 |
| composemorph | env | 150 | 150/150 | 15.5 | 56/116 |
| yamlcpp-careful | image | 150 | 150/150 | 13.0 | 130/149 |
| yamlcpp-careful | hostname | 39 | 39/39 | 31.0 | 23/39 |
| yamlcpp-careful | env | 150 | 150/150 | 15.5 | 56/116 |
| yamlcpp-naive | image | 150 | 150/150 | 23.0 | 0/149 |
| yamlcpp-naive | hostname | 39 | 39/39 | 48.0 | 0/39 |
| yamlcpp-naive | env | 150 | 150/150 | 17.0 | 0/116 |

**Collateral preserved** = of the cases where the modified service had other pre-existing fields (or, for `env`, other pre-existing environment variables) besides the one being changed, how many still have all of them, unchanged, after the edit. `yamlcpp-naive` is expected near 0% for `image`/`hostname` (whole service subtree replaced) and for `env` (whole environment section replaced).

## 3. Unknown property / x-* preservation, by tool

| Tool | N | Top-level markers preserved | Service-level markers preserved |
|---|---|---|---|
| composemorph | 100 | 300/300 (100.0%) | 200/200 (100.0%) |
| yamlcpp-careful | 100 | 300/300 (100.0%) | 200/200 (100.0%) |
| yamlcpp-naive | 100 | 300/300 (100.0%) | 0/200 (0.0%) |

**Expected pattern:** `composemorph` and `yamlcpp-careful` preserve both scopes at ~100%. `yamlcpp-naive`'s `image` edit replaces the whole service subtree, so service-level markers (`future_compose_property`, `x-service-meta`) are lost while top-level markers (`x-company-security`, `x-default-logging`, `unknown_top_level_section`) survive untouched -- collateral damage is scoped to whatever subtree the naive code happened to overwrite.

## 4. Lines of code per single-property edit

Counted by brace-matching each `if (op == "X") { ... }` branch body in the tool's source.

| Op | composemorph | yaml-cpp (careful) | yaml-cpp (naive) |
|---|---|---|---|
| deploy-cpus | 1 | 4 | not modeled |
| env | 1 | 2 | 6 |
| extra-host | 1 | 2 | not modeled |
| healthcheck-retries | 1 | 2 | not modeled |
| hostname | 1 | 1 | 3 |
| image | 1 | 1 | 5 |
| network | 1 | 2 | not modeled |
| port | 1 | 2 | not modeled |
| restart | 1 | 1 | not modeled |
| volume-source | 1 | 24 | not modeled |

yaml-cpp (naive)'s lower or equal LOC for `image`/`hostname` is exactly the problem: the destructive version is not more work to write than the correct one -- there is no natural code-review signal that distinguishes them.

## 5. Capability matrix (PDF section 9)

Grounded in the measurements above and in source inspection (`src/ComposeFile.cpp`, `benchmarks/comparison/*.cpp`).

| Feature | ComposeMorph | yaml-cpp (careful use) | yaml-cpp (naive use) |
|---|---|---|---|
| C++ API | Yes -- typed classes | Yes -- raw `YAML::Node` only | Yes -- raw `YAML::Node` only |
| Docker Compose-aware API | Yes (`Service`, `Environment`, `Ports`, ...) | No | No |
| Generic property support | Yes (`Service::set/get/remove`) | Yes, unguided (manual `Node` indexing) | Yes, unguided |
| Unknown field preservation | 100% (Exp. 3, this experiment) | 100% (this experiment) | Top-level only -- service-level lost on `image`/`hostname` |
| x-* preservation | 100% (Exp. 4, this experiment) | 100% (this experiment) | Top-level only -- service-level lost on `image`/`hostname` |
| Comment preservation | No (Exp. 1) | No (same yaml-cpp emitter) | No |
| Formatting preservation | No (Exp. 1: quote/flow-style normalized) | No (identical, section 1 above) | No |
| Key order preservation | Existing keys: yes; new keys appended at end | Same (yaml-cpp preserves map insertion order) | Same, within whatever subtree survives |
| Round-trip support | Semantic yes, byte-identical no (Exp. 1) | Identical to ComposeMorph (section 1) | N/A -- not a round-trip tool |
| Compose validation integration | Basic business-rule `validate()` (image/build required, ...) | None built in | None built in |
| Safe/atomic save | Yes -- `SaveOptions::atomic` writes to a temp file + rename | No -- direct `ofstream` overwrite | No -- direct `ofstream` overwrite |
