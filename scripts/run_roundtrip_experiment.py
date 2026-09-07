#!/usr/bin/env python3
"""Experiment 1 -- Identity Round-Trip Test (RQ1 / RQ2).

For every Compose file in a corpus: load it with the library, save it back
with *no* modification, then reload the saved output. Measures:

  - parse success rate         (input loads without a ParseException)
  - reparse success rate       (output re-loads without a ParseException)
  - textual preservation       (changed-line ratio, line-level Levenshtein
                                 distance, normalized edit distance,
                                 byte-identity)

Semantic preservation (`docker compose config` on input vs. output,
normalized and compared) is implemented behind --semantic but is skipped
by default and reported as such when no Docker daemon is reachable --
this repo's dev sandbox has no daemon, so semantic numbers here should be
reproduced in an environment that does (see Experiment 5 / RQ1).

Usage:
    python3 scripts/run_roundtrip_experiment.py
    python3 scripts/run_roundtrip_experiment.py --limit 20 --semantic
"""
from __future__ import annotations

import argparse
import csv
import difflib
import shutil
import statistics
import subprocess
import sys
import time
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

EXIT_LOAD_FAILED = 10
EXIT_SAVE_FAILED = 11
EXIT_REPARSE_FAILED = 12


def line_levenshtein(a_lines: list[str], b_lines: list[str]) -> int:
    """Edit distance over lines (insert/delete/substitute), two-row DP."""
    n, m = len(a_lines), len(b_lines)
    if n == 0:
        return m
    if m == 0:
        return n
    prev = list(range(m + 1))
    curr = [0] * (m + 1)
    for i in range(1, n + 1):
        curr[0] = i
        ai = a_lines[i - 1]
        for j in range(1, m + 1):
            cost = 0 if ai == b_lines[j - 1] else 1
            curr[j] = min(prev[j] + 1, curr[j - 1] + 1, prev[j - 1] + cost)
        prev, curr = curr, prev
    return prev[m]


def changed_line_count(a_lines: list[str], b_lines: list[str]) -> int:
    sm = difflib.SequenceMatcher(a=a_lines, b=b_lines, autojunk=False)
    changed = 0
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag != "equal":
            changed += max(i2 - i1, j2 - j1)
    return changed


def docker_daemon_available() -> bool:
    if shutil.which("docker") is None:
        return False
    try:
        proc = subprocess.run(["docker", "info"], capture_output=True, timeout=5)
        return proc.returncode == 0
    except Exception:
        return False


def semantic_diff(src: Path, out: Path) -> str:
    """Compare `docker compose config` output for src vs. out.

    Returns one of: "match", "mismatch", or "error: <reason>".
    """
    try:
        a = subprocess.run(
            ["docker", "compose", "-f", str(src), "config"],
            capture_output=True, text=True, timeout=30,
        )
        b = subprocess.run(
            ["docker", "compose", "-f", str(out), "config"],
            capture_output=True, text=True, timeout=30,
        )
    except Exception as e:  # pragma: no cover - environment dependent
        return f"error: {e}"
    if a.returncode != 0:
        return f"error: input invalid per docker compose ({a.stderr.strip()[:120]})"
    if b.returncode != 0:
        return f"error: output invalid per docker compose ({b.stderr.strip()[:120]})"
    try:
        a_norm = yaml.safe_load(a.stdout)
        b_norm = yaml.safe_load(b.stdout)
    except Exception as e:
        return f"error: normalize failed ({e})"
    return "match" if a_norm == b_norm else "mismatch"


