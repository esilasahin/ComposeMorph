# Supplementary statistics quoted in the paper

Derived from committed datasets and raw outputs; see the script docstring (`scripts/paper_supplementary_stats.py`).

## 1. Block scalars in Dataset B

- Files with at least one block scalar (`|` or `>`): **55/647** (8.5%), 201 occurrences in total.
- ComposeMorph keeps their content but writes them as escaped, single-line double-quoted strings (the `!` tag marks every non-plain scalar).

## 2. Experiment 6: yamlcpp-careful collateral misses

| Op | Failed cases | Sibling fields present (scalar presentation changed) | Output not parseable | Other |
|---|---|---|---|---|
| image | 19 | 18 | 1 | 0 |
| hostname | 16 | 15 | 1 | 0 |
| env | 16 | 15 | 1 | 0 |

## 3. Experiment 2: edits that change more than one line after noise subtraction

| Op | Syntax form | Before fix: >1 line / cases (median) | After fix: >1 line / cases (median) |
|---|---|---|---|
| env | list | 83/94 (3) | 0/94 (1) |
| env | map | 1/106 (1) | 0/106 (1) |
| extra-host | list | 9/34 (1) | 0/34 (1) |
| image | all | 0/200 (1) | 0/200 (1) |

## 4. Experiment 7: cold first iteration of the modify step

- Files: 59; modify_ms at iteration 0: median=1.26ms, max=2.08ms.
