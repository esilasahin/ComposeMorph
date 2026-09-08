#!/usr/bin/env python3
"""Experiment 2 -- Targeted Modification Test (RQ3 -- Change Locality).

For a sample of Compose files, change exactly one property of one service
through the typed C++ API (benchmarks/modification/modify_tool) and measure
how much of the file changed beyond that single property.

Change Locality Ratio = Expected Changed Lines / Actual Changed Lines
(PDF section 5). Expected Changed Lines is 1 for every op here: a scalar
edit or a single new list entry is, in principle, a one-line change.

Because Experiment 1 already showed this library does not preserve
formatting on a no-op save (quote/flow-style normalization, blank-line
collapse), "Actual Changed Lines" mixes that baseline re-serialization
noise with the cost of the edit itself. This script also reports an
adjusted ratio that subtracts each file's own identity-round-trip noise
(from results/raw/roundtrip_dataset_b.csv, produced by
run_roundtrip_experiment.py) to isolate the edit's true footprint.

Usage:
    python3 scripts/run_modification_experiment.py
    python3 scripts/run_modification_experiment.py --max-per-op 50
"""
from __future__ import annotations

import argparse
import csv
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Callable, Optional

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from diffmetrics import changed_line_count  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# One eligibility finder per targeted property (PDF section 5 examples).
# Each returns None if the service does not have the property to modify, or
# a dict describing the modify_tool CLI args and a human-readable before/after.
# Ports/extra_hosts/networks have no "set" in the library's API (only
# add/remove) so the single targeted change modelled here is "add one
# entry" -- see the summary's Notes section.
# ---------------------------------------------------------------------------

def find_image(svc: dict) -> Optional[dict]:
    img = svc.get("image")
    if not isinstance(img, str) or not img:
        return None
    base = img.rsplit(":", 1)[0] if ":" in img else img
    new_img = base + ":cm-test-9.9"
    if new_img == img:
        new_img = base + ":cm-test-9.9x"
    return {"tool_args": [new_img], "before": img, "after": new_img}


def find_hostname(svc: dict) -> Optional[dict]:
    h = svc.get("hostname")
    if not isinstance(h, str) or not h:
        return None
    new_h = h + "-cmtest"
    return {"tool_args": [new_h], "before": h, "after": new_h}


def find_restart(svc: dict) -> Optional[dict]:
    r = svc.get("restart")
    if not isinstance(r, str) or not r:
        return None
    new_r = "on-failure" if r != "on-failure" else "always"
    return {"tool_args": [new_r], "before": r, "after": new_r}


def find_env(svc: dict) -> Optional[dict]:
    env = svc.get("environment")
    key = None
    if isinstance(env, dict) and env:
        key = next(iter(env.keys()))
    elif isinstance(env, list) and env:
        for item in env:
            if isinstance(item, str) and "=" in item:
                key = item.split("=", 1)[0]
                break
    if key is None:
        return None
    return {"tool_args": [str(key), "cm-test-value"], "before": str(key), "after": "cm-test-value"}


def find_port(svc: dict) -> Optional[dict]:
    ports = svc.get("ports")
    if not isinstance(ports, list) or not ports:
        return None
    sentinel = "39999:39999"
    if sentinel in ports:
        sentinel = "39998:39998"
    return {"tool_args": [sentinel], "before": None, "after": sentinel}


def find_volume_source(svc: dict) -> Optional[dict]:
    vols = svc.get("volumes")
    if not isinstance(vols, list):
        return None
    for v in vols:
        if not isinstance(v, str) or ":" not in v:
            continue  # long (mapping) syntax not supported by Volumes::setSource
        parts = v.split(":")
        if len(parts) < 2 or not parts[0] or not parts[1]:
            continue
        source, target = parts[0], parts[1]
        new_source = "/opt/cm-test-source"
        if new_source == source:
            new_source = "/opt/cm-test-source-2"
        return {"tool_args": [target, new_source], "before": source, "after": new_source}
    return None


def find_extra_host(svc: dict) -> Optional[dict]:
    hosts = svc.get("extra_hosts")
    if not isinstance(hosts, (list, dict)) or not hosts:
        return None
    return {"tool_args": ["cm-test-host", "10.10.10.99"], "before": None, "after": "10.10.10.99"}


