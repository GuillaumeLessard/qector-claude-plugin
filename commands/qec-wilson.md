---
description: Compute Wilson 95% score intervals for Monte Carlo logical-error-rate data.
argument-hint: "--errors 10 --trials 1000  (or several error counts for one trial count)"
---

Compute Wilson score confidence intervals for quantum error correction Monte Carlo trials (Reference Manual chapter 15.2).

Arguments: `$ARGUMENTS` (e.g. `--errors 10 --trials 1000`, or several error counts sharing one trial count).

The tools are on the research profile. If they are not listed, apply the formula below yourself and say the number is computed, not tool-verified.

1. **Compute the interval**
   - One point: call `wilson_ci(k=errors, n=trials)` (`z` defaults to `1.959963985`; it must be positive and `k <= n`).
   - Several points with the same `n`: call `wilson_table(n=trials, k_list=[k1, k2, ...])`.
   - Formula, for reference: with `p = k/n`, centre `(p + z²/2n) / (1 + z²/n)`, half-width `z·sqrt(p(1-p)/n + z²/4n²) / (1 + z²/n)`.

2. **Format the report**
   - Present the point estimate `k/n`, the Wilson lower and upper bounds and the half-width.
   - When comparing two decoders or configurations, use a two-proportion test with explicit assumptions; interval overlap alone is not a test.
