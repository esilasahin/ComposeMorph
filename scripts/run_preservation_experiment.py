#!/usr/bin/env python3
"""Experiment 3 & 4 -- Unknown Property / x-* Extension Preservation.

Real-world Compose files rarely contain extension fields or forward-looking
unknown properties (Dataset B's `extension_field_count` median is 0), so
this experiment injects controlled synthetic markers -- both "unknown
property" style (a plausible future Compose field, not part of this
library's object model) and spec-legal `x-*` extension fields -- into a
sample of real files, applies one unrelated single-property change through
the typed API (reusing Experiment 2's eligibility finders), and checks
whether the markers survive semantically intact.

Two data sources feed the same aggregate metric:
  1. Dataset B sample (datasets/real-world-combined) with markers injected.
  2. A hand-authored controlled file (datasets/controlled/
     preservation-standard-markers.yml) that already contains the same
     markers -- Dataset A's first slice (PDF section 3).

A second controlled file (datasets/controlled/preservation-edge-cases.yml)
exercises trickier, non-uniform scenarios (null-valued x-*, scalar x-*,
list-valued x-*, an unknown property nested inside a *known* section, x-*
nested inside another unknown block) that don't fit the uniform marker
schema; these are checked individually and reported as a checklist rather
than folded into the aggregate rate, per the PDF's instruction not to hide
unsupported/failing cases.

Usage:
    python3 scripts/run_preservation_experiment.py
    python3 scripts/run_preservation_experiment.py --max-per-op 50
"""
from __future__ import annotations

import argparse
import copy
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Optional

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from run_modification_experiment import find_image, find_env, find_eligible  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Marker schema shared between the injected real-world sample and the
# hand-authored controlled file (datasets/controlled/preservation-standard-
# markers.yml), which contains these exact keys/values pre-authored.
# ---------------------------------------------------------------------------
MARKER_SPECS: list[dict[str, Any]] = [
    {
        "id": "unknown_service_property",
        "category": "unknown",
        "scope": "service",
        "key": "future_compose_property",
        "value": {
            "enabled": True,
            "mode": "experimental",
            "nested": {"level": 2, "items": ["a", "b", "c"]},
        },
    },
    {
        "id": "unknown_top_level_section",
        "category": "unknown",
        "scope": "top",
        "key": "unknown_top_level_section",
        "value": {"note": "not yet part of the compose spec", "value": 42},
    },
    {
        "id": "x_top_security",
        "category": "extension",
        "scope": "top",
        "key": "x-company-security",
        "value": {"hsm": "enabled"},
    },
    {
        "id": "x_top_logging",
        "category": "extension",
        "scope": "top",
        "key": "x-default-logging",
        "value": {"driver": "json-file"},
    },
    {
        "id": "x_service_meta",
        "category": "extension",
        "scope": "service",
        "key": "x-service-meta",
        "value": {"owner": "team-a", "tier": 3},
    },
]


def inject_markers(doc: dict, service_name: str) -> dict:
    doc = copy.deepcopy(doc)
    for spec in MARKER_SPECS:
        value = copy.deepcopy(spec["value"])
        if spec["scope"] == "top":
            doc[spec["key"]] = value
        else:
            doc["services"][service_name][spec["key"]] = value
    return doc


def verify_markers(doc: Optional[dict], service_name: str) -> dict[str, bool]:
    result = {}
    for spec in MARKER_SPECS:
        if doc is None:
            result[spec["id"]] = False
            continue
        if spec["scope"] == "top":
            actual = doc.get(spec["key"])
        else:
            svc = doc.get("services", {}).get(service_name, {}) if isinstance(doc.get("services"), dict) else {}
            actual = svc.get(spec["key"]) if isinstance(svc, dict) else None
        result[spec["id"]] = actual == spec["value"]
    return result


OPS_FOR_SAMPLING = {"image": find_image, "env": find_env}


def run_case(tool: Path, seed_path: Path, op: str, service: str, tool_args: list[str],
             out_path: Path) -> tuple[bool, str]:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        proc = subprocess.run(
            [str(tool), str(seed_path), str(out_path), op, service, *tool_args],
            capture_output=True, text=True, timeout=60,
        )
    except subprocess.TimeoutExpired:
        return False, "TIMEOUT"
    if proc.returncode != 0:
        return False, proc.stderr.strip() or f"exit={proc.returncode}"
    return True, "OK"


