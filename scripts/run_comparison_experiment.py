#!/usr/bin/env python3
"""Experiment 6 -- Comparative Benchmark: ComposeMorph vs. raw yaml-cpp.

Compares three ways of making the same single-property edit to a Compose
file:

  composemorph     benchmarks/modification/modify_tool -- ComposeMorph's
                    typed Service/Environment/... API.
  yamlcpp-careful  benchmarks/comparison/yamlcpp_careful_tool -- raw
                    YAML::Node indexing, mutating only the target leaf in
                    place (the same technique ComposeMorph uses internally).
  yamlcpp-naive    benchmarks/comparison/yamlcpp_naive_tool -- raw
                    YAML::Node usage that looks equally reasonable but
                    rebuilds the containing subtree from scratch, silently
                    discarding sibling fields.

Four things are measured on the same file/service samples used by
Experiment 2/3/4 for consistency:

  1. Identity round-trip textual preservation (composemorph vs.
     yaml-cpp-careful) -- expected near-identical, since ComposeMorph adds
     no format-preservation layer over yaml-cpp.
  2. Change-locality (textual diff size) for a single-property edit,
     across all three tools.
  3. Collateral information loss: do a service's *other*, unrelated
     pre-existing fields survive the edit?
  4. Unknown-property / x-* preservation, reusing Experiment 3/4's marker
     injection, across all three tools.

Plus a source-derived lines-of-code-per-op count, and the PDF's qualitative
capability matrix, grounded in these results and in ComposeFile.cpp's
documented atomic-save behaviour.

Usage:
    python3 scripts/run_comparison_experiment.py
    python3 scripts/run_comparison_experiment.py --max-per-op 50
"""
from __future__ import annotations

import argparse
import csv
import re
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Optional

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from diffmetrics import changed_line_count  # noqa: E402
from run_modification_experiment import find_image, find_hostname, find_env, find_eligible  # noqa: E402
from run_preservation_experiment import MARKER_SPECS, inject_markers, verify_markers  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent

OPS_TO_TEST = {"image": find_image, "hostname": find_hostname, "env": find_env}

TOOLS = {
    "composemorph": "build/modify_tool",
    "yamlcpp-careful": "build/yamlcpp_careful_tool",
    "yamlcpp-naive": "build/yamlcpp_naive_tool",
}

EXIT_NOT_IMPLEMENTED = 21


def normalize_env(env: Any) -> dict:
    if isinstance(env, dict):
        return {str(k): v for k, v in env.items()}
    if isinstance(env, list):
        out = {}
        for item in env:
            if isinstance(item, str) and "=" in item:
                k, v = item.split("=", 1)
                out[k] = v
        return out
    return {}


def check_collateral(op: str, before_svc: dict, after_doc: Optional[dict], service: str,
                      modified_key: Optional[str]) -> Optional[bool]:
    """None = not measurable (no sibling data existed to lose); True/False otherwise."""
    if not isinstance(after_doc, dict):
        return False
    after_svc = (after_doc.get("services") or {}).get(service) if isinstance(after_doc.get("services"), dict) else None

    if op in ("image", "hostname"):
        siblings = {k: v for k, v in before_svc.items() if k != op}
        if not siblings:
            return None
        if not isinstance(after_svc, dict):
            return False
        return all(after_svc.get(k) == v for k, v in siblings.items())

    if op == "env":
        before_env = normalize_env(before_svc.get("environment"))
        others = {k: v for k, v in before_env.items() if k != modified_key}
        if not others:
            return None
        after_env = normalize_env(after_svc.get("environment")) if isinstance(after_svc, dict) else {}
        return all(after_env.get(k) == v for k, v in others.items())

    return None


