# MCP API contract (2.0)

Every QECTOR tool advertises a JSON Schema 2020-12 `inputSchema`, a
tool-specific `outputSchema`, and MCP behavioural annotations. The server
validates arguments against the input schema **before** any decoder code
runs and validates the finished envelope against the output schema
**before** it is written to the client. Tool lists are sorted and
deterministic across processes, SDK generations and Python versions.

The committed copies of every schema live in [`schemas/`](schemas/)
(`<tool>.input.schema.json`, `<tool>.output.schema.json`,
`envelope.schema.json`, `audit-record.schema.json`, `index.json` with
SHA-256 digests). `scripts/export_schemas.py --check` fails CI when they
drift from the code; the `schema_catalog` tool returns the same content
live.

## Envelope

Every response, success or error, is one `QECTORToolResult` object carried
both as `structuredContent` and as canonical JSON text in `content[0]`:

```json
{
  "contract_version": "2.0",
  "tool": "decode_syndrome",
  "status": "verified | reference_only | measured | not_checked | error",
  "claim_class": "runtime_verified | verification_failed | reference_only | machine_scoped_measurement | metadata_or_unverified | none",
  "provenance": {"server": "qector-secure-mcp", "server_version": "2.0.1", "reference_manual": "10.5281/zenodo.21941046", "mcp_sdk": "1.30.0", "contract_sha256": "..."},
  "runtime": {"qector_decoder_v3": "1.0.0", "elapsed_ms": 0.9},
  "scope": {"tool": "decode_syndrome", "stability": "stable", "network": "local_only", "performance_claim": "none"},
  "verification": {"status": "verified", "checks": ["runtime_contract", "theorem_1_syndrome_faithfulness"]},
  "artifact": null,
  "warnings": [],
  "audit": {"sequence": 17, "record_sha256": "..."},
  "result": { "...tool specific, see schemas/<tool>.output.schema.json..." }
}
```

`audit` is present only when the hash-chained audit log is enabled.
`result` is `{}` for an error raised before a result existed (invalid input,
budget, backend failure). When a tool's own in-process check fails
(`integrity_check` on a modified tree, a decode whose correction fails the
parity gate), `status` is `error`, `error.code` is `INTEGRITY_FAILED` or
`VERIFICATION_FAILED`, and `result` keeps the diagnostic payload. A check
tool that answers a question (`decode_faithfulness_check`) returns
`verified` with the answer in `result.syndrome_valid`; a `false` answer is a
verified result, not a tool failure.

### Status semantics

| `status` | Meaning | Never means |
|:---------|:--------|:------------|
| `verified` | the parity gate `H c = s (mod 2)` (and Theorem 2 scoring when logicals exist) ran in this process and passed | a performance claim |
| `measured` | a per-machine, per-build measurement (`threshold_sweep`, `hot_path_microbench`, `hardware_probe`) | a portable number |
| `reference_only` | text looked up from the bundled reference manual | a runtime capability |
| `not_checked` | metadata, inventory or utility output | verification |
| `error` | stable error code in `error.code` | partial success |

### Error codes (closed set)

`INVALID_INPUT` (with `error.path` as a JSON path), `UNKNOWN_TOOL`,
`RESOURCE_LIMIT`, `LICENSE_DENIED`, `BACKEND_UNAVAILABLE`,
`DEPENDENCY_MISSING`, `VERIFICATION_FAILED`, `CONTRACT_VIOLATION`,
`INTEGRITY_FAILED`, `IO_ERROR`, `NETWORK_DISABLED`, `NETWORK_REQUIRED`,
`PERMISSION_DENIED`, `PROTOCOL_ERROR`, `RUNTIME_ERROR`.

Errors are derived from exception classes first (`QECTORSchemaError →
INVALID_INPUT`, `QECTORNetworkDisabledError → NETWORK_DISABLED`,
`QECTORContractViolation → CONTRACT_VIOLATION`, `PermissionError →
PERMISSION_DENIED`, `ImportError → DEPENDENCY_MISSING`, ...), then from
message heuristics. Messages redact the home directory and are capped.

## Servers and tools

### `qector-secure` (default) — safe profile, 12 tools

| Tool | Status | Inputs | Notes |
|:-----|:-------|:-------|:------|
| `list_code_families` | not_checked | — | per-family `health` probe: `ok`, `unscored`, `weak`, `degenerate`, `unavailable`; `effective_distance` computed exactly for graphlike codes (shortest odd-parity cycle of the matching graph) or bounded otherwise, never the wheel's label; `source` is `wheel` or `plugin` (`rotated_surface_corrected` is built by `mcp/qector_codes.py` and verified at construction) |
| `list_decoders` | not_checked | — | `graphlike_only` flag per decoder |
| `get_license_info` | not_checked | — | live offline licence; no network |
| `decode_syndrome` | verified | `family`, `size`, `syndrome` (required), `decoder_name`, `n_qubits` | refuses degenerate families, warns on weak ones |
| `decode_single` | verified | `family`, `distance`, `decoder_name`, `error_rate`, `seed` | `logical_failure` null when no logicals; `effective_distance` of the code actually decoded |
| `threshold_sweep` | measured | `family`, `distances`, `error_rates`, `trials`, `seed`, `decoder_name`, `artifact_path` | Wilson 95 %, hashed artifact inside the artifact root; every row carries `effective_distance`; refused with `RESOURCE_LIMIT` past a wall-clock budget (`QECTOR_MCP_MAX_SWEEP_SECONDS`, default 120) |
| `build_code_from_matrix` | not_checked | `H_matrix` (required), `family`, `distance` | GF(2) rank, graphlike flag; constructs, verifies nothing |
| `compat_report` | not_checked | `check_pypi` | includes `network_policy`, Python and SDK windows |
| `airgap_status` | not_checked | — | live guards and the wheel's native network surface |
| `integrity_check` | verified / error | — | SHA-256 of runtime files vs `INTEGRITY.json` |
| `schema_catalog` | not_checked | — | every schema with digests |
| `audit_log_status` | not_checked | — | chain state |

### `qector-secure --profile research` — 41 tools

Adds the 29 research tools. The research `compat_report` is exposed as
`research_compat_report` to avoid a name clash.

### Standalone servers

`qector-library` (8), `qector-research` (29) and `qector-admin` (3) remain
available for embedded or legacy use and share the same contract,
validation and air-gap behaviour. The admin server is the only one allowed
to launch processes and requires `QECTOR_ADMIN_ENABLED=1` plus
`confirm=true`; its `system_setup` accepts `offline_wheelhouse` and refuses
online pip in air-gapped mode.

## Network policy in results

Tools that accept `check_pypi` embed:

```json
"network_policy": {"air_gapped": true, "python_socket_guard": true, "subprocess_guard": true, "env_scrubbed": true, "transport": "stdio", "note": "..."},
"pypi_freshness": {"status": "disabled", "reason": "air-gapped mode (QECTOR_AIR_GAPPED=1, default) refuses the PyPI freshness check"}
```

and `scope.network` reads `disabled_air_gapped`. With
`QECTOR_AIR_GAPPED=0` the single GET to
`https://pypi.org/pypi/qector-decoder-v3/json` is made once per process and
`scope.network` reads `opt_in_pypi_freshness`.

## SDK generations

The servers run unmodified on `mcp>=1.30,<2` and `mcp>=2,<3` through
`mcp/qector_mcp_compat.py`, which constructs every model with wire
(camelCase) names and adapts the low-level `Server` registration API.
Wire output is identical on both generations; `provenance.mcp_sdk` records
which one served the call.
