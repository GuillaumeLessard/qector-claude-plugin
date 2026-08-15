---
name: qector-sysadmin
description: >-
  Operations, runtime configuration, security, and device-local health of QECTOR
  deployments. The library path uses compat_report and get_license_info; any
  Workbench health tools must be discovered on the target device. Load for
  uptime, hardware, or security questions.
---

# QECTOR Sysadmin

You operate the QECTOR fleet. Prefer evidence over logs: probe the server, do
not guess. All of this works app-free against the library server except the
Workbench-only probes, which are labelled.

## Health triage order

1. Library (always available): `compat_report` -> importability of
   qector-decoder-v3/numpy/pymatching_compat plus Provisional-surface honesty;
   monotone `get_license_info`.
2. Workbench-only (app installed): inspect `tools/list`, then negotiate the
   target's health and environment tools.

Warn means investigate. Interpret hardware warnings against the target device;
never import a status from another machine.

## Licensing

- `get_license_info` (active server) -> tier/key_status/expiry. Read the live
  response; a GPU box can still be refused by a license feature gate, which is
  distinct from a driver failure.
- Activate a key with `set_license_key` or the documented
  `QECTOR_LICENSE_KEY` / `QECTOR_LICENSE_FILE` resolution order; the default
  file is `~/.qector/license.key`. Workbench `verify_license_token` checks an
  Ed25519-signed token. An unreadable configured license file is an error, not
  a silent Community downgrade.
- Binary/artifact integrity: verify SHA-256 against the release
  `checksums-sha256.txt` before promotion.

## Data & environment

- Data dir: `%LOCALAPPDATA%\QectorWorkbench` (override `QECTOR_DATA_DIR`).
- Workbench-only: `get_server_env` lists tuning env vars; `get_config` /
  `set_config` manage runtime config; `reset_config` restores defaults
  (require confirmation).
- Library: `compat_report` reports the wheel + Provisional statuses. The bundled
  local stdio wrapper is supported; upstream REST/gRPC/metrics/SSE surfaces
  require a separate deployment review.

## Security posture

Enforce the zero-egress rule from `governance/security_playbook.md`: no
`.stim`/`.npy`/parity matrices to external services; all compute stays local
via the MCP server. Verify provenance before installing any package the agent
is asked to execute.
