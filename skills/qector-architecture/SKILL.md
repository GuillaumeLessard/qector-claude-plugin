---
name: qector-architecture
description: >-
  QECTOR architecture overview: the Rust core / Python layer FFI
  boundary, the module map, the threading and memory models, the
  layering of services, and the bit-determinism guarantee. Load
  for any question about the engine's internals, where a class
  lives, how the GIL interacts with the decode call, or why
  batch decode is reproducible across worker counts.
---

# QECTOR Architecture Overview

Source of authority: v1.0.0 reference manual, chapter 26.

## Module map (Table 26.1)

| Area         | Rust modules                                                           | Responsibility                                       |
| ------------ | ---------------------------------------------------------------------- | ---------------------------------------------------- |
| Matching     | `blossom.rs`, `mwpm.rs`, `sparse_blossom.rs`, `fusion_mwpm.rs`          | Exact and near-optimal MWPM                          |
| Union-Find   | `uf_core.rs`, `fast_uf.rs`, `decoder.rs`, `batch.rs`, `cpu_batch.rs`    | Graphlike approximate decoding, single and batch      |
| BP-OSD       | `bp_osd.rs`, `gf2.rs`, `ambig_cluster.rs`                              | Belief propagation and ordered statistics            |
| GPU          | `cuda_*.rs`, `opencl_batch.rs`, `cuda_kernels.cu`                       | Bit-identical batch kernels                          |
| Temporal     | `space_time_decoder.rs`, `streaming.rs`, `sliding_window.rs`           | Multi-round and windowed decoding                    |
| Routing      | `auto_decoder.rs`, `cascade_decoder.rs`, `two_stage_decoder.rs`         | Dispatch, escalation, sector coupling                |
| GNN / ML     | `gnn_*.rs`, `neural_predecoder.rs`, `hybrid_decoder.rs`                 | Learned predecoders and hybrids                      |
| Services     | `mcp_server.rs`, `grpc_server.rs`, `metrics.rs`, `stripe_billing.rs`, `license.rs` | Interfaces, telemetry, licensing                |
| Utilities    | `gf2.rs`, `bitpack.rs`, `core/`, `utils.rs`, `safetensors_loader.rs`    | Shared infrastructure                                |

This is an architecture table; individual module internals are
proprietary and are not reproduced in the manual.

## The FFI boundary (manual 26.2)

- The Rust core is exposed to Python through **PyO3**.
- Arrays cross the boundary as **contiguous uint8 NumPy buffers**.
- The boundary layer repacks only when the input is non-
  contiguous or of the wrong dtype; it never aligns gratuitously.
- **Decode calls release the GIL**, so batched and single-shot
  decodes run concurrently with other Python threads.

## The threading model (manual 26.3)

- Batch paths use **Rayon** data parallelism.
- Each worker keeps its own scratch so results are independent of
  worker count and row-to-worker assignment.
- Single-shot paths use **thread-local reusable buffers**.
- Observable property: **bit-determinism** (the bit-identity
  claim of the GPU path extends to the CPU batch path). Neither
  the worker count nor prior calls can change a result.
- The test that locks this is the cross-decoder equivalence
  layer (manual 23): batch equals per-shot; UF equals FastUF; GPU
  equals CPU.

## The memory model (manual 26.4)

- Hot paths are **allocation-free** by construction: buffers are
  pre-allocated to the graph size, grown only when the graph
  grows, and reset in place per decode.
- The arena and bit-packed tracking structures support this.
- The GPU path allocates per-thread scratch on the device in
  advance and reuses it across batches, growing only to the
  high-water batch size.
- **Peak memory is proportional to the problem size, not to the
  number of shots.**

## The services layering (manual 26.5)

- The service surfaces (MCP, gRPC, REST, metrics) sit on top of
  the same decoder contracts.
- They all dispatch to the same core decoders and apply the same
  faithfulness gate (Theorem 1).
- None of them reimplements decoding; they are thin transport
  layers, which is why the contracts of chapters 4-13 transfer
  to them unchanged.

## The licensing layer (manual 18, 24.2)

- License tiers are enforced in the Rust core.
- `QECTOR_ENFORCE=1` turns tier violations into hard errors;
  without it, violations log a warning.
- The decoder never makes a blocking network call during
  decoding: verification is offline and local.
- The signing key lives only in the fulfillment environment.

## Common pitfalls

- **Crossing the FFI boundary with non-contiguous arrays** -> the
  boundary repacks; small input overhead, no correctness
  change.
- **Holding the GIL during a decode** -> the decode releases the
  GIL, so blocking calls in Python are not blocked by the
  decode.
- **Assuming the worker count changes a result** -> the
  bit-determinism guarantee says it does not.
- **Looking for a class in the wrong submodule** -> the module
  map (Table 26.1) is the index.
- **Assuming the Rust module API is stable** -> it is not; the
  stable surface is the Python class set (manual 16.1) plus the
  documented service surface.

## How the bench server helps

- `qector-research.env_block` returns the environment block
  (manual 22.3) so an architectural artifact carries the
  required metadata.
- `qector-research.hardware_probe` reports the live hardware
  state and license tier.
- `qector-research.code_export_matrices` exports a code's matrices
  in JSON form (useful when tracing data through the FFI
  boundary by hand).
- `qector-research.decode_faithfulness_check` re-verifies
  `H c = s` (mod 2) externally.
