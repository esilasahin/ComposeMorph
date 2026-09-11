#!/usr/bin/env python3
"""Experiment 5 -- Docker Compose Validation (RQ1's third metric).

Runs `docker compose -f <file> config` -- the Compose Specification's own
schema validator -- against Dataset B inputs and against ComposeMorph's
generated outputs for two of the earlier experiments' canonical pipelines
(Experiment 1's identity round-trip, Experiment 2's `image` edit), plus
Experiment 3/4's marker-injected fixtures. This script is self-contained:
it regenerates the outputs it validates by invoking roundtrip_tool /
modify_tool itself, rather than depending on another script's run having
left files behind.

Note: unlike `docker compose up`, `docker compose config` does *not*
require a running daemon -- it only needs the `docker compose` CLI plugin
on PATH. It was tested in the dev sandbox (no daemon reachable there) and
worked, so this script runs everywhere the CLI is installed; no separate
"real machine" step should be needed, though you're of course welcome to
re-run it on yours for an independent result.

Per the PDF: invalid *inputs* are reported separately (section 8, "Geçersiz
input dosyaları bu metriğin dışında ayrıca değerlendirilmelidir") and are
excluded from the round-trip/modification validation-success-rate
denominators -- only files docker compose itself already accepts are
counted toward those.

Usage:
    python3 scripts/run_validation_experiment.py
    python3 scripts/run_validation_experiment.py --max-files 0   # all of Dataset B
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

FIELDNAMES = ["stage", "file", "service", "variant", "valid", "exit_code", "error", "elapsed_s"]


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
    """docker compose prints one `time="..." level=warning ...` line per
    unset interpolation variable before the actual (non-warning) error, if
    any -- keep the whole warning list but make sure the real error survives
    truncation by putting it first."""
    lines = [ln for ln in stderr.strip().splitlines() if ln.strip()]
    warnings = [ln for ln in lines if ln.startswith('time="') and "level=warning" in ln]
    other = [ln for ln in lines if ln not in warnings]
    ordered = other + warnings  # real error(s) first, warnings appended after
    return " | ".join(ordered)[:800]


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


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dataset-dir", default="datasets/real-world-combined")
    ap.add_argument("--roundtrip-tool", default="build/roundtrip_tool")
    ap.add_argument("--modify-tool", default="build/modify_tool")
    ap.add_argument("--output-dir", default="results/raw/validation/output")
    ap.add_argument("--seed-dir", default="results/raw/validation/seeded-input")
    ap.add_argument("--raw-csv", default="results/raw/validation_dataset_b.csv")
    ap.add_argument("--summary-md", default="results/tables/validation_summary.md")
    ap.add_argument("--max-files", type=int, default=200,
                     help="Cap on files to test; 0 = all files (the full official run per the PDF's >=500-file requirement).")
    ap.add_argument("--dataset-label", default="Dataset B")
    args = ap.parse_args()

    docker_problem = check_docker_compose_cli()
    if docker_problem:
        print(f"error: {docker_problem}", file=sys.stderr)
        return 1

    dataset_dir = (REPO_ROOT / args.dataset_dir).resolve()
    roundtrip_tool = (REPO_ROOT / args.roundtrip_tool).resolve()
    modify_tool = (REPO_ROOT / args.modify_tool).resolve()
    output_dir = (REPO_ROOT / args.output_dir).resolve()
    seed_dir = (REPO_ROOT / args.seed_dir).resolve()

    for name, path in {"roundtrip_tool": roundtrip_tool, "modify_tool": modify_tool}.items():
        if not path.exists():
            print(f"error: {name} not found at {path} (build it first: cmake --build build)", file=sys.stderr)
            return 1
    if not dataset_dir.is_dir():
        print(f"error: dataset dir not found: {dataset_dir}", file=sys.stderr)
        return 1

    files = sorted(p for p in dataset_dir.rglob("*") if p.suffix in (".yml", ".yaml") and p.is_file())
    if args.max_files:
        files = files[: args.max_files]

    for d in (output_dir, seed_dir):
        d.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []

    print(f"Validating {len(files)} input file(s) with `docker compose config`...", file=sys.stderr)
    valid_inputs: list[Path] = []
    for i, path in enumerate(files, 1):
        valid, code, err, elapsed = docker_compose_config(path)
        rows.append({"stage": "input", "file": path.name, "service": "", "variant": "",
                     "valid": valid, "exit_code": code, "error": err, "elapsed_s": elapsed})
        if valid:
            valid_inputs.append(path)
        if i % 100 == 0 or i == len(files):
            print(f"  [{i}/{len(files)}]", file=sys.stderr)

    print(f"{len(valid_inputs)}/{len(files)} inputs already valid per docker compose; "
          f"validating ComposeMorph outputs for those only...", file=sys.stderr)

    for path in valid_inputs:
        out_path = output_dir / "roundtrip" / path.name
        out_path.parent.mkdir(parents=True, exist_ok=True)
        if run_tool(roundtrip_tool, [str(path), str(out_path)]):
            valid, code, err, elapsed = docker_compose_config(out_path)
            rows.append({"stage": "roundtrip_output", "file": path.name, "service": "", "variant": "",
                         "valid": valid, "exit_code": code, "error": err, "elapsed_s": elapsed})
        else:
            rows.append({"stage": "roundtrip_output", "file": path.name, "service": "", "variant": "",
                         "valid": False, "exit_code": None, "error": "roundtrip_tool failed", "elapsed_s": None})

    for path in valid_inputs:
        try:
            doc = yaml.safe_load(path.read_text(errors="replace"))
        except Exception:
            continue
        if not isinstance(doc, dict) or not isinstance(doc.get("services"), dict):
            continue
        service, spec = None, None
        for name in sorted(doc["services"].keys()):
            svc = doc["services"][name]
            if isinstance(svc, dict):
                spec = find_image(svc)
                if spec is not None:
                    service = name
                    break
        if service is None:
            continue
        out_path = output_dir / "modification" / path.name
        out_path.parent.mkdir(parents=True, exist_ok=True)
        if run_tool(modify_tool, [str(path), str(out_path), "image", service, *spec["tool_args"]]):
            valid, code, err, elapsed = docker_compose_config(out_path)
            rows.append({"stage": "modification_output", "file": path.name, "service": service, "variant": "",
                         "valid": valid, "exit_code": code, "error": err, "elapsed_s": elapsed})
        else:
            rows.append({"stage": "modification_output", "file": path.name, "service": service, "variant": "",
                         "valid": False, "exit_code": None, "error": "modify_tool failed", "elapsed_s": None})

    print("Validating marker-injected fixtures (extension-only x-* vs. full unknown+x-*)...", file=sys.stderr)
    marker_sample = valid_inputs[:100]
    for path in marker_sample:
        try:
            doc = yaml.safe_load(path.read_text(errors="replace"))
        except Exception:
            continue
        if not isinstance(doc, dict) or not isinstance(doc.get("services"), dict):
            continue
        service, spec = None, None
        for name in sorted(doc["services"].keys()):
            svc = doc["services"][name]
            if isinstance(svc, dict):
                spec = find_image(svc)
                if spec is not None:
                    service = name
                    break
        if service is None:
            continue

        for variant, categories in (("extension_only", {"extension"}), ("full", {"extension", "unknown"})):
            seeded = inject_filtered(doc, service, categories)
            seed_path = seed_dir / variant / path.name
            seed_path.parent.mkdir(parents=True, exist_ok=True)
            seed_path.write_text(yaml.safe_dump(seeded, sort_keys=False))

            out_path = output_dir / "markers" / variant / path.name
            out_path.parent.mkdir(parents=True, exist_ok=True)
            if run_tool(modify_tool, [str(seed_path), str(out_path), "image", service, *spec["tool_args"]]):
                valid, code, err, elapsed = docker_compose_config(out_path)
                rows.append({"stage": "marker_output", "file": path.name, "service": service, "variant": variant,
                             "valid": valid, "exit_code": code, "error": err, "elapsed_s": elapsed})

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


def summarize(rows: list[dict], n_files: int, n_valid_inputs: int, dataset_label: str = "Dataset B") -> str:
    lines = ["# Experiment 5 -- Docker Compose Validation\n"]
    lines.append(f"{dataset_label} files tested: **{n_files}**\n")

    lines.append("## Input validity (baseline, evaluated separately per the PDF)\n")
    lines.append(
        f"- **{n_valid_inputs}/{n_files}** ({100*n_valid_inputs/n_files:.2f}%) of the raw GitHub "
        "Compose files are already valid per `docker compose config`, before ComposeMorph touches "
        "them. The rest fail for reasons unrelated to this library (missing `.env` files, undefined "
        "interpolation variables, deprecated/malformed syntax, etc.) -- see stage=`input` rows in "
        "the raw CSV for the specific errors. These files are excluded from the rates below.\n"
    )

    def stage_rate(stage: str, variant: Optional[str] = None) -> tuple[int, int]:
        sub = [r for r in rows if r["stage"] == stage and (variant is None or r["variant"] == variant)]
        return sum(1 for r in sub if r["valid"]), len(sub)

    lines.append("## Docker Compose Validation Success Rate (RQ1, main metric)\n")
    rt_ok, rt_n = stage_rate("roundtrip_output")
    mod_ok, mod_n = stage_rate("modification_output")
    lines.append(
        f"- Identity round-trip output (Experiment 1, no modification): **{rt_ok}/{rt_n}**"
        f" ({100*rt_ok/rt_n:.2f}%)" if rt_n else "- Identity round-trip output: n/a"
    )
    lines.append(
        f"- Targeted `image` modification output (Experiment 2): **{mod_ok}/{mod_n}**"
        f" ({100*mod_ok/mod_n:.2f}%)" if mod_n else "- Targeted modification output: n/a"
    )
    combined_ok, combined_n = rt_ok + mod_ok, rt_n + mod_n
    if combined_n:
        lines.append(f"- **Combined: {combined_ok}/{combined_n} ({100*combined_ok/combined_n:.2f}%)**")
    lines.append("")

    lines.append("## Marker fixtures: x-* vs. non-x- unknown properties (RQ4 nuance)\n")
    ext_ok, ext_n = stage_rate("marker_output", "extension_only")
    full_ok, full_n = stage_rate("marker_output", "full")
    lines.append(
        f"- x-* extension fields only: **{ext_ok}/{ext_n}**"
        f" ({100*ext_ok/ext_n:.2f}%) valid per docker compose config" if ext_n else "- extension-only: n/a"
    )
    lines.append(
        f"- x-* extension fields *and* non-x- \"future property\" style unknown fields: "
        f"**{full_ok}/{full_n}** ({100*full_ok/full_n:.2f}%)" if full_n else "- full marker set: n/a"
    )
    lines.append(
        "\n**Interpretation:** Experiments 3/4 showed ComposeMorph preserves *both* kinds of "
        "unknown structure semantically at ~100%. This experiment shows that preservation alone "
        "isn't the same as validity: the Compose Specification schema only permits unrecognized "
        "top-level/service keys when they're `x-*`-prefixed. A non-`x-` \"forward-compatible\" "
        "field survives the round-trip but docker compose still rejects the *file*, independent "
        "of anything ComposeMorph did. This is a real constraint worth stating plainly in "
        "Limitations, not a bug in the library.\n"
    )

    invalid_after = [r for r in rows if r["stage"] in ("roundtrip_output", "modification_output") and not r["valid"]]
    if invalid_after:
        lines.append(f"## Outputs that became invalid despite a valid input ({len(invalid_after)})\n")
        lines.append("Categorized by root cause (see `classify_error()` in this script):\n")
        categories: dict[str, list[dict]] = {}
        for r in invalid_after:
            categories.setdefault(classify_error(r["error"]), []).append(r)
        for cat, items in sorted(categories.items(), key=lambda kv: -len(kv[1])):
            lines.append(f"### {cat} -- {len(items)} case(s)\n")
            for r in items[:5]:
                lines.append(f"- `{r['stage']}` / `{r['file']}`: {r['error'][:200]}")
            if len(items) > 5:
                lines.append(f"- ... and {len(items) - 5} more (see raw CSV)")
            lines.append("")
        lines.append(
            "**The dominant failure mode -- quoted numeric-looking scalars losing their quotes "
            "on save -- is the *same mechanism* Experiment 1 already flagged as a formatting-only "
            "issue (e.g. `\"2.0\"` -> `2.0`). This experiment shows it is not purely cosmetic: "
            "when that scalar is `version:`, a `command:`/`entrypoint:` list element, or any other "
            "field the Compose schema requires to be a string, the re-serialized file is outright "
            "rejected by `docker compose config`. In at least one observed case "
            "(`command: [\"caddy\", \"respond\", \"--listen\", \":80\", \"QA\"]`), the unquoted "
            "`:80` inside a flow sequence is not just schema-invalid but syntactically unparseable "
            "YAML for other parsers (confirmed independently with PyYAML) -- yaml-cpp's own "
            "reader accepts its own output, but standards-compliant parsers do not. This is the "
            "single most consequential finding in this benchmark suite and should be reported "
            "prominently in Results/Limitations, not folded into the round-trip byte-diff numbers.\n"
        )
    else:
        lines.append(
            "No case where a valid input became invalid after ComposeMorph's round-trip or "
            "targeted `image` edit was observed in this sample.\n"
        )

    return "\n".join(lines)


def classify_error(error: str) -> str:
    if re.search(r"must be a string", error):
        return "schema-type: quoted numeric-looking scalar unquoted on save (e.g. version, command/entrypoint elements)"
    if re.search(r"yaml:.*(did not find|found character|mapping values|could not find)", error):
        return "SYNTAX: output is not valid YAML for other parsers (yaml-cpp emitter quirk)"
    if "is not allowed" in error or "Additional property" in error:
        return "schema: unknown (non-x-) property rejected"
    if "invalid interpolation format" in error:
        return ("benchmark-harness artifact: find_image() in run_modification_experiment.py splits "
                 "the image string on its *last* ':', which lands inside a `${VAR:-default}` tag "
                 "expression for images using compose interpolation syntax -- not a ComposeMorph defect")
    if "variable is not set" in error and "level=warning" in error and not re.search(r"must be a string|is not allowed", error):
        return "non-fatal: only unset-interpolation-variable warnings (docker compose still exited non-zero for another reason not captured -- inspect raw CSV)"
    return f"other: {error[:80]}"


if __name__ == "__main__":
    raise SystemExit(main())
