#!/usr/bin/env python3
"""Paper figures with Turkish labels, drawn from the committed raw CSVs.

The experiment scripts write English figures to results/figures/ for the
repository. The paper is in Turkish and needs the same data without the
in-figure titles (the LaTeX caption carries the title), so this script
re-plots from results/raw/ without re-running any experiment.

  paper/figures/comparison_yamlcpp_tr.{pdf,png}
      Experiment 6: median changed lines per edit and collateral fields
      preserved, per tool and op (from comparison_modification.csv).

Usage:
    python3 scripts/make_paper_figures.py
"""
from __future__ import annotations

import argparse
import csv
import statistics
import sys
from pathlib import Path

OPS = ["image", "hostname", "env"]
TOOLS = {
    "composemorph": "ComposeMorph",
    "yamlcpp-careful": "yaml-cpp (dikkatli)",
    "yamlcpp-naive": "yaml-cpp (naif)",
}


def load_rows(csv_path: Path) -> list[dict]:
    with csv_path.open(newline="") as f:
        return list(csv.DictReader(f))


def comparison_figure(rows: list[dict], figure_stub: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    width = 0.25
    x = range(len(OPS))
    fig, axes = plt.subplots(1, 2, figsize=(10, 3.6))

    for i, (tool, label) in enumerate(TOOLS.items()):
        medians, rates = [], []
        for op in OPS:
            ok = [r for r in rows if r["tool"] == tool and r["op"] == op and r["status"] == "OK"]
            changed = [float(r["actual_changed_lines"]) for r in ok if r["actual_changed_lines"]]
            medians.append(statistics.median(changed) if changed else 0)
            measurable = [r for r in ok if r["collateral_preserved"] in ("True", "False")]
            preserved = sum(1 for r in measurable if r["collateral_preserved"] == "True")
            rates.append(100 * preserved / len(measurable) if measurable else 0)
        offsets = [xi + (i - 1) * width for xi in x]
        axes[0].bar(offsets, medians, width=width, label=label)
        axes[1].bar(offsets, rates, width=width, label=label)

    for ax in axes:
        ax.set_xticks(list(x))
        ax.set_xticklabels(OPS)
    axes[0].set_ylabel("Değişen satır (medyan)")
    axes[1].set_ylabel("Korunan kardeş alanlar (%)")
    axes[1].set_ylim(0, 105)
    axes[0].legend(fontsize="small", loc="upper left")

    fig.tight_layout()
    figure_stub.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(figure_stub.with_suffix(".png"), dpi=150)
    fig.savefig(figure_stub.with_suffix(".pdf"))
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--comparison-csv", default="results/raw/comparison_modification.csv")
    ap.add_argument("--output-dir", default="paper/figures")
    args = ap.parse_args()

    try:
        import matplotlib  # noqa: F401
    except ImportError:
        print("warning: matplotlib not available, skipping paper figures", file=sys.stderr)
        return 0

    comparison_figure(load_rows(Path(args.comparison_csv)), Path(args.output_dir) / "comparison_yamlcpp_tr")
    print(f"wrote {args.output_dir}/comparison_yamlcpp_tr.{{pdf,png}}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
