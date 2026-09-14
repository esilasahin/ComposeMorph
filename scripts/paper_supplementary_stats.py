#!/usr/bin/env python3
"""Supplementary statistics quoted in the paper, from committed raw outputs.

Every figure here is derived from files already under datasets/ and
results/raw/ (no experiment is re-run), so the numbers the paper quotes
outside the per-experiment summaries stay traceable:

  1. Block scalars (| and >) in Dataset B -- how many files are affected by
     the serializer writing them as escaped double-quoted strings.
  2. Experiment 6: why yamlcpp-careful misses some collateral fields --
     classifies each failed case as "fields present, only scalar
     presentation changed" (compared with PyYAML's BaseLoader, which keeps
     every scalar as text) or "output not parseable".
  3. Experiment 2: effect of the short-syntax fix -- cases whose edit still
     changed more than one line after subtracting the identity round-trip
     noise, before (results/pre-fix/raw/) vs. after (results/raw/).
  4. Experiment 7: cold first-iteration cost of the modify step.

Usage:
    python3 scripts/paper_supplementary_stats.py
"""
from __future__ import annotations

import argparse
import csv
import statistics
import sys
from pathlib import Path

import yaml


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def load_text_tree(path: Path):
    """Load with BaseLoader: every scalar stays a string, so values compare as text."""
    with path.open(errors="replace") as f:
        return yaml.load(f, Loader=yaml.BaseLoader)


def block_scalars(dataset_dir: Path) -> tuple[int, int, int]:
    files = with_block = occurrences = 0
    for path in sorted(dataset_dir.glob("*.yml")):
        files += 1
        try:
            events = list(yaml.parse(path.open(errors="replace")))
        except yaml.YAMLError:
            continue
        n = sum(1 for e in events if isinstance(e, yaml.ScalarEvent) and e.style in ("|", ">"))
        if n:
            with_block += 1
            occurrences += n
    return files, with_block, occurrences


def env_keys(env) -> set[str]:
    if isinstance(env, dict):
        return set(env)
    return {str(item).partition("=")[0] for item in env or []}


def careful_collateral(rows: list[dict], dataset_dir: Path, output_dir: Path) -> dict[str, dict[str, int]]:
    result: dict[str, dict[str, int]] = {}
    for r in rows:
        if r["tool"] != "yamlcpp-careful" or r["collateral_preserved"] != "False":
            continue
        op, service = r["op"], r["service"]
        counts = result.setdefault(op, {"failed": 0, "fields_present": 0, "unparseable": 0, "other": 0})
        counts["failed"] += 1
        before = load_text_tree(dataset_dir / r["file"])["services"][service]
        try:
            after_doc = load_text_tree(output_dir / "yamlcpp-careful" / op / r["file"])
        except yaml.YAMLError:
            counts["unparseable"] += 1
            continue
        after = (after_doc.get("services") or {}).get(service) or {}
        if op == "env":
            present = env_keys(before.get("environment")) <= env_keys(after.get("environment"))
        else:
            present = all(k in after for k in before if k != op)
        counts["fields_present" if present else "other"] += 1
    return result


def syntax_form(dataset_dir: Path, file: str, service: str, key: str) -> str:
    try:
        value = yaml.safe_load((dataset_dir / file).read_text(errors="replace"))["services"][service].get(key)
    except Exception:
        return "unknown"
    return "list" if isinstance(value, list) else "map" if isinstance(value, dict) else "unknown"


def multi_line_edits(rows: list[dict], dataset_dir: Path) -> dict[tuple[str, str], tuple[int, int, float]]:
    """(op, syntax form) -> (cases, cases with incremental lines > 1, median incremental lines)."""
    keys = {"env": "environment", "extra-host": "extra_hosts", "image": None}
    groups: dict[tuple[str, str], list[float]] = {}
    for r in rows:
        if r["op"] not in keys or r["status"] != "OK" or not r["incremental_changed_lines"]:
            continue
        key = keys[r["op"]]
        form = syntax_form(dataset_dir, r["file"], r["service"], key) if key else "all"
        groups.setdefault((r["op"], form), []).append(float(r["incremental_changed_lines"]))
    return {g: (len(v), sum(1 for x in v if x > 1), statistics.median(v)) for g, v in sorted(groups.items())}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dataset-dir", default="datasets/real-world-combined")
    ap.add_argument("--comparison-csv", default="results/raw/comparison_modification.csv")
    ap.add_argument("--comparison-output", default="results/raw/comparison/output/modification")
    ap.add_argument("--modification-csv", default="results/raw/modification_dataset_b.csv")
    ap.add_argument("--prefix-modification-csv", default="results/pre-fix/raw/modification_dataset_b.csv")
    ap.add_argument("--performance-csv", default="results/raw/performance_dataset_b.csv")
    ap.add_argument("--summary-md", default="results/tables/paper_supplementary_stats.md")
    args = ap.parse_args()

    dataset_dir = Path(args.dataset_dir)
    lines = ["# Supplementary statistics quoted in the paper\n",
             "Derived from committed datasets and raw outputs; see the script docstring "
             "(`scripts/paper_supplementary_stats.py`).\n"]

    files, with_block, occurrences = block_scalars(dataset_dir)
    lines.append("## 1. Block scalars in Dataset B\n")
    lines.append(f"- Files with at least one block scalar (`|` or `>`): **{with_block}/{files}** "
                 f"({100 * with_block / files:.1f}%), {occurrences} occurrences in total.")
    lines.append("- ComposeMorph keeps their content but writes them as escaped, single-line "
                 "double-quoted strings (the `!` tag marks every non-plain scalar).\n")

    lines.append("## 2. Experiment 6: yamlcpp-careful collateral misses\n")
    lines.append("| Op | Failed cases | Sibling fields present (scalar presentation changed) | Output not parseable | Other |")
    lines.append("|---|---|---|---|---|")
    for op, c in careful_collateral(read_csv(Path(args.comparison_csv)), dataset_dir,
                                    Path(args.comparison_output)).items():
        lines.append(f"| {op} | {c['failed']} | {c['fields_present']} | {c['unparseable']} | {c['other']} |")
    lines.append("")

    lines.append("## 3. Experiment 2: edits that change more than one line after noise subtraction\n")
    lines.append("| Op | Syntax form | Before fix: >1 line / cases (median) | After fix: >1 line / cases (median) |")
    lines.append("|---|---|---|---|")
    before = multi_line_edits(read_csv(Path(args.prefix_modification_csv)), dataset_dir)
    after = multi_line_edits(read_csv(Path(args.modification_csv)), dataset_dir)
    for group in sorted(set(before) | set(after)):
        b = before.get(group)
        a = after.get(group)
        fmt = lambda t: f"{t[1]}/{t[0]} ({t[2]:g})" if t else "n/a"
        lines.append(f"| {group[0]} | {group[1]} | {fmt(b)} | {fmt(a)} |")
    lines.append("")

    perf = read_csv(Path(args.performance_csv))
    cold = [float(r["modify_ms"]) for r in perf if r["iteration"] == "0"]
    lines.append("## 4. Experiment 7: cold first iteration of the modify step\n")
    lines.append(f"- Files: {len(cold)}; modify_ms at iteration 0: median={statistics.median(cold):.2f}ms, "
                 f"max={max(cold):.2f}ms.\n")

    out = Path(args.summary_md)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines))
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
