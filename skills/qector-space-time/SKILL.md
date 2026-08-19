---
name: qector-space-time
description: >-
  Space-time and streaming decoding for QECTOR. Covers the (2+1)D
  detector lattice, the detector-difference formulation
  d_{c,t} = s_{c,t} xor s_{c,t-1}, the space-time lifting theorem
  (manual 10.2), the streaming primitives (OR-accumulated history,
  exponentially decayed window), the truncation bound
  ||S_W - S_inf||_1 <= lambda^W / (1 - lambda) * ||s||_inf, and the
  Python layer's "decode per round" scope (manual 10.3). Load for
  any question about measurement errors, glitch absorption, multi-
  round decoding, or windowed commit latency.
---

# QECTOR Space-Time and Streaming

Source of authority: v1.0.0 reference manual, chapter 10.

## Why space-time

Physical measurements are noisy, so a detector event must be
attributable either to a data fault or to a measurement fault. The
space-time approach builds a `(2+1)`-dimensional detector lattice
over `T` rounds and solves a single matching problem on it, with
anisotropic edge weights.

## Detector formulation (manual 10.1)

    d_{c,t} = s_{c,t} xor s_{c,t-1}

- A data error in round `t` flips the same checks in round `t` and
  `t+1`, producing two detection events in consecutive layers.
- A measurement error flips one detector in a single layer.

The lifted matrix `H_ST` contains data columns and measurement
columns, with:

- **Spatial weights** derived from the data-error probability.
- **Temporal weights** derived from the measurement-error
  probability.

## Theorem 13 (space-time lifting faithfulness, manual 10.2)

> Let `H_ST` be the lifted parity-check matrix with data and
> measurement columns. A correction `c_ST` whose boundary in the
> detector graph equals `d` satisfies `H_ST c_ST = d (mod 2)`;
> projecting the measurement columns away yields a spatial
> correction whose syndrome differs from the final raw round only
> by the final-round measurement error term.

The proof sketch: the lifted matrix is a chain complex whose
boundary operator applies the spatial syndrome to each time layer
and the difference operator across layers. Any matching whose paths
pair the defects of `d` reproduces `d` by Theorem 3, with temporal
degree cancellation handled by the boundary term of time-like
paths. The projection statement follows from the telescope identity
`XOR_r d_{c,r} = s_{c,T}` over raw rounds, leaving the
measurement-boundary term.

## Validation patterns (manual 10.2)

The `SpaceTimeDecoder` is validated against two failure modes:

- A lone measurement glitch that reverts on the next round must be
  absorbed as two time-like edges and must not corrupt the spatial
  correction.
- A persistent data error must not trigger the single-round
  fallback.

Both are locked by regression tests.

## Worked example (manual 10.4)

Take a ring of 8 checks over 6 rounds. Rounds 1-2 clean, round 3
reports a single spurious flip at check 2, round 4 is clean again.
XOR differencing produces two detection events (appearance and
disappearance) paired by a temporal edge: the **spatial correction
is empty, as it must be - no data error was ever present**.

This is the regression locked by the space-time tests.

## The streaming layer (manual 10.3, 20.5)

- **Compiled core**: `StreamingDecoder` (OR-accumulated history)
  and `SlidingWindowDecoder` (exponentially decayed window).
- **Higher-level Python layer**: decodes each round independently.
  It explicitly does **not** claim full circuit-level space-time
  matching; its window controls commit latency, batching, and
  telemetry. For stateless inner decoders the per-round result is
  window-invariant.

### Truncation bound (manual 10.3)

For the decayed window with decay factor `lambda` in `[0, 1)`:

    || S_W - S_inf ||_1  <=  lambda^W / (1 - lambda) * || s ||_inf

by the geometric tail series. The excess logical-error implication
is qualitative (`O(lambda^W)`); no numerical fidelity loss is
claimed without a surviving artifact.

## Scoping rules

- The Python streaming layer and the Rust streaming primitives
  decode per-round or windowed syndromes; they do **not** implement
  full circuit-level space-time matching unless the 3D
  `SpaceTimeDecoder` is used (manual 20.5).
- The sliding-window decoder is a simulation workflow, **not**
  hardware control (manual 4, Table 4.1).

## Common pitfalls

- **Using the Python streaming layer for full space-time
  matching** -> it is per-round by design; route to
  `SpaceTimeDecoder` for (2+1)D.
- **Picking `lambda` close to 1** -> the truncation bound explodes;
  a value of `0.95` over `W = 100` rounds leaves a tail of order
  `0.95^100 / 0.05 ~ 5.9e-3 * ||s||_inf`.
- **Claiming "streaming beats single-shot" without an artifact** ->
  per-machine, per-workload only (manual 22.5).

## How the bench server helps

- `qector-bench.env_block` returns the chapter 22.3 environment
  block for the space-time artifact.
- `qector-bench.artifact_metadata_check` generates the metadata
  block (decoder class, mode, weight scheme) for a space-time run.
- `qector-bench.decode_faithfulness_check` re-verifies
  `H c = s` on the spatial projection of the lifted correction.
- `qector-bench.hot_path_microbench` produces a per-machine
  latency sample (always per-machine, never portable).
