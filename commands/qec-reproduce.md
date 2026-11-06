---
description: Look up and execute reference manual Appendix D (D.1 through D.6) reproduction workflows.
argument-hint: "d1_build_smoke | d2_validation_suite | d3_focused_correctness | d4_ler_parity | d5_gpu_bit_identity | d6_artifact_hashing | all"
---

Reproduce experimental results, validation suites, and numerical benchmarks from the QECTOR Decoder v3 Reference Manual v1.0.0 (DOI `10.5281/zenodo.21941046`).

Arguments: `$ARGUMENTS` (e.g. `d1_build_smoke`, `d2_validation_suite`, `d3_focused_correctness`, `d4_ler_parity`, `d5_gpu_bit_identity`, `d6_artifact_hashing`, or `all`).

1. **Step 1 - Lookup Commands**:
   - Call `reproduction_command_lookup(section="$ARGUMENTS")` (research profile) and run the plugin-local command it returns; it is the only recipe for this package. The upstream-repository recipe in `skills/qector-reproducibility` needs network access and is not usable air-gapped.
   - Available sections:
     - `d1_build_smoke`: Wheel installation and basic smoke testing.
     - `d2_validation_suite`: `scripts/run_manual_math_validation.py` (29 tests: the 16 theorem obligations plus Appendix E checks) and the unit suite.
     - `d3_focused_correctness`: Focused check on syndrome faithfulness and logical coset equivalence.
     - `d4_ler_parity`: Logical error rate threshold comparison sweeps with 95% Wilson confidence intervals.
     - `d5_gpu_bit_identity`: Exact bit-identity equivalence verification between CPU and GPU backends.
     - `d6_artifact_hashing`: SHA-256 sidecar checksum computation and validation.

2. **Step 2 - Execution & Reporting**:
   - Execute the selected reproduction command (e.g. `python scripts/run_manual_math_validation.py`).
   - Format results as a markdown report citing the specific reference manual section and DOI.
   - Retain raw artifacts and external SHA-256 sidecars.
