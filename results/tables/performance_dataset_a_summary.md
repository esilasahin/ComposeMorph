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

- load_ms: mean=0.058ms, median=0.052ms, stdev=0.026ms, p95=0.121ms
- modify_ms: mean=0.031ms, median=0.003ms, stdev=0.155ms, p95=0.007ms
- save_ms: mean=0.101ms, median=0.088ms, stdev=0.249ms, p95=0.183ms
- total_ms: mean=0.190ms, median=0.143ms, stdev=0.314ms, p95=0.315ms
- peak RSS: mean=4.625MiB, median=4.613MiB, stdev=0.038MiB, p95=4.676MiB
- file line count range: 3-32

### Medium (100-500 lines) -- 1 file(s)

- load_ms: mean=0.356ms, median=0.333ms, stdev=0.055ms, p95=0.448ms
- modify_ms: mean=0.032ms, median=0.006ms, stdev=0.141ms, p95=0.011ms
- save_ms: mean=0.314ms, median=0.290ms, stdev=0.065ms, p95=0.411ms
- total_ms: mean=0.702ms, median=0.627ms, stdev=0.224ms, p95=0.851ms
- peak RSS: mean=4.809MiB, median=4.809MiB, stdev=0.000MiB, p95=4.809MiB
- file line count range: 118-118

### Large (500-2000 lines) -- 0 file(s)

No eligible files found in this bucket (needs a service with an `image` field).

### XLarge (>2000 lines) -- 0 file(s)

No eligible files found in this bucket (needs a service with an `image` field).

## Serializer cost: yaml-cpp's emitter vs. ComposeMorph's quote-preserving serializer

Both serializers write the same loaded tree to memory inside the same process, in alternating order per iteration (`emit_yamlcpp_ms`, `emit_preserving_ms` in the raw CSV). yaml-cpp's emitter is what `ComposeFile::save` used before the quote-preserving serializer. Paired two-sided Wilcoxon signed-rank test (normal approximation) per bucket.

| Bucket | Pairs | yaml-cpp median (ms) | quote-preserving median (ms) | median ratio | Wilcoxon z | p |
|---|---|---|---|---|---|---|
| Small (<100 lines) | 1050 | 0.028 | 0.028 | 0.956 | -3.57 | 0.000351 |
| Medium (100-500 lines) | 30 | 0.252 | 0.237 | 0.944 | -3.77 | 0.00016 |

Ratio < 1 means the quote-preserving serializer is faster; z < 0 means its times are systematically lower.

## Notes

- Dataset A (controlled corpus) contains only 0 file(s) over 2000 lines, so the XLarge bucket's statistics rest on a small sample -- reported as-is per the acceptance criteria (dataset limitation acknowledged rather than hidden).
- The first iteration of each file (cold: page faults, filesystem cache, and for `modify_ms` the one-time compilation of the regular expression ComposeMorph uses to decide whether a string written through the API needs quotes) is included in the pooled statistics rather than discarded, so mean/p95 are conservative; median is a better single-number summary for typical steady-state cost.
