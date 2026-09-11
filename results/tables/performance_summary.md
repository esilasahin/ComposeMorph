# Experiment 7 -- Performance Benchmark

## Benchmark environment

- CPU: 12th Gen Intel(R) Core(TM) i7-1255U (12 logical cores)
- RAM: 15.3 GiB
- OS: Debian GNU/Linux 13 (trixie) (kernel 6.12.107+deb13-amd64)
- Compiler: g++ (Debian 14.2.0-19) 14.2.0
- Build type: Release
- C++ standard: C++20
- Docker Compose: Docker Compose version 2.26.1-4
- Iterations per file: 30 (in-process, same loaded ComposeFile instance discarded and recreated each iteration)
- Op under test: `image` (Service::setImage), via find_image eligibility from Experiment 2

## Per-bucket results (pooled across all iterations of all files in the bucket)

### Small (<100 lines) -- 17 file(s)

- load_ms: mean=0.335ms, median=0.286ms, stdev=0.161ms, p95=0.633ms
- modify_ms: mean=0.048ms, median=0.006ms, stdev=0.242ms, p95=0.012ms
- save_ms: mean=0.348ms, median=0.309ms, stdev=0.370ms, p95=0.650ms
- total_ms: mean=0.732ms, median=0.605ms, stdev=0.540ms, p95=1.388ms
- peak RSS: mean=4.738MiB, median=4.742MiB, stdev=0.065MiB, p95=4.805MiB
- file line count range: 16-93

### Medium (100-500 lines) -- 20 file(s)

- load_ms: mean=1.355ms, median=1.307ms, stdev=0.548ms, p95=2.291ms
- modify_ms: mean=0.059ms, median=0.015ms, stdev=0.242ms, p95=0.033ms
- save_ms: mean=1.175ms, median=1.115ms, stdev=0.494ms, p95=2.007ms
- total_ms: mean=2.589ms, median=2.457ms, stdev=1.095ms, p95=4.343ms
- peak RSS: mean=5.020MiB, median=4.990MiB, stdev=0.174MiB, p95=5.352MiB
- file line count range: 101-384

### Large (500-2000 lines) -- 20 file(s)

- load_ms: mean=5.594ms, median=4.579ms, stdev=2.982ms, p95=13.820ms
- modify_ms: mean=0.082ms, median=0.038ms, stdev=0.222ms, p95=0.106ms
- save_ms: mean=4.685ms, median=3.567ms, stdev=3.187ms, p95=13.185ms
- total_ms: mean=10.362ms, median=8.281ms, stdev=6.181ms, p95=26.998ms
- peak RSS: mean=6.007MiB, median=5.711MiB, stdev=0.824MiB, p95=7.488MiB
- file line count range: 505-1870

### XLarge (>2000 lines) -- 2 file(s)

- load_ms: mean=15.438ms, median=15.828ms, stdev=1.725ms, p95=17.357ms
- modify_ms: mean=0.165ms, median=0.139ms, stdev=0.194ms, p95=0.151ms
- save_ms: mean=11.090ms, median=10.848ms, stdev=1.017ms, p95=12.310ms
- total_ms: mean=26.692ms, median=27.166ms, stdev=2.122ms, p95=29.952ms
- peak RSS: mean=8.201MiB, median=8.201MiB, stdev=0.088MiB, p95=8.289MiB
- file line count range: 2057-2591

## Serializer cost: yaml-cpp's emitter vs. ComposeMorph's quote-preserving serializer

Both serializers write the same loaded tree to memory inside the same process, in alternating order per iteration (`emit_yamlcpp_ms`, `emit_preserving_ms` in the raw CSV). yaml-cpp's emitter is what `ComposeFile::save` used before the quote-preserving serializer. Paired two-sided Wilcoxon signed-rank test (normal approximation) per bucket.

| Bucket | Pairs | yaml-cpp median (ms) | quote-preserving median (ms) | median ratio | Wilcoxon z | p |
|---|---|---|---|---|---|---|
| Small (<100 lines) | 510 | 0.225 | 0.204 | 0.966 | -11.98 | 4.74e-33 |
| Medium (100-500 lines) | 600 | 1.059 | 0.997 | 0.944 | -17.60 | 2.47e-69 |
| Large (500-2000 lines) | 600 | 4.480 | 3.427 | 0.944 | -16.84 | 1.19e-63 |
| XLarge (>2000 lines) | 60 | 15.025 | 10.659 | 0.785 | -6.74 | 1.63e-11 |

Ratio < 1 means the quote-preserving serializer is faster; z < 0 means its times are systematically lower.

## Notes

- Dataset B contains only 2 file(s) over 2000 lines, so the XLarge bucket's statistics rest on a small sample -- reported as-is per the acceptance criteria (dataset limitation acknowledged rather than hidden).
- The first iteration of each file (cold: page faults, filesystem cache, and for `modify_ms` the one-time compilation of the regular expression ComposeMorph uses to decide whether a string written through the API needs quotes) is included in the pooled statistics rather than discarded, so mean/p95 are conservative; median is a better single-number summary for typical steady-state cost.