def run_one(tool: Path, src: Path, out_dir: Path, semantic: bool, semantic_ok: bool) -> dict:
    out_path = out_dir / src.name
    t0 = time.perf_counter()
    try:
        proc = subprocess.run(
            [str(tool), str(src), str(out_path)],
            capture_output=True, text=True, timeout=60,
        )
        timed_out = False
    except subprocess.TimeoutExpired:
        proc = None
        timed_out = True
    elapsed = time.perf_counter() - t0

    row: dict = {
        "file": src.name,
        "size_bytes": src.stat().st_size,
        "elapsed_s": round(elapsed, 4),
    }

    if timed_out:
        row.update(
            parse_success=False, save_success=False, reparse_success=False,
            stderr="TIMEOUT", total_lines=None, output_lines=None,
            byte_identical=None, changed_lines=None, changed_line_ratio=None,
            line_levenshtein=None, normalized_edit_distance=None,
            semantic_status="skipped: input failed round-trip",
        )
        return row

    rc = proc.returncode
    row["parse_success"] = rc != EXIT_LOAD_FAILED
    row["save_success"] = rc not in (EXIT_LOAD_FAILED, EXIT_SAVE_FAILED)
    row["reparse_success"] = rc == 0
    row["stderr"] = proc.stderr.strip()

    if rc == 0 and out_path.exists():
        a_text = src.read_text(errors="replace")
        b_text = out_path.read_text(errors="replace")
        a_lines = a_text.splitlines()
        b_lines = b_text.splitlines()
        row["total_lines"] = len(a_lines)
        row["output_lines"] = len(b_lines)
        row["byte_identical"] = a_text == b_text
        changed = changed_line_count(a_lines, b_lines)
        row["changed_lines"] = changed
        row["changed_line_ratio"] = round(changed / max(1, len(a_lines)), 6)
        dist = line_levenshtein(a_lines, b_lines)
        row["line_levenshtein"] = dist
        row["normalized_edit_distance"] = round(dist / max(1, max(len(a_lines), len(b_lines))), 6)
        if semantic:
            row["semantic_status"] = semantic_diff(src, out_path) if semantic_ok else "skipped: no docker daemon"
        else:
            row["semantic_status"] = "not requested"
    else:
        for k in (
            "total_lines", "output_lines", "byte_identical", "changed_lines",
            "changed_line_ratio", "line_levenshtein", "normalized_edit_distance",
        ):
            row[k] = None
        row["semantic_status"] = "skipped: input failed round-trip"

    return row


FIELDNAMES = [
    "file", "size_bytes", "elapsed_s", "parse_success", "save_success",
    "reparse_success", "total_lines", "output_lines", "byte_identical",
    "changed_lines", "changed_line_ratio", "line_levenshtein",
    "normalized_edit_distance", "semantic_status", "stderr",
]


def rate(rows: list[dict], key: str) -> tuple[int, int]:
    ok = sum(1 for r in rows if r.get(key))
    return ok, len(rows)


