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

- load_ms: mean=0.073ms, median=0.065ms, stdev=0.041ms, p95=0.130ms
- modify_ms: mean=0.001ms, median=0.001ms, stdev=0.002ms, p95=0.002ms
- save_ms: mean=0.118ms, median=0.105ms, stdev=0.251ms, p95=0.184ms
- total_ms: mean=0.193ms, median=0.173ms, stdev=0.263ms, p95=0.305ms
- peak RSS: mean=4.486MiB, median=4.492MiB, stdev=0.025MiB, p95=4.520MiB
- file line count range: 3-32

### Medium (100-500 lines) -- 1 file(s)

- load_ms: mean=0.358ms, median=0.327ms, stdev=0.088ms, p95=0.566ms
- modify_ms: mean=0.001ms, median=0.001ms, stdev=0.002ms, p95=0.003ms
- save_ms: mean=0.331ms, median=0.300ms, stdev=0.089ms, p95=0.571ms
- total_ms: mean=0.691ms, median=0.629ms, stdev=0.178ms, p95=1.139ms
- peak RSS: mean=4.586MiB, median=4.586MiB, stdev=0.000MiB, p95=4.586MiB
- file line count range: 118-118

### Large (500-2000 lines) -- 0 file(s)

No eligible files found in this bucket (needs a service with an `image` field).

### XLarge (>2000 lines) -- 0 file(s)

No eligible files found in this bucket (needs a service with an `image` field).

## Notes

- Dataset A (controlled corpus) contains only 0 file(s) over 2000 lines, so the XLarge bucket's statistics rest on a small sample -- reported as-is per the acceptance criteria (dataset limitation acknowledged rather than hidden).
- The first iteration of each file (cold: page faults, filesystem cache) is included in the pooled statistics rather than discarded, so mean/p95 are conservative; median is a better single-number summary for typical steady-state cost.