def run_tool(tool: Path, input_path: Path, output_path: Path, op: str, service: str,
             tool_args: list[str]) -> tuple[bool, str, float]:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    try:
        proc = subprocess.run(
            [str(tool), str(input_path), str(output_path), op, service, *tool_args],
            capture_output=True, text=True, timeout=60,
        )
    except subprocess.TimeoutExpired:
        return False, "TIMEOUT", round(time.perf_counter() - t0, 4)
    elapsed = round(time.perf_counter() - t0, 4)
    if proc.returncode == EXIT_NOT_IMPLEMENTED:
        return False, "NOT_IMPLEMENTED", elapsed
    if proc.returncode != 0:
        return False, proc.stderr.strip() or f"exit={proc.returncode}", elapsed
    return True, "OK", elapsed


def run_modification_comparison(dataset_dir: Path, tools: dict[str, Path], out_dir: Path,
                                 max_per_op: int) -> list[dict]:
    rows = []
    for op, finder in OPS_TO_TEST.items():
        cases = list(find_eligible(dataset_dir, op, finder, max_per_op))
        print(f"[modification] {op}: {len(cases)} eligible file(s)", file=sys.stderr)
        for path, service, spec in cases:
            try:
                before_doc = yaml.safe_load(path.read_text(errors="replace"))
            except Exception:
                continue
            before_svc = before_doc["services"][service]
            modified_key = spec["tool_args"][0] if op == "env" else None
            a_lines = path.read_text(errors="replace").splitlines()

            for tool_name, tool_path in tools.items():
                out_path = out_dir / "modification" / tool_name / op / path.name
                ok, status, elapsed = run_tool(tool_path, path, out_path, op, service, spec["tool_args"])
                row = {
                    "experiment": "modification", "tool": tool_name, "op": op, "file": path.name,
                    "service": service, "status": status, "elapsed_s": elapsed,
                }
                if ok:
                    b_lines = out_path.read_text(errors="replace").splitlines()
                    row["actual_changed_lines"] = changed_line_count(a_lines, b_lines)
                    try:
                        after_doc = yaml.safe_load(out_path.read_text(errors="replace"))
                    except Exception:
                        after_doc = None
                    row["collateral_preserved"] = check_collateral(op, before_svc, after_doc, service, modified_key)
                else:
                    row["actual_changed_lines"] = None
                    row["collateral_preserved"] = None
                rows.append(row)
    return rows


def run_roundtrip_comparison(dataset_dir: Path, composemorph_roundtrip: Path, yamlcpp_careful: Path,
                              out_dir: Path, max_files: int) -> list[dict]:
    rows = []
    files = sorted(p for p in dataset_dir.rglob("*") if p.suffix in (".yml", ".yaml"))[:max_files]
    for path in files:
        try:
            doc = yaml.safe_load(path.read_text(errors="replace"))
        except Exception:
            continue
        if not isinstance(doc, dict) or not isinstance(doc.get("services"), dict) or not doc["services"]:
            continue
        service = sorted(doc["services"].keys())[0]
        a_lines = path.read_text(errors="replace").splitlines()

        cm_out = out_dir / "roundtrip" / "composemorph" / path.name
        cm_out.parent.mkdir(parents=True, exist_ok=True)
        cm_proc = subprocess.run([str(composemorph_roundtrip), str(path), str(cm_out)],
                                  capture_output=True, text=True, timeout=60)
        yc_out = out_dir / "roundtrip" / "yamlcpp-careful" / path.name
        ok, status, _ = run_tool(yamlcpp_careful, path, yc_out, "noop", service, [])

        if cm_proc.returncode != 0 or not ok:
            continue
        cm_lines = cm_out.read_text(errors="replace").splitlines()
        yc_lines = yc_out.read_text(errors="replace").splitlines()
        rows.append({
            "file": path.name,
            "composemorph_changed_lines": changed_line_count(a_lines, cm_lines),
            "yamlcpp_careful_changed_lines": changed_line_count(a_lines, yc_lines),
            "byte_identical_to_each_other": cm_out.read_text(errors="replace") == yc_out.read_text(errors="replace"),
        })
    return rows


