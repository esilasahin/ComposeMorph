# Results before the quote-preserving serializer

Snapshot of `results/tables/` as of commit `29e8445`, taken before
`src/ScalarQuoting.cpp` (quote-preserving serialization) and the
short-syntax `environment`/`extra_hosts` fix were added. Kept so the
paper's before/after numbers stay traceable. The "before" columns in the
current Experiment 5 and quoted-scalar tables are regenerated with
`build/yamlcpp_careful_tool`, whose round-trip output was byte-identical to
ComposeMorph's at this commit (see `tables/comparison_summary.md`, section 1).

`raw/modification_dataset_b.csv` is Experiment 2's raw output from the same
commit (`git show 29e8445:results/raw/modification_dataset_b.csv`). Its
`incremental_changed_lines` column shows the short-syntax bug: before the
fix, 83 of 94 `env` edits on list-form `environment` sections and 9 of 34
`extra-host` edits changed more than one line after subtracting the file's
identity round-trip noise; after the fix, none do.
