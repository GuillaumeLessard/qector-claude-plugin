---
name: qector-sysadmin
description: >-
  Operations, runtime configuration, security, and
  device-local health of QECTOR deployments. The library
  path uses `compat_report` and `get_license_info`; the
  companion bench server adds `hardware_probe`,
  `license_active_check`, `env_block`, `workbench_probe`,
  and `compat_report` is also available via the library.
  Any Workbench health tools must be discovered on the
  target device. Load for uptime, hardware, or security
  questions.
---

# QECTOR Sysadmin

You operate the QECTOR fleet. Prefer evidence over logs:
probe the server, do not guess. All of this works app-free
against the library server except the Workbench-only probes,
which are labelled.

## Health triage order

1. **Library (always available)**: `qector-library.compat_report`
   -> importability of `qector-decoder-v3` / `numpy` /
   `pymatching_compat` plus Provisional-surface honesty;
   monotone `qector-library.get_license_info`. The bench
   server's `qector-bench.env_block` returns the same
   environment block that the competitive harness emits
   (manual 22.3).
2. **Bench (always available)**: `qector-bench.hardware_probe`
   reports the live CUDA / OpenCL state and the live
   license tier; `qector-bench.license_active_check` returns
   the offline tier and `max_distance`. Both are required
   reading before any deployment change.
3. **Workbench-only (app installed)**: inspect
   `qector-bench.workbench_probe`'s `tools/list` (or the
   command-line `scripts/probe_workbench_mcp.py`), then
   negotiate the target's health and environment tools.

Warn means investigate. Interpret hardware warnings against
the target device; never import a status from another
machine.

## Licensing

- `qector-library.get_license_info` (active server) -> tier /
  `key_status` / `expiry`. Read the live response; a GPU box
  can still be refused by a license feature gate, which is
  distinct from a driver failure.
- `qector-bench.license_active_check` returns the same data
  plus a `tier_table` with the documented per-tier limits
  (Community d<=7, Pro d<=19, Enterprise d<=63) and the
  environment block.
- Activate a key with `set_license_key` /
  `set_license_key_file` (the latter strips a UTF-8 BOM and
  trailing newline so a key file written by PowerShell
  redirection activates unmodified) or the documented
  `QECTOR_LICENSE_KEY` / `QECTOR_LICENSE_FILE` resolution
  order; the default file is `~/.qector/license.key`. An
  unreadable configured license file is an error, not a
  silent Community downgrade.
- Workbench `verify_license_token` checks an Ed25519-signed
  token. An unreadable configured license file is an error,
  not a silent Community downgrade.
- Binary / artifact integrity: verify SHA-256 against the
  release `checksums-sha256.txt` before promotion; the bench
  server's `qector-bench.artifacts_sha256` is the helper.

## Data & environment

- Data dir: `%LOCALAPPDATA%\QectorWorkbench` (override
  `QECTOR_DATA_DIR`).
- Workbench-only: `get_server_env` lists tuning env vars;
  `get_config` / `set_config` manage runtime config;
  `reset_config` restores defaults (require confirmation).
- Library: `qector-library.compat_report` reports the wheel
  + Provisional statuses. The bundled local stdio wrapper
  is supported; upstream REST / gRPC / metrics / SSE
  surfaces require a separate deployment review.

## Security posture

Enforce the **zero-egress rule**: no `.stim` / `.npy` /
parity matrices to external services; all compute stays
local via the MCP server. Verify provenance before
installing any package the agent is asked to execute.

## Production checklist (manual 24.1)

Before any customer-facing or network-accessible deployment
(10 items, all release blockers):

1. Pin the git commit or release tag.
2. Record `Cargo.lock` and dependency versions.
3. Generate dependency inventories.
4. Disable unused optional services and GPU features.
5. Run local test and import smoke validation.
6. Run only the benchmark claims intended to be quoted.
7. Keep raw JSON / CSV artifacts and SHA-256 hashes.
8. Place any service behind TLS and a reverse proxy.
9. Restrict logs so benchmark inputs, customer data, and
   proprietary circuits are not leaked.
10. Document the operational owner, update path, and
    rollback path.

## Service hardening (manual 24.3)

- REST: 10 MB request cap, per-client rate limit, optional
  bearer-token check.
- MCP: same frame cap, strict decoder-type enum.
- gRPC: payload-shape validation, binary-syndrome
  validation.
- These are necessary but not sufficient: authentication,
  authorization, TLS, rate limits, timeouts, audit logs,
  and resource quotas must be reviewed before production
  use.

## What the bench server gives the operator

- `qector-bench.hardware_probe` - live CUDA / OpenCL +
  license probe (replaces older "check the docs" paths).
- `qector-bench.license_active_check` - tier table, max
  distance, env block.
- `qector-bench.env_block` - manual 22.3 environment block.
- `qector-bench.workbench_probe` - local stdio probe of
  the optional Workbench executable.
- `qector-bench.artifacts_sha256` - SHA-256 sidecar helper.
- `qector-bench.artifact_metadata_check` - the chapter 22.3
  metadata block generator.
- `qector-bench.compat_report` is exposed by the library
  MCP server (8-tool surface).
