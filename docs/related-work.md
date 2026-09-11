# Related Work Research (PDF task section 2)

Systematic survey conducted before writing any "first/only" claim in the
paper, per the task's explicit instruction not to assert novelty without
checking. Findings are grounded in project documentation, source-hosted
issue trackers, and peer-reviewed/preprint literature (all sources listed
at the end; BibTeX entries in `paper/references.bib`).

## 1. C/C++ YAML parser/emitter libraries

| Library | Language | Round-trip / comment preservation | Evidence |
|---|---|---|---|
| **yaml-cpp** (jbeder/yaml-cpp) | C++ | **No.** Comments are dropped on parse and never re-emitted. Two long-standing feature requests are open: "Preserve comments after parsing and re-emit them" (#457) and "option to not eat comments" (#154). | GitHub issues #457, #154 |
| **libyaml** (yaml/libyaml) | C | **No.** The parser does not generate comment tokens/events at all -- an architectural gap, not a missing convenience API. An open issue (#42) tracks the (unimplemented) feature request. | GitHub issue #42 |
| **rapidyaml / ryml** (biojppm/rapidyaml) | C++ | **Partial, and in the opposite direction from yaml-cpp's bug.** ryml is view-based (nodes hold pointers into the source buffer, no copies) and is fully YAML 1.2 conformant, but an open issue (#30, "Preserving scalar type information when emitting") reports that scalar *type* fidelity is not reliably preserved on emit -- e.g. integers can come back as strings. This is the same *class* of defect as our Experiment 5 finding (quoted-scalar round-trip changes a value's resolved type), just manifesting in the opposite direction (over-stringification instead of over-numification), on a different, source-buffer-view C++ design. | GitHub issue #30; project README |
| **fkYAML** (fktn-k/fkYAML) | C++11+ (header-only) | Not documented. fkYAML markets itself on performance (~6.5x faster than yaml-cpp in its own benchmark) and spec conformance/encoding support, but its documentation makes no round-trip or comment-preservation claim. | Project docs/releases page |

**Takeaway:** every actively maintained C/C++ YAML library we could find either
explicitly lacks comment/format preservation (yaml-cpp, libyaml) or has its
own open, unresolved round-trip fidelity bug of the same general class our
benchmarks measure (rapidyaml). None make a comment/format-preservation
claim we could evaluate as a competitor in that dimension. Nothing in the
C or C++ ecosystem approaches ruamel.yaml/eemeli-yaml-level guarantees
(see section 3).

## 2. YAML Concrete Syntax Tree (CST) / AST-based tooling

- **cstree** (Rust) -- a generic, language-agnostic CST library (used to
  build lossless syntax trees for arbitrary grammars); not YAML-specific.
- **yaml-edit** (Rust, on docs.rs) -- built on `rowan` (the same lossless
  CST engine behind rust-analyzer), explicitly designed to parse and edit
  YAML "while preserving formatting, comments, and whitespace." This is
  the closest systems-language analogue to what a fully format-preserving
  ComposeMorph would need to be -- but it targets generic YAML, has no
  Compose-specification awareness, and is Rust, not C++.
- **LibCST** (Python, Instagram) -- a CST parser/serializer for *Python
  source code*, cited here only to establish that the "keep a lossless
  tree, edit nodes in place" pattern used successfully for round-trip
  source-code tooling is the same architectural pattern the mature YAML
  tools below apply to configuration files.

## 3. Comment-preserving / round-trip YAML editors, by ecosystem

| Tool | Language | Preserves | Caveats |
|---|---|---|---|
| **ruamel.yaml** | Python | Comments (block/inline/multi-line), key order, flow/block style, through `load -> mutate -> dump` | The reference implementation this whole problem space is usually measured against |
| **yaml** (eemeli/yaml, npm) | JavaScript/TypeScript | Comments and whitespace, via an explicit three-layer API (plain JS objects / `Document` / CST) | Documented as *the* choice "for editors and configuration systems where preserving user comments... is essential" |
| **yaml-edit** | Rust | Formatting, comments, whitespace (CST/rowan-based) | Generic YAML, not Compose-aware |
| **kyaml** (sigs.k8s.io/kustomize/kyaml) | Go (Kubernetes SIG-CLI) | Structure and comments *for Kubernetes manifests specifically*, via a `Pipe`/`Filter` transformation model and a `comments.CopyComments` helper | Self-documented limitation: "the underlying go-yaml library does not always handle comments properly... it is possible that some comments will be formatted wrongly, or lost entirely" |

**Takeaway:** Python, JavaScript, and Rust each have a mature,
widely-used, CST- or token-preserving YAML library. C++ has none. Even
Go's domain-specific solution (kyaml, built for exactly this kind of
"edit one field of a structured config, keep everything else intact"
task) documents known, unresolved comment-corruption cases -- i.e. even
the best non-C++ prior art in this space is not a solved problem, only a
*better-solved* one than what C++ currently offers.

