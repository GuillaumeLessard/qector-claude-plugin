# Tool Stability

## Stable (8) — in `qector-secure` and `qector-library`

`list_code_families`, `list_decoders`, `get_license_info`, `decode_syndrome`,
`decode_single`, `threshold_sweep`, `build_code_from_matrix`, `compat_report`.
Their input schemas and result schemas (`schemas/<tool>.*.schema.json`) are
the compatibility contract; fields are added, never removed, within 2.x.

## Control plane (4) — `qector-secure` only

`airgap_status`, `integrity_check`, `schema_catalog`, `audit_log_status`.
Read-only; their shape is part of the stable contract.

## Provisional (29) — `qector-research` and `qector-secure --profile research`

Methodology, DEM/circuit inspection, code introspection, optional ecosystem
checks, machine-scoped measurement, reference lookup, artifact integrity
helpers and the evidence layer (`get_capability_matrix`,
`get_evidence_policy`, `get_runtime_provenance`). They may evolve between
minor versions; their output schemas type the top-level keys and leave
wheel-mirroring blocks open. In the secure research profile the research
`compat_report` is named `research_compat_report`.

## Administrative (3) — `qector-admin` only

`system_setup`, `configure_claude_desktop`, `workbench_probe`. Require server
enablement plus per-call confirmation. Administrative availability never
implies a capability is present, licensed, or safe to run without local
review.
