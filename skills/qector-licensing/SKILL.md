---
name: qector-licensing
description: >-
  QECTOR licensing, tier enforcement, and key activation. Covers
  the three license tiers (Community d<=7, Pro d<=19,
  Enterprise d<=63), the Ed25519-signed token formats (QECT-PRO-*,
  QECT-ENT-*, v2), the resolution order
  (QECTOR_LICENSE_KEY, QECTOR_LICENSE_FILE, ~/.qector/license.key),
  the QECTOR_ENFORCE / QECTOR_SILENT / QECTOR_CRL_PATH environment
  variables, the offline verification, and the licensing-gate vs
  hardware-probe distinction. Load for any question about license
  tiers, key activation, tier limits, or what an Enterprise key
  unlocks.
---

# QECTOR Licensing

Source of authority: v1.0.0 reference manual, chapter 18, plus the
license-resolution order and the deploy-time env variables in
section 18.1.

## The three tiers (manual 18.1, Table 18.1)

| Tier        | Max distance | GPU batch | Notes                                 |
| ----------- | ------------ | --------- | ------------------------------------- |
| Community   | d <= 7       | No        | Free, source-available wheel          |
| Pro         | d <= 19      | No        | Ed25519-signed token                  |
| Enterprise  | d <= 63      | Yes       | Ed25519-signed token; GPU / GNN paths |

Tiers are **enforced by the Rust core** at construction and decode
time. Tokens are verified **offline in the Rust core** with
Ed25519, covering the v2 format and the `QECT-PRO-` / `QECT-ENT-`
prefixed formats, with expiry and an offline revocation list.

## Environment variables (manual 18.1)

| Variable                   | Meaning                                                                |
| -------------------------- | ---------------------------------------------------------------------- |
| `QECTOR_LICENSE_KEY`       | Ed25519-signed key (QECT-PRO-*, QECT-ENT-*, v2)                        |
| `QECTOR_LICENSE_FILE`      | Path to a key file; unreadable path is **invalid**, not a silent downgrade |
| `~/.qector/license.key`    | Default key location                                                   |
| `QECTOR_ENFORCE`           | `1` raises `PermissionError` when tier limits are exceeded             |
| `QECTOR_SILENT`            | `1` suppresses the startup banner                                      |
| `QECTOR_CRL_PATH`          | Override path for the revocation list                                  |
| `QECTOR_CUDA_DEVICE_ID`    | CUDA device selection for native batch decoders                         |
| `QECTOR_ENABLE_OPENCL_AUTO`| `1` enables OpenCL auto-routing                                        |
| `QECTOR_BLOSSOM_K_MULT`    | Candidate-neighbour multiplier for sparse MWPM (default `2.0`)         |

**Resolution order** for the key: `QECTOR_LICENSE_KEY`,
`QECTOR_LICENSE_FILE`, `~/.qector/license.key`.

A set-but-unreadable `QECTOR_LICENSE_FILE` is invalid, **not** a
silent Community downgrade. The Python `set_license_key_file(path)`
strips a UTF-8 BOM and trailing newline so a key file written by
PowerShell redirection activates unmodified.

## Hard rules

- The signing key lives only in the fulfillment environment.
- The decoder itself **never** makes a blocking network call during
  decoding.
- `QECTOR_ENFORCE=1` turns tier violations into hard errors;
  without it, exceeding a tier limit logs a warning.
- The licensing gate is **separate from the hardware probe**:
  `cuda_is_available()` reports hardware; the license tier is a
  separate gate.

## How to activate a key (library MCP)

- `qector-library.get_license_info` returns the live tier, customer
  id, max distance, key status, expiry, and enforce mode.
- `qector_decoder_v3.set_license_key(key)` activates a key in
  process. The native verifier rejects invalid keys with
  `ValueError` (rejection used to be swallowed, so an expired /
  revoked / malformed key looked accepted; that path now raises
  explicitly).
- `qector_decoder_v3.set_license_key_file(path)` reads a key file,
  strips the BOM, and activates it.
- `QECTOR_LICENSE` (env var) plus `verify_license_token` checks an
  Ed25519 token. The library also keeps a `_is_license_active()`
  helper.

## How to probe (bench server)

- `qector-research.license_active_check` returns:
  - `license_active` (bool)
  - `tier` (string: Community / Pro / Enterprise)
  - `max_distance` (int)
  - `tier_table` (the documented per-tier limits)
  - the live `info` dict
  - the environment block (manual 22.3)

- `qector-research.hardware_probe` returns `cuda_available`,
  `opencl_available`, `cuda_batch_decoder` (the hardware probe for
  `CUDABatchDecoder.is_available()`), and the live license info.

- `qector-research.env_block` returns the environment block only
  (manual 22.3).

## Tier-enforcement pitfalls

- **Passing `QECTOR_LICENSE_KEY` but not `QECTOR_ENFORCE=1`** ->
  tier limits are warned, not raised. With `QECTOR_ENFORCE=1`,
  the same call raises `PermissionError`.
- **Putting a non-QECTOR-LICENSE_FILE path in `QECTOR_LICENSE_FILE`
  that is unreadable** -> the path is invalid; this is not a
  silent Community downgrade. Activate via `set_license_key_file`
  or `set_license_key` instead.
- **Reusing a key on a different machine** -> the offline verifier
  still validates the Ed25519 signature; expiry and the offline
  revocation list are the only reasons a key can be rejected.
- **Hard-coding tier limits in delivered code** -> the limits live
  in the Rust core and may change in a 1.x release. Always read
  `get_license_info()` at runtime.

## Workbench key (optional, manual 17.5)

The optional Workbench controller exposes
`verify_license_token` for an Ed25519-signed token when the
target runtime ships it. The token is separate from the library
license; consult the target device's `tools/list` response before
calling any Workbench tool name.

## Pricing and commercial use

- The Python layer emits a one-time stderr notice when no license
  is active (skipped under `QECTOR_SILENT=1`, in CI, or in
  interactive REPLs that have already loaded the library).
- Commercial use requires a license:
  `https://qector.store/pricing`.
- A 60-day commercial evaluation is creditable toward any annual
  license.