def summarize(rows: list[dict], dataset_label: str, semantic_requested: bool, semantic_ok: bool) -> str:
    n = len(rows)
    parse_ok, _ = rate(rows, "parse_success")
    save_ok, _ = rate(rows, "save_success")
    reparse_ok, _ = rate(rows, "reparse_success")
    byte_ident_rows = [r for r in rows if r.get("byte_identical") is not None]
    byte_ident_ok = sum(1 for r in byte_ident_rows if r["byte_identical"])

    def stats_line(key: str) -> str:
        vals = [r[key] for r in rows if r.get(key) is not None]
        if not vals:
            return "n/a (no successful round-trips)"
        return (
            f"mean={statistics.mean(vals):.4f}, median={statistics.median(vals):.4f}, "
            f"stdev={statistics.pstdev(vals):.4f}, max={max(vals):.4f}"
        )

    failures = [r for r in rows if not r["reparse_success"]]

    lines = []
    lines.append(f"# Experiment 1 -- Identity Round-Trip -- {dataset_label}\n")
    lines.append(f"Files evaluated: **{n}**\n")
    lines.append("## RQ1 -- Correctness\n")
    lines.append(f"- Parse success rate: **{parse_ok}/{n}** ({100*parse_ok/n:.2f}%)")
    lines.append(f"- Save success rate: **{save_ok}/{n}** ({100*save_ok/n:.2f}%)")
    lines.append(f"- Reparse (save-then-reload) success rate: **{reparse_ok}/{n}** ({100*reparse_ok/n:.2f}%)")
    if semantic_requested:
        if semantic_ok:
            sem_match = sum(1 for r in rows if r.get("semantic_status") == "match")
            sem_considered = sum(1 for r in rows if r.get("semantic_status") in ("match", "mismatch"))
            lines.append(
                f"- `docker compose config` semantic match: **{sem_match}/{sem_considered}**"
                f" ({100*sem_match/sem_considered:.2f}%)" if sem_considered else
                "- `docker compose config` semantic match: n/a"
            )
        else:
            lines.append("- `docker compose config` semantic check: **skipped -- no reachable Docker daemon in this environment**")
    else:
        lines.append("- `docker compose config` semantic check: not requested (run with --semantic)")
    lines.append("")

    lines.append("## RQ2 -- Preservation (textual, identity round-trip)\n")
    lines.append(
        f"- Byte-identical round-trip: **{byte_ident_ok}/{len(byte_ident_rows)}**"
        f" ({100*byte_ident_ok/len(byte_ident_rows):.2f}%)" if byte_ident_rows else
        "- Byte-identical round-trip: n/a"
    )
    if byte_ident_rows and byte_ident_ok < len(byte_ident_rows):
        lines.append(
            "  - **The library does not guarantee byte-identical round-trip.** "
            "yaml-cpp re-emits scalars/flow sequences with normalized quoting and "
            "collapses blank lines on save; see per-file diffs in the raw CSV."
        )
    lines.append(f"- Changed line ratio: {stats_line('changed_line_ratio')}")
    lines.append(f"- Line-level Levenshtein distance: {stats_line('line_levenshtein')}")
    lines.append(f"- Normalized edit distance: {stats_line('normalized_edit_distance')}")
    lines.append("")

    lines.append("## Performance (informational, see Experiment 7 for the full benchmark)\n")
    lines.append(f"- Load+save+reload wall time per file: {stats_line('elapsed_s')} seconds")
    lines.append("")

    if failures:
        lines.append(f"## Failures ({len(failures)})\n")
        for r in failures[:50]:
            lines.append(f"- `{r['file']}`: {r['stderr'] or 'unknown failure'}")
        if len(failures) > 50:
            lines.append(f"- ... and {len(failures) - 50} more (see raw CSV)")
        lines.append("")

    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dataset-dir", default="datasets/real-world-combined")
    ap.add_argument("--dataset-label", default="Dataset B (real-world corpus)")
    ap.add_argument("--tool", default="build/roundtrip_tool")
    ap.add_argument("--output-dir", default="results/raw/roundtrip/dataset-b-output")
    ap.add_argument("--raw-csv", default="results/raw/roundtrip_dataset_b.csv")
    ap.add_argument("--summary-md", default="results/tables/roundtrip_dataset_b_summary.md")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--semantic", action="store_true", help="Also attempt docker compose config semantic comparison")
    args = ap.parse_args()

    dataset_dir = (REPO_ROOT / args.dataset_dir).resolve()
    tool = (REPO_ROOT / args.tool).resolve()
    output_dir = (REPO_ROOT / args.output_dir).resolve()
    raw_csv = (REPO_ROOT / args.raw_csv).resolve()
    summary_md = (REPO_ROOT / args.summary_md).resolve()

    if not tool.exists():
        print(f"error: round-trip tool not found at {tool} (build it first: cmake --build build --target roundtrip_tool)", file=sys.stderr)
        return 1
    if not dataset_dir.is_dir():
        print(f"error: dataset dir not found: {dataset_dir}", file=sys.stderr)
        return 1

    files = sorted(p for p in dataset_dir.iterdir() if p.suffix in (".yml", ".yaml") and p.is_file())
    if args.limit:
        files = files[: args.limit]
    if not files:
        print(f"error: no .yml/.yaml files found in {dataset_dir}", file=sys.stderr)
        return 1

    output_dir.mkdir(parents=True, exist_ok=True)
    raw_csv.parent.mkdir(parents=True, exist_ok=True)
    summary_md.parent.mkdir(parents=True, exist_ok=True)

    semantic_ok = docker_daemon_available() if args.semantic else False
    if args.semantic and not semantic_ok:
        print("warning: --semantic requested but no reachable Docker daemon; semantic checks will be marked skipped", file=sys.stderr)

    rows = []
    for i, src in enumerate(files, 1):
        row = run_one(tool, src, output_dir, args.semantic, semantic_ok)
        rows.append(row)
        if i % 50 == 0 or i == len(files):
            print(f"[{i}/{len(files)}] {src.name}", file=sys.stderr)

    with raw_csv.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)

    summary = summarize(rows, args.dataset_label, args.semantic, semantic_ok)
    summary_md.write_text(summary)

    def _display(p: Path) -> str:
        try:
            return str(p.relative_to(REPO_ROOT))
        except ValueError:
            return str(p)

    print(summary)
    print(f"\nRaw per-file results: {_display(raw_csv)}", file=sys.stderr)
    print(f"Summary: {_display(summary_md)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
