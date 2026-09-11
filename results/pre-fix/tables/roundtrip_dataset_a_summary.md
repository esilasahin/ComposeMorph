# Experiment 1 -- Identity Round-Trip -- Dataset A (controlled corpus)

Files evaluated: **38**

## RQ1 -- Correctness

- Parse success rate: **38/38** (100.00%)
- Save success rate: **38/38** (100.00%)
- Reparse (save-then-reload) success rate: **38/38** (100.00%)
- `docker compose config` semantic check: not requested (run with --semantic)

## RQ2 -- Preservation (textual, identity round-trip)

- Byte-identical round-trip: **8/38** (21.05%)
  - **The library does not guarantee byte-identical round-trip.** yaml-cpp re-emits scalars/flow sequences with normalized quoting and collapses blank lines on save; see per-file diffs in the raw CSV.
- Changed line ratio: mean=0.1671, median=0.1250, stdev=0.1349, max=0.5385
- Line-level Levenshtein distance: mean=2.6053, median=1.5000, stdev=4.6143, max=28.0000
- Normalized edit distance: mean=0.1671, median=0.1250, stdev=0.1349, max=0.5385

## Performance (informational, see Experiment 7 for the full benchmark)

- Load+save+reload wall time per file: mean=0.0027, median=0.0029, stdev=0.0005, max=0.0036 seconds