def process_real_world_sample(dataset_dir: Path, tool: Path, seed_dir: Path, out_dir: Path,
                               max_per_op: int) -> list[dict]:
    rows = []
    for op, finder in OPS_FOR_SAMPLING.items():
        for path, service, spec in find_eligible(dataset_dir, op, finder, max_per_op):
            try:
                doc = yaml.safe_load(path.read_text(errors="replace"))
            except Exception as e:
                rows.append({"source": "real-world", "file": path.name, "op": op,
                             "service": service, "status": f"LOAD_FAILED: {e}",
                             **{s["id"]: False for s in MARKER_SPECS}})
                continue
            if not isinstance(doc, dict):
                continue

            seeded = inject_markers(doc, service)
            seed_path = seed_dir / op / path.name
            seed_path.parent.mkdir(parents=True, exist_ok=True)
            seed_path.write_text(yaml.safe_dump(seeded, sort_keys=False))

            out_path = out_dir / op / path.name
            t0 = time.perf_counter()
            ok, status = run_case(tool, seed_path, op, service, spec["tool_args"], out_path)
            elapsed = round(time.perf_counter() - t0, 4)

            if ok:
                out_doc = yaml.safe_load(out_path.read_text(errors="replace"))
                marker_results = verify_markers(out_doc, service)
            else:
                marker_results = {s["id"]: False for s in MARKER_SPECS}

            rows.append({"source": "real-world", "file": path.name, "op": op,
                         "service": service, "status": status, "elapsed_s": elapsed,
                         **marker_results})
    return rows


def process_controlled_standard(tool: Path, out_dir: Path) -> list[dict]:
    path = REPO_ROOT / "datasets" / "controlled" / "preservation-standard-markers.yml"
    doc = yaml.safe_load(path.read_text())
    service = "app"
    spec = find_image(doc["services"][service])
    assert spec is not None, "controlled fixture must have an image to modify"

    out_path = out_dir / "controlled" / path.name
    ok, status = run_case(tool, path, "image", service, spec["tool_args"], out_path)
    if ok:
        out_doc = yaml.safe_load(out_path.read_text(errors="replace"))
        marker_results = verify_markers(out_doc, service)
    else:
        marker_results = {s["id"]: False for s in MARKER_SPECS}
    return [{"source": "controlled", "file": path.name, "op": "image", "service": service,
              "status": status, **marker_results}]


# ---------------------------------------------------------------------------
# Edge cases (datasets/controlled/preservation-edge-cases.yml): each exercises
# a scenario that doesn't fit the uniform marker schema above. Checked
# individually; not folded into the aggregate preservation rate.
# ---------------------------------------------------------------------------
def get_path(doc: Optional[dict], path: list[str]) -> Any:
    cur: Any = doc
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur[key]
    return cur


EDGE_CASES = [
    {"id": "x_null_extension", "description": "top-level x-* with a null value",
     "path": ["x-null-extension"], "expected": None},
    {"id": "x_scalar_extension", "description": "top-level x-* whose value is a bare scalar, not a map",
     "path": ["x-scalar-extension"], "expected": "just-a-string"},
    {"id": "x_list_extension", "description": "top-level x-* whose value is a list of maps",
     "path": ["x-list-extension"], "expected": [{"a": 1}, {"b": 2}]},
    {"id": "unknown_list_section", "description": "unknown top-level section that is a list, not a map",
     "path": ["unknown_list_section"], "expected": [1, 2, 3]},
    {"id": "unknown_property_inside_known_section",
     "description": "unknown property nested inside a *known*, typed section (deploy.future_scaling_hint)",
     "path": ["services", "app", "deploy", "future_scaling_hint"], "expected": "aggressive"},
    {"id": "x_nested_inside_unknown_block",
     "description": "x-* field nested two levels inside another unknown block",
     "path": ["services", "app", "x-nested-service-block", "inner", "x-double-nested"], "expected": True},
]


