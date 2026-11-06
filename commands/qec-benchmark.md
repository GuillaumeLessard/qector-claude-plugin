---
description: Run a hot-path decoder latency microbenchmark (machine-scoped, never a portable claim).
argument-hint: "--family rotated_surface --size 5 --decoder blossom --shots 500"
---

Measure local decoder hot-path latency with the discipline of Reference Manual chapter 22 (reproducibility and safe wording).

Arguments: `$ARGUMENTS` (e.g. `--family rotated_surface --size 5 --decoder blossom --shots 500`).
Defaults: family `rotated_surface`, size `3`, decoder `blossom`, shots `100`.

The tool lives on the research profile (`qector-secure --profile research`); it is not in the default 12-tool safe profile. If it is not listed by `tools/list`, say so and stop.

1. **Benchmark execution**
   - Call `hot_path_microbench(family=..., size=..., decoder_name=..., shots=...)`. Argument names are exactly `family`, `size`, `decoder_name`, `shots`, `seed`.
   - The tool runs untimed warm-up shots, then times `decoder.decode()` alone per shot; the `H c = s (mod 2)` check runs outside the timed window. Read `timed_window` and `warmup_shots` in the result and say so.

2. **Safe wording and reporting**
   - Report from `latency_us`: `mean`, `p50`, `p95`, `p99`, `min`, `max`, `n` (shots completed) and `ci95_mean` (null below 30 shots; say "insufficient shots for a CI" rather than inventing one).
   - Throughput is not returned. If the user wants it, derive `1e6 / mean` shots/s and label it *derived from mean latency*.
   - The envelope `status` is `measured`; repeat `measurement_scope` (machine, backend version, workload hash). Rule M7: numbers are machine-, workload- and build-specific; never make an unqualified or comparative throughput claim.
   - If `warnings` mention shots that violated `H c = s`, report the count; they are excluded from the sample.
