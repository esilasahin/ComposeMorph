# Experiment 6 -- Comparative Benchmark: ComposeMorph vs. raw yaml-cpp

## 1. Identity round-trip: ComposeMorph vs. careful raw yaml-cpp

Files compared: **100**

- Byte-identical output between the two tools: **4/100** (4.00%)
- Outputs that differ only in quote characters/escapes: **96/100**
- Outputs that differ in anything else: **0/100**
- Output loads (PyYAML) to exactly the same data as the input: ComposeMorph **100/100**, yaml-cpp (careful) **33/100**
- Mean changed lines vs. input: ComposeMorph 28.67, yaml-cpp (careful) 33.68
- **Interpretation:** where the outputs differ, they differ only in quoting in 96 of 96 files. ComposeMorph keeps the quotes that yaml-cpp's emitter drops, which is what lifts semantic identity with the input from 33/100 to 100/100.

## 2. Targeted modification: change locality and collateral loss

| Tool | Op | N | Success | Median changed lines | Collateral preserved |
|---|---|---|---|---|---|
| composemorph | image | 150 | 150/150 | 10.0 | 149/149 |
| composemorph | hostname | 39 | 39/39 | 23.0 | 39/39 |
| composemorph | env | 150 | 150/150 | 10.0 | 116/116 |
| yamlcpp-careful | image | 150 | 150/150 | 13.0 | 130/149 |
| yamlcpp-careful | hostname | 39 | 39/39 | 31.0 | 23/39 |
| yamlcpp-careful | env | 150 | 150/150 | 14.0 | 100/116 |
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
| env | 1 | 18 | 6 |
| extra-host | 1 | 22 | not modeled |
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
| Unknown field preservation | Measured (Exp. 3, section 3) | Measured (section 3) | Top-level only -- service-level lost on `image`/`hostname` |
| x-* preservation | Measured (Exp. 4, section 3) | Measured (section 3) | Top-level only -- service-level lost on `image`/`hostname` |
| Comment preservation | No (Exp. 1) | No | No |
| Formatting preservation | Partial -- the author's quoting is kept (as double quotes); comments, blank lines, indentation and single-quote style are not (Exp. 1) | No -- quoted scalars lose their quotes | No |
| Key order preservation | Existing keys: yes; new keys appended at end | Same (yaml-cpp preserves map insertion order) | Same, within whatever subtree survives |
| Round-trip support | Structure and scalar types: loads to the same data as the input in 100/100 files (section 1); byte-identical: no (Exp. 1) | Structure yes; quoted scalars can change type -- 33/100 files load to the same data as the input (section 1) | N/A -- not a round-trip tool |
| Compose validation integration | Basic business-rule `validate()` (image/build required, ...) | None built in | None built in |
| Safe/atomic save | Yes -- `SaveOptions::atomic` writes to a temp file + rename | No -- direct `ofstream` overwrite | No -- direct `ofstream` overwrite |
