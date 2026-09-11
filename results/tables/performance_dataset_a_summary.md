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

### Small (<100 lines) -- 35 file(s)

- load_ms: mean=0.095ms, median=0.085ms, stdev=0.048ms, p95=0.211ms
- modify_ms: mean=0.053ms, median=0.004ms, stdev=0.259ms, p95=0.012ms
- save_ms: mean=0.140ms, median=0.123ms, stdev=0.076ms, p95=0.272ms
- total_ms: mean=0.288ms, median=0.212ms, stdev=0.323ms, p95=0.526ms
- peak RSS: mean=4.671MiB, median=4.664MiB, stdev=0.033MiB, p95=4.719MiB
- file line count range: 3-32

### Medium (100-500 lines) -- 1 file(s)

- load_ms: mean=0.639ms, median=0.636ms, stdev=0.023ms, p95=0.678ms
- modify_ms: mean=0.048ms, median=0.010ms, stdev=0.204ms, p95=0.013ms
- save_ms: mean=0.521ms, median=0.518ms, stdev=0.037ms, p95=0.543ms
- total_ms: mean=1.208ms, median=1.160ms, stdev=0.241ms, p95=1.252ms
- peak RSS: mean=4.824MiB, median=4.824MiB, stdev=0.000MiB, p95=4.824MiB
- file line count range: 118-118

### Large (500-2000 lines) -- 0 file(s)

No eligible files found in this bucket (needs a service with an `image` field).

### XLarge (>2000 lines) -- 0 file(s)

No eligible files found in this bucket (needs a service with an `image` field).

## Serializer cost: yaml-cpp's emitter vs. ComposeMorph's quote-preserving serializer

Both serializers write the same loaded tree to memory inside the same process, in alternating order per iteration (`emit_yamlcpp_ms`, `emit_preserving_ms` in the raw CSV). yaml-cpp's emitter is what `ComposeFile::save` used before the quote-preserving serializer. Paired two-sided Wilcoxon signed-rank test (normal approximation) per bucket.

| Bucket | Pairs | yaml-cpp median (ms) | quote-preserving median (ms) | median ratio | Wilcoxon z | p |
|---|---|---|---|---|---|---|
| Small (<100 lines) | 1050 | 0.050 | 0.049 | 0.974 | -5.39 | 7.14e-08 |
| Medium (100-500 lines) | 30 | 0.484 | 0.453 | 0.930 | -4.78 | 1.73e-06 |

Ratio < 1 means the quote-preserving serializer is faster; z < 0 means its times are systematically lower.

## Notes

- Dataset A (controlled corpus) contains only 0 file(s) over 2000 lines, so the XLarge bucket's statistics rest on a small sample -- reported as-is per the acceptance criteria (dataset limitation acknowledged rather than hidden).
- The first iteration of each file (cold: page faults, filesystem cache, and for `modify_ms` the one-time compilation of the regular expression ComposeMorph uses to decide whether a string written through the API needs quotes) is included in the pooled statistics rather than discarded, so mean/p95 are conservative; median is a better single-number summary for typical steady-state cost.
