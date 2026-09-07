# Experiment 1 -- Identity Round-Trip -- Dataset B (real-world corpus)

Files evaluated: **647**

## RQ1 -- Correctness

- Parse success rate: **647/647** (100.00%)
- Save success rate: **647/647** (100.00%)
- Reparse (save-then-reload) success rate: **647/647** (100.00%)
- `docker compose config` semantic check: not requested (run with --semantic)

## RQ2 -- Preservation (textual, identity round-trip)

- Byte-identical round-trip: **5/647** (0.77%)
  - **The library does not guarantee byte-identical round-trip.** yaml-cpp re-emits scalars/flow sequences with normalized quoting and collapses blank lines on save; see per-file diffs in the raw CSV.
- Changed line ratio: mean=0.3110, median=0.2500, stdev=0.2103, max=1.8297
- Line-level Levenshtein distance: mean=39.8393, median=11.0000, stdev=113.6133, max=1404.0000
- Normalized edit distance: mean=0.3097, median=0.2500, stdev=0.2034, max=1.0000

## Performance (informational, see Experiment 7 for the full benchmark)

- Load+save+reload wall time per file: mean=0.0046, median=0.0034, stdev=0.0041, max=0.0449 seconds
