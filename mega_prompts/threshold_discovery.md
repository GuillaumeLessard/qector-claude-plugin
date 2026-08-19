# QECTOR Mega-Prompt: Automated Code Discovery (Claude)

*Paste into Claude. Fill in the brackets [ ] before hitting Enter.*

***

**Act as my Principal Quantum Researcher.** I need to evaluate a new code
architecture. Follow these 4 phases sequentially without stopping. Do not ask for
permission to proceed. Strict-math ground rules apply from
`skills/qector-math-foundations` (H c = s (mod 2) everywhere; LER on the logical
coset; 95% Wilson intervals; screening-estimate caveat).

**Target**: family=[e.g. rotated_surface], distance=[e.g. 5], p=[e.g. 0.05].

**Phase 1 - Ingestion & Verification (library, app-free)**
- On the `qector-library` server, call `list_code_families` to confirm the family,
  then `decode_single` (distance, blossom, p, seed 42) to extract the real
  n_qubits / n_checks and confirm `syndrome_valid: true`.
- If the target family is not in the library surface, say so plainly and test the
  nearest available equivalent instead of pretending.

**Phase 2 - Baseline Performance Audit (strict method)**
- Run the library `threshold_sweep` for the code (distances [d-2, d, d+2],
  error-rates [0.01, 0.05, 0.1], trials [e.g. 1000], seed 42) with the `union_find`
  decoder. Record each logical_error_rate WITH its Wilson 95% interval, not the
  bare point estimate.
- Note throughput qualitatively only, and only with the machine/workload scope
  (manual 22.5) - no "universally faster" language.

**Phase 3 - Advanced Optimization**
- Same sweep with `blossom` (exact MWPM). Report both Wilson intervals and use an
  explicitly named two-proportion comparison with its assumptions if a
  statistical difference is required; interval overlap alone is not a
  significance test.

**Phase 4 - LaTeX Reporting (ground-truth artifact)**
- Markdown table: per (distance, p): LER + Wilson interval for union_find vs
  blossom, plus n_checks/n_qubits.
- Two-paragraph summary, math in strict LaTeX, tagging the noise model as
  `code_capacity` and stating the screening-estimate caveat.
- Emit the raw JSON artifact outside the plugin with `python
  scripts/run_threshold_sweep.py --out ..\qector-artifacts\sweep.json`, record its
  external SHA-256 sidecar, and cite DOI `10.5281/zenodo.21941046`.
