# Experiment 5 -- Docker Compose Validation

Dataset A (controlled corpus) files tested: **38**

## Input validity (baseline, evaluated separately per the PDF)

- **33/38** (86.84%) of the raw GitHub Compose files are already valid per `docker compose config`, before ComposeMorph touches them. The rest fail for reasons unrelated to this library (missing `.env` files, undefined interpolation variables, deprecated/malformed syntax, etc.) -- see stage=`input` rows in the raw CSV for the specific errors. These files are excluded from the rates below.

## Docker Compose Validation Success Rate (RQ1, main metric)

- Identity round-trip output (Experiment 1, no modification): **32/33** (96.97%)
- Targeted `image` modification output (Experiment 2): **30/31** (96.77%)
- **Combined: 62/64 (96.88%)**

## Marker fixtures: x-* vs. non-x- unknown properties (RQ4 nuance)

- x-* extension fields only: **30/31** (96.77%) valid per docker compose config
- x-* extension fields *and* non-x- "future property" style unknown fields: **0/31** (0.00%)

**Interpretation:** Experiments 3/4 showed ComposeMorph preserves *both* kinds of unknown structure semantically at ~100%. This experiment shows that preservation alone isn't the same as validity: the Compose Specification schema only permits unrecognized top-level/service keys when they're `x-*`-prefixed. A non-`x-` "forward-compatible" field survives the round-trip but docker compose still rejects the *file*, independent of anything ComposeMorph did. This is a real constraint worth stating plainly in Limitations, not a bug in the library.

## Outputs that became invalid despite a valid input (2)

Categorized by root cause (see `classify_error()` in this script):

### schema-type: quoted numeric-looking scalar unquoted on save (e.g. version, command/entrypoint elements) -- 2 case(s)

- `roundtrip_output` / `quoted-scalar-types.yml`: validating /home/user/ComposeMorph/results/raw/validation/dataset-a-output/roundtrip/quoted-scalar-types.yml: services.app.command.2 must be a string
- `modification_output` / `quoted-scalar-types.yml`: validating /home/user/ComposeMorph/results/raw/validation/dataset-a-output/modification/quoted-scalar-types.yml: services.app.command.2 must be a string

**The dominant failure mode -- quoted numeric-looking scalars losing their quotes on save -- is the *same mechanism* Experiment 1 already flagged as a formatting-only issue (e.g. `"2.0"` -> `2.0`). This experiment shows it is not purely cosmetic: when that scalar is `version:`, a `command:`/`entrypoint:` list element, or any other field the Compose schema requires to be a string, the re-serialized file is outright rejected by `docker compose config`. In at least one observed case (`command: ["caddy", "respond", "--listen", ":80", "QA"]`), the unquoted `:80` inside a flow sequence is not just schema-invalid but syntactically unparseable YAML for other parsers (confirmed independently with PyYAML) -- yaml-cpp's own reader accepts its own output, but standards-compliant parsers do not. This is the single most consequential finding in this benchmark suite and should be reported prominently in Results/Limitations, not folded into the round-trip byte-diff numbers.
