#!/usr/bin/env python3
"""Deep-dive on quoted-scalar type stability (follow-up to Experiment 5).

A scalar the author quoted (`version: "3.8"`, `DEBUG: "true"`) is a string.
If an editor writes it back without quotes, YAML resolvers read it as a
float/bool/int instead. Experiment 5 found this was the dominant cause of
`docker compose config` rejecting yaml-cpp-based output. This script measures
it for two editors:

  composemorph       build/roundtrip_tool (quote-preserving serializer).
  yamlcpp-baseline   build/yamlcpp_careful_tool noop: yaml-cpp's default
                     emitter, byte-identical to ComposeMorph before the fix
                     (Experiment 6), i.e. the "before" column.

Two independent measurements:

  1. Canonical-forms fixture: one quoted value per YAML scalar shape
     (integer-, float-, bool-, null-, sexagesimal-, special-float-, hex/octal-,
     timestamp-like, plain text) in an `environment:` value, a `command:` list
     element and an `x-*` map, plus a quoted top-level `version`. Each editor
     round-trips it and the Python type at each path is compared with `str`.

  2. Corpus scan: every explicitly quoted scalar in the corpus is located via
     PyYAML's event stream (which, unlike yaml.safe_load, keeps quote style),
     each editor round-trips the file, and the value at the same path in the
     output is checked against `str`. Experiment 5's raw CSV is joined in to
     report which files docker compose actually rejected.

Usage:
    python3 scripts/analyze_quote_normalization.py
"""
from __future__ import annotations

import argparse
import csv as csv_mod
import re
import statistics
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent

PatternPath = tuple[Any, ...]


# ---------------------------------------------------------------------------
# 1. Locate every explicitly quoted scalar VALUE (not mapping keys) in a YAML
#    document, with its path, via the event stream (which -- unlike
#    yaml.safe_load -- still carries quote style).
# ---------------------------------------------------------------------------
def iter_quoted_scalars(text: str) -> list[tuple[PatternPath, str, str]]:
    results: list[tuple[PatternPath, str, str]] = []
    stack: list[dict] = []  # frames: {"kind": "map"/"seq", "path": tuple, "awaiting_key": bool, "key": Any, "index": int}

    def current_value_path() -> tuple:
        if not stack:
            return ()
        top = stack[-1]
        if top["kind"] == "map":
            return top["path"] + (top["key"],)
        else:
            return top["path"] + (top["index"],)

    def on_node_end():
        """Call after a complete node (scalar, or matched end-event) is consumed as a value."""
        if not stack:
            return
        top = stack[-1]
        if top["kind"] == "map":
            top["awaiting_key"] = True
            top["key"] = None
        else:
            top["index"] += 1

    for event in yaml.parse(text, Loader=yaml.SafeLoader):
        if isinstance(event, (yaml.StreamStartEvent, yaml.StreamEndEvent,
                               yaml.DocumentStartEvent, yaml.DocumentEndEvent)):
            continue

        if isinstance(event, yaml.MappingStartEvent):
            path = current_value_path() if stack else ()
            stack.append({"kind": "map", "path": path, "awaiting_key": True, "key": None})
            continue
        if isinstance(event, yaml.MappingEndEvent):
            stack.pop()
            on_node_end()
            continue
        if isinstance(event, yaml.SequenceStartEvent):
            path = current_value_path() if stack else ()
            stack.append({"kind": "seq", "path": path, "index": 0})
            continue
        if isinstance(event, yaml.SequenceEndEvent):
            stack.pop()
            on_node_end()
            continue

        if isinstance(event, yaml.ScalarEvent):
            if stack and stack[-1]["kind"] == "map" and stack[-1]["awaiting_key"]:
                stack[-1]["key"] = event.value
                stack[-1]["awaiting_key"] = False
                continue
            path = current_value_path()
            if event.style in ('"', "'"):
                results.append((path, event.value, event.style))
            on_node_end()
            continue

        if isinstance(event, yaml.AliasEvent):
            on_node_end()
            continue

    return results


def get_by_path(doc: Any, path: PatternPath) -> Any:
    cur = doc
    for seg in path:
        if isinstance(seg, int):
            if not isinstance(cur, list) or seg >= len(cur):
                return _MISSING
            cur = cur[seg]
        else:
            if not isinstance(cur, dict) or seg not in cur:
                return _MISSING
            cur = cur[seg]
    return cur


_MISSING = object()


def path_str(path: PatternPath) -> str:
    parts = []
    for seg in path:
        parts.append(f"[{seg}]" if isinstance(seg, int) else str(seg))
    return ".".join(p for p in parts if p) if parts else "(root)"


