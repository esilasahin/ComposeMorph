#!/usr/bin/env python3
"""Experiment 5 -- Docker Compose Validation (RQ1's third metric).

Runs `docker compose -f <file> config` -- the Compose Specification's own
schema validator -- against the inputs of a corpus and against the outputs of
two editors for the same two canonical pipelines (Experiment 1's identity
round-trip, Experiment 2's `image` edit), plus Experiment 3/4's
marker-injected fixtures:

  composemorph       build/roundtrip_tool and build/modify_tool (current
                     library, with the quote-preserving serializer).
  yamlcpp-baseline   build/yamlcpp_careful_tool: raw yaml-cpp with in-place
                     edits and yaml-cpp's default emitter. Before the
                     quote-preserving serializer, ComposeMorph's round-trip
                     output was byte-identical to it (Experiment 6, 100/100
                     files; results/pre-fix/tables/comparison_summary.md), so it
                     stands in for the "before" column and keeps that number
                     reproducible.

The script regenerates every output it validates rather than relying on
files left behind by another script.

`docker compose config` does not need a running daemon, only the
`docker compose` CLI plugin on PATH.

Per the task spec, invalid *inputs* are reported separately and excluded
from the output validation-rate denominators -- only files docker compose
already accepts count toward those.

Usage:
    python3 scripts/run_validation_experiment.py
    python3 scripts/run_validation_experiment.py --max-files 0   # whole corpus
"""
from __future__ import annotations

import argparse
import copy
import csv
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_modification_experiment import find_image  # noqa: E402
from run_preservation_experiment import MARKER_SPECS  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent

TOOL_NAMES = ("composemorph", "yamlcpp-baseline")
TOOL_LABELS = {
    "composemorph": "ComposeMorph",
    "yamlcpp-baseline": "yaml-cpp baseline (= ComposeMorph before the quote fix)",
}

FIELDNAMES = ["tool", "stage", "file", "service", "variant", "valid", "exit_code", "error", "elapsed_s"]


def check_docker_compose_cli() -> Optional[str]:
    if shutil.which("docker") is None:
        return "docker CLI not found on PATH. Install Docker (https://docs.docker.com/get-docker/) and re-run."
    try:
        proc = subprocess.run(["docker", "compose", "version"], capture_output=True, text=True, timeout=10)
    except Exception as e:
        return f"could not run 'docker compose version': {e}"
    if proc.returncode != 0:
        return f"'docker compose version' failed: {proc.stderr.strip()}"
    return None


def extract_error(stderr: str) -> str:
    """docker compose prints one `time="..." level=warning ...` line per unset
    interpolation variable before the actual error, if any; put the real error
    first so it survives truncation."""
    lines = [ln for ln in stderr.strip().splitlines() if ln.strip()]
    warnings = [ln for ln in lines if ln.startswith('time="') and "level=warning" in ln]
    other = [ln for ln in lines if ln not in warnings]
    return " | ".join(other + warnings)[:800]


def docker_compose_config(path: Path) -> tuple[bool, int, str, float]:
    t0 = time.perf_counter()
    try:
        proc = subprocess.run(["docker", "compose", "-f", str(path), "config"],
                               capture_output=True, text=True, timeout=30)
    except subprocess.TimeoutExpired:
        return False, -1, "TIMEOUT", round(time.perf_counter() - t0, 3)
    elapsed = round(time.perf_counter() - t0, 3)
    return proc.returncode == 0, proc.returncode, extract_error(proc.stderr), elapsed


def inject_filtered(doc: dict, service: str, categories: set[str]) -> dict:
    doc = copy.deepcopy(doc)
    for spec in MARKER_SPECS:
        if spec["category"] not in categories:
            continue
        value = copy.deepcopy(spec["value"])
        if spec["scope"] == "top":
            doc[spec["key"]] = value
        else:
            doc["services"][service][spec["key"]] = value
    return doc


