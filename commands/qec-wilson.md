---
description: Calculate Wilson 95% score confidence intervals and comparative statistical tables for Monte Carlo LER data.
---

Calculate strict Wilson 95% binomial score confidence intervals for quantum error correction Monte Carlo trials.

Arguments: `$ARGUMENTS` (e.g. `--errors 10 --trials 1000`, or a matrix of multiple points).

1. **Step 1 - Compute Interval**:
   - Call MCP tool `wilson_ci(k=errors, n=trials)` on `qector-bench` or calculate using the analytical formula:
     $$\hat{p} = \frac{k + \frac{z^2}{2}}{n + z^2} \pm \frac{z}{n + z^2} \sqrt{\frac{k(n-k)}{n} + \frac{z^2}{4}}$$
     where $z = 1.959963985$ for 95% coverage (Reference Manual Chapter 15.2).
   - If multiple data points are provided, call `wilson_table(data=...)`.

2. **Step 2 - Format Report**:
   - Present the point estimate $k/n$, Wilson lower bound, Wilson upper bound, and margin of error.
   - For comparing two decoders or configurations, perform a two-proportion test with explicit assumptions (do not rely on simple interval overlap).
