---
description: Run a strict-math QECTOR threshold sweep (logical error rate vs distance and error rate) with 95% Wilson intervals and a SHA-256-verified artifact, library-only (no app).
---

Execute a seeded threshold sweep on the QECTOR library (no Workbench app needed).
Strict-math contract: skill `qector-math-foundations` (Theorems 1-2, Wilson CI
15.2, required metadata 22.3, safe wording 22.5).

`$ARGUMENTS` may configure it, e.g.:
`--family rotated_surface --distances 3 5 7 --error-rates 0.01 0.05 0.1 --trials 200 --seed 42 --out ..\qector-artifacts\sweep_d357.json`
Defaults: family rotated_surface, distances 3 5 7, error-rates 0.01 0.05 0.1, trials 100, seed 42.

1. Run the reference script: `python bin/run_threshold_sweep.py $ARGUMENTS`.
2. Optionally cross-check with the library MCP server's `threshold_sweep` tool and
   ensure the two artifacts agree (same seed, same trials) - if they differ, report
   the discrepancy rather than picking one.
3. Report: markdown table of logical_error_rate with the 95% Wilson interval per
    (distance, p); the LaTeX summary; the actual Theorem-1 harness violation count;
   the code_capacity tag; and the caveat that low-trial LER is a screening estimate,
   never a converged threshold. Cite the artifact path and its SHA-256.