def find_network(svc: dict) -> Optional[dict]:
    nets = svc.get("networks")
    if not isinstance(nets, (list, dict)) or not nets:
        return None
    return {"tool_args": ["cm-test-network"], "before": None, "after": "cm-test-network"}


def find_healthcheck_retries(svc: dict) -> Optional[dict]:
    hc = svc.get("healthcheck")
    if not isinstance(hc, dict):
        return None
    retries = hc.get("retries")
    if not isinstance(retries, int):
        return None
    new_r = retries + 1
    return {"tool_args": [str(new_r)], "before": str(retries), "after": str(new_r)}


def find_deploy_cpus(svc: dict) -> Optional[dict]:
    deploy = svc.get("deploy")
    if not isinstance(deploy, dict):
        return None
    limits = (deploy.get("resources") or {}).get("limits") if isinstance(deploy.get("resources"), dict) else None
    if not isinstance(limits, dict) or "cpus" not in limits:
        return None
    cpus_str = str(limits["cpus"])
    new_cpus = "9.9" if cpus_str != "9.9" else "8.8"
    return {"tool_args": [new_cpus], "before": cpus_str, "after": new_cpus}


OPS: dict[str, Callable[[dict], Optional[dict]]] = {
    "image": find_image,
    "hostname": find_hostname,
    "restart": find_restart,
    "env": find_env,
    "port": find_port,
    "volume-source": find_volume_source,
    "extra-host": find_extra_host,
    "network": find_network,
    "healthcheck-retries": find_healthcheck_retries,
    "deploy-cpus": find_deploy_cpus,
}

ADDITIVE_OPS = {"port", "extra-host", "network"}

FIELDNAMES = [
    "op", "file", "service", "before", "after", "total_lines",
    "actual_changed_lines", "expected_changed_lines", "locality_ratio",
    "baseline_noise_changed_lines", "incremental_changed_lines",
    "adjusted_locality_ratio", "elapsed_s", "status",
]


def load_baseline_noise(csv_path: Path) -> dict[str, int]:
    """filename -> identity-round-trip changed_lines, from Experiment 1's CSV."""
    if not csv_path.exists():
        return {}
    out: dict[str, int] = {}
    with csv_path.open(newline="") as f:
        for row in csv.DictReader(f):
            val = row.get("changed_lines")
            if val not in (None, ""):
                try:
                    out[row["file"]] = int(val)
                except ValueError:
                    pass
    return out


def find_eligible(dataset_dir: Path, op: str, finder: Callable[[dict], Optional[dict]], max_count: int):
    """Yield (path, service_name, spec) for up to max_count files with one
    eligible service each, in sorted filename order for reproducibility."""
    found = 0
    for path in sorted(dataset_dir.iterdir()):
        if found >= max_count:
            return
        if path.suffix not in (".yml", ".yaml") or not path.is_file():
            continue
        try:
            doc = yaml.safe_load(path.read_text(errors="replace"))
        except Exception:
            continue
        if not isinstance(doc, dict):
            continue
        services = doc.get("services")
        if not isinstance(services, dict):
            continue
        for name in sorted(services.keys()):
            svc = services[name]
            if not isinstance(svc, dict):
                continue
            spec = finder(svc)
            if spec is not None:
                yield path, name, spec
                found += 1
                break


