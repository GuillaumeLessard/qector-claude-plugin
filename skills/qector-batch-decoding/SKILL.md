---
name: qector-batch-decoding
description: >-
  Batch, streaming, and GPU-accelerated decoding paths for QECTOR. Covers
  the manual 13 CUDA / OpenCL bit-identity contract, the per-thread
  scratch sizing formula (manual 13.4), the warm-up / dispatch / hot-path
  pattern, the worker-thread determinism guarantee (manual 26.3), and
  the cold-path / hot-path reporting rule. Load when a question involves
  millions of shots, GPU acceleration, batch decode, or performance
  tuning.
---

# QECTOR Batch Decoding

Source of authority: v1.0.0 reference manual, chapters 13, 17, 20, 26.

## The batch and streaming surfaces (manual 16.2 - Provisional)

| Class                       | Notes                                                      |
| --------------------------- | ---------------------------------------------------------- |
| `CPUBatchDecoder`           | batch shape stable; performance workload-sensitive         |
| `BatchDecoder`              | batch shape stable; performance workload-sensitive         |
| `CUDABatchDecoder`          | per-thread port of the UF core; bit-identity tested        |
| `OpenCLBatchDecoder`        | source build only; bit-identity tested                     |
| `CUDABpOsdDecoder`          | batched BP+OSD; single-shot CPU preferred                  |
| `StreamingDecoder`          | OR-accumulated history; simulation workflow                |
| `SlidingWindowDecoder`      | exponentially decayed window; bounded tail                 |

The library MCP server does **not** expose any batch tool (manual
8.0: the 8-tool library surface is frozen). The bench server adds
`qector-research.hot_path_microbench` for per-shot latency distribution
sampling, but it caps at `QECTOR_MCP_BENCH_MAX_BENCH_SHOTS` (default
5000) and the result is per-machine, per-workload, per-build only
(manual 22.5).

## The bit-identity contract (manual 13.2, Theorem 16)

> For any graphlike code and any syndrome `s`, the unweighted batch
> kernels produce `c_GPU(s) = c_CPU(s)` bit for bit.

The claim is scoped to the **tested graphlike configurations** and
to the **unweighted path**. The weighted kernel mirrors the CPU
weighted growth with an adaptive time step; its accuracy
equivalence to the weighted CPU decoder is validated by the
regression tests on tested configurations. The batch-size threshold
below which the GPU path delegates to the CPU is an implementation
detail, **not a throughput claim**.

`qector-research.pymatching_compat_check` is a related smoke test: it
verifies that a QECTOR decode and a `pymatching.Matching` decode on
the same syndrome produce syndrome-valid corrections (Theorem 1) on
the same parity-check matrix. Bitwise equality is reported when
present, but the explicit "agreement note" says "Bitwise equality is
the coset-representative equality QECTOR and pymatching may not
share (degeneracy, Theorem 1 corollary)."

## Per-thread scratch sizing (manual 13.4)

For a graphlike code with `n_checks` and `n_qubits`,
`N = n_checks + 1` nodes and `E` edges:

- `u32` scratch stride: `6N + 1 + 4E` words
- `u8` scratch stride: `5N + E` bytes
- A batch of `B` shots: `B * 251 * 4` bytes (u32) plus `B * 150`
  bytes (u8), in addition to syndrome and correction buffers.

The workspace allocates these sizes in advance, checks against
available memory, and falls back to managed memory on large codes.
This is the **engineering contract**; it is not a measured figure.

## GPU context pitfalls (manual 20.3)

- The native CUDA batch path creates a driver-API context; CuPy uses
  the primary context.
- A known intermittent access violation was observed when both
  paths are exercised in one process under load on one tested
  configuration.
- The documented workaround: run the two workloads in **separate
  processes** or **hide the device** for monolithic suite runs.
- A primary-context sharing fix is a candidate v1.x change
  (manual 27.3).

## OpenCL distribution (manual 20.4)

- Published wheels are **CUDA-only** by design; OpenCL requires a
  documented **source build**.
- `opencl_is_available()` probes in a child process because some
  drivers abort during kernel setup.

## Threading and memory model (manual 26.3, 26.4)

- Batch paths use **Rayon** data parallelism; each worker keeps its
  own scratch so results are independent of worker count and
  row-to-worker assignment.
- Single-shot paths use **thread-local reusable buffers**.
- Observable property: bit-determinism. Neither the worker count
  nor prior calls can change a result, which is exactly what the
  batch-equivalence and scratch-reuse tests lock.
- The hot paths are **allocation-free** by construction: buffers
  are pre-allocated to the graph size, grown only when the graph
  grows, and reset in place per decode.

## Cold path vs hot path (manual 22.1)

- **Cold path**: decoder construction (graph build, weight
  preprocessing, allocation). Reported separately.
- **Hot path**: `decode()` on a pre-built decoder with syndromes
  already in memory. Reported as `decode_hotpath_latency_us` or
  similar.
- Reporting only the hot path is acceptable only for a clearly
  labelled pre-built, repeated-decode workload.

## How the bench server helps

- `qector-research.hot_path_microbench` runs a per-machine hot-path
  latency sample, capped at `QECTOR_MCP_BENCH_MAX_BENCH_SHOTS`
  (default 5000). The result is a per-shot distribution; never a
  portable claim.
- `qector-research.env_block` returns the environment block (manual
  22.3) so a hot-path run carries the required metadata.

## Common pitfalls

- **Single-decode in a Python loop** for millions of shots -> use a
  batch / streaming surface (manual 17). The library 8-tool MCP
  does not expose a batch tool, so the right path is the direct
  wheel `BatchDecoder` (Provisional) or the optional Workbench
  `tools/list`-discovered batch tool.
- **Comparing GPU vs CPU latency** without an artifact -> the
  comparison is per-machine, per-workload, per-build only (manual
  22.5).
- **CUDA + CuPy in one process** -> use separate processes or hide
  the device (manual 20.3).
- **OpenCL on a published wheel** -> not shipped; source build
  only (manual 20.4).
