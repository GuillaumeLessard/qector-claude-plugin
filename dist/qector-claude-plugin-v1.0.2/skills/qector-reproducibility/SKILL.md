---
name: qector-reproducibility
description: >-
  Reproducibility and claim boundaries for QECTOR (manual 19, 22,
  27, Appendix D). Covers the chapter 22.3 required-artifact
  metadata, the safe / unsafe wording rule (manual 22.5), the
  reproduction commands in Appendix D, the competitive-harness
  pipeline (same Stim circuit, same samples, same DEM, same
  observable scoring), the withdrawn benchmark policy, and the
  hot/cold path label. Load for any question about how to
  reproduce a result, what counts as evidence, or how to write
  a paper-ready claim.
---

# QECTOR Reproducibility and Claim Boundaries

Source of authority: v1.0.0 reference manual, chapters 19, 22, 27;
Appendix D.

## Required elements of a published result (manual 19)

For every published result, the repository policy requires:

- a scoped one-sentence claim
- a clean git commit
- an environment capture (OS, Python, Rust, package versions,
  hardware)
- the exact command
- raw JSON / CSV artifacts with SHA-256
- a Wilson interval for LER
- hot / cold path labels for latency
- safe / unsafe wording attached to every result

## Required artifact metadata (manual 22.3, table 22.1)

| Field           | Required detail                                                                 |
| --------------- | -------------------------------------------------------------------------------- |
| code family     | `repetition`, `ring`, `rotated_surface`, `toric`, `heavy_hex`, `color_code`, `bicycle`, `bivariate_bicycle`, custom (from `H_matrix`), or DEM-derived |
| distance / size | `distance`, `rounds`, `n_checks`, `n_qubits`, `n_detectors`, or code parameters   |
| noise model     | physical error rate, channel/circuit source, `code_capacity` vs `circuit_level` tag |
| decoder         | exact class and mode (weighted / batch / GPU flags)                              |
| sample count    | trials, shots, warmup, seed                                                       |
| metric          | correctness, LER, latency, throughput, memory, GPU bit-identity, or scaling     |
| environment     | OS, CPU, RAM, Python / Rust / package versions, GPU / runtime, git commit        |
| artifact        | raw JSON / CSV path plus SHA-256 sidecar                                         |

`qector-bench.artifact_metadata_check` generates the full block
(no decoder execution); `qector-library.threshold_sweep` already
emits the same block plus the SHA-256 sidecar.

## Safe / unsafe wording (manual 22.5)

**Safe** (anchored to a machine, workload, and artifact):

- "on this machine, for this code/distance/noise/seed/batch
  configuration, decoder A had median hot-path latency X and p99
  Y."
- "on this checked-in artifact, QECTOR weighted Blossom produced
  LER parity with PyMatching on the tested d=15 Stim workload."

**Unsafe** (never published):

- "decoder A is universally faster"
- "always more accurate"
- "production real-time hardware infrastructure"
- any speed superlative without a surviving artifact

## Hot path and cold path (manual 22.1)

- **Cold path**: decoder construction (graph build, weight
  preprocessing, allocation). Reported separately.
- **Hot path**: `decode()` on a pre-built decoder with syndromes
  already in memory. Reported as `decode_hotpath_latency_us` or
  similar.
- Reporting only the hot path is acceptable only for a clearly
  labelled pre-built, repeated-decode workload.

## Statistics (manual 22.2)

Latency distributions are reported with:

- `n`
- mean
- median
- standard deviation
- min, max
- p50, p90, p95, p99
- a 95% confidence interval on the mean

Throughput is computed from the same timing basis, usually median
hot-path latency. A single mean without the distribution is **not**
a public claim.

## Memory methodology (manual 22.4)

- Python-side: `tracemalloc` peak; process RSS via `psutil` when
  installed.
- Native Rust and GPU memory: backend diagnostics or vendor
  tools; label separately.
- Python allocation, process RSS, native heap, and VRAM are
  **never** mixed as a single metric.

## Reproduction commands (manual Appendix D)

```bash
# D.1 Build and import smoke
git clone https://github.com/qectorlab/qector-decoder.git
cd qector-decoder
python -m venv .venv
.venv/Scripts/python -m pip install --upgrade pip maturin
PYO3_PYTHON=".venv/Scripts/python.exe"
.venv/Scripts/python -m maturin develop --release --no-default-features
.venv/Scripts/python -c "from qector_decoder_v3 import UnionFindDecoder; print('QECTOR OK')"

# D.2 Validation suite
.venv/Scripts/python -m pip install stim sinter pymatching ldpc beliefmatching scipy psutil matplotlib tabulate pytest hypothesis fastapi uvicorn httpx
.venv/Scripts/python -m pytest python/tests -q --tb=short
cargo test --release --lib

# D.3 Focused correctness tests
.venv/Scripts/python -m pytest python/tests/test_syndrome_faithfulness.py -q --tb=short
.venv/Scripts/python -m pytest python/tests/test_brute_force_small.py -q --tb=short
.venv/Scripts/python -m pytest python/tests/test_pymatching_compat.py -q --tb=short
.venv/Scripts/python -m pytest python/tests/test_property_faithfulness.py -q --tb=short

# D.4 LER parity workflows
.venv/Scripts/python scripts/competitive_stim_ler.py --distances 13 15 --shots 20000 --out benchmark_results/stim_ler_d13_d15_local
.venv/Scripts/python scripts/competitive_belief_matching.py --distances 3 5 7 --shots 3000 --no-ref --out benchmark_results/competitive_belief_local

# D.5 GPU bit-identity workflows
.venv/Scripts/python -m maturin develop --release --no-default-features --features cuda
.venv/Scripts/python -m pytest python/tests/test_cuda_cpu_bit_identical.py -q --tb=short
.venv/Scripts/python -m maturin develop --release --no-default-features --features opencl
.venv/Scripts/python -m pytest python/tests/test_opencl_cpu_bit_identical.py -q --tb=short

# D.6 Artifact hashing
Get-FileHash benchmark_results/competitive_belief.json -Algorithm SHA256
Get-FileHash benchmark_results/stim_ler_d13_d15.json -Algorithm SHA256
```

## Withdrawn benchmark policy (manual 19, 21)

The reference manual deliberately excludes all latency,
throughput, and VRAM figures tied to a specific machine:

- "All latency/throughput/VRAM figures [are] withdrawn artifacts"
  (manual 19, Table 19.1).
- Hardware benchmark charts (`benchmark_results/charts/*`) and
  paper figures (`paper_figures/*`) are explicitly excluded from
  the manual.
- The figure-disposition index (manual 21) lists every figure and
  the reason for inclusion / exclusion.

This is the published policy. Any new result must follow the
same scope rule.

## The screening-estimate caveat (manual 19, 27)

- 25 trials is a **screening estimate**, not a converged threshold.
- The shipped `qector-researcher` skill uses the word "screening
  estimate" whenever the trial count is small, never "converged
  threshold" without a dated, reproducible artifact.

## How the bench server helps

- `qector-bench.artifact_metadata_check` generates the
  chapter 22.3 metadata block.
- `qector-bench.wilson_ci` and `wilson_table` are the math
  utilities for LER reports.
- `qector-bench.artifacts_sha256` computes the SHA-256 sidecar
  required by the metadata block.
- `qector-bench.env_block` returns the chapter 22.3 environment
  block.
- `qector-bench.decode_faithfulness_check` re-verifies
  `H c = s` (mod 2) for any external decode.
