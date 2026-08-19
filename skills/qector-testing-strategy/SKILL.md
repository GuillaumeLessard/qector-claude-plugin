---
name: qector-testing-strategy
description: >-
  The QECTOR testing and validation strategy (manual 23). Covers
  the eight validation layers (syndrome faithfulness, property-
  based, exhaustive oracle, cross-decoder equivalence, DEM
  pipeline, LER parity, qLDPC correctness, memory behaviour, API
  stability, GPU kernels), the stale test-count policy, the
  cross-decoder equivalence tests (batch == per-shot; UF ==
  FastUF; GPU == CPU), and the hardware-gated GPU test policy.
  Load for any question about how a result is verified, what
  tests are required, or what the "stale" notice means.
---

# QECTOR Testing and Validation Strategy

Source of authority: v1.0.0 reference manual, chapter 23.

## The eight validation layers (Table 23.1)

| Layer                      | What it locks                                                              | Representative evidence                                                       |
| -------------------------- | -------------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| Syndrome faithfulness      | `H c = s` for reachable syndromes across all backends                       | `test_syndrome_faithfulness.py`, `cross_decoder_tests.rs`                      |
| Property-based             | Randomised reachable syndromes, adversarial and degenerate inputs          | `test_property_faithfulness.py`, `test_property_gf2_invariants.py`            |
| Exhaustive oracle          | Exact MWPM optimality on small codes                                        | `test_brute_force_small.py`                                                    |
| Cross-decoder equivalence  | Batch equals per-shot; UF equals FastUF; GPU equals CPU                    | `test_property_batch_equivalence.py`, `test_cuda_cpu_bit_identical.py`         |
| DEM pipeline               | Parser, collapse rule, weights, observables                                | `test_dem*.py`, `test_dem_collapse_*.py`                                       |
| LER parity                 | Observable-space scoring and noise-model comparability                      | `test_ler_noise_model_parity.py`, `test_competitive_ler.py`                    |
| qLDPC correctness          | CSS commutation, rowspace metric, BB codes                                 | `test_bposd_bb72.py`, `test_bposd_bb144.py`, `test_bposd_ldpc.py`              |
| Memory behaviour           | No Python growth, no native RSS leak, scratch reuse                        | `test_no_python_memory_growth.py`, `test_no_native_rss_leak.py`                |
| API stability              | Public symbols, signatures, entry points                                    | `test_public_symbols.py`, `test_api_compat.py`                                 |
| GPU kernels                | Compile-gate and bit identity on tested configs                            | `test_cuda_cpu_bit_identical.py`, `cuda_batch_tests.rs`                        |

## The cross-decoder equivalence contract

The cross-decoder equivalence layer is what makes the
"bit-determinism" claim of the threading model (manual 26.3)
testable:

- **Batch equals per-shot**: `decoder.batch_decode(syndromes)`
  produces corrections that match `decoder.decode(s)` for every
  `s` in `syndromes`, in order. Test:
  `test_property_batch_equivalence.py`.
- **UF equals FastUF**: the unweighted Union-Find and Fast
  Union-Find corrections agree on every reachable syndrome. Test:
  `test_property_batch_equivalence.py`.
- **GPU equals CPU**: the unweighted CUDA / OpenCL batch kernels
  produce `c_GPU(s) = c_CPU(s)` bit for bit. Test:
  `test_cuda_cpu_bit_identical.py`,
  `test_opencl_cpu_bit_identical.py`.

## The hardware-gated GPU test policy

> GPU and OpenCL tests are hardware-gated: they run on machines
> that provide the runtime, and **a skipped test is not GPU
> evidence** (manual 23).

This means:

- A `pytest` run that skips GPU tests on a non-GPU machine is
  not GPU evidence.
- A `pytest` run that passes GPU tests on a GPU machine is
  GPU evidence only for that machine, that workload, that
  configuration (manual 22.5).
- A publication that claims "GPU correctness" must specify the
  tested configuration and the worker's GPU.

## The stale test-count policy (manual 23)

- The frozen tree records a v0.5 local validation report of
  **832 Python** and **87 Rust** tests.
- The tree itself marks that table **stale for post-0.5 builds**.
- `python/tests/` now contains more files than at the time of
  the report.
- **No current pass / fail count is claimed** in the v1.0.0
  manual.
- The reader is directed to `docs/CORRECTNESS_AUDIT.md` and to
  the live suite.

This is the official policy. Any new test count must be re-
generated on the live tree; do not quote the v0.5 numbers as
current.

## The withdrawn benchmark policy (manual 19, 21)

- The competitive and throughput tables published for earlier
  cores were withdrawn in the frozen tree because the measured
  figures did not survive a core fingerprint change.
- No performance number in the v1.0.0 manual is intended to
  replace a regenerated artifact.
- See `qector-reproducibility` for the chapter 22.3 metadata
  contract that any new benchmark must satisfy.

## The DEM pipeline tests (manual 14)

- `test_dem_*.py` covers the parser, the collapse rule, the
  weight calculation, the observables matrix, and the
  recalibration step.
- The worked example `p1 = 0.01, p2 = 0.02 -> p = 0.0296, weight
  = 3.489` is locked by `test_dem_collapse_probability.py` and
  `test_dem_collapse_parallel_edges.py`.

## The qLDPC correctness tests (manual 8)

- `test_bposd_bb72.py` and `test_bposd_bb144.py` lock the BB
  qLDPC codes.
- `test_bposd_ldpc.py` covers the general LDPC path.
- `test_bposd_rowspace_metric.py` covers the rowspace
  consistency check.

## Common pitfalls

- **Quoting the 0.5 test count as current** -> it is stale;
  regenerate on the live tree.
- **Treating a skipped GPU test as GPU evidence** -> a skipped
  test is not GPU evidence; the test is hardware-gated.
- **Publishing a benchmark without a Wilson interval** -> manual
  15.2 requires a 95% Wilson interval.
- **Comparing code_capacity to circuit_level LER** -> refused by
  the competitive harness (manual 15.3); tag the run first.
- **Running the validation suite on a different machine from the
  publication** -> every artifact carries the chapter 22.3
  environment block; mismatches are a release blocker.

## How the bench server helps

- `qector-bench.artifact_metadata_check` generates the
  chapter 22.3 metadata block for a validation artifact.
- `qector-bench.wilson_ci` and `wilson_table` are the math
  utilities for the LER parity tests.
- `qector-bench.decode_faithfulness_check` re-verifies
  `H c = s` (mod 2) externally.
- `qector-bench.pymatching_compat_check` is the
  cross-decoder-equivalence smoke test for the PyMatching shim.
- `qector-bench.env_block` returns the chapter 22.3 environment
  block for a validation artifact.
