# Results before the quote-preserving serializer

Snapshot of `results/tables/` as of commit `29e8445`, taken before
`src/ScalarQuoting.cpp` (quote-preserving serialization) and the
short-syntax `environment`/`extra_hosts` fix were added. Kept so the
paper's before/after numbers stay traceable. The "before" columns in the
current Experiment 5 and quoted-scalar tables are regenerated with
`build/yamlcpp_careful_tool`, whose round-trip output was byte-identical to
ComposeMorph's at this commit (see `tables/comparison_summary.md`, section 1).