# ---------------------------------------------------------------------------
# Classification (for grouping/reporting only -- the actual "corrupted?"
# verdict always comes from comparing real before/after types, never from
# these regexes).
# ---------------------------------------------------------------------------
PATTERN_RULES: list[tuple[str, re.Pattern]] = [
    ("null-word", re.compile(r"^(null|~|Null|NULL)?$")),
    ("bool-word", re.compile(r"^(true|false|True|False|TRUE|FALSE|yes|no|Yes|No|YES|NO|on|off|On|Off|ON|OFF|y|n|Y|N)$")),
    ("special-float", re.compile(r"^[-+]?\.(inf|Inf|INF|nan|NaN|NAN)$")),
    ("sexagesimal", re.compile(r"^-?\d+(:\d{1,2})+$")),
    ("octal-or-hex-like", re.compile(r"^0[xXoO][0-9a-fA-F]+$")),
    ("integer-like", re.compile(r"^[-+]?\d+$")),
    ("float-like", re.compile(r"^[-+]?\d+\.\d+([eE][-+]?\d+)?$")),
    ("timestamp-like", re.compile(r"^\d{4}-\d{1,2}-\d{1,2}([Tt ].*)?$")),
]


def classify_pattern(value: str) -> str:
    for name, rx in PATTERN_RULES:
        if rx.match(value):
            return name
    return "plain-text (safe)"


FIELD_RULES: list[tuple[str, re.Pattern]] = [
    ("version", re.compile(r"^version$")),
    ("command/entrypoint element", re.compile(r"\b(command|entrypoint)\b")),
    ("deploy resources (cpus/memory/replicas)", re.compile(r"\b(cpus|memory|replicas)\b")),
    ("healthcheck", re.compile(r"\bhealthcheck\b")),
    ("environment value", re.compile(r"\benvironment\b")),
    ("labels value", re.compile(r"\blabels\b")),
    ("ports element", re.compile(r"\bports\b")),
    ("build args/context", re.compile(r"\bbuild\b")),
]


def classify_field(path: PatternPath) -> str:
    p = path_str(path)
    for name, rx in FIELD_RULES:
        if rx.search(p):
            return name
    return "other/unclassified"


# ---------------------------------------------------------------------------
# Part 1: canonical-forms fixture
# ---------------------------------------------------------------------------
CANONICAL_VALUES = [
    ("integer_zero", "0"),
    ("integer_positive", "8080"),
    ("integer_leading_zero", "007"),
    ("integer_negative", "-1"),
    ("float_simple", "2.0"),
    ("float_version_like", "3.8"),
    ("float_scientific", "1.5e10"),
    ("semver_two_dots", "1.0.0"),
    ("bool_true_lower", "true"),
    ("bool_false_lower", "false"),
    ("bool_yes", "yes"),
    ("bool_on", "on"),
    ("bool_y", "y"),
    ("null_word", "null"),
    ("null_tilde", "~"),
    ("empty_string", ""),
    ("sexagesimal", "1:30"),
    ("special_float_inf", ".inf"),
    ("special_float_nan", ".nan"),
    ("hex_like", "0x1A"),
    ("octal_like", "0o17"),
    ("timestamp_date", "2024-01-01"),
    ("timestamp_datetime", "2024-01-01T00:00:00Z"),
    ("plain_text", "hello-world"),
    ("plain_text_with_dash", "my-service"),
]


def build_canonical_fixture() -> tuple[str, list[PatternPath]]:
    lines = ['version: "3.9"', "", "services:", "  app:", '    image: "nginx:latest"',
             "    command:"]
    paths: list[PatternPath] = [("version",)]
    for name, val in CANONICAL_VALUES:
        escaped = val.replace('"', '\\"')
        lines.append(f'      - "{escaped}"')
    for i in range(len(CANONICAL_VALUES)):
        paths.append(("services", "app", "command", i))
    lines.append("    environment:")
    for name, val in CANONICAL_VALUES:
        escaped = val.replace('"', '\\"')
        lines.append(f'      {name}: "{escaped}"')
        paths.append(("services", "app", "environment", name))
    lines.append("    x-test-values:")
    for name, val in CANONICAL_VALUES:
        escaped = val.replace('"', '\\"')
        lines.append(f'      {name}: "{escaped}"')
        paths.append(("services", "app", "x-test-values", name))
    return "\n".join(lines) + "\n", paths


EDITORS = ("yamlcpp-baseline", "composemorph")
EDITOR_LABELS = {
    "yamlcpp-baseline": "yaml-cpp baseline (before fix)",
    "composemorph": "ComposeMorph",
}


