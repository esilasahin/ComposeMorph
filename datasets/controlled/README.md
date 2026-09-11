# Dataset A -- Controlled Compose Corpus

Hand-authored fixtures exercising each Compose feature listed in the task
spec (section 3), used alongside Dataset B (`datasets/real-world-combined/`)
so every benchmark has both a real-world statistical sample and a
deterministic, feature-isolated regression corpus.

- `individual/` -- one file per feature, in isolation: `services`, `image`,
  `build`, `environment` (short & long syntax), `ports` (short & long),
  `volumes` (short & long), `networks`, `depends_on`, `healthcheck`,
  `deploy`, `configs`, `secrets`, `labels`, `profiles`, `logging`,
  `sysctls`, `ulimits`, `devices`, `x-*` extension fields, unknown
  (non-`x-`) properties, and nested generic properties.
- `combined/` -- the same features combined into realistic multi-service
  files (`full-featured.yml` uses nearly all of them together;
  `minimal-multi-service.yml` is a small two-service app+db pair).
- `corner-cases/` -- scenarios expected to stress the library: YAML anchors
  and merge keys (`<<: *anchor`), the exact quoted-scalar shapes that
  Experiment 5's deep-dive found risky (`"true"`, `"3"`, `"2.5"`, ...),
  a `build`-only service with no `image`, Unicode/emoji content, `deploy`
  placement constraints, null/empty values, `external: true` resources,
  the (removed-from-spec-but-still-common) `extends` keyword, the newer
  `include:` top-level directive, and environment keys that differ only by
  case or separator.
- `preservation-standard-markers.yml` / `preservation-edge-cases.yml`
  (repo root of this directory, not a subfolder) -- pre-existing fixtures
  used directly by `scripts/run_preservation_experiment.py` and
  `scripts/run_comparison_experiment.py`; left in place so those scripts'
  hardcoded paths keep working.

All benchmark scripts (`run_roundtrip_experiment.py`,
`run_modification_experiment.py`, `run_validation_experiment.py`,
`run_comparison_experiment.py`, `run_performance_experiment.py`,
`analyze_quote_normalization.py`) accept `--dataset-dir` and scan it
recursively, so pointing any of them at `datasets/controlled/` runs the
same benchmark against this corpus instead of Dataset B.

Not every file here is expected to pass `docker compose config` --
`build-only-no-image.yml`'s relative build context, `include-directive.yml`'s
missing referenced file, and `extends-keyword.yml`'s removed-from-spec
keyword are deliberately included to see how the library and Docker's own
validator each react, not to be deployable Compose projects.
