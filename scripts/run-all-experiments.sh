#!/usr/bin/env bash
# Rebuilds ComposeMorph and re-runs all 7 experiments end to end, against
# both Dataset B (real-world) and Dataset A (controlled), writing results
# into results/{raw,tables,figures}/ exactly as committed in this repo.
#
# Requirements: cmake, a C++20 compiler, yaml-cpp + GTest dev packages,
# python3 with pyyaml (matplotlib optional -- figures are skipped with a
# warning if it's missing). Experiment 5 (Docker Compose Validation) and
# the docker-confirmed column of the quote-normalization analysis need
# the `docker compose` CLI on PATH; if it's missing, this script skips
# that step with a warning rather than failing the whole run.
#
# Usage:
#   ./scripts/run-all-experiments.sh
#   ./scripts/run-all-experiments.sh --skip-build   # reuse an existing build/
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

SKIP_BUILD=0
for arg in "$@"; do
  case "$arg" in
    --skip-build) SKIP_BUILD=1 ;;
    *) echo "Unknown argument: $arg" >&2; exit 2 ;;
  esac
done

log() { printf '\n=== %s ===\n' "$1"; }

if [ "$SKIP_BUILD" -eq 0 ]; then
  log "Building (cmake --build build)"
  cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
  cmake --build build -j"$(nproc 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 4)"
else
  log "Skipping build (--skip-build)"
fi

DOCKER_OK=0
if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
  DOCKER_OK=1
else
  echo "warning: 'docker compose' not available -- Experiment 5 and the" >&2
  echo "docker-confirmed column of the quote-normalization analysis will be skipped." >&2
fi

run_dataset_b() {
  log "Experiment 1 -- Identity Round-Trip (Dataset B)"
  python3 scripts/run_roundtrip_experiment.py

  log "Experiment 2 -- Targeted Modification / Change Locality (Dataset B)"
  python3 scripts/run_modification_experiment.py

  log "Experiment 3 & 4 -- Unknown Property / x-* Extension Preservation (Dataset B)"
  python3 scripts/run_preservation_experiment.py

  if [ "$DOCKER_OK" -eq 1 ]; then
    log "Experiment 5 -- Docker Compose Validation (Dataset B, full 647 files)"
    python3 scripts/run_validation_experiment.py --max-files 0
  fi

  log "Experiment 6 -- Comparative Benchmark vs. raw yaml-cpp (Dataset B)"
  python3 scripts/run_comparison_experiment.py

  log "Experiment 7 -- Performance Benchmark (Dataset B)"
  python3 scripts/run_performance_experiment.py

  log "Quote-normalization deep dive (Dataset B, full 647 files)"
  python3 scripts/analyze_quote_normalization.py
}

run_dataset_a() {
  log "Experiment 1 -- Identity Round-Trip (Dataset A)"
  python3 scripts/run_roundtrip_experiment.py \
    --dataset-dir datasets/controlled --dataset-label "Dataset A (controlled corpus)" \
    --output-dir results/raw/roundtrip/dataset-a-output \
    --raw-csv results/raw/roundtrip_dataset_a.csv \
    --summary-md results/tables/roundtrip_dataset_a_summary.md

  log "Experiment 2 -- Targeted Modification / Change Locality (Dataset A)"
  python3 scripts/run_modification_experiment.py \
    --dataset-dir datasets/controlled --dataset-label "Dataset A (controlled corpus)" \
    --output-dir results/raw/modification/dataset-a-output \
    --baseline-csv results/raw/roundtrip_dataset_a.csv \
    --raw-csv results/raw/modification_dataset_a.csv \
    --summary-md results/tables/modification_dataset_a_summary.md \
    --figure results/figures/modification_change_locality_dataset_a

  log "Experiment 3 & 4 -- Unknown Property / x-* Extension Preservation (Dataset A)"
  python3 scripts/run_preservation_experiment.py \
    --dataset-dir datasets/controlled --sample-source-label "controlled" \
    --seed-dir results/raw/preservation/dataset-a-seeded-input \
    --output-dir results/raw/preservation/dataset-a-output \
    --raw-csv results/raw/preservation_dataset_a.csv \
    --summary-md results/tables/preservation_dataset_a_summary.md \
    --figure results/figures/preservation_rates_dataset_a

  if [ "$DOCKER_OK" -eq 1 ]; then
    log "Experiment 5 -- Docker Compose Validation (Dataset A)"
    python3 scripts/run_validation_experiment.py \
      --dataset-dir datasets/controlled --dataset-label "Dataset A (controlled corpus)" --max-files 0 \
      --output-dir results/raw/validation/dataset-a-output \
      --seed-dir results/raw/validation/dataset-a-seeded-input \
      --raw-csv results/raw/validation_dataset_a.csv \
      --summary-md results/tables/validation_dataset_a_summary.md
  fi

  log "Experiment 6 -- Comparative Benchmark vs. raw yaml-cpp (Dataset A)"
  python3 scripts/run_comparison_experiment.py \
    --dataset-dir datasets/controlled \
    --output-dir results/raw/comparison/dataset-a-output \
    --seed-dir results/raw/comparison/dataset-a-seeded-input \
    --modification-csv results/raw/comparison_modification_dataset_a.csv \
    --roundtrip-csv results/raw/comparison_roundtrip_dataset_a.csv \
    --marker-csv results/raw/comparison_markers_dataset_a.csv \
    --summary-md results/tables/comparison_summary_dataset_a.md \
    --figure results/figures/comparison_yamlcpp_dataset_a \
    --max-roundtrip-files 40 --max-marker-files 40

  log "Experiment 7 -- Performance Benchmark (Dataset A)"
  python3 scripts/run_performance_experiment.py \
    --dataset-dir datasets/controlled --dataset-label "Dataset A (controlled corpus)" \
    --max-per-bucket 40 --iterations 30 \
    --raw-csv results/raw/performance_dataset_a.csv \
    --summary-md results/tables/performance_dataset_a_summary.md \
    --figure results/figures/performance_by_bucket_dataset_a

  log "Quote-normalization deep dive (Dataset A)"
  python3 scripts/analyze_quote_normalization.py \
    --dataset-dir datasets/controlled --dataset-label "Dataset A (controlled corpus)" \
    --output-dir results/raw/quote-analysis/dataset-a-output \
    --scratch-dir results/raw/quote-analysis/dataset-a-fixture \
    --raw-csv results/raw/quote_normalization_analysis_dataset_a.csv \
    --summary-md results/tables/quote_normalization_analysis_dataset_a.md \
    --exp5-csv results/raw/validation_dataset_a.csv \
    --max-files 0
}

run_dataset_b
run_dataset_a

log "Done. Tables: results/tables/  Figures: results/figures/  Raw data: results/raw/"
