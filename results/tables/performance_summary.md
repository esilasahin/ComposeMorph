# Experiment 7 -- Performance Benchmark

## Benchmark environment

- CPU: 12th Gen Intel(R) Core(TM) i7-1255U (12 logical cores)
- RAM: 15.3 GiB
- OS: Debian GNU/Linux 13 (trixie) (kernel 6.12.101+deb13-amd64)
- Compiler: g++ (Debian 14.2.0-19) 14.2.0
- Build type: Release
- C++ standard: C++20
- Docker Compose: Docker Compose version 2.26.1-4
- Iterations per file: 30 (in-process, same loaded ComposeFile instance discarded and recreated each iteration)
- Op under test: `image` (Service::setImage), via find_image eligibility from Experiment 2

## Per-bucket results (pooled across all iterations of all files in the bucket)

### Small (<100 lines) -- 17 file(s)

- load_ms: mean=0.178ms, median=0.150ms, stdev=0.096ms, p95=0.329ms
- modify_ms: mean=0.001ms, median=0.001ms, stdev=0.001ms, p95=0.002ms
- save_ms: mean=0.191ms, median=0.159ms, stdev=0.103ms, p95=0.358ms
- total_ms: mean=0.370ms, median=0.315ms, stdev=0.196ms, p95=0.669ms
- peak RSS: mean=4.506MiB, median=4.504MiB, stdev=0.042MiB, p95=4.566MiB
- file line count range: 16-93

### Medium (100-500 lines) -- 20 file(s)

- load_ms: mean=0.675ms, median=0.648ms, stdev=0.279ms, p95=1.168ms
- modify_ms: mean=0.001ms, median=0.001ms, stdev=0.001ms, p95=0.003ms
- save_ms: mean=0.634ms, median=0.597ms, stdev=0.280ms, p95=1.113ms
- total_ms: mean=1.311ms, median=1.256ms, stdev=0.555ms, p95=2.240ms
- peak RSS: mean=4.638MiB, median=4.607MiB, stdev=0.080MiB, p95=4.773MiB
- file line count range: 101-384

### Large (500-2000 lines) -- 20 file(s)

- load_ms: mean=2.726ms, median=2.217ms, stdev=1.438ms, p95=6.543ms
- modify_ms: mean=0.002ms, median=0.002ms, stdev=0.002ms, p95=0.004ms
- save_ms: mean=2.532ms, median=2.236ms, stdev=1.588ms, p95=7.214ms
- total_ms: mean=5.259ms, median=4.561ms, stdev=3.009ms, p95=13.165ms
- peak RSS: mean=5.099MiB, median=4.955MiB, stdev=0.390MiB, p95=5.789MiB
- file line count range: 505-1870

### XLarge (>2000 lines) -- 2 file(s)

- load_ms: mean=7.734ms, median=7.901ms, stdev=0.893ms, p95=8.744ms
- modify_ms: mean=0.005ms, median=0.005ms, stdev=0.002ms, p95=0.006ms
- save_ms: mean=7.433ms, median=7.628ms, stdev=1.215ms, p95=8.823ms
- total_ms: mean=15.172ms, median=15.544ms, stdev=2.101ms, p95=17.523ms
- peak RSS: mean=6.133MiB, median=6.133MiB, stdev=0.023MiB, p95=6.156MiB
- file line count range: 2057-2591

## Notes

- Dataset B contains only 2 file(s) over 2000 lines, so the XLarge bucket's statistics rest on a small sample -- reported as-is per the acceptance criteria (dataset limitation acknowledged rather than hidden).
- The first iteration of each file (cold: page faults, filesystem cache) is included in the pooled statistics rather than discarded, so mean/p95 are conservative; median is a better single-number summary for typical steady-state cost.