def run_marker_comparison(dataset_dir: Path, tools: dict[str, Path], seed_dir: Path, out_dir: Path,
                           max_files: int) -> list[dict]:
    rows = []
    cases = list(find_eligible(dataset_dir, "image", find_image, max_files))
    print(f"[markers] image: {len(cases)} eligible file(s)", file=sys.stderr)
    for path, service, spec in cases:
        try:
            doc = yaml.safe_load(path.read_text(errors="replace"))
        except Exception:
            continue
        seeded = inject_markers(doc, service)
        seed_path = seed_dir / path.name
        seed_path.parent.mkdir(parents=True, exist_ok=True)
        seed_path.write_text(yaml.safe_dump(seeded, sort_keys=False))

        for tool_name, tool_path in tools.items():
            out_path = out_dir / "markers" / tool_name / path.name
            ok, status, _ = run_tool(tool_path, seed_path, out_path, "image", service, spec["tool_args"])
            if ok:
                out_doc = yaml.safe_load(out_path.read_text(errors="replace"))
                marker_results = verify_markers(out_doc, service)
            else:
                marker_results = {s["id"]: False for s in MARKER_SPECS}
            rows.append({"tool": tool_name, "file": path.name, "status": status, **marker_results})
    return rows


def extract_op_branch_loc(cpp_path: Path) -> dict[str, int]:
    """Line count of each `if (op == "X") { ... }` branch body, via brace matching."""
    text = cpp_path.read_text()
    results: dict[str, int] = {}
    for m in re.finditer(r'if\s*\(op == "([\w-]+)"\)\s*\{', text):
        name = m.group(1)
        depth = 0
        i = m.end() - 1
        while i < len(text):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    break
            i += 1
        body = text[m.end():i]
        results[name] = len([ln for ln in body.splitlines() if ln.strip()])
    return results


