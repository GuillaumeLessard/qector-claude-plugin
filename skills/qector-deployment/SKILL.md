---
name: qector-deployment
description: >-
  QECTOR deployment modes, security posture, and the production
  checklist. Covers the six deployment modes (manual 24, Table
  24.1), the production checklist (manual 24.1, 10 items), the
  service hardening rules (10 MB cap, bearer token, strict
  decoder-type enum), the zero-egress policy, the
  package-provenance rule, the SHA-256 checksums-sha256.txt
  rule, and the "service behind TLS and a reverse proxy" rule.
  Load for any question about deploying, hosting, exposing, or
  shipping QECTOR in any non-local context.
---

# QECTOR Deployment and Security

Source of authority: v1.0.0 reference manual, chapter 24.

## The six deployment modes (manual 24, Table 24.1)

| Mode                          | Status                            | Guidance                                  |
| ----------------------------- | --------------------------------- | ----------------------------------------- |
| Local CPU library             | Supported public path             | Preferred for research and evaluation     |
| CUDA / OpenCL batch           | Optional local path               | Controlled driver / runtime setup only    |
| Docker REST server            | Demo / local service path          | Do not expose directly to the public internet |
| gRPC / MCP / metrics          | Optional feature-gated paths      | Experimental unless deployment-reviewed   |
| SaaS / hosted API             | Contact-only beta review          | Separate commercial agreement and hardening |
| OEM / embedded                | Contact-only partner validation    | Hardware / platform scope and support terms |

Network use, hosted API use, OEM integration, internal commercial
use, product integration, paid consulting, and commercial
benchmarking **require a written commercial license**.

## The production checklist (manual 24.1)

Before any customer-facing or network-accessible deployment:

1. **Pin the git commit or release tag** - the deployed build
   must be reproducible from a known source.
2. **Record `Cargo.lock` and dependency versions** - the lockfile
   is the source of truth for the build.
3. **Generate dependency inventories** - SBOM-style output for
   the receiving organization.
4. **Disable unused optional services and GPU features** - every
   enabled service is an attack surface.
5. **Run local test and import smoke validation** - the library
   must import cleanly and the suite must pass on the deployed
   wheel.
6. **Run only the benchmark claims intended to be quoted** - the
   competitive harness is opinionated; the published claim is
   the one the harness produced.
7. **Keep raw JSON / CSV artifacts and SHA-256 hashes** -
   manual 22.3.
8. **Place any service behind TLS and a reverse proxy** - the
   bundled services are not production-hardened.
9. **Restrict logs** so benchmark inputs, customer data, and
   proprietary circuits are not leaked.
10. **Document the operational owner, update path, and rollback
    path** - the receiving organization must know who to call.

## Service hardening (manual 24.3)

The service layers ship with default hardening:

- **REST layer**: 10 MB request cap, per-client rate limit,
  optional bearer-token check.
- **MCP server**: same frame cap, strict decoder-type enum.
- **gRPC path**: payload-shape validation, binary-syndrome
  validation.

These are **necessary but not sufficient**. Before production
use, review:

- authentication (who is the caller)
- authorization (what can the caller do)
- TLS (channel security)
- rate limits (DoS protection)
- timeouts (resource bound)
- audit logs (who did what when)
- resource quotas (per-tenant isolation)

## License enforcement in deployment (manual 18.2, 24.2)

- Tier limits are enforced in the Rust core.
- `QECTOR_ENFORCE=1` turns tier violations into hard errors;
  without it, violations log a warning.
- The decoder never makes a blocking network call during
  decoding: verification is offline and local.
- Activate a key with `set_license_key` /
  `set_license_key_file` (the latter strips a UTF-8 BOM).

## Binary / artifact integrity

- Verify SHA-256 against the release `checksums-sha256.txt` before
  promotion.
- The Rust core is delivered to the build pipeline through a
  chunked, hash-anchored packaging mechanism (12 base64 chunks
  plus a tracked manifest digest). The pipeline verifies the
  manifest against the packed core before building.
- This mechanism is build infrastructure; the chunks and digest
  are not reproduced in the manual.

## Zero-egress policy

- All compute stays local via the MCP server. No `.stim` /
  `.npy` / parity matrices leave the machine.
- The Python streaming layer is local. The decoder is local. The
  MCP server is local.
- Stripe billing (`flush_usage`) is the only exception; it is
  documented and gated by `QECTOR_STRIPE_CUSTOMER_ID` /
  `STRIPE_SECRET_KEY`.

## Feature flags in published wheels (manual 25.3)

- Published wheels are built with the **CUDA feature only**.
- CUDA support ships; OpenCL does not.
- Both backends load their drivers at runtime, so a CUDA-enabled
  wheel still installs and runs on machines without a GPU.
- `cuda_is_available()` simply returns `False` on machines
  without a GPU.
- OpenCL remains a documented source build.

## Common pitfalls

- **Exposing a Docker REST server to the public internet** -> the
  service is demo / local; put it behind TLS and a reverse
  proxy.
- **Skipping the production checklist** -> manual 24.1 lists 10
  items; every one of them is a release blocker.
- **Hard-coding the license tier in deployment scripts** -> the
  tier lives in the active key; read `get_license_info()` at
  runtime.
- **Forgetting `QECTOR_ENFORCE=1`** in production -> without it,
  tier violations log a warning but do not fail.
- **Using a `QECTOR_LICENSE_FILE` path that is unreadable** -> it
  is invalid; activate via `set_license_key_file` instead.

## How the bench server helps

- `qector-research.hardware_probe` returns the live hardware state
  and license tier for the deployment environment.
- `qector-research.license_active_check` reports the offline
  license tier and feature gates.
- `qector-research.env_block` returns the chapter 22.3 environment
  block for the deployment artifact.
- `qector-research.compat_report` (via `qector-library`) returns
  the package version and Provisional-surface boundaries.
- `qector-research.artifacts_sha256` computes the SHA-256 sidecar
  required by the production checklist.
