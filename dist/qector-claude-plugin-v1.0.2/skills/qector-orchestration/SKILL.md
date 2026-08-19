---
name: qector-orchestration
description: >-
  Routing, dispatch, and orchestration in QECTOR (manual chapter 11).
  Covers the structural validity predicate (max qubit degree), the
  recommend_decoder policy, Theorem 14 (AutoDecoder dispatch
  faithfulness), the 7-tier self-debugging fallback chain (native
  auto, CUDA, OpenCL, Rayon batch, CPU batch, single-thread,
  Blossom, lookup table, BP-OSD), the syndrome-verification
  between tiers, the GPU-permanent-disable rule, and the hybrid
  cascade pre-filter (UF + exact fallback). Load for any question
  about which decoder to choose, why a particular backend was
  picked, or how the fallback chain works.
---

# QECTOR Orchestration

Source of authority: v1.0.0 reference manual, chapter 11.

## The two questions

The routing layer answers two questions:

1. **Validity**: which decoder family is valid for a problem?
2. **Execution**: which execution backend should run it?

The validity answer is **structural**: a problem with any qubit of
degree > 2 is non-graphlike, so matching decoders are not eligible
and BP-OSD is forced regardless of how the problem was labelled.

## The recommend_decoder policy (manual 11.1)

Inputs: `(code family, distance, qubit count, batch size,
priority)`. Output: a decoder name.

For graphlike problems:

- **accuracy priority** -> exact `Blossom` for small / moderate
  codes, region-growing `SparseBlossom` for large ones.
- **speed priority** -> `FastUnionFind` (or the GPU batch path for
  huge batches).
- **balanced priority** -> interpolate by batch size and code size.

For non-graphlike problems: always route to `BPOSDDecoder`.

## Theorem 14 (dispatch faithfulness, manual 11.1)

> Let `Auto(s) = D_{k(s)}(s)` be the dispatch of syndrome `s` to
> the decoder selected by the policy `k(s)`. If every backend `D_i`
> is syndrome-faithful for the problems it is eligible to decode,
> and the policy only selects eligible backends, then `Auto(s)`
> satisfies `H c = s` whenever any eligible backend can satisfy
> it.

The dispatch selects `k(s)` among eligible backends; no syndrome
alteration occurs before dispatch; by hypothesis the selected
backend returns `c` with `H c = s`. The eligibility predicate is
structural (max qubit degree), so the guarantee does not depend on
labels.

## The AutoDecoder fallback chain (manual 11.2)

The Python `AutoDecoder` adds a **seven-tier self-debugging
fallback chain** with syndrome verification after every tier:

1. native auto
2. CUDA
3. OpenCL
4. Rayon batch
5. CPU batch
6. single-thread
7. Blossom
8. lookup table

If every tier fails verification, the controller falls back to
**BP-OSD** (the only decoder defined for arbitrary GF(2)
matrices), and, as a documented last resort, returns a zero
correction.

GPU backends are **permanently disabled** after failure; CPU
backends are **retried**, since their failures are more likely
transient.

## The hybrid cascade (manual 11.3)

`HybridCascadeDecoder` runs `FastUnionFind` as a pre-filter and
escalates to `Blossom` (or `BP-OSD` with a wall-clock deadline)
when the pre-filter's correction fails the parity check or exceeds
a weight budget. The acceptance criterion is

    H c_UF = s (mod 2)  AND  |c_UF| <= W_budget

Because the escalation is exact and the pre-filter is faithful,
the cascade preserves faithfulness; its accuracy and throughput
statements are workload-specific and are **not** claimed here
without a surviving artifact.

## The Rust native_auto primitive

The Rust class is `NativeAutoDecoder` (manual 16.1); the Python
`AutoDecoder` is the 7-tier controller (manual 11.2). The naming
distinction matters:

- `NativeAutoDecoder` is the routing primitive; it enforces the
  license tier at construction time.
- `AutoDecoder` is the 7-tier self-debugging controller imported
  from the Python `backend` module.

A class is also bound as `SpaceTimeDecoder` (manual 16.2 - this
binding was added in 1.0.0 to fix a missing re-export).

## What the engine does not do

- **No hand-picked decoder per workload** -> the policy is the
  single source of dispatch truth.
- **No "always fastest" claims** -> Theorem 14 guarantees
  faithfulness, not speed.
- **No automatic tier escalation at construction** -> tier limits
  are enforced by the Rust core (manual 18).

## How the bench server helps

- `qector-bench.code_family_info` reports `max_qubit_degree`,
  `is_matching_graph`, and a routing hint.
- `qector-bench.hardware_probe` returns the live license tier,
  CUDA / OpenCL availability, and environment block.
- `qector-bench.license_active_check` reports the offline license
  tier and feature gates (manual 18.1).
- `qector-bench.decode_faithfulness_check` re-verifies
  `H c = s` for any decoder output.
