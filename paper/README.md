# Paper

Language: **Turkish** (the target venue accepts papers in English or
Turkish; body text is Turkish, RQ labels and established technical terms
are kept in English per common practice).

`paper.tex` -- IEEEtran-format paper source (uses `babel[turkish]`).
`references.bib` -- bibliography
(see `../docs/related-work.md` for the research behind it). Figures are
pulled directly from `../results/figures/` (regenerate with
`../scripts/run-all-experiments.sh`) rather than duplicated here.

## Building

This repo's dev environment has no TeX toolchain installed. To build:

```
pdflatex paper.tex
bibtex paper
pdflatex paper.tex
pdflatex paper.tex
```

or, with `latexmk`:

```
latexmk -pdf paper.tex
```

Alternatively, upload `paper.tex` + `references.bib` (and a copy of
`../results/figures/`) to Overleaf using the "IEEE Conference" template.

## Status

Skeleton only (section headers + TODO comments describing what each
section must cover and which `results/` files back it) -- see the
project conversation history / task spec section 15 for the section-by-
section plan. Sections are being filled in one at a time, not all at once.
