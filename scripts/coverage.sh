#!/usr/bin/env bash
# Kütüphane kaynakları için satır kapsamını ölçer (Madde 25).
#
# Ek araç gerektirmez: GCC ile gelen gcov kullanılır. Ayrı bir derleme
# dizininde (build-coverage) ölçüm yapar, böylece normal build/ etkilenmez.
#
# Kullanım:
#   ./scripts/coverage.sh            # eşik %80
#   ./scripts/coverage.sh 90         # eşik %90
set -euo pipefail

THRESHOLD="${1:-80}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="$REPO_ROOT/build-coverage"
OUT_DIR="$REPO_ROOT/results/coverage"

cd "$REPO_ROOT"
cmake -S . -B "$BUILD_DIR" -DCMAKE_BUILD_TYPE=Debug -DCOMPOSEMORPH_COVERAGE=ON >/dev/null
cmake --build "$BUILD_DIR" -j"$(nproc 2>/dev/null || echo 4)" >/dev/null
ctest --test-dir "$BUILD_DIR" --output-on-failure

mkdir -p "$OUT_DIR"
OBJ_DIR="$BUILD_DIR/CMakeFiles/composemorph.dir/src"
rm -f "$OUT_DIR"/*.gcov
(cd "$OUT_DIR" && gcov -p "$OBJ_DIR"/*.gcda >/dev/null)

python3 - "$OUT_DIR" "$THRESHOLD" <<'PY'
import pathlib, sys

out_dir, threshold = pathlib.Path(sys.argv[1]), float(sys.argv[2])
rows, total_hit, total_lines = [], 0, 0
for gcov_file in sorted(out_dir.glob("*.gcov")):
    name = gcov_file.read_text(errors="replace").splitlines()[0].split(":")[-1].strip()
    if "/src/" not in name and "/include/compose/" not in name:
        continue
    hit = missed = 0
    for line in gcov_file.read_text(errors="replace").splitlines():
        count = line.split(":", 1)[0].strip()
        if count == "#####":
            missed += 1
        elif count not in ("-", "") and count[0].isdigit():
            hit += 1
    if hit + missed == 0:
        continue
    rows.append((pathlib.Path(name).name, hit, hit + missed))
    total_hit += hit
    total_lines += hit + missed

report = ["file,covered_lines,total_lines,percent"]
for name, hit, total in sorted(rows):
    report.append(f"{name},{hit},{total},{100 * hit / total:.1f}")
overall = 100 * total_hit / total_lines if total_lines else 0.0
report.append(f"TOTAL,{total_hit},{total_lines},{overall:.1f}")
(out_dir / "coverage.csv").write_text("\n".join(report) + "\n")

for line in report:
    print(line.replace(",", "\t"))
print(f"\nthreshold: {threshold:.0f}%")
sys.exit(0 if overall >= threshold else 1)
PY