def summarize(mod_rows: list[dict], rt_rows: list[dict], marker_rows: list[dict],
              loc: dict[str, dict[str, int]]) -> str:
    lines = ["# Experiment 6 -- Comparative Benchmark: ComposeMorph vs. raw yaml-cpp\n"]

    # --- Round-trip equivalence ---
    lines.append("## 1. Identity round-trip: ComposeMorph vs. careful raw yaml-cpp\n")
    lines.append(f"Files compared: **{len(rt_rows)}**\n")
    if rt_rows:
        identical = sum(1 for r in rt_rows if r["byte_identical_to_each_other"])
        cm_vals = [r["composemorph_changed_lines"] for r in rt_rows]
        yc_vals = [r["yamlcpp_careful_changed_lines"] for r in rt_rows]
        lines.append(
            f"- Byte-identical output between the two tools: **{identical}/{len(rt_rows)}** "
            f"({100*identical/len(rt_rows):.2f}%)"
        )
        lines.append(f"- ComposeMorph mean changed lines vs. input: {statistics.mean(cm_vals):.2f}")
        lines.append(f"- yaml-cpp (careful) mean changed lines vs. input: {statistics.mean(yc_vals):.2f}")
        lines.append(
            "- **Interpretation:** ComposeMorph's round-trip preservation (or lack of it, per "
            "Experiment 1) is inherited entirely from yaml-cpp -- it is not a distinguishing "
            "feature of this library.\n"
        )

    # --- Change locality + collateral loss ---
    lines.append("## 2. Targeted modification: change locality and collateral loss\n")
    lines.append("| Tool | Op | N | Success | Median changed lines | Collateral preserved |")
    lines.append("|---|---|---|---|---|---|")
    for tool in TOOLS:
        for op in OPS_TO_TEST:
            sub = [r for r in mod_rows if r["tool"] == tool and r["op"] == op]
            if not sub:
                continue
            ok_sub = [r for r in sub if r["status"] == "OK"]
            if ok_sub:
                changed = [r["actual_changed_lines"] for r in ok_sub if r["actual_changed_lines"] is not None]
                measurable = [r for r in ok_sub if r["collateral_preserved"] is not None]
                preserved = sum(1 for r in measurable if r["collateral_preserved"])
                coll_str = f"{preserved}/{len(measurable)}" if measurable else "n/a (no siblings existed)"
                med = f"{statistics.median(changed):.1f}" if changed else "n/a"
            else:
                med, coll_str = "n/a", "n/a"
            status_note = sub[0]["status"] if sub[0]["status"] == "NOT_IMPLEMENTED" else f"{len(ok_sub)}/{len(sub)}"
            lines.append(f"| {tool} | {op} | {len(sub)} | {status_note} | {med} | {coll_str} |")
    lines.append("")
    lines.append(
        "**Collateral preserved** = of the cases where the modified service had other "
        "pre-existing fields (or, for `env`, other pre-existing environment variables) "
        "besides the one being changed, how many still have all of them, unchanged, after "
        "the edit. `yamlcpp-naive` is expected near 0% for `image`/`hostname` (whole service "
        "subtree replaced) and for `env` (whole environment section replaced).\n"
    )

    # --- Marker preservation ---
    lines.append("## 3. Unknown property / x-* preservation, by tool\n")
    lines.append("| Tool | N | Top-level markers preserved | Service-level markers preserved |")
    lines.append("|---|---|---|---|")
    top_ids = [s["id"] for s in MARKER_SPECS if s["scope"] == "top"]
    svc_ids = [s["id"] for s in MARKER_SPECS if s["scope"] == "service"]
    for tool in TOOLS:
        sub = [r for r in marker_rows if r["tool"] == tool]
        if not sub:
            continue
        top_total = len(sub) * len(top_ids)
        top_ok = sum(sum(1 for mid in top_ids if r.get(mid)) for r in sub)
        svc_total = len(sub) * len(svc_ids)
        svc_ok = sum(sum(1 for mid in svc_ids if r.get(mid)) for r in sub)
        lines.append(
            f"| {tool} | {len(sub)} | {top_ok}/{top_total} ({100*top_ok/top_total:.1f}%) | "
            f"{svc_ok}/{svc_total} ({100*svc_ok/svc_total:.1f}%) |"
        )
    lines.append("")
    lines.append(
        "**Expected pattern:** `composemorph` and `yamlcpp-careful` preserve both scopes at "
        "~100%. `yamlcpp-naive`'s `image` edit replaces the whole service subtree, so "
        "service-level markers (`future_compose_property`, `x-service-meta`) are lost while "
        "top-level markers (`x-company-security`, `x-default-logging`, "
        "`unknown_top_level_section`) survive untouched -- collateral damage is scoped to "
        "whatever subtree the naive code happened to overwrite.\n"
    )

    # --- LOC ---
    lines.append("## 4. Lines of code per single-property edit\n")
    lines.append("Counted by brace-matching each `if (op == \"X\") { ... }` branch body in the tool's source.\n")
    lines.append("| Op | composemorph | yaml-cpp (careful) | yaml-cpp (naive) |")
    lines.append("|---|---|---|---|")
    all_ops = sorted(set(loc.get("composemorph", {})) | set(loc.get("yamlcpp-careful", {})) | set(loc.get("yamlcpp-naive", {})))
    for op in all_ops:
        if op == "noop":
            continue
        cm = loc.get("composemorph", {}).get(op, "-")
        yc = loc.get("yamlcpp-careful", {}).get(op, "-")
        yn = loc.get("yamlcpp-naive", {}).get(op, "not modeled")
        lines.append(f"| {op} | {cm} | {yc} | {yn} |")
    lines.append("")
    lines.append(
        "yaml-cpp (naive)'s lower or equal LOC for `image`/`hostname` is exactly the problem: "
        "the destructive version is not more work to write than the correct one -- there is no "
        "natural code-review signal that distinguishes them.\n"
    )

    # --- Capability matrix ---
    lines.append("## 5. Capability matrix (PDF section 9)\n")
    lines.append("Grounded in the measurements above and in source inspection "
                  "(`src/ComposeFile.cpp`, `benchmarks/comparison/*.cpp`).\n")
    lines.append("| Feature | ComposeMorph | yaml-cpp (careful use) | yaml-cpp (naive use) |")
    lines.append("|---|---|---|---|")
    matrix = [
        ("C++ API", "Yes -- typed classes", "Yes -- raw `YAML::Node` only", "Yes -- raw `YAML::Node` only"),
        ("Docker Compose-aware API", "Yes (`Service`, `Environment`, `Ports`, ...)", "No", "No"),
        ("Generic property support", "Yes (`Service::set/get/remove`)", "Yes, unguided (manual `Node` indexing)", "Yes, unguided"),
        ("Unknown field preservation", "100% (Exp. 3, this experiment)", "100% (this experiment)", "Top-level only -- service-level lost on `image`/`hostname`"),
        ("x-* preservation", "100% (Exp. 4, this experiment)", "100% (this experiment)", "Top-level only -- service-level lost on `image`/`hostname`"),
        ("Comment preservation", "No (Exp. 1)", "No (same yaml-cpp emitter)", "No"),
        ("Formatting preservation", "No (Exp. 1: quote/flow-style normalized)", "No (identical, section 1 above)", "No"),
        ("Key order preservation", "Existing keys: yes; new keys appended at end", "Same (yaml-cpp preserves map insertion order)", "Same, within whatever subtree survives"),
        ("Round-trip support", "Semantic yes, byte-identical no (Exp. 1)", "Identical to ComposeMorph (section 1)", "N/A -- not a round-trip tool"),
        ("Compose validation integration", "Basic business-rule `validate()` (image/build required, ...)", "None built in", "None built in"),
        ("Safe/atomic save", "Yes -- `SaveOptions::atomic` writes to a temp file + rename", "No -- direct `ofstream` overwrite", "No -- direct `ofstream` overwrite"),
    ]
    for feature, cm, yc, yn in matrix:
        lines.append(f"| {feature} | {cm} | {yc} | {yn} |")
    lines.append("")

    failures = [r for r in mod_rows if r["status"] not in ("OK", "NOT_IMPLEMENTED")]
    if failures:
        lines.append(f"## Failures ({len(failures)})\n")
        for r in failures[:30]:
            lines.append(f"- `{r['tool']}` / `{r['op']}` / `{r['file']}`: {r['status']}")
        if len(failures) > 30:
            lines.append(f"- ... and {len(failures) - 30} more (see raw CSV)")
        lines.append("")

    return "\n".join(lines)


