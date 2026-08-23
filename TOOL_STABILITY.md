# Tool Stability

## Stable: `qector-library`

The 8 default tools are the public, compatibility-oriented surface:
`list_code_families`, `list_decoders`, `get_license_info`, `decode_syndrome`,
`decode_single`, `threshold_sweep`, `build_code_from_matrix`, and
`compat_report`.

## Provisional: `qector-research`

The 29 research tools may evolve independently of the stable surface. They
provide methodology, DEM/circuit inspection, code introspection, optional
ecosystem checks, machine-scoped measurement, reference lookup, artifact
integrity helpers, and a self-describing evidence layer
(`get_capability_matrix` / `get_evidence_policy` /
`get_runtime_provenance`). Enable this server only for a research workflow.

## Administrative: `qector-admin`

The 3 admin tools are intentionally not part of normal agent workflows. They
require explicit server enablement plus per-call confirmation. Administrative
availability never implies a capability is present, licensed, or safe to run
without local review.
