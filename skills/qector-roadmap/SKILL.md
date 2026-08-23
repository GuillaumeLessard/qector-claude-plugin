---
name: qector-roadmap
description: >-
  QECTOR roadmap and promotion path (manual 27). Covers the
  four-step Provisional-to-stable promotion bar, the artifact
  roadmap, the candidate engineering items (CUDA primary
  context sharing, OpenCL side-wheel, hypergraph rejection
  testing), and the 1.x release policy. Load for any question
  about what is coming, what is a candidate, and when a
  Provisional symbol can be promoted.
---

# QECTOR Roadmap and Promotion Path

Source of authority: v1.0.0 reference manual, chapter 27.

## From provisional to stable (manual 27.1)

A provisional symbol may be promoted to stable only after:

1. **A dated promotion entry** in `docs/API_STABILITY.md` naming
   the surface and the review.
2. **The same test bar as stable symbols**: a property test, a
   regression test, and an example.
3. **A move** between the corresponding sections of
   `docs/STABLE_API.md`.
4. **A changelog note**.

As of the v1.0.0 manual, **the promotion log is empty**: no
experimental surface has been promoted. Any future promotion
must clear the four-step bar.

## The stable and provisional surfaces (manual 16)

### Stable (manual 16.1)

- `UnionFindDecoder`, `FastUnionFindDecoder`, `BlossomDecoder`,
  `SparseBlossomDecoder`, `NativeAutoDecoder`
- `generate_repetition_code_checks`, `generate_ring_code_checks`,
  `generate_surface_code_checks` (legacy toric-weight-4)
- `set_license_key` / `get_license_info`
- `record_shots` / `get_accumulated_shots`
- `DecodeResult` structured result

### Provisional (manual 16.2)

- `CPUBatchDecoder` / `BatchDecoder` (batch shape stable;
  performance workload-sensitive)
- `AutoDecoder` (7-tier ordering is behaviour, not contract)
- `StreamingDecoder` / `SlidingWindowDecoder` (constructor and
  commit API stable)
- `BpOsdDecoder` tuning kwargs (names stable; defaults may shift
  in 1.x)
- `CUDABatchDecoder` / `OpenCLBatchDecoder` / `CUDABpOsdDecoder`
  (bit-identity tested; performance not claimed)
- Network surfaces: REST, gRPC, MCP, metrics (Provisional;
  deployment review required)

## Artifact roadmap (manual 27.2)

The public artifact corpus is intended to grow toward:

- CI-run evidence.
- Cross-platform benchmark reports.
- SBOM-style dependency inventories.
- Prebuilt CPU-safe wheels.

Each artifact class carries an explicit claim boundary:
checked-in JSON is **evidence snapshots for the recorded
environment**, not universal proof.

## Candidate engineering items (manual 27.3)

The following candidate items are recorded in the source tree
as future work:

- **Sharing the CUDA primary context** between the native and
  CuPy paths. The documented dual-context workaround is
  separate processes (manual 20.3).
- **An OpenCL side-wheel or OpenCL leg in the release pipeline**.
  Deferred unless demand materializes; published wheels are
  CUDA-only by design (manual 20.4).
- **Continued hard-rejection testing** for hypergraph inputs on
  the Union-Find family (manual 20.8).

These items are explicitly candidates; their status may change
in any 1.x release.

## The candidate workbench controller

- `qector_decoder_v3.workbench` is a headless application
  controller (benchmark job queue, JSON/CSV/PDF export).
- Its docstring references a `run-qector` skill that is not part
  of this package.
- It is real historical code (changelog 0.7.0 -> 1.0.0) but is
  absent from the shipped wheel (manual 17.5).

## What the roadmap does **not** promise

The roadmap is **policy text**, not a promise of results (manual
27). Items in the candidate list may not ship. Items not in the
candidate list may ship.

Any claim about "what's coming in 1.x" is out of scope of the
v1.0.0 manual. The reference manual is the source of authority
for what exists today; the roadmap is the source of authority
for what is a candidate.

## How the bench server helps

- `qector-research.compat_report` (via `qector-library`) returns
  the live package version and the Provisional-surface
  boundaries.
- `qector-research.env_block` returns the chapter 22.3 environment
  block for a roadmap artifact.
- `qector-research.artifact_metadata_check` generates the
  chapter 22.3 metadata block.
- `qector-research.license_active_check` reports the offline
  license tier; the candidate items do not unlock new tier
  features beyond the three documented tiers.