def run_tool(tool: Path, args: list[str]) -> bool:
    try:
        proc = subprocess.run([str(tool), *args], capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        return False
    return proc.returncode == 0


class Editors:
    def __init__(self, roundtrip: Path, modify: Path, baseline: Path):
        self.roundtrip, self.modify, self.baseline = roundtrip, modify, baseline

    def roundtrip_file(self, tool: str, src: Path, out: Path, any_service: Optional[str]) -> bool:
        if tool == "composemorph":
            return run_tool(self.roundtrip, [str(src), str(out)])
        if any_service is None:
            return False
        return run_tool(self.baseline, [str(src), str(out), "noop", any_service])

    def edit_image(self, tool: str, src: Path, out: Path, service: str, tool_args: list[str]) -> bool:
        exe = self.modify if tool == "composemorph" else self.baseline
        return run_tool(exe, [str(src), str(out), "image", service, *tool_args])


def first_service(doc) -> Optional[str]:
    if isinstance(doc, dict) and isinstance(doc.get("services"), dict) and doc["services"]:
        return sorted(doc["services"].keys())[0]
    return None


def image_target(doc) -> tuple[Optional[str], Optional[dict]]:
    if not isinstance(doc, dict) or not isinstance(doc.get("services"), dict):
        return None, None
    for name in sorted(doc["services"].keys()):
        svc = doc["services"][name]
        if isinstance(svc, dict):
            spec = find_image(svc)
            if spec is not None:
                return name, spec
    return None, None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dataset-dir", default="datasets/real-world-combined")
    ap.add_argument("--roundtrip-tool", default="build/roundtrip_tool")
    ap.add_argument("--modify-tool", default="build/modify_tool")
    ap.add_argument("--baseline-tool", default="build/yamlcpp_careful_tool")
    ap.add_argument("--output-dir", default="results/raw/validation/output")
    ap.add_argument("--seed-dir", default="results/raw/validation/seeded-input")
    ap.add_argument("--raw-csv", default="results/raw/validation_dataset_b.csv")
    ap.add_argument("--summary-md", default="results/tables/validation_summary.md")
    ap.add_argument("--max-files", type=int, default=200,
                     help="Cap on files to test; 0 = all files (the full official run).")
    ap.add_argument("--dataset-label", default="Dataset B")
    args = ap.parse_args()

    docker_problem = check_docker_compose_cli()
    if docker_problem:
        print(f"error: {docker_problem}", file=sys.stderr)
        return 1

    dataset_dir = (REPO_ROOT / args.dataset_dir).resolve()
    editors = Editors((REPO_ROOT / args.roundtrip_tool).resolve(),
                      (REPO_ROOT / args.modify_tool).resolve(),
                      (REPO_ROOT / args.baseline_tool).resolve())
    output_dir = (REPO_ROOT / args.output_dir).resolve()
    seed_dir = (REPO_ROOT / args.seed_dir).resolve()

    for name, path in {"roundtrip_tool": editors.roundtrip, "modify_tool": editors.modify,
                       "baseline_tool": editors.baseline}.items():
        if not path.exists():
            print(f"error: {name} not found at {path} (build it first: cmake --build build)", file=sys.stderr)
            return 1
    if not dataset_dir.is_dir():
        print(f"error: dataset dir not found: {dataset_dir}", file=sys.stderr)
        return 1

    files = sorted(p for p in dataset_dir.rglob("*") if p.suffix in (".yml", ".yaml") and p.is_file())
    if args.max_files:
        files = files[: args.max_files]

    rows: list[dict] = []

    def record(tool, stage, path, ok, out_path, service="", variant=""):
        if ok:
            valid, code, err, elapsed = docker_compose_config(out_path)
        else:
            valid, code, err, elapsed = False, None, "editor failed", None
        rows.append({"tool": tool, "stage": stage, "file": path.name, "service": service,
                     "variant": variant, "valid": valid, "exit_code": code, "error": err,
                     "elapsed_s": elapsed})

    print(f"Validating {len(files)} input file(s) with `docker compose config`...", file=sys.stderr)
    valid_inputs: list[Path] = []
    for i, path in enumerate(files, 1):
        valid, code, err, elapsed = docker_compose_config(path)
        rows.append({"tool": "", "stage": "input", "file": path.name, "service": "", "variant": "",
                     "valid": valid, "exit_code": code, "error": err, "elapsed_s": elapsed})
        if valid:
            valid_inputs.append(path)
        if i % 100 == 0 or i == len(files):
            print(f"  [{i}/{len(files)}]", file=sys.stderr)

    print(f"{len(valid_inputs)}/{len(files)} inputs already valid; validating editor outputs for those...",
          file=sys.stderr)

    docs = {}
    for path in valid_inputs:
        try:
            docs[path] = yaml.safe_load(path.read_text(errors="replace"))
        except Exception:
            docs[path] = None

    for tool in TOOL_NAMES:
        for path in valid_inputs:
            out = output_dir / tool / "roundtrip" / path.name
            out.parent.mkdir(parents=True, exist_ok=True)
            record(tool, "roundtrip_output", path,
                   editors.roundtrip_file(tool, path, out, first_service(docs[path])), out)

        for path in valid_inputs:
            service, spec = image_target(docs[path])
            if service is None:
                continue
            out = output_dir / tool / "modification" / path.name
            out.parent.mkdir(parents=True, exist_ok=True)
            record(tool, "modification_output", path,
                   editors.edit_image(tool, path, out, service, spec["tool_args"]), out, service)

    print("Validating marker-injected fixtures (extension-only x-* vs. full unknown+x-*)...", file=sys.stderr)
    for path in valid_inputs[:100]:
        service, spec = image_target(docs[path])
        if service is None:
            continue
        for variant, categories in (("extension_only", {"extension"}), ("full", {"extension", "unknown"})):
            seed_path = seed_dir / variant / path.name
            seed_path.parent.mkdir(parents=True, exist_ok=True)
            seed_path.write_text(yaml.safe_dump(inject_filtered(docs[path], service, categories), sort_keys=False))
            for tool in TOOL_NAMES:
                out = output_dir / tool / "markers" / variant / path.name
                out.parent.mkdir(parents=True, exist_ok=True)
                record(tool, "marker_output", path,
                       editors.edit_image(tool, seed_path, out, service, spec["tool_args"]), out, service, variant)

    raw_csv = (REPO_ROOT / args.raw_csv).resolve()
    raw_csv.parent.mkdir(parents=True, exist_ok=True)
    with raw_csv.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    summary = summarize(rows, len(files), len(valid_inputs), args.dataset_label)
    summary_md = (REPO_ROOT / args.summary_md).resolve()
    summary_md.parent.mkdir(parents=True, exist_ok=True)
    summary_md.write_text(summary)

    print(summary)
    print(f"\nRaw per-case results: {raw_csv}", file=sys.stderr)
    print(f"Summary: {summary_md}", file=sys.stderr)
    return 0


def rate(rows: list[dict], tool: str, stage: str, variant: Optional[str] = None) -> tuple[int, int]:
    sub = [r for r in rows if r["tool"] == tool and r["stage"] == stage
           and (variant is None or r["variant"] == variant)]
    return sum(1 for r in sub if r["valid"]), len(sub)


def fmt_rate(ok: int, n: int) -> str:
    return f"{ok}/{n} ({100 * ok / n:.2f}%)" if n else "n/a"


def summarize(rows: list[dict], n_files: int, n_valid_inputs: int, dataset_label: str = "Dataset B") -> str:
    lines = ["# Experiment 5 -- Docker Compose Validation\n"]
    lines.append(f"{dataset_label} files tested: **{n_files}**\n")

    lines.append("## Input validity (evaluated separately per the task spec)\n")
    lines.append(
        f"- **{fmt_rate(n_valid_inputs, n_files)}** of the input files are already valid per "
        "`docker compose config` before any editor touches them. The rest fail for reasons "
        "unrelated to the editors (missing `.env` files, undefined interpolation variables, "
        "deprecated or malformed syntax, ...); see the stage=`input` rows in the raw CSV. They are "
        "excluded from the rates below.\n"
    )

    lines.append("## Docker Compose Validation Success Rate (RQ1, main metric)\n")
    header = "| Output | " + " | ".join(TOOL_LABELS[t] for t in TOOL_NAMES) + " |"
    lines.append(header)
    lines.append("|---" * (len(TOOL_NAMES) + 1) + "|")
    combined = {}
    for stage, label in (("roundtrip_output", "Identity round-trip (Experiment 1)"),
                         ("modification_output", "Targeted `image` edit (Experiment 2)")):
        cells = []
        for tool in TOOL_NAMES:
            ok, n = rate(rows, tool, stage)
            c_ok, c_n = combined.get(tool, (0, 0))
            combined[tool] = (c_ok + ok, c_n + n)
            cells.append(fmt_rate(ok, n))
        lines.append(f"| {label} | " + " | ".join(cells) + " |")
    lines.append("| **Combined** | " + " | ".join(f"**{fmt_rate(*combined[t])}**" for t in TOOL_NAMES) + " |")
    lines.append("")

    lines.append("## Marker fixtures: x-* vs. non-x- unknown properties (RQ4 nuance)\n")
    lines.append("| Fixture | " + " | ".join(TOOL_LABELS[t] for t in TOOL_NAMES) + " |")
    lines.append("|---" * (len(TOOL_NAMES) + 1) + "|")
    for variant, label in (("extension_only", "x-* extension fields only"),
                           ("full", "x-* plus non-x- \"future property\" unknown fields")):
        lines.append(f"| {label} | " + " | ".join(fmt_rate(*rate(rows, t, "marker_output", variant))
                                                  for t in TOOL_NAMES) + " |")
    lines.append(
        "\nThe Compose Specification schema only admits unrecognized top-level or service keys "
        "when they are `x-*`-prefixed. A non-`x-` field that an editor preserves faithfully still "
        "makes docker compose reject the file, so the second row measures the schema, not the "
        "editor.\n"
    )

    for tool in TOOL_NAMES:
        invalid = [r for r in rows if r["tool"] == tool
                   and r["stage"] in ("roundtrip_output", "modification_output") and not r["valid"]]
        lines.append(f"## {TOOL_LABELS[tool]}: outputs that became invalid despite a valid input "
                     f"({len(invalid)})\n")
        if not invalid:
            lines.append("None observed.\n")
            continue
        categories: dict[str, list[dict]] = {}
        for r in invalid:
            categories.setdefault(classify_error(r["error"]), []).append(r)
        for cat, items in sorted(categories.items(), key=lambda kv: -len(kv[1])):
            lines.append(f"### {cat} -- {len(items)} case(s)\n")
            for r in items[:5]:
                lines.append(f"- `{r['stage']}` / `{r['file']}`: {r['error'][:200]}")
            if len(items) > 5:
                lines.append(f"- ... and {len(items) - 5} more (see raw CSV)")
            lines.append("")

    return "\n".join(lines)


def classify_error(error: str) -> str:
    if error == "editor failed":
        return "editor failed before producing output"
    if re.search(r"must be a string", error):
        return "schema-type: a string field came back as a number/bool (quoted scalar lost its quotes)"
    if re.search(r"yaml:.*(did not find|found character|mapping values|could not find)", error):
        return "syntax: output is not valid YAML for docker compose's parser"
    if "is not allowed" in error or "Additional property" in error:
        return "schema: unknown (non-x-) property rejected"
    if "invalid interpolation format" in error:
        return "interpolation: invalid ${...} expression in output"
    return f"other: {error[:80]}"


if __name__ == "__main__":
    raise SystemExit(main())
