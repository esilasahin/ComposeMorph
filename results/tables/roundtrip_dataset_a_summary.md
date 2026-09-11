# Experiment 1 -- Identity Round-Trip -- Dataset A (controlled corpus)

Files evaluated: **38**

## RQ1 -- Correctness

- Parse success rate: **38/38** (100.00%)
- Save success rate: **38/38** (100.00%)
- Reparse (save-then-reload) success rate: **38/38** (100.00%)
- `docker compose config` semantic check: not requested (run with --semantic)

## RQ2 -- Preservation (textual, identity round-trip)

- Byte-identical round-trip: **21/38** (55.26%)
  - **The library does not guarantee byte-identical round-trip.** The yaml-cpp emitter it serializes through drops comments and blank lines, re-indents to two spaces, writes empty values as `~` and writes quoted scalars with double quotes; see per-file diffs in the raw CSV.
- Changed line ratio: mean=0.0678, median=0.0000, stdev=0.0916, max=0.3333
- Line-level Levenshtein distance: mean=1.2895, median=0.0000, stdev=2.5434, max=14.0000
- Normalized edit distance: mean=0.0678, median=0.0000, stdev=0.0916, max=0.3333

## Performance (informational, see Experiment 7 for the full benchmark)

- Load+save+reload wall time per file: mean=0.0033, median=0.0032, stdev=0.0005, max=0.0047 seconds
