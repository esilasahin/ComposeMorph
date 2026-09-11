# Experiment 3 & 4 -- Unknown Property / x-* Extension Preservation

Cases evaluated: **48** (48 completed the modify step; 0 failed before markers could be checked)

## Aggregate preservation rate, by marker

| Marker | Category | Scope | N | Preserved | Rate |
|---|---|---|---|---|---|
| `future_compose_property` | unknown | service | 48 | 48 | 100.00% |
| `unknown_top_level_section` | unknown | top | 48 | 48 | 100.00% |
| `x-company-security` | extension | top | 48 | 48 | 100.00% |
| `x-default-logging` | extension | top | 48 | 48 | 100.00% |
| `x-service-meta` | extension | service | 48 | 48 | 100.00% |

- **Unknown Property Preservation Rate (RQ -- Experiment 3): 96/96** (100.00%)
- **x-* Extension Preservation Rate (RQ -- Experiment 4): 144/144** (100.00%)

## By source and modification op

| Source | Op | N | Fully preserved (all markers) |
|---|---|---|---|
| controlled | env | 11 | 11/11 |
| controlled | image | 37 | 37/37 |

## Controlled edge cases (datasets/controlled/preservation-edge-cases.yml)

Not part of the aggregate rate above -- these probe non-uniform scenarios individually, and a failure here is reported rather than hidden.

| Case | Preserved | Expected | Actual |
|---|---|---|---|
| top-level x-* with a null value | yes | `None` | `None` |
| top-level x-* whose value is a bare scalar, not a map | yes | `'just-a-string'` | `'just-a-string'` |
| top-level x-* whose value is a list of maps | yes | `[{'a': 1}, {'b': 2}]` | `[{'a': 1}, {'b': 2}]` |
| unknown top-level section that is a list, not a map | yes | `[1, 2, 3]` | `[1, 2, 3]` |
| unknown property nested inside a *known*, typed section (deploy.future_scaling_hint) | yes | `'aggressive'` | `'aggressive'` |
| x-* field nested two levels inside another unknown block | yes | `True` | `True` |
