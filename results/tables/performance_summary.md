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

- load_ms: mean=0.166ms, median=0.148ms, stdev=0.078ms, p95=0.328ms
- modify_ms: mean=0.026ms, median=0.003ms, stdev=0.134ms, p95=0.006ms
- save_ms: mean=0.166ms, median=0.146ms, stdev=0.080ms, p95=0.293ms
- total_ms: mean=0.357ms, median=0.306ms, stdev=0.227ms, p95=0.638ms
- peak RSS: mean=4.691MiB, median=4.680MiB, stdev=0.057MiB, p95=4.801MiB
- file line count range: 16-93

### Medium (100-500 lines) -- 20 file(s)

- load_ms: mean=0.662ms, median=0.635ms, stdev=0.252ms, p95=1.093ms
- modify_ms: mean=0.032ms, median=0.007ms, stdev=0.140ms, p95=0.012ms
- save_ms: mean=0.576ms, median=0.554ms, stdev=0.228ms, p95=0.982ms
- total_ms: mean=1.271ms, median=1.208ms, stdev=0.525ms, p95=2.110ms
- peak RSS: mean=4.981MiB, median=4.971MiB, stdev=0.166MiB, p95=5.246MiB
- file line count range: 101-384

### Large (500-2000 lines) -- 20 file(s)

- load_ms: mean=2.849ms, median=2.247ms, stdev=1.550ms, p95=6.797ms
- modify_ms: mean=0.041ms, median=0.019ms, stdev=0.118ms, p95=0.057ms
- save_ms: mean=2.420ms, median=1.963ms, stdev=1.655ms, p95=6.341ms
- total_ms: mean=5.311ms, median=4.256ms, stdev=3.211ms, p95=13.369ms
- peak RSS: mean=5.966MiB, median=5.666MiB, stdev=0.819MiB, p95=7.434MiB
- file line count range: 505-1870

### XLarge (>2000 lines) -- 2 file(s)

- load_ms: mean=8.559ms, median=8.624ms, stdev=0.999ms, p95=9.702ms
- modify_ms: mean=0.089ms, median=0.076ms, stdev=0.108ms, p95=0.090ms
- save_ms: mean=6.255ms, median=6.167ms, stdev=0.502ms, p95=6.829ms
- total_ms: mean=14.903ms, median=15.227ms, stdev=1.127ms, p95=16.502ms
- peak RSS: mean=8.154MiB, median=8.154MiB, stdev=0.143MiB, p95=8.297MiB
- file line count range: 2057-2591

## Serializer cost: yaml-cpp's emitter vs. ComposeMorph's quote-preserving serializer

Both serializers write the same loaded tree to memory inside the same process, in alternating order per iteration (`emit_yamlcpp_ms`, `emit_preserving_ms` in the raw CSV). yaml-cpp's emitter is what `ComposeFile::save` used before the quote-preserving serializer. Paired two-sided Wilcoxon signed-rank test (normal approximation) per bucket.

| Bucket | Pairs | yaml-cpp median (ms) | quote-preserving median (ms) | median ratio | Wilcoxon z | p |
|---|---|---|---|---|---|---|
| Small (<100 lines) | 510 | 0.114 | 0.115 | 0.965 | -10.53 | 5.98e-26 |
| Medium (100-500 lines) | 600 | 0.522 | 0.511 | 0.945 | -17.55 | 6.2e-69 |
| Large (500-2000 lines) | 600 | 2.190 | 1.868 | 0.960 | -15.53 | 2.33e-54 |
| XLarge (>2000 lines) | 60 | 8.287 | 6.001 | 0.821 | -6.52 | 7.27e-11 |

Ratio < 1 means the quote-preserving serializer is faster; z < 0 means its times are systematically lower.

## Notes

- Dataset B contains only 2 file(s) over 2000 lines, so the XLarge bucket's statistics rest on a small sample -- reported as-is per the acceptance criteria (dataset limitation acknowledged rather than hidden).
- The first iteration of each file (cold: page faults, filesystem cache, and for `modify_ms` the one-time compilation of the regular expression ComposeMorph uses to decide whether a string written through the API needs quotes) is included in the pooled statistics rather than discarded, so mean/p95 are conservative; median is a better single-number summary for typical steady-state cost.