## 4. Kubernetes YAML/configuration transformation tooling

Covered under kyaml/kustomize above (section 3). Kustomize and kpt build
on kyaml specifically so that resource-patching pipelines don't destroy
unrelated YAML structure -- functionally the same goal as this paper's
RQ2/RQ3 (Preservation, Change Locality), applied to Kubernetes manifests
instead of Compose files, and in Go instead of C++.

## 5. Docker Compose configuration manipulation tools, by language

| Tool | Language | What it is | Compose-aware typed API? | Documented preservation guarantee? |
|---|---|---|---|---|
| **compose-go** (compose-spec/compose-go) | Go | The *official* reference library docker/compose itself uses to parse/load/validate Compose files | Yes (it *is* the schema) | Not applicable -- it's a loader/validator, not an editor; no round-trip-editing claim |
| **FishFinger** (TimTosi/fishfinger) | Go | "Lightweight programmatic library" for using a Compose file programmatically | Partial | Not documented |
| **compose-py** (bonprosoft/compose-py) | Python | Parses Compose files into Pydantic *or* dataclass models; modify the model, dump back to YAML | Yes (typed models) | Not documented -- schema/dataclass-based reconstruction on dump is architecturally the riskiest pattern surveyed here for forward-compatible preservation, since a strict typed model has nowhere to keep a field it doesn't know about unless it explicitly opts into an "extras" bucket |
| **docker-compose-parser**, **pydockercompose** | Python | Simpler parse/generate helpers | No | Not documented |
| **docker-compose-yaml-parser** (WisdomSky) | JavaScript | A `Parser` class with chained methods (`getService()`, `getImage()`, `setName()`, `setTag()`) | Yes -- structurally the closest analogue to ComposeMorph's `Service` API found in any language | Not documented |
| **resin-compose-parse** | JavaScript | Validates/normalizes/types Compose files | Yes | Deprecated, repository archived |
| **docker-compose-spec-typescript** | TypeScript | Compose JSON-Schema translated to TypeScript interfaces | Types only, no editing behavior | N/A |

**Takeaway, answering the PDF's six required questions directly:**

1. *Is there a Docker Compose-aware editing API in C++?* No comparable
   library was found in C++ at all, typed or otherwise.
2. *Which C++ YAML tools provide round-trip preservation?* None of the
   four surveyed (yaml-cpp, libyaml, rapidyaml, fkYAML) document
   comment/format-preserving round-trip editing as a supported feature;
   two have open, years-old issues asking for exactly that.
3. *Which tools have comment/formatting/key-order preservation?* Python
   (ruamel.yaml), JavaScript (eemeli/yaml), and Rust (yaml-edit) do, in
   general-purpose YAML; Go's kyaml does, specifically for Kubernetes
   manifests, with documented gaps. None are C++, none are
   Compose-specific.
4. *How is unknown-property preservation typically achieved?* By keeping
   a lossless token/CST-level representation and mutating only the
   touched node (ruamel.yaml, eemeli/yaml, kyaml) -- the same principle
   ComposeMorph applies at the yaml-cpp `Node` level, rather than the
   schema/dataclass round-trip pattern used by compose-py, which is
   structurally more likely to drop anything outside its modeled schema.
5. *Are there Compose-Specification-specific models?* Yes, in Go
   (compose-go, the official reference), Python (compose-py), and
   TypeScript (type-only) -- but none in C++, and none advertise a tested
   unknown-field/`x-*` preservation guarantee the way this paper measures
   for ComposeMorph in Experiments 3 and 4.
6. *To what extent do existing tools measure parse -> object -> serialize
   diff?* We found no published quantitative measurement (changed-line
   ratio, edit distance, or similar) for *any* of the tools surveyed --
   claims in this space are uniformly qualitative ("preserves comments",
   "loses formatting"). Experiments 1, 2, and 6 in this repository are, to
   our knowledge, the first to quantify this for a Compose-editing tool.

## 6. Empirical studies of Docker Compose in the wild (methodological precedent for Dataset B)

- Ibrahim, Sayagh & Hassan, "A Study of How Docker Compose is Used to
  Compose Multi-component Systems," *Empirical Software Engineering*
  (Springer), 2021 -- mined **4,103** open-source GitHub projects using
  Docker Compose; found over a quarter use it for single-component
  applications, 30% of Compose files are never modified after creation,
  and only 4.3% of multi-component projects use any security-related
  option. Directly validates that GitHub-sourced Compose corpora (our
  Dataset B methodology) are an established, credible data source for
  this kind of study, and that real Compose files skew toward the
  "small, rarely touched, config-light" profile we also observed in
  Dataset B's own size/complexity distribution.
