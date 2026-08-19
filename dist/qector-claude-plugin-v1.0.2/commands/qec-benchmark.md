---
description: Run latency and throughput microbenchmarks on decoder backends with cold/hot path separation.
---

Perform local decoder latency and throughput microbenchmarking adhering to Reference Manual Chapter 22 (reproducibility and safe wording).

Arguments: `$ARGUMENTS` (e.g. `--family rotated_surface --distance 5 --decoder blossom --shots 500`).
Defaults: family `rotated_surface`, distance `3`, decoder `blossom`, shots `100`.

1. **Step 1 - Benchmark Execution**:
   - Call MCP tool `hot_path_microbench(family=..., distance=..., decoder_name=..., n_shots=...)` on `qector-bench`.
   - Separate initial setup/cold-start graph construction from warm/hot-path syndrome decoding loop.

2. **Step 2 - Safe Wording & Reporting**:
   - Report:
     - Mean decode latency per syndrome ($\mu\text{s}$).
     - Median, P95, and P99 latency percentiles.
     - Syndrome throughput ($\text{shots/sec}$).
   - Enforce Rule M7: All performance numbers are machine-, workload-, and environment-specific. Never make unqualified universal throughput claims.
