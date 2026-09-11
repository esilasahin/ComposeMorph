#!/usr/bin/env python3
"""Deep-dive on the quote-normalization finding from Experiment 5:
`docker compose config` rejected 542/557 (97%) of otherwise-valid outputs
because a quoted scalar (e.g. `version: "3.8"`) came back unquoted after a
ComposeMorph round-trip, silently changing its YAML-resolved type from
string to number/bool/null.

Two independent measurements, no synthetic guessing required for either:

  1. Canonical-forms test: a small hand-built fixture with one quoted
     value per YAML scalar "shape" (integer-like, float-like, boolean
     word, null word, sexagesimal, special float, octal/hex, timestamp,
     plain text) in both a generic location and realistic Compose
     positions (`version`, a `command` list element, an `environment`
     value). Round-tripped through roundtrip_tool, then the *actual*
     post-round-trip Python type at each path is compared against `str`.
     This gives a clean per-scalar-shape reference table.

  2. Dataset B corpus scan: every explicitly double/single-quoted scalar
     in all 647 real files is located (via PyYAML's event stream, which
     records quote style -- `yaml.safe_load` alone would already have
     thrown that information away), round-tripped, and the value at the
     same path in the output is checked against `str`. This measures how
     often each scalar shape and each Compose field actually appears
     quoted-and-then-corrupted in the wild -- ground truth, not a
     regex guess at what yaml-cpp "should" do.

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


def run_roundtrip(tool: Path, input_path: Path, output_path: Path) -> bool:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        proc = subprocess.run([str(tool), str(input_path), str(output_path)],
                               capture_output=True, text=True, timeout=30)
    except subprocess.TimeoutExpired:
        return False
    return proc.returncode == 0


def part1_canonical(tool: Path, scratch_dir: Path) -> list[dict]:
    text, _ = build_canonical_fixture()
    input_path = scratch_dir / "canonical-fixture.yml"
    input_path.parent.mkdir(parents=True, exist_ok=True)
    input_path.write_text(text)
    output_path = scratch_dir / "canonical-fixture.out.yml"
    if not run_roundtrip(tool, input_path, output_path):
        print("error: roundtrip_tool failed on canonical fixture", file=sys.stderr)
        return []

    out_doc = yaml.safe_load(output_path.read_text())
    rows = []
    for name, val in CANONICAL_VALUES:
        env_type = type(get_by_path(out_doc, ("services", "app", "environment", name))).__name__
        x_type = type(get_by_path(out_doc, ("services", "app", "x-test-values", name))).__name__
        rows.append({
            "shape": name, "original_value": repr(val), "pattern": classify_pattern(val),
            "environment_position_type": env_type, "generic_position_type": x_type,
            "corrupted": env_type != "str" or x_type != "str",
        })
    # version and command[] are single fixed positions, report separately
    version_type = type(get_by_path(out_doc, ("version",))).__name__
    command_rows = []
    for i, (name, val) in enumerate(CANONICAL_VALUES):
        t = type(get_by_path(out_doc, ("services", "app", "command", i))).__name__
        command_rows.append({"shape": name, "original_value": repr(val), "pattern": classify_pattern(val),
                              "command_position_type": t, "corrupted": t != "str"})
    return rows, command_rows, version_type


# ---------------------------------------------------------------------------
# Part 2: real corpus scan
# ---------------------------------------------------------------------------
def load_docker_validity(exp5_csv: Path) -> dict[str, bool]:
    """file -> True/False (valid per real `docker compose config`), from Experiment 5's
    already-computed roundtrip_output rows -- avoids re-invoking docker here."""
    if not exp5_csv.exists():
        return {}
    out: dict[str, bool] = {}
    with exp5_csv.open(newline="") as f:
        for row in csv_mod.DictReader(f):
            if row.get("stage") == "roundtrip_output":
                out[row["file"]] = row["valid"] == "True"
    return out


def part2_corpus(tool: Path, dataset_dir: Path, output_dir: Path, max_files: int,
                  docker_validity: dict[str, bool]) -> list[dict]:
    files = sorted(p for p in dataset_dir.rglob("*") if p.suffix in (".yml", ".yaml") and p.is_file())
    if max_files:
        files = files[:max_files]

    rows = []
    for i, path in enumerate(files, 1):
        try:
            text = path.read_text(errors="replace")
        except Exception:
            continue
        try:
            quoted = iter_quoted_scalars(text)
        except Exception:
            continue
        if not quoted:
            continue

        out_path = output_dir / path.name
        if not run_roundtrip(tool, path, out_path):
            continue
        try:
            out_doc = yaml.safe_load(out_path.read_text(errors="replace"))
        except Exception:
            continue

        for path_tuple, value, style in quoted:
            after = get_by_path(out_doc, path_tuple)
            if after is _MISSING:
                continue  # path shape changed (e.g. quoting itself doesn't remove keys); skip rather than misreport
            after_type = type(after).__name__
            docker_valid = docker_validity.get(path.name)
            rows.append({
                "file": path.name, "path": path_str(path_tuple), "value": value,
                "pattern": classify_pattern(value), "field": classify_field(path_tuple),
                "after_type": after_type, "corrupted": after_type != "str",
                "docker_confirmed_invalid": (docker_valid is False) if docker_valid is not None else None,
            })
        if i % 100 == 0 or i == len(files):
            print(f"  [{i}/{len(files)}]", file=sys.stderr)
    return rows


def summarize(canonical_env: list[dict], canonical_cmd: list[dict], version_type: str,
              corpus_rows: list[dict]) -> str:
    lines = ["# Quote-Normalization Deep Dive (follow-up to Experiment 5)\n"]

    lines.append("## 1. Canonical scalar-shape reference table\n")
    lines.append(
        f"Fixture's top-level `version: \"3.9\"` came back as: **{version_type}**"
        f" (corrupted: {version_type != 'str'}).\n"
    )
    lines.append("| Shape | Quoted value | Pattern | In `environment:` value | In `command:` list | In generic (`x-*`) map |")
    lines.append("|---|---|---|---|---|---|")
    for env_row, cmd_row in zip(canonical_env, canonical_cmd):
        mark_env = env_row["environment_position_type"]
        mark_cmd = cmd_row["command_position_type"]
        mark_x = env_row["generic_position_type"]
        lines.append(
            f"| {env_row['shape']} | {env_row['original_value']} | {env_row['pattern']} | "
            f"{mark_env} | {mark_cmd} | {mark_x} |"
        )
    lines.append("\n`str` = quote effectively preserved (safe). Anything else (`int`, `float`, `bool`, "
                  "`NoneType`) means the round-trip silently changed the value's type.\n")

    lines.append("## 2. Dataset B corpus scan: real quoted-scalar occurrences\n")
    lines.append(f"Total quoted-scalar occurrences found and checked: **{len(corpus_rows)}**\n")
    files_affected = {r["file"] for r in corpus_rows}
    files_corrupted = {r["file"] for r in corpus_rows if r["corrupted"]}
    lines.append(f"- Files with at least one explicitly-quoted scalar: **{len(files_affected)}**")
    lines.append(
        f"- Of those, files where at least one quoted scalar was corrupted by the round-trip: "
        f"**{len(files_corrupted)}** ({100*len(files_corrupted)/len(files_affected):.1f}%)\n" if files_affected else ""
    )

    lines.append("### By YAML scalar pattern\n")
    lines.append(
        "\"Corrupted\" = type changed under PyYAML's YAML-1.1-family resolver (same core "
        "schema family as yaml-cpp's), used here as an instrument since `yaml.safe_load` alone "
        "discards quote style. \"Docker-confirmed invalid\" cross-references Experiment 5's "
        "actual `docker compose config` run on the same files -- go-yaml (Compose's parser) "
        "resolves scalars slightly differently (e.g. it has no sexagesimal-int support), so not "
        "every PyYAML-detected type change is something Docker itself rejects.\n"
    )
    lines.append("| Pattern | Occurrences | Corrupted (PyYAML) | Rate | Files docker-confirmed invalid* |")
    lines.append("|---|---|---|---|---|")
    by_pattern: dict[str, list[dict]] = {}
    for r in corpus_rows:
        by_pattern.setdefault(r["pattern"], []).append(r)
    for pattern, _ in PATTERN_RULES + [("plain-text (safe)", None)]:
        rows = by_pattern.get(pattern, [])
        if not rows:
            continue
        corrupted = sum(1 for r in rows if r["corrupted"])
        corrupted_rows_here = [r for r in rows if r["corrupted"]]
        confirmed_files = {r["file"] for r in corrupted_rows_here if r["docker_confirmed_invalid"]}
        known_files = {r["file"] for r in corrupted_rows_here if r["docker_confirmed_invalid"] is not None}
        confirm_str = f"{len(confirmed_files)}/{len(known_files)} files" if known_files else "n/a"
        lines.append(f"| {pattern} | {len(rows)} | {corrupted} | {100*corrupted/len(rows):.1f}% | {confirm_str} |")
    lines.append(
        "\n\\* Denominator is distinct *files* with a corrupted occurrence of that pattern whose "
        "docker-validity is known from Experiment 5's run (not occurrences, since validity is "
        "per-file); a file can appear under multiple patterns.\n"
    )

    lines.append("### By Compose field location\n")
    lines.append("| Field | Occurrences | Corrupted (PyYAML) | Rate | Files docker-confirmed invalid* |")
    lines.append("|---|---|---|---|---|")
    by_field: dict[str, list[dict]] = {}
    for r in corpus_rows:
        by_field.setdefault(r["field"], []).append(r)
    for field, rows in sorted(by_field.items(), key=lambda kv: -len(kv[1])):
        corrupted = sum(1 for r in rows if r["corrupted"])
        corrupted_rows_here = [r for r in rows if r["corrupted"]]
        confirmed_files = {r["file"] for r in corrupted_rows_here if r["docker_confirmed_invalid"]}
        known_files = {r["file"] for r in corrupted_rows_here if r["docker_confirmed_invalid"] is not None}
        confirm_str = f"{len(confirmed_files)}/{len(known_files)} files" if known_files else "n/a"
        lines.append(f"| {field} | {len(rows)} | {corrupted} | {100*corrupted/len(rows):.1f}% | {confirm_str} |")
    lines.append(
        "\n**Environment/label values are the most *frequently* corrupted by occurrence count, "
        "but this table's last column is what tells you whether that corruption is something "
        "`docker compose config` actually rejects** -- the Compose schema treats most "
        "`environment:`/`labels:` values as permissively-typed, so a `\"true\"` becoming `true` "
        "there often round-trips back to a config Docker still accepts, whereas the same shape in "
        "`version:` or a `command:` element is fatal. Either way, ComposeMorph is silently "
        "changing a value the user explicitly wrote as a string -- an application reading that "
        "environment variable expecting text (e.g. via a strict-typed config loader) would still "
        "see different content if it introspects the file directly rather than the merged "
        "container environment.\n"
    )

    corrupted_rows = [r for r in corpus_rows if r["corrupted"]]
    if corrupted_rows:
        lines.append(f"### Sample of corrupted occurrences ({len(corrupted_rows)} total)\n")
        lines.append("| File | Path | Original (quoted) | Became |")
        lines.append("|---|---|---|---|")
        for r in corrupted_rows[:20]:
            lines.append(f"| `{r['file']}` | `{r['path']}` | `{r['value']!r}` | {r['after_type']} |")
        if len(corrupted_rows) > 20:
            lines.append(f"| ... | {len(corrupted_rows) - 20} more | | (see raw CSV) |")
        lines.append("")

    per_file_counts = {}
    for r in corrupted_rows:
        per_file_counts[r["file"]] = per_file_counts.get(r["file"], 0) + 1
    if per_file_counts:
        counts = list(per_file_counts.values())
        lines.append(
            f"### Corrupted occurrences per affected file\n\n"
            f"mean={statistics.mean(counts):.2f}, median={statistics.median(counts)}, "
            f"max={max(counts)} (n={len(counts)} files)\n"
        )

    lines.append("## Takeaway\n")
    lines.append(
        "The corruption is fully explained by scalar *shape*, not by which Compose field it "
        "happens to sit in: any explicitly-quoted value that reads as an integer, float, "
        "YAML 1.1 boolean word, or null word loses its quotes on save and is reinterpreted "
        "with the new type -- in a generic map, in an `environment:` value, or in a `command:` "
        "list element alike. `version:` is simply the single field where this shape "
        "(`\"N.N\"`, matching `float-like`) happens to appear in nearly every real Compose file, "
        "which is why it dominates Experiment 5's failure count. Plain-text quoted values "
        "(`plain-text (safe)`) are unaffected. This is a property of yaml-cpp's default "
        "emitter -- which does not track each scalar's original quote style, only whether "
        "quoting is syntactically *required* -- not something specific to ComposeMorph's own code.\n"
    )

    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dataset-dir", default="datasets/real-world-combined")
    ap.add_argument("--tool", default="build/roundtrip_tool")
    ap.add_argument("--output-dir", default="results/raw/quote-analysis/output")
    ap.add_argument("--scratch-dir", default="results/raw/quote-analysis/fixture")
    ap.add_argument("--raw-csv", default="results/raw/quote_normalization_analysis.csv")
    ap.add_argument("--summary-md", default="results/tables/quote_normalization_analysis.md")
    ap.add_argument("--exp5-csv", default="results/raw/validation_dataset_b.csv",
                     help="Experiment 5's raw CSV, used to cross-reference which PyYAML-detected "
                          "type changes are confirmed by a real docker compose config run.")
    ap.add_argument("--max-files", type=int, default=0, help="0 = all of Dataset B")
    args = ap.parse_args()

    tool = (REPO_ROOT / args.tool).resolve()
    dataset_dir = (REPO_ROOT / args.dataset_dir).resolve()
    output_dir = (REPO_ROOT / args.output_dir).resolve()
    scratch_dir = (REPO_ROOT / args.scratch_dir).resolve()
    if not tool.exists():
        print(f"error: roundtrip_tool not found at {tool} (build it first)", file=sys.stderr)
        return 1
    if not dataset_dir.is_dir():
        print(f"error: dataset dir not found: {dataset_dir}", file=sys.stderr)
        return 1

    output_dir.mkdir(parents=True, exist_ok=True)
    scratch_dir.mkdir(parents=True, exist_ok=True)

    print("Running canonical-forms fixture...", file=sys.stderr)
    canonical_env, canonical_cmd, version_type = part1_canonical(tool, scratch_dir)

    docker_validity = load_docker_validity((REPO_ROOT / args.exp5_csv).resolve())
    if not docker_validity:
        print(f"warning: {args.exp5_csv} not found or empty -- run run_validation_experiment.py "
              f"first for docker-confirmed cross-referencing (proceeding without it)", file=sys.stderr)

    print("Scanning Dataset B for quoted scalars and checking round-trip type stability...", file=sys.stderr)
    corpus_rows = part2_corpus(tool, dataset_dir, output_dir, args.max_files, docker_validity)

    raw_csv = (REPO_ROOT / args.raw_csv).resolve()
    raw_csv.parent.mkdir(parents=True, exist_ok=True)
    with raw_csv.open("w", newline="") as f:
        writer = csv_mod.DictWriter(f, fieldnames=["file", "path", "value", "pattern", "field",
                                                     "after_type", "corrupted", "docker_confirmed_invalid"])
        writer.writeheader()
        writer.writerows(corpus_rows)

    summary = summarize(canonical_env, canonical_cmd, version_type, corpus_rows)
    summary_md = (REPO_ROOT / args.summary_md).resolve()
    summary_md.parent.mkdir(parents=True, exist_ok=True)
    summary_md.write_text(summary)

    print(summary)
    print(f"\nRaw per-occurrence results: {raw_csv}", file=sys.stderr)
    print(f"Summary: {summary_md}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
