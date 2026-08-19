---
name: qector-release-engineering
description: >-
  QECTOR release engineering, wheel-only distribution, the
  chunked base64 Rust-core delivery, feature flags in published
  wheels, the pre-flight gates, and the v2 token format. Load
  for any question about packaging, building, releasing, the
  RUST_SRC_B64_* secrets bundle, the promotion of a Provisional
  symbol to stable, or the qector.store / PyPI flow.
---

# QECTOR Release Engineering

Source of authority: v1.0.0 reference manual, chapter 25; the
release procedure in `docs/RELEASING.md`; the
`docs/API_STABILITY.md` promotion policy.

## Wheels only (manual 25.1)

- The package publishes **deterministic binary wheels only**.
- **No source distribution is published**, by design: the
  proprietary Rust core is not tracked as source, and an sdist
  cannot be rebuilt.
- `pip install` must resolve to a wheel on every supported
  platform.
- The release procedure lives in `docs/RELEASING.md`.

## The core delivery path (manual 25.2)

The Rust core is delivered to the build pipeline through a
**chunked, hash-anchored packaging mechanism**:

- 12 base64 chunks
- a tracked manifest digest
- the pipeline verifies the manifest against the packed core
  before building, so a stale or corrupted core fails the build
  explicitly rather than silently shipping older source

This mechanism is build infrastructure; the chunks and digest are
not reproduced in the manual.

## Feature flags in published wheels (manual 25.3)

- Published wheels are built with the **CUDA feature only**.
- CUDA support ships; OpenCL does not.
- Both backends load their drivers at runtime, so a CUDA-enabled
  wheel still installs and runs on machines without a GPU.
- `cuda_is_available()` returns `False` on machines without a
  GPU.
- OpenCL remains a documented source build.

## Pre-flight gates (manual 25.4, Table 25.1)

| Gate                          | Purpose                                            |
| ----------------------------- | -------------------------------------------------- |
| `cargo test` (no-default and full features) | Core unit tests in both configurations    |
| `cargo clippy -D warnings`    | Lint gate in both configurations                   |
| `ruff check` / `ruff format`  | Python lint and formatting                         |
| `pytest` via the dev wrapper  | Python suite with the license token that unlocks GPU paths |
| Wheel smoke test              | Install a built wheel, decode, and assert `H c = s`|
| Dependency audit              | Blocking on release tags; advisory-only otherwise  |

## Promotion of a Provisional symbol to stable (manual 27.1)

A provisional symbol may be promoted to stable only after:

1. A dated promotion entry in `docs/API_STABILITY.md` naming the
   surface and the review.
2. The same test bar as stable symbols (a property test, a
   regression test, and an example).
3. A move between the corresponding sections of
   `docs/STABLE_API.md`.
4. A changelog note.

As of the v1.0.0 manual, the promotion log is empty: no
experimental surface has been promoted. Any future promotion must
clear the bar above.

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

The following candidate items are recorded in the source tree as
future work:

- Sharing the CUDA primary context between the native and CuPy
  paths (the documented dual-context workaround is separate
  processes).
- An OpenCL side-wheel or OpenCL leg in the release pipeline
  (deferred unless demand materializes).
- Continued hard-rejection testing for hypergraph inputs on the
  Union-Find family.

These items are explicitly candidates; their status may change
in any 1.x release.

## The license token formats

- **v2 format** - the generic Ed25519-signed token format.
- **`QECT-PRO-*` prefix** - Pro tier token.
- **`QECT-ENT-*` prefix** - Enterprise tier token.

The offline verifier accepts all three. `QECTOR_LICENSE_KEY` or
`QECTOR_LICENSE_FILE` resolves to one of them.

## SHA-256 sidecar

Every evidence artifact carries a `*.sha256` sidecar:

```
<sha256_hex>  <filename>
```

The format is the standard `sha256sum` format, so `sha256sum -c`
verifies the artifact on any POSIX system. PowerShell
verification uses `Get-FileHash -Algorithm SHA256`.

## Common pitfalls

- **Publishing a wheel without the SHA-256 sidecar** -> manual
  22.3 requires the sidecar; an artifact without it is a smoke
  test, not public evidence.
- **Skipping a pre-flight gate on a release tag** -> the gate is
  blocking; do not bypass.
- **Promoting a provisional symbol without the four-step bar** ->
  manual 27.1 is normative.
- **Comparing a new wheel against a withdrawn benchmark** -> the
  withdrawn benchmark policy is in manual 19 / 21.

## How the bench server helps

- `qector-bench.artifact_metadata_check` generates the
  chapter 22.3 metadata block.
- `qector-bench.artifacts_sha256` computes the SHA-256 sidecar.
- `qector-bench.env_block` returns the chapter 22.3 environment
  block.
- `qector-bench.compat_report` (via `qector-library`) returns
  the package version.