- Eng, Hindle & Stroulia, "Patterns of Multi-Container Composition for
  Service Orchestration with Docker Compose," 2023 (arXiv:2305.11293) --
  catalogs recurring multi-container composition patterns from a curated
  set of real-world Compose projects.

## 7. Configuration-as-code / model-driven transformation research

- Predoaia, Kolovos, Garcia-Dominguez, Lenk, Ebel & Burkl, "Towards
  Processing YAML Documents with Model Management Languages," *MODELS
  '24 Companion Proceedings* (ACM/IEEE), Linz, Austria, 2024 -- identifies
  a "conceptual gap between contemporary model management languages and
  YAML" and demonstrates model-to-YAML transformation (EMF models to
  Ansible Playbooks) in an industrial cloud-infrastructure case study.
  Relevant as evidence that YAML-as-a-transformation-target is an active
  research concern beyond just tooling/library work, but this line of
  work operates at the model-transformation level, not the
  structure-preserving, minimal-diff editing level this paper addresses.

## Conclusion: is the "no comparable C++ library" claim defensible?

Yes, with the PDF's own recommended phrasing rather than an absolute
"first/only" claim:

> "To the best of our knowledge, existing C++ libraries do not provide the
> same combination of Docker Compose-aware structured manipulation,
> forward-compatible unknown-property preservation, and validated
> round-trip editing."

This is supported because: (a) no Docker Compose-aware *editing* API
(typed or generic) was found in C++ in any form; (b) no C++ YAML library
was found that treats round-trip preservation as a solved, documented
feature -- the two most relevant ones (yaml-cpp, rapidyaml) each have
their own open, unresolved round-trip fidelity issues; (c) the closest
matches to ComposeMorph's design intent exist only in other languages
(compose-py in Python, docker-compose-yaml-parser in JavaScript, kyaml in
Go for a different config domain), none of which publish the kind of
preservation-rate or change-locality measurements this paper's benchmark
suite produces.

What the survey does **not** support: any claim that ComposeMorph solves
comment or full-formatting preservation better than the state of the art
elsewhere -- it does not attempt to, and Python/JavaScript/Rust tooling
in other ecosystems already does this for generic YAML. ComposeMorph's
defensible contribution, per this survey, is narrower and more concrete:
a *Compose-specification-aware, type-safe C++ API* built directly on
yaml-cpp's Node tree (inheriting its round-trip limitations, as
Experiment 6 shows empirically) that adds structured accessors, a
generic property API, and measured (not just asserted) unknown-property
and `x-*` preservation guarantees -- a combination nothing surveyed here
offers in C++.

## Sources

- yaml-cpp: <https://github.com/jbeder/yaml-cpp/issues/457>, <https://github.com/jbeder/yaml-cpp/issues/154>
- libyaml: <https://github.com/yaml/libyaml/issues/42>
- rapidyaml/ryml: <https://github.com/biojppm/rapidyaml>, <https://github.com/biojppm/rapidyaml/issues/30>
- fkYAML: <https://fktn-k.github.io/fkYAML/>, <https://fktn-k.github.io/fkYAML/home/releases/>
- ruamel.yaml: <https://yaml.dev/doc/ruamel.yaml/detail/>, <https://pypi.org/project/ruamel.yaml/>
- eemeli/yaml: <https://github.com/eemeli/yaml>, <https://eemeli.org/yaml/v1/>
- yaml-edit (Rust): <https://docs.rs/yaml-edit/latest/yaml_edit/>
- cstree: <https://github.com/domenicquirl/cstree>
- LibCST: <https://github.com/Instagram/LibCST>
- kyaml/kustomize: <https://pkg.go.dev/sigs.k8s.io/kustomize/kyaml>, <https://github.com/kubernetes-sigs/kustomize/issues/259>, <https://pkg.go.dev/sigs.k8s.io/kustomize/kyaml/comments>
- compose-go: <https://github.com/compose-spec/compose-go>
- FishFinger: <https://github.com/TimTosi/fishfinger>
- compose-py: <https://github.com/bonprosoft/compose-py>
- docker-compose-yaml-parser: <https://github.com/WisdomSky/docker-compose-yaml-parser>
- resin-compose-parse: <https://www.npmjs.com/package/resin-compose-parse>
- docker-compose-spec-typescript: <https://github.com/inetum-orleans/docker-compose-spec-typescript>
- Ibrahim, Sayagh & Hassan (2021): DOI 10.1007/s10664-021-10025-1; preprint <https://sailresearch.github.io/sail-website/data/pdfs/EMSE2021_A_Study_of_How_Docker_Compose_is_Used_to_Compose_Multi-component_Systems.pdf>
- Eng, Hindle & Stroulia (2023): <https://arxiv.org/abs/2305.11293>
- Predoaia et al. (2024): <https://pure.york.ac.uk/portal/en/publications/towards-processing-yaml-documents-with-model-management-languages/>
