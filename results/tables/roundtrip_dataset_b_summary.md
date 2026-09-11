# Experiment 1 -- Identity Round-Trip -- Dataset B (real-world corpus)

Files evaluated: **647**

## RQ1 -- Correctness

- Parse success rate: **647/647** (100.00%)
- Save success rate: **647/647** (100.00%)
- Reparse (save-then-reload) success rate: **647/647** (100.00%)
- `docker compose config` semantic check: not requested (run with --semantic)

## RQ2 -- Preservation (textual, identity round-trip)

- Byte-identical round-trip: **26/647** (4.02%)
  - **The library does not guarantee byte-identical round-trip.** The yaml-cpp emitter it serializes through drops comments and blank lines, re-indents to two spaces, writes empty values as `~` and writes quoted scalars with double quotes; see per-file diffs in the raw CSV.
- Changed line ratio: mean=0.2368, median=0.1667, stdev=0.2267, max=1.8297
- Line-level Levenshtein distance: mean=29.6012, median=7.0000, stdev=90.6833, max=1388.0000
- Normalized edit distance: mean=0.2355, median=0.1667, stdev=0.2199, max=1.0000

## Performance (informational, see Experiment 7 for the full benchmark)

- Load+save+reload wall time per file: mean=0.0057, median=0.0040, stdev=0.0058, max=0.0560 seconds