def first_service(path: Path) -> Optional[str]:
    try:
        doc = yaml.safe_load(path.read_text(errors="replace"))
    except Exception:
        return None
    if isinstance(doc, dict) and isinstance(doc.get("services"), dict) and doc["services"]:
        return sorted(doc["services"].keys())[0]
    return None


def run_editor(editor: str, tools: dict[str, Path], src: Path, out: Path) -> bool:
    out.parent.mkdir(parents=True, exist_ok=True)
    if editor == "composemorph":
        cmd = [str(tools["composemorph"]), str(src), str(out)]
    else:
        service = first_service(src)
        if service is None:
            return False
        cmd = [str(tools["yamlcpp-baseline"]), str(src), str(out), "noop", service]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    except subprocess.TimeoutExpired:
        return False
    return proc.returncode == 0


def type_at(doc: Any, path: PatternPath) -> str:
    value = get_by_path(doc, path)
    return "missing" if value is _MISSING else type(value).__name__


def part1_canonical(tools: dict[str, Path], scratch_dir: Path) -> dict[str, dict]:
    """editor -> {"version": type, "rows": [{shape, value, pattern, env, command, x}]}"""
    text, _ = build_canonical_fixture()
    input_path = scratch_dir / "canonical-fixture.yml"
    input_path.parent.mkdir(parents=True, exist_ok=True)
    input_path.write_text(text)

    results = {}
    for editor in EDITORS:
        output_path = scratch_dir / f"canonical-fixture.{editor}.out.yml"
        if not run_editor(editor, tools, input_path, output_path):
            print(f"error: {editor} failed on the canonical fixture", file=sys.stderr)
            continue
        out_doc = yaml.safe_load(output_path.read_text())
        rows = []
        for i, (name, val) in enumerate(CANONICAL_VALUES):
            rows.append({
                "shape": name, "value": repr(val), "pattern": classify_pattern(val),
                "env": type_at(out_doc, ("services", "app", "environment", name)),
                "command": type_at(out_doc, ("services", "app", "command", i)),
                "x": type_at(out_doc, ("services", "app", "x-test-values", name)),
            })
        results[editor] = {"version": type_at(out_doc, ("version",)), "rows": rows}
    return results


# ---------------------------------------------------------------------------
# Part 2: corpus scan
# ---------------------------------------------------------------------------
def load_docker_validity(exp5_csv: Path) -> dict[tuple[str, str], bool]:
    """(editor, file) -> valid per `docker compose config`, from Experiment 5's
    roundtrip_output rows, so docker is not re-invoked here."""
    if not exp5_csv.exists():
        return {}
    out: dict[tuple[str, str], bool] = {}
    with exp5_csv.open(newline="") as f:
        for row in csv_mod.DictReader(f):
            if row.get("stage") == "roundtrip_output" and row.get("tool") in EDITORS:
                out[(row["tool"], row["file"])] = row["valid"] == "True"
    return out


def part2_corpus(tools: dict[str, Path], dataset_dir: Path, output_dir: Path, max_files: int,
                  docker_validity: dict[tuple[str, str], bool]) -> list[dict]:
    files = sorted(p for p in dataset_dir.rglob("*") if p.suffix in (".yml", ".yaml") and p.is_file())
    if max_files:
        files = files[:max_files]

    rows = []
    for i, path in enumerate(files, 1):
        try:
            quoted = iter_quoted_scalars(path.read_text(errors="replace"))
        except Exception:
            continue
        if not quoted:
            continue

        out_docs = {}
        for editor in EDITORS:
            out_path = output_dir / editor / path.name
            if not run_editor(editor, tools, path, out_path):
                continue
            try:
                out_docs[editor] = yaml.safe_load(out_path.read_text(errors="replace"))
            except Exception:
                continue
        if len(out_docs) != len(EDITORS):
            continue

        for path_tuple, value, _style in quoted:
            row = {"file": path.name, "path": path_str(path_tuple), "value": value,
                   "pattern": classify_pattern(value), "field": classify_field(path_tuple)}
            skip = False
            for editor in EDITORS:
                after = get_by_path(out_docs[editor], path_tuple)
                if after is _MISSING:
                    skip = True
                    break
                valid = docker_validity.get((editor, path.name))
                row[f"{editor}_type"] = type(after).__name__
                row[f"{editor}_corrupted"] = type(after) is not str
                row[f"{editor}_docker_invalid"] = (valid is False) if valid is not None else None
            if not skip:
                rows.append(row)
        if i % 100 == 0 or i == len(files):
            print(f"  [{i}/{len(files)}]", file=sys.stderr)
    return rows