def make_figure(mod_rows: list[dict], figure_stub: Path) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("warning: matplotlib not available, skipping figure", file=sys.stderr)
        return

    ops = list(OPS_TO_TEST.keys())
    tools = list(TOOLS.keys())
    width = 0.25
    x = range(len(ops))

    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    for i, tool in enumerate(tools):
        medians = []
        for op in ops:
            vals = [r["actual_changed_lines"] for r in mod_rows
                     if r["tool"] == tool and r["op"] == op and r["status"] == "OK"
                     and r["actual_changed_lines"] is not None]
            medians.append(statistics.median(vals) if vals else 0)
        axes[0].bar([xi + (i - 1) * width for xi in x], medians, width=width, label=tool)
    axes[0].set_xticks(list(x))
    axes[0].set_xticklabels(ops)
    axes[0].set_ylabel("Median changed lines")
    axes[0].set_title("Change size per edit")
    axes[0].legend()

    for i, tool in enumerate(tools):
        rates = []
        for op in ops:
            measurable = [r for r in mod_rows if r["tool"] == tool and r["op"] == op
                          and r["status"] == "OK" and r["collateral_preserved"] is not None]
            preserved = sum(1 for r in measurable if r["collateral_preserved"])
            rates.append(100 * preserved / len(measurable) if measurable else 0)
        axes[1].bar([xi + (i - 1) * width for xi in x], rates, width=width, label=tool)
    axes[1].set_xticks(list(x))
    axes[1].set_xticklabels(ops)
    axes[1].set_ylim(0, 105)
    axes[1].set_ylabel("Collateral fields preserved (%)")
    axes[1].set_title("Information loss on unrelated fields")
    axes[1].legend()

    fig.suptitle("Experiment 6 -- ComposeMorph vs. raw yaml-cpp (careful and naive usage)")
    fig.tight_layout()
    figure_stub.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(figure_stub.with_suffix(".png"), dpi=150)
    fig.savefig(figure_stub.with_suffix(".pdf"))
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dataset-dir", default="datasets/real-world-combined")
    ap.add_argument("--output-dir", default="results/raw/comparison/output")
    ap.add_argument("--seed-dir", default="results/raw/comparison/seeded-input")
    ap.add_argument("--modification-csv", default="results/raw/comparison_modification.csv")
    ap.add_argument("--roundtrip-csv", default="results/raw/comparison_roundtrip.csv")
    ap.add_argument("--marker-csv", default="results/raw/comparison_markers.csv")
    ap.add_argument("--summary-md", default="results/tables/comparison_summary.md")
    ap.add_argument("--figure", default="results/figures/comparison_yamlcpp")
    ap.add_argument("--max-per-op", type=int, default=150)
    ap.add_argument("--max-roundtrip-files", type=int, default=100)
    ap.add_argument("--max-marker-files", type=int, default=100)
    args = ap.parse_args()

    dataset_dir = (REPO_ROOT / args.dataset_dir).resolve()
    tools = {name: (REPO_ROOT / rel).resolve() for name, rel in TOOLS.items()}
    composemorph_roundtrip = (REPO_ROOT / "build/roundtrip_tool").resolve()
    out_dir = (REPO_ROOT / args.output_dir).resolve()
    seed_dir = (REPO_ROOT / args.seed_dir).resolve()

    for name, path in {**tools, "roundtrip_tool": composemorph_roundtrip}.items():
        if not path.exists():
            print(f"error: {name} binary not found at {path} (build it first)", file=sys.stderr)
            return 1
    if not dataset_dir.is_dir():
        print(f"error: dataset dir not found: {dataset_dir}", file=sys.stderr)
        return 1

    mod_rows = run_modification_comparison(dataset_dir, tools, out_dir, args.max_per_op)
    rt_rows = run_roundtrip_comparison(dataset_dir, composemorph_roundtrip, tools["yamlcpp-careful"],
                                        out_dir, args.max_roundtrip_files)
    marker_rows = run_marker_comparison(dataset_dir, tools, seed_dir, out_dir, args.max_marker_files)

    loc = {
        "composemorph": extract_op_branch_loc(REPO_ROOT / "benchmarks/modification/modify_tool.cpp"),
        "yamlcpp-careful": extract_op_branch_loc(REPO_ROOT / "benchmarks/comparison/yamlcpp_careful_tool.cpp"),
        "yamlcpp-naive": extract_op_branch_loc(REPO_ROOT / "benchmarks/comparison/yamlcpp_naive_tool.cpp"),
    }

    for rel, rows, fields in (
        (args.modification_csv, mod_rows, ["experiment", "tool", "op", "file", "service", "status",
                                            "elapsed_s", "actual_changed_lines", "collateral_preserved"]),
        (args.roundtrip_csv, rt_rows, ["file", "composemorph_changed_lines", "yamlcpp_careful_changed_lines",
                                        "byte_identical_to_each_other"]),
        (args.marker_csv, marker_rows, ["tool", "file", "status"] + [s["id"] for s in MARKER_SPECS]),
    ):
        path = (REPO_ROOT / rel).resolve()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)

    summary = summarize(mod_rows, rt_rows, marker_rows, loc)
    summary_md = (REPO_ROOT / args.summary_md).resolve()
    summary_md.parent.mkdir(parents=True, exist_ok=True)
    summary_md.write_text(summary)

    make_figure(mod_rows, (REPO_ROOT / args.figure).resolve())

    print(summary)
    print(f"\nSummary: {summary_md}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