def run_one(tool: Path, op: str, path: Path, service: str, spec: dict, out_dir: Path,
            baseline: dict[str, int]) -> dict:
    out_path = out_dir / op / path.name
    out_path.parent.mkdir(parents=True, exist_ok=True)

    t0 = time.perf_counter()
    try:
        proc = subprocess.run(
            [str(tool), str(path), str(out_path), op, service, *spec["tool_args"]],
            capture_output=True, text=True, timeout=60,
        )
        timed_out = False
    except subprocess.TimeoutExpired:
        proc = None
        timed_out = True
    elapsed = time.perf_counter() - t0

    row = {
        "op": op, "file": path.name, "service": service,
        "before": spec.get("before"), "after": spec.get("after"),
        "elapsed_s": round(elapsed, 4),
    }

    if timed_out or proc.returncode != 0:
        row.update(
            total_lines=None, actual_changed_lines=None, expected_changed_lines=1,
            locality_ratio=None, baseline_noise_changed_lines=None,
            incremental_changed_lines=None, adjusted_locality_ratio=None,
            status="TIMEOUT" if timed_out else (proc.stderr.strip() or f"exit={proc.returncode}"),
        )
        return row

    a_lines = path.read_text(errors="replace").splitlines()
    b_lines = out_path.read_text(errors="replace").splitlines()
    actual = changed_line_count(a_lines, b_lines)
    total_lines = len(a_lines)

    noise = baseline.get(path.name)
    incremental = max(0, actual - noise) if noise is not None else None

    row.update(
        total_lines=total_lines,
        actual_changed_lines=actual,
        expected_changed_lines=1,
        locality_ratio=round(1 / actual, 6) if actual > 0 else None,
        baseline_noise_changed_lines=noise,
        incremental_changed_lines=incremental,
        adjusted_locality_ratio=round(1 / max(1, incremental), 6) if incremental is not None else None,
        status="OK",
    )
    return row


def summarize(rows: list[dict]) -> str:
    lines = ["# Experiment 2 -- Targeted Modification / Change Locality -- Dataset B\n"]
    lines.append(f"Total (op, file) cases evaluated: **{len(rows)}**\n")
    lines.append(
        "Change Locality Ratio = Expected Changed Lines (1) / Actual Changed Lines. "
        "Adjusted ratio further divides by (Actual - that file's own identity-round-trip "
        "noise from Experiment 1), isolating the edit's footprint from the library's "
        "baseline re-serialization noise (quote/flow-style normalization, blank-line loss).\n"
    )

    lines.append("## Per-property results\n")
    lines.append("| Op | N | Success | Median actual changed lines | Median locality ratio | Median adjusted ratio |")
    lines.append("|---|---|---|---|---|---|")
    by_op: dict[str, list[dict]] = {}
    for r in rows:
        by_op.setdefault(r["op"], []).append(r)
    for op in OPS:
        op_rows = by_op.get(op, [])
        ok_rows = [r for r in op_rows if r["status"] == "OK"]
        if not op_rows:
            lines.append(f"| {op} | 0 | - | - | - | - |")
            continue
        actuals = [r["actual_changed_lines"] for r in ok_rows if r["actual_changed_lines"] is not None]
        ratios = [r["locality_ratio"] for r in ok_rows if r["locality_ratio"] is not None]
        adj = [r["adjusted_locality_ratio"] for r in ok_rows if r["adjusted_locality_ratio"] is not None]
        lines.append(
            f"| {op} | {len(op_rows)} | {len(ok_rows)}/{len(op_rows)} | "
            f"{statistics.median(actuals):.1f} | "
            f"{statistics.median(ratios):.4f} | "
            f"{statistics.median(adj):.4f} |"
            if actuals and ratios and adj else
            f"| {op} | {len(op_rows)} | {len(ok_rows)}/{len(op_rows)} | n/a | n/a | n/a |"
        )
    lines.append("")

    lines.append("## Notes\n")
    lines.append(
        "- `port`, `extra-host`, `network`: the library's API only exposes `add`/`remove` "
        "(no in-place setter), so the single targeted change modelled here is *adding one "
        "entry* to an existing list, not replacing an existing value."
    )
    lines.append(
        "- `volume-source`: only short-syntax volume entries (`source:target[:mode]`) are "
        "eligible -- `Volumes::setSource` calls `.as<std::string>()` on each entry and throws "
        "on long-syntax (mapping) volume definitions, so files using only long syntax are skipped."
    )
    lines.append(
        "- `port`: `Ports::has` (called by `add` to avoid duplicates) runs `.as<std::string>()` "
        "over every existing entry, so a service whose `ports` list mixes short-syntax strings "
        "with a long-syntax (mapping) port definition throws a yaml-cpp bad-conversion error -- "
        "the same short-syntax-only assumption seen in `Volumes` and `Networks`."
    )
    lines.append(
        "- `network`: eligibility only requires a `networks` key to exist, but "
        "`Networks::add` pushes onto it without checking the node is a sequence. Services "
        "using the long (mapping) `networks:` syntax cause `add` to throw "
        "(\"appending to a non-sequence\") -- a real library bug surfaced by this experiment, "
        "left visible below rather than filtered out."
    )
    failures = [r for r in rows if r["status"] != "OK"]
    if failures:
        lines.append(f"\n## Failures ({len(failures)})\n")
        for r in failures[:50]:
            lines.append(f"- `{r['op']}` / `{r['file']}` (service `{r['service']}`): {r['status']}")
        if len(failures) > 50:
            lines.append(f"- ... and {len(failures) - 50} more (see raw CSV)")
    lines.append("")

    return "\n".join(lines)