def process_controlled_edge_cases(tool: Path, out_dir: Path) -> list[dict]:
    path = REPO_ROOT / "datasets" / "controlled" / "preservation-edge-cases.yml"
    doc = yaml.safe_load(path.read_text())
    service = "app"
    spec = find_image(doc["services"][service])
    assert spec is not None

    out_path = out_dir / "controlled" / path.name
    ok, status = run_case(tool, path, "image", service, spec["tool_args"], out_path)
    out_doc = yaml.safe_load(out_path.read_text(errors="replace")) if ok else None

    rows = []
    for case in EDGE_CASES:
        actual = get_path(out_doc, case["path"]) if ok else None
        rows.append({
            "id": case["id"], "description": case["description"],
            "expected": case["expected"], "actual": actual,
            "preserved": ok and actual == case["expected"],
            "status": status,
        })
    return rows


def summarize(rows: list[dict], edge_rows: list[dict]) -> str:
    lines = ["# Experiment 3 & 4 -- Unknown Property / x-* Extension Preservation\n"]

    ok_rows = [r for r in rows if r["status"] == "OK"]
    lines.append(f"Cases evaluated: **{len(rows)}** ({len(ok_rows)} completed the modify step; "
                 f"{len(rows) - len(ok_rows)} failed before markers could be checked)\n")

    lines.append("## Aggregate preservation rate, by marker\n")
    lines.append("| Marker | Category | Scope | N | Preserved | Rate |")
    lines.append("|---|---|---|---|---|---|")
    for spec in MARKER_SPECS:
        mid = spec["id"]
        n = len(rows)
        preserved = sum(1 for r in rows if r.get(mid))
        rate = f"{100 * preserved / n:.2f}%" if n else "n/a"
        lines.append(f"| `{spec['key']}` | {spec['category']} | {spec['scope']} | {n} | {preserved} | {rate} |")
    lines.append("")

    unknown_ids = [s["id"] for s in MARKER_SPECS if s["category"] == "unknown"]
    ext_ids = [s["id"] for s in MARKER_SPECS if s["category"] == "extension"]

    def category_rate(ids: list[str]) -> tuple[int, int]:
        total = len(rows) * len(ids)
        preserved = sum(sum(1 for mid in ids if r.get(mid)) for r in rows)
        return preserved, total

    up, ut = category_rate(unknown_ids)
    ep, et = category_rate(ext_ids)
    lines.append(f"- **Unknown Property Preservation Rate (RQ -- Experiment 3): {up}/{ut}** "
                 f"({100*up/ut:.2f}%)" if ut else "- Unknown Property Preservation Rate: n/a")
    lines.append(f"- **x-* Extension Preservation Rate (RQ -- Experiment 4): {ep}/{et}** "
                 f"({100*ep/et:.2f}%)" if et else "- x-* Extension Preservation Rate: n/a")
    lines.append("")

    lines.append("## By source and modification op\n")
    lines.append("| Source | Op | N | Fully preserved (all markers) |")
    lines.append("|---|---|---|---|")
    keys = sorted({(r["source"], r["op"]) for r in rows})
    for source, op in keys:
        sub = [r for r in rows if r["source"] == source and r["op"] == op]
        full = sum(1 for r in sub if all(r.get(s["id"]) for s in MARKER_SPECS))
        lines.append(f"| {source} | {op} | {len(sub)} | {full}/{len(sub)} |")
    lines.append("")

    failures = [r for r in rows if r["status"] != "OK"]
    if failures:
        lines.append(f"## Failures before marker check ({len(failures)})\n")
        for r in failures[:30]:
            lines.append(f"- `{r['source']}` / `{r['op']}` / `{r['file']}`: {r['status']}")
        if len(failures) > 30:
            lines.append(f"- ... and {len(failures) - 30} more (see raw CSV)")
        lines.append("")

    partial = [r for r in ok_rows if not all(r.get(s["id"]) for s in MARKER_SPECS)]
    if partial:
        lines.append(f"## Completed but with at least one marker lost ({len(partial)})\n")
        for r in partial[:30]:
            lost = [s["key"] for s in MARKER_SPECS if not r.get(s["id"])]
            lines.append(f"- `{r['source']}` / `{r['op']}` / `{r['file']}`: lost {lost}")
        if len(partial) > 30:
            lines.append(f"- ... and {len(partial) - 30} more (see raw CSV)")
        lines.append("")

    lines.append("## Controlled edge cases (datasets/controlled/preservation-edge-cases.yml)\n")
    lines.append("Not part of the aggregate rate above -- these probe non-uniform scenarios "
                 "individually, and a failure here is reported rather than hidden.\n")
    lines.append("| Case | Preserved | Expected | Actual |")
    lines.append("|---|---|---|---|")
    for r in edge_rows:
        mark = "yes" if r["preserved"] else "**NO**"
        lines.append(f"| {r['description']} | {mark} | `{r['expected']!r}` | `{r['actual']!r}` |")
    lines.append("")

    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dataset-dir", default="datasets/real-world-combined")
    ap.add_argument("--tool", default="build/modify_tool")
    ap.add_argument("--seed-dir", default="results/raw/preservation/seeded-input")
    ap.add_argument("--output-dir", default="results/raw/preservation/output")
    ap.add_argument("--raw-csv", default="results/raw/preservation_dataset_b.csv")
    ap.add_argument("--summary-md", default="results/tables/preservation_summary.md")
    ap.add_argument("--figure", default="results/figures/preservation_rates")
    ap.add_argument("--max-per-op", type=int, default=200)
    args = ap.parse_args()

    dataset_dir = (REPO_ROOT / args.dataset_dir).resolve()
    tool = (REPO_ROOT / args.tool).resolve()
    seed_dir = (REPO_ROOT / args.seed_dir).resolve()
    out_dir = (REPO_ROOT / args.output_dir).resolve()
    raw_csv = (REPO_ROOT / args.raw_csv).resolve()
    summary_md = (REPO_ROOT / args.summary_md).resolve()
    figure_stub = (REPO_ROOT / args.figure).resolve()

    if not tool.exists():
        print(f"error: modify_tool not found at {tool} (build it first)", file=sys.stderr)
        return 1
    if not dataset_dir.is_dir():
        print(f"error: dataset dir not found: {dataset_dir}", file=sys.stderr)
        return 1

    for d in (seed_dir, out_dir, raw_csv.parent, summary_md.parent):
        d.mkdir(parents=True, exist_ok=True)

    rows = process_real_world_sample(dataset_dir, tool, seed_dir, out_dir, args.max_per_op)
    rows += process_controlled_standard(tool, out_dir)
    edge_rows = process_controlled_edge_cases(tool, out_dir)

    import csv as csv_mod
    fieldnames = ["source", "file", "op", "service", "status", "elapsed_s"] + [s["id"] for s in MARKER_SPECS]
    with raw_csv.open("w", newline="") as f:
        writer = csv_mod.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    summary = summarize(rows, edge_rows)
    summary_md.write_text(summary)

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        ids = [s["id"] for s in MARKER_SPECS]
        rates = [100 * sum(1 for r in rows if r.get(mid)) / len(rows) for mid in ids]
        colors = ["#4c72b0" if s["category"] == "unknown" else "#dd8452" for s in MARKER_SPECS]

        fig, ax = plt.subplots(figsize=(8, 5))
        ax.bar([s["key"] for s in MARKER_SPECS], rates, color=colors)
        ax.set_ylim(0, 105)
        ax.set_ylabel("Preservation rate (%)")
        ax.set_title("Experiment 3 & 4 -- Marker Preservation Rate (Dataset B + controlled)")
        ax.axhline(100, color="gray", linewidth=0.8, linestyle="--")
        plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
        fig.tight_layout()
        figure_stub.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(figure_stub.with_suffix(".png"), dpi=150)
        fig.savefig(figure_stub.with_suffix(".pdf"))
        plt.close(fig)
    except ImportError:
        print("warning: matplotlib not available, skipping figure", file=sys.stderr)

    print(summary)
    print(f"\nRaw per-case results: {raw_csv}", file=sys.stderr)
    print(f"Summary: {summary_md}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