def _group_table(rows: list[dict], key: str, order: list[str]) -> list[str]:
    out = []
    head = "| " + key.capitalize() + " | Occurrences | " + " | ".join(
        f"{EDITOR_LABELS[e]}: corrupted | {EDITOR_LABELS[e]}: files docker-invalid*" for e in EDITORS) + " |"
    out.append(head)
    out.append("|---" * (2 + 2 * len(EDITORS)) + "|")
    groups: dict[str, list[dict]] = {}
    for r in rows:
        groups.setdefault(r[key], []).append(r)
    for name in order:
        g = groups.get(name, [])
        if not g:
            continue
        cells = []
        for e in EDITORS:
            bad = [r for r in g if r[f"{e}_corrupted"]]
            confirmed = {r["file"] for r in bad if r[f"{e}_docker_invalid"]}
            known = {r["file"] for r in bad if r[f"{e}_docker_invalid"] is not None}
            cells.append(f"{len(bad)} ({100 * len(bad) / len(g):.1f}%)")
            cells.append(f"{len(confirmed)}/{len(known)}" if known else "n/a")
        out.append(f"| {name} | {len(g)} | " + " | ".join(cells) + " |")
    return out


def summarize(canonical: dict[str, dict], corpus_rows: list[dict], dataset_label: str) -> str:
    lines = ["# Quoted-Scalar Type Stability (follow-up to Experiment 5)\n"]

    lines.append("## 1. Canonical scalar-shape reference table\n")
    for e in EDITORS:
        if e in canonical:
            lines.append(f"- {EDITOR_LABELS[e]}: quoted top-level `version: \"3.9\"` came back as "
                         f"**{canonical[e]['version']}**")
    lines.append("")
    lines.append("Each cell gives the resolved type after the round-trip in an `environment:` value / "
                 "a `command:` element / an `x-*` map. `str` everywhere means the quotes held.\n")
    lines.append("| Shape | Quoted value | Pattern | " + " | ".join(EDITOR_LABELS[e] for e in EDITORS) + " |")
    lines.append("|---" * (3 + len(EDITORS)) + "|")
    base_rows = canonical.get(EDITORS[0], {}).get("rows", [])
    for i, r in enumerate(base_rows):
        cells = []
        for e in EDITORS:
            er = canonical.get(e, {}).get("rows", [])
            cells.append(f"{er[i]['env']} / {er[i]['command']} / {er[i]['x']}" if i < len(er) else "n/a")
        lines.append(f"| {r['shape']} | {r['value']} | {r['pattern']} | " + " | ".join(cells) + " |")
    lines.append("")

    lines.append(f"## 2. {dataset_label} corpus scan: real quoted-scalar occurrences\n")
    files_quoted = {r["file"] for r in corpus_rows}
    lines.append(f"- Quoted-scalar occurrences checked: **{len(corpus_rows)}** "
                 f"in **{len(files_quoted)}** files")
    for e in EDITORS:
        bad = [r for r in corpus_rows if r[f"{e}_corrupted"]]
        bad_files = {r["file"] for r in bad}
        share = f"{100 * len(bad_files) / len(files_quoted):.1f}%" if files_quoted else "n/a"
        lines.append(f"- {EDITOR_LABELS[e]}: **{len(bad)}** occurrences changed type, in "
                     f"**{len(bad_files)}** files ({share} of files with quoted scalars)")
    lines.append("")
    lines.append(
        "\"Corrupted\" = the value at the same path no longer resolves to `str` under PyYAML "
        "(YAML 1.1 resolution rules). \"Files docker-invalid\" joins Experiment 5's "
        "`docker compose config` result for that editor's output of the same file; go-yaml, "
        "Compose's parser, resolves some shapes differently (e.g. no sexagesimal ints), so not "
        "every PyYAML-level type change is rejected by Docker.\n"
    )

    lines.append("### By YAML scalar pattern\n")
    lines.extend(_group_table(corpus_rows, "pattern",
                              [name for name, _ in PATTERN_RULES] + ["plain-text (safe)"]))
    lines.append("")
    lines.append("### By Compose field location\n")
    field_order = sorted({r["field"] for r in corpus_rows},
                         key=lambda f: -sum(1 for r in corpus_rows if r["field"] == f))
    lines.extend(_group_table(corpus_rows, "field", field_order))
    lines.append("\n\\* Distinct files with a corrupted occurrence in that group whose docker "
                 "validity is known from Experiment 5 (validity is per file, not per occurrence).\n")

    for e in EDITORS:
        bad = [r for r in corpus_rows if r[f"{e}_corrupted"]]
        if not bad:
            continue
        lines.append(f"### {EDITOR_LABELS[e]}: sample of corrupted occurrences ({len(bad)} total)\n")
        lines.append("| File | Path | Original (quoted) | Became |")
        lines.append("|---|---|---|---|")
        for r in bad[:20]:
            lines.append(f"| `{r['file']}` | `{r['path']}` | `{r['value']!r}` | {r[f'{e}_type']} |")
        if len(bad) > 20:
            lines.append(f"| ... | {len(bad) - 20} more | | (see raw CSV) |")
        lines.append("")

    lines.append("## Mechanism\n")
    lines.append(
        "yaml-cpp's parser marks every quoted scalar with the non-specific tag `!` (plain scalars "
        "get `?`), but its emitter ignores that tag: `IsValidPlainScalar` in yaml-cpp 0.8.0's "
        "`src/emitterutils.cpp` writes a string without quotes unless it is null-like "
        "(`IsNullString`) or syntactically unsafe. That is why only the null-word shapes keep "
        "their quotes in the baseline column. ComposeMorph's serializer writes every `!`-tagged "
        "scalar double-quoted and leaves `?`-tagged (plain) scalars plain; see "
        "`src/ScalarQuoting.cpp`.\n"
    )
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dataset-dir", default="datasets/real-world-combined")
    ap.add_argument("--dataset-label", default="Dataset B")
    ap.add_argument("--tool", default="build/roundtrip_tool")
    ap.add_argument("--baseline-tool", default="build/yamlcpp_careful_tool")
    ap.add_argument("--output-dir", default="results/raw/quote-analysis/output")
    ap.add_argument("--scratch-dir", default="results/raw/quote-analysis/fixture")
    ap.add_argument("--raw-csv", default="results/raw/quote_normalization_analysis.csv")
    ap.add_argument("--summary-md", default="results/tables/quote_normalization_analysis.md")
    ap.add_argument("--exp5-csv", default="results/raw/validation_dataset_b.csv",
                     help="Experiment 5's raw CSV, joined in for docker-confirmed validity.")
    ap.add_argument("--max-files", type=int, default=0, help="0 = whole corpus")
    args = ap.parse_args()

    tools = {"composemorph": (REPO_ROOT / args.tool).resolve(),
             "yamlcpp-baseline": (REPO_ROOT / args.baseline_tool).resolve()}
    dataset_dir = (REPO_ROOT / args.dataset_dir).resolve()
    output_dir = (REPO_ROOT / args.output_dir).resolve()
    scratch_dir = (REPO_ROOT / args.scratch_dir).resolve()
    for name, path in tools.items():
        if not path.exists():
            print(f"error: {name} binary not found at {path} (build it first)", file=sys.stderr)
            return 1
    if not dataset_dir.is_dir():
        print(f"error: dataset dir not found: {dataset_dir}", file=sys.stderr)
        return 1
    output_dir.mkdir(parents=True, exist_ok=True)
    scratch_dir.mkdir(parents=True, exist_ok=True)

    print("Running canonical-forms fixture...", file=sys.stderr)
    canonical = part1_canonical(tools, scratch_dir)

    docker_validity = load_docker_validity((REPO_ROOT / args.exp5_csv).resolve())
    if not docker_validity:
        print(f"warning: no per-tool rows in {args.exp5_csv} -- run run_validation_experiment.py "
              f"first for docker-confirmed columns (proceeding without them)", file=sys.stderr)

    print("Scanning corpus for quoted scalars...", file=sys.stderr)
    corpus_rows = part2_corpus(tools, dataset_dir, output_dir, args.max_files, docker_validity)

    raw_csv = (REPO_ROOT / args.raw_csv).resolve()
    raw_csv.parent.mkdir(parents=True, exist_ok=True)
    fields = ["file", "path", "value", "pattern", "field"] + [
        f"{e}_{k}" for e in EDITORS for k in ("type", "corrupted", "docker_invalid")]
    with raw_csv.open("w", newline="") as f:
        writer = csv_mod.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(corpus_rows)

    summary = summarize(canonical, corpus_rows, args.dataset_label)
    summary_md = (REPO_ROOT / args.summary_md).resolve()
    summary_md.parent.mkdir(parents=True, exist_ok=True)
    summary_md.write_text(summary)

    print(summary)
    print(f"\nRaw per-occurrence results: {raw_csv}", file=sys.stderr)
    print(f"Summary: {summary_md}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
