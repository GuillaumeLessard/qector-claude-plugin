---
name: qector-ler-methodology
description: >-
  Logical error rate (LER) methodology for QECTOR. Covers the
  Wilson 95% score interval, the chapter 22.3 required-artifact
  metadata block, the code_capacity / circuit_level tagging rule,
  safe / unsafe wording, and the screening-estimate caveat. Load
  for any LER report, threshold sweep, or competitive
  comparison.
---

# QECTOR LER Methodology

Source of authority: v1.0.0 reference manual, chapters 15, 19, 22.

## Definitions

- **Logical error rate**: the probability that the predicted
  observable flips differ from the sampled observable flips on the
  same Stim circuit. Scoring with `correction != error` is
  explicitly rejected (manual 15).
- **Wilson 95% score interval**: a binomial confidence interval with
  correct coverage at small `k` and extreme `p`, unlike the Wald
  approximation. Always `z = 1.959963985`.

## Wilson formula (manual 15.2)

For `k` logical errors in `n` trials:

    centre  = ( p + z^2/(2n) ) / ( 1 + z^2/n )
    margin  = z * sqrt( p(1-p)/n + z^2/(4 n^2) ) / ( 1 + z^2/n )
    CI_95   = ( max(0, centre - margin), min(1, centre + margin) )

with `p = k/n` and `z = 1.959963985`.

Worked example (manual 15.2, appendix E.2): `k=10, n=1000` -> CI is
approximately `(0.00544, 0.01831)`. The `qector-bench.wilson_ci` tool
returns exactly this; `qector-bench.wilson_table` returns a batch of
intervals for a series of `k` values at fixed `n`.

## Required-artifact metadata (manual 22.3, table 22.1)

Every evidence artifact must include:

| Field           | Required detail                                                                 |
| --------------- | -------------------------------------------------------------------------------- |
| code_family     | `repetition`, `ring`, `rotated_surface`, `toric`, `heavy_hex`, `color_code`, `bicycle`, `bivariate_bicycle`, custom (from `H_matrix`), or DEM-derived |
| distance / size | `distance`, `rounds`, `n_checks`, `n_qubits`, `n_detectors`, or code parameters   |
| noise model     | physical error rate, channel/circuit source, `code_capacity` vs `circuit_level` tag |
| decoder         | exact class and mode (weighted / batch / GPU flags)                              |
| sample count    | trials, shots, warmup, seed                                                       |
| metric          | correctness, LER, latency, throughput, memory, GPU bit-identity, or scaling     |
| environment     | OS, CPU, RAM, Python / Rust / package versions, GPU / runtime, git commit        |
| artifact        | raw JSON / CSV path plus SHA-256 sidecar                                         |

The `qector-bench.artifact_metadata_check` tool generates the full
required-metadata block for a candidate artifact (no decoder
execution). The library `qector-library.threshold_sweep` already
emits the same block plus the chapter 22.3 SHA-256 sidecar.

## Tagging rule (manual 15.3)

- Tag every LER run `code_capacity` or `circuit_level`.
- The harness **refuses** to compare across tags. A code_capacity
  LER at a nominal `p` is not comparable to a circuit_level LER at
  the same `p`.
- Historically some artifacts mixed a code_capacity QECTOR
  measurement with a circuit_level PyMatching measurement; those
  artifacts were withdrawn (manual 15.3 + 19.1).
- "Competitive harness drives every decoder through the same
  pipeline - the same Stim circuit, the same detector samples, the
  same DEM, the same observable scoring - so the only thing that
  varies between rows is the decoder."

## Safe / unsafe wording (manual 22.5)

**Safe** (anchored to a machine, workload, and artifact):

- "on this machine, for this code/distance/noise/seed/batch
  configuration, decoder A had median hot-path latency X and p99 Y."
- "on this checked-in artifact, QECTOR weighted Blossom produced
  LER parity with PyMatching on the tested d=15 Stim workload."

**Unsafe** (never published):

- "decoder A is universally faster"
- "always more accurate"
- "production real-time hardware infrastructure"
- any speed superlative without a surviving artifact

## Memory methodology (manual 22.4)

- Python-side: `tracemalloc` peak; process RSS via `psutil` when
  installed.
- Native Rust and GPU memory: backend diagnostics or vendor tools;
  label separately.
- Python allocation, process RSS, native heap, and VRAM are **never
  mixed** as a single metric.

## Hot path vs cold path (manual 22.1)

- **Cold path**: decoder construction (graph build, weight
  preprocessing, allocation). Reported separately.
- **Hot path**: `decode()` on a pre-built decoder with syndromes
  already in memory. Reported as `decode_hotpath_latency_us` or
  similar.
- Reporting only the hot path is acceptable only for a clearly
  labelled pre-built, repeated-decode workload.

## The screening-estimate caveat (manual 19, 27)

- 25 trials is a **screening estimate**, not a converged threshold.
- The shipped `qector-researcher` skill uses the word "screening
  estimate" whenever the trial count is small, never "converged
  threshold" without a dated, reproducible artifact.

## How the bench server helps

- `qector-bench.wilson_ci` and `wilson_table` cover the math
  utility without running a decode.
- `qector-bench.logical_coset_score` scores a batch of
  `(predicted, sampled)` logical observables on the logical coset
  (Theorem 2) and reports a Wilson 95% interval.
- `qector-bench.artifact_metadata_check` generates the chapter
  22.3 metadata block for a candidate artifact.
- `qector-bench.decode_faithfulness_check` re-verifies the
  `H c = s` (mod 2) gate externally (useful when ingesting
  corrections from a third-party decoder or older wheel build).
- `qector-bench.hot_path_microbench` runs a per-machine hot-path
  latency sample. The result is **never a portable claim**.