def make_figure(rows: list[dict], figure_path_stub: Path) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("warning: matplotlib not available, skipping figure generation", file=sys.stderr)
        return

    by_op: dict[str, list[float]] = {}
    for r in rows:
        if r["status"] == "OK" and r["adjusted_locality_ratio"] is not None:
            by_op.setdefault(r["op"], []).append(r["adjusted_locality_ratio"])

    ops_with_data = [op for op in OPS if by_op.get(op)]
    if not ops_with_data:
        print("warning: no successful rows to plot", file=sys.stderr)
        return

    data = [by_op[op] for op in ops_with_data]

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.boxplot(data, tick_labels=ops_with_data, showfliers=False)
    ax.set_ylabel("Adjusted Change Locality Ratio\n(1 = only the targeted line changed)")
    ax.set_title("Experiment 2 -- Change Locality by Modified Property (Dataset B)")
    ax.set_ylim(bottom=0)
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right")
    fig.tight_layout()

    figure_path_stub.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(figure_path_stub.with_suffix(".png"), dpi=150)
    fig.savefig(figure_path_stub.with_suffix(".pdf"))
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dataset-dir", default="datasets/real-world-combined")
    ap.add_argument("--tool", default="build/modify_tool")
    ap.add_argument("--output-dir", default="results/raw/modification/dataset-b-output")
    ap.add_argument("--baseline-csv", default="results/raw/roundtrip_dataset_b.csv")
    ap.add_argument("--raw-csv", default="results/raw/modification_dataset_b.csv")
    ap.add_argument("--summary-md", default="results/tables/modification_dataset_b_summary.md")
    ap.add_argument("--figure", default="results/figures/modification_change_locality")
    ap.add_argument("--max-per-op", type=int, default=200)
    args = ap.parse_args()

    dataset_dir = (REPO_ROOT / args.dataset_dir).resolve()
    tool = (REPO_ROOT / args.tool).resolve()
    output_dir = (REPO_ROOT / args.output_dir).resolve()
    raw_csv = (REPO_ROOT / args.raw_csv).resolve()
    summary_md = (REPO_ROOT / args.summary_md).resolve()
    figure_stub = (REPO_ROOT / args.figure).resolve()

    if not tool.exists():
        print(f"error: modify_tool not found at {tool} (build it first)", file=sys.stderr)
        return 1
    if not dataset_dir.is_dir():
        print(f"error: dataset dir not found: {dataset_dir}", file=sys.stderr)
        return 1

    baseline = load_baseline_noise((REPO_ROOT / args.baseline_csv).resolve())
    if not baseline:
        print("warning: no baseline round-trip CSV found; adjusted ratios will be n/a (run run_roundtrip_experiment.py first)", file=sys.stderr)

    output_dir.mkdir(parents=True, exist_ok=True)
    raw_csv.parent.mkdir(parents=True, exist_ok=True)
    summary_md.parent.mkdir(parents=True, exist_ok=True)

    rows: list[dict] = []
    for op, finder in OPS.items():
        cases = list(find_eligible(dataset_dir, op, finder, args.max_per_op))
        print(f"{op}: {len(cases)} eligible file(s)", file=sys.stderr)
        for path, service, spec in cases:
            rows.append(run_one(tool, op, path, service, spec, output_dir, baseline))

    with raw_csv.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    summary = summarize(rows)
    summary_md.write_text(summary)
    make_figure(rows, figure_stub)

    print(summary)
    print(f"\nRaw per-case results: {raw_csv}", file=sys.stderr)
    print(f"Summary: {summary_md}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
