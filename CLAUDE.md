# QECTOR Claude Code Context

QECTOR is a local, air-gapped quantum-error-correction plugin backed by
`qector-decoder-v3==1.0.1`. The default Claude Code configuration in
`.claude-plugin/plugin.json` and `.mcp.json` exposes only `qector-secure`
(`mcp/mcp_server_secure.py --profile safe`).

## MCP Profiles

- `qector-secure`: 12 tools = the 8 stable tools below + `airgap_status`,
  `integrity_check`, `schema_catalog`, `audit_log_status`. Every request and
  response is validated against JSON Schema 2020-12; `--profile research`
  adds the 29 research tools behind the same control plane.
- `qector-library`: 8 stable decoding, code-building, threshold, license, and
  compatibility tools. Corrections are verified against `H c = s (mod 2)`.
- `qector-research`: 29 opt-in provisional tools for methodology, inspection,
  measured benchmarks, evidence policy, and reproduction references.
- `qector-admin`: 3 opt-in privileged tools. It is disabled until its server
  environment sets `QECTOR_ADMIN_ENABLED=1`; each call also requires
  `confirm=true`.

Claude-facing content is in `commands/`, `agents/`, `skills/`, `prompts/`, and
`hooks/`. The separate Claude Desktop adapter starts in its safe profile.

## Validation

```bash
python scripts/qector_runtime_check.py
python -m unittest discover -s tests -v
python scripts/test_structure.py
python scripts/release_validate.py
python scripts/export_schemas.py --check
python scripts/generate_integrity_manifest.py --check
ruff check .
```

Keep default operations local and air-gapped. The PyPI freshness check is
refused unless `QECTOR_AIR_GAPPED=0`; never add telemetry, network transports
or hardcoded user paths. Regenerate `INTEGRITY.json` and `schemas/` after
touching anything under `mcp/`.

## Security

- Default install exposes only `qector-secure` (12 tools, air-gapped, integrity-checked).
- Research and admin servers are explicit opt-in; see `SECURITY.md` and
  `governance/security_playbook.md`.
- Privileged tools require `QECTOR_ADMIN_ENABLED=1`, `confirm=true`, and
  per-process call budgets documented in `SECURITY.md`.
- Artifact hashing is limited to `QECTOR_ARTIFACT_DIR`; never upload syndromes,
  matrices, or circuits externally.

## Evidence Protocol

Before stating runtime capability, license tier, or benchmark numbers:

1. Call `get_evidence_policy` and `get_runtime_provenance` on
   `qector-research` when that server is enabled; otherwise use live library
   tool results only.
2. Respect MCP envelope `status` values from `mcp/qector_mcp_contract.py`:
   - `verified` — parity or setup checks passed in this process.
   - `reference_only` — manual or lookup content; not a live measurement.
   - `measured` — machine-scoped timing or hardware probe; not portable.
   - `not_checked` / `error` — do not upgrade to a stronger claim.
3. Never invent tool names, decoder classes, or version strings. Confirm with
   `tools/list` or `skills/qector-core/references/qector_verified_api.md`.
4. Route governance questions through `agents/qec-validator.md` before green
   verdicts on reproducibility or security posture.
