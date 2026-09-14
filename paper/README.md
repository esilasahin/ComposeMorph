# Paper

Target venue: 6th Global Conference on Engineering Research
(GLOBCER'26), which accepts English or Turkish.

Language: **Turkish** (title, author block, body, table and figure
captions), with the English title printed under the Turkish one and an
English abstract + keywords following the Turkish `Özet`, as is usual for
Turkish-language submissions. `babel` is loaded with both languages so the
English abstract hyphenates correctly and IEEEtran's caption strings
("Özet"/"Abstract", "Kaynaklar", "Şekil", "TABLO") switch with it. RQ
labels and established technical terms (round-trip, YAML, `x-*`, Compose)
stay in English per common practice, and cited works keep their original
titles; only the connecting text in the bibliography is Turkish.

The English abstract is a revision of the one submitted with the abstract
form: the framing is unchanged, but "600+ files" is now the actual 647,
and the placeholder results ("preliminary validation ... currently
underway") are replaced by the measured ones.

`paper.tex` -- IEEEtran-format paper source (`babel[turkish]`), complete:
abstract plus twelve sections, two tables and two figures. The
bibliography is embedded as a `thebibliography` block, so the source
compiles on its own with no BibTeX pass.

`references.bib` -- the same 23 entries in BibTeX form (English
connecting text), kept as the editable source of record (see
`../docs/related-work.md` for the survey behind them). It is *not* read by
`paper.tex` any more: if you change a reference, change it in both places,
or switch `paper.tex` back to `\bibliography{references}`.

Figures are pulled from `../results/figures/` via `\graphicspath`
(regenerate with `../scripts/run-all-experiments.sh`) rather than
duplicated here; the same `\graphicspath` also looks next to `paper.tex`,
so a flat upload works.

## Building

This repo's dev environment has no TeX toolchain installed. To build:

```
pdflatex paper.tex
pdflatex paper.tex
```

(the second pass resolves `\ref`/`\cite`), or with `latexmk`:

```
latexmk -pdf paper.tex
```

For Overleaf: upload `paper.tex` together with the four PDFs used by the
figures (`modification_change_locality.pdf`, `comparison_yamlcpp.pdf` --
or their `.png` variants) from `../results/figures/`, and pick the
"IEEE Conference" template.

## Status

Complete draft. Every number in the text comes from a committed summary
under `../results/tables/`; if the experiments are re-run, re-check the
figures quoted in the Abstract, Introduction and Section "Bulgular".

Known pre-submission items:

- The author block gives the three TÜBİTAK authors separate superscripts
  (2, 3, 4) resolving to one shared affiliation line. That is deliberate;
  the more common IEEE convention is to give all three the same superscript
  and list the institution once. Either reads correctly -- just keep it
  consistent with whatever the venue's template shows.
- The corresponding-author address follows the abstract form
  (`esila.sahin@stu.fsm.edu.tr`), not the gmail address that was in the
  earlier draft.

- The absolute timings in Table `tab:perf` are sensitive to machine load.
  Re-run Experiment 7 (`scripts/run_performance_experiment.py`) on an
  otherwise idle machine before submitting; the paired serializer
  comparison in the same table is in-process and unaffected.
- Length is roughly 6,000 words plus two tables and two figures. Check it
  against the venue's page limit.
