# Experiment 3 & 4 -- Unknown Property / x-* Extension Preservation

Cases evaluated: **401** (401 completed the modify step; 0 failed before markers could be checked)

## Aggregate preservation rate, by marker

| Marker | Category | Scope | N | Preserved | Rate |
|---|---|---|---|---|---|
| `future_compose_property` | unknown | service | 401 | 401 | 100.00% |
| `unknown_top_level_section` | unknown | top | 401 | 401 | 100.00% |
| `x-company-security` | extension | top | 401 | 401 | 100.00% |
| `x-default-logging` | extension | top | 401 | 401 | 100.00% |
| `x-service-meta` | extension | service | 401 | 401 | 100.00% |

- **Unknown Property Preservation Rate (RQ -- Experiment 3): 802/802** (100.00%)
- **x-* Extension Preservation Rate (RQ -- Experiment 4): 1203/1203** (100.00%)

## By source and modification op

| Source | Op | N | Fully preserved (all markers) |
|---|---|---|---|
| controlled | image | 1 | 1/1 |
| real-world | env | 200 | 200/200 |
| real-world | image | 200 | 200/200 |

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
