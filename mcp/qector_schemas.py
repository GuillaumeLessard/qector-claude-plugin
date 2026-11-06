"""Per-tool JSON Schema (draft 2020-12) result contracts for QECTOR tools.

Every QECTOR tool advertises an ``outputSchema`` built from the shared
``QECTORToolResult`` envelope with the ``result`` property replaced by the
tool-specific schema defined here. The secure server validates every
outgoing envelope against that schema before it is written to the client;
a mismatch is reported as a ``CONTRACT_VIOLATION`` error instead of being
silently forwarded.

The schemas are plain dictionaries so they can be exported to
``schemas/*.schema.json`` (``scripts/export_schemas.py``) and consumed by
non-Python clients. Nothing in this module imports the decoder wheel or
the MCP SDK.
"""

from __future__ import annotations

from typing import Any

SCHEMA_DIALECT = "https://json-schema.org/draft/2020-12/schema"
SCHEMA_ID_BASE = "https://qector.store/schemas/mcp/2.0.0/"

# ---------------------------------------------------------------------------
# Reusable fragments
# ---------------------------------------------------------------------------

BIT = {"type": "integer", "enum": [0, 1]}
BIT_VECTOR = {"type": "array", "items": BIT}
BIT_MATRIX = {"type": "array", "items": BIT_VECTOR}
NON_NEGATIVE_INT = {"type": "integer", "minimum": 0}
POSITIVE_INT = {"type": "integer", "minimum": 1}
PROBABILITY = {"type": "number", "minimum": 0.0, "maximum": 1.0}
UNIT_INTERVAL_PAIR = {
    "type": "array",
    "items": PROBABILITY,
    "minItems": 2,
    "maxItems": 2,
}
SHA256_HEX = {"type": "string", "pattern": "^[0-9a-f]{64}$"}
NULLABLE_STRING = {"type": ["string", "null"]}
NULLABLE_INT = {"type": ["integer", "null"]}
NULLABLE_BOOL = {"type": ["boolean", "null"]}
FREE_OBJECT = {"type": "object", "additionalProperties": True}
STRING_LIST = {"type": "array", "items": {"type": "string"}}
DOI = {"type": "string", "pattern": "^10\\.\\d{4,9}/\\S+$"}

ENVIRONMENT_BLOCK = {
    "type": "object",
    "required": ["os", "platform", "python", "numpy", "qector_decoder_v3", "mcp_sdk"],
    "properties": {
        "os": {"type": "string"},
        "platform": {"type": "string"},
        "cpu": {"type": "string"},
        "ram_bytes": NULLABLE_INT,
        "python": {"type": "string"},
        "numpy": {"type": "string"},
        "qector_decoder_v3": {"type": "string"},
        "mcp_sdk": {"type": "string"},
        "git_commit": {"type": "string"},
    },
    "additionalProperties": True,
}

PYPI_FRESHNESS = {
    "type": "object",
    "required": ["status"],
    "properties": {
        "status": {"type": "string", "enum": ["ok", "unavailable", "not_checked", "disabled"]},
        "reason": {"type": "string"},
        "latest_version": {"type": "string"},
        "installed_version": {"type": "string"},
        "up_to_date": {"type": "boolean"},
        "source": {"type": "string"},
    },
    "additionalProperties": False,
}

NETWORK_POLICY = {
    "type": "object",
    "required": ["air_gapped", "python_socket_guard", "subprocess_guard", "env_scrubbed"],
    "properties": {
        "air_gapped": {"type": "boolean"},
        "python_socket_guard": {"type": "boolean"},
        "subprocess_guard": {"type": "boolean"},
        "env_scrubbed": {"type": "boolean"},
        "transport": {"type": "string", "enum": ["stdio"]},
        "note": {"type": "string"},
    },
    "additionalProperties": True,
}

EFFECTIVE_DISTANCE = {
    "type": "object",
    "description": (
        "Minimum weight of an undetectable logical error (H e = 0, L e != 0), found by zero/duplicate-column "
        "checks and a bounded enumeration. exact=true means min_logical_weight is the true distance; otherwise "
        "only lower_bound is known. The wheel's nominal distance is reported alongside and never trusted."
    ),
    "required": ["nominal", "min_logical_weight", "lower_bound", "exact", "searched_weight", "supports_examined", "witness", "method"],
    "properties": {
        "nominal": POSITIVE_INT,
        "min_logical_weight": NULLABLE_INT,
        "lower_bound": NULLABLE_INT,
        "exact": {"type": "boolean"},
        "searched_weight": NON_NEGATIVE_INT,
        "supports_examined": NON_NEGATIVE_INT,
        "witness": {"type": ["array", "null"], "items": NON_NEGATIVE_INT},
        "method": NULLABLE_STRING,
    },
    "additionalProperties": False,
}

FAMILY_HEALTH = {
    "type": "object",
    "required": ["status", "notes"],
    "properties": {
        "status": {"type": "string", "enum": ["ok", "unscored", "weak", "degenerate", "unavailable", "not_probed"]},
        "probe_size": NULLABLE_INT,
        "n_checks": NULLABLE_INT,
        "n_qubits": NULLABLE_INT,
        "rank": NULLABLE_INT,
        "logicals_present": NULLABLE_BOOL,
        "graphlike": NULLABLE_BOOL,
        "unchecked_qubits": {"type": "array", "items": NON_NEGATIVE_INT},
        "effective_distance": {"oneOf": [EFFECTIVE_DISTANCE, {"type": "null"}]},
        "notes": STRING_LIST,
    },
    "additionalProperties": False,
}

LATENCY_STATS = {
    "type": "object",
    "required": ["n", "mean", "stddev", "min", "max", "p50", "p90", "p95", "p99", "ci95_mean"],
    "properties": {
        "n": POSITIVE_INT,
        "mean": {"type": "number", "minimum": 0},
        "stddev": {"type": "number", "minimum": 0},
        "min": {"type": "number", "minimum": 0},
        "max": {"type": "number", "minimum": 0},
        "p50": {"type": "number", "minimum": 0},
        "p90": {"type": "number", "minimum": 0},
        "p95": {"type": "number", "minimum": 0},
        "p99": {"type": "number", "minimum": 0},
        "ci95_mean": {"type": ["array", "null"], "items": {"type": "number", "minimum": 0}, "minItems": 2, "maxItems": 2},
    },
    "additionalProperties": False,
}

NOISE_MODEL = {
    "type": "object",
    "required": ["tag", "source"],
    "properties": {
        "tag": {"type": "string", "enum": ["code_capacity"]},
        "error_rate": PROBABILITY,
        "error_rates": {"type": "array", "items": PROBABILITY},
        "source": {"type": "string"},
    },
    "additionalProperties": False,
}

MEASUREMENT_SCOPE = {
    "type": "object",
    "required": [
        "machine", "os", "platform", "python", "cpu", "ram_bytes", "backend", "backend_version",
        "decoder_class", "code_family", "code_size", "noise_model", "shots_requested", "shots_completed",
        "seed", "workload_hash", "scope", "claim_class",
    ],
    "properties": {
        "machine": {"type": "string"},
        "os": {"type": ["string", "null"]},
        "platform": {"type": ["string", "null"]},
        "python": {"type": ["string", "null"]},
        "cpu": {"type": ["string", "null"]},
        "ram_bytes": NULLABLE_INT,
        "backend": {"type": "string", "const": "qector-decoder-v3"},
        "backend_version": {"type": "string"},
        "decoder_class": {"type": "string"},
        "code_family": {"type": "string"},
        "code_size": POSITIVE_INT,
        "noise_model": NOISE_MODEL,
        "shots_requested": POSITIVE_INT,
        "shots_completed": NON_NEGATIVE_INT,
        "seed": NON_NEGATIVE_INT,
        "workload_hash": SHA256_HEX,
        "scope": {"type": "string", "const": "single_machine"},
        "claim_class": {"type": "string", "const": "machine_scoped_measurement"},
    },
    "additionalProperties": False,
}

REQUIRED_METADATA = {
    "type": "object",
    "required": ["code_family", "distance_size", "noise_model", "dem_settings", "decoder", "sample_count", "metric", "environment", "artifact"],
    "properties": {
        "code_family": {"type": "string"},
        "distance_size": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["distance", "n_checks", "n_qubits"],
                "properties": {
                    "distance": POSITIVE_INT,
                    "n_checks": POSITIVE_INT,
                    "n_qubits": POSITIVE_INT,
                    "effective_distance": EFFECTIVE_DISTANCE,
                },
                "additionalProperties": False,
            },
        },
        "noise_model": NOISE_MODEL,
        "dem_settings": {
            "type": "object",
            "required": ["decompose_errors", "graphlike_collapse", "applicable"],
            "properties": {
                "decompose_errors": NULLABLE_BOOL,
                "graphlike_collapse": NULLABLE_BOOL,
                "applicable": {"type": "boolean"},
            },
            "additionalProperties": False,
        },
        "decoder": {
            "type": "object",
            "required": ["class", "name", "weighted", "batch", "gpu"],
            "properties": {
                "class": {"type": "string"},
                "name": {"type": "string"},
                "weighted": {"type": "boolean"},
                "batch": {"type": "boolean"},
                "gpu": {"type": "boolean"},
            },
            "additionalProperties": False,
        },
        "sample_count": {
            "type": "object",
            "required": ["trials_per_point", "seed"],
            "properties": {"trials_per_point": POSITIVE_INT, "seed": NON_NEGATIVE_INT},
            "additionalProperties": False,
        },
        "metric": {"type": "string"},
        "environment": ENVIRONMENT_BLOCK,
        "artifact": {
            "type": "object",
            "required": ["format"],
            "properties": {
                "format": {"type": "string"},
                "sha256": {"type": "string"},
                "path": {"type": "string"},
                "sha256_sidecar": {"type": "string"},
            },
            "additionalProperties": False,
        },
    },
    "additionalProperties": False,
}

DEM_MECHANISM = {
    "type": "object",
    "required": ["line", "probabilities", "detectors", "observables", "weight"],
    "properties": {
        "line": POSITIVE_INT,
        "probabilities": {"type": "array", "items": {"type": "number"}},
        "detectors": STRING_LIST,
        "observables": STRING_LIST,
        "weight": NON_NEGATIVE_INT,
        "component": NON_NEGATIVE_INT,
        "n_components": POSITIVE_INT,
    },
    "additionalProperties": False,
}

CAPABILITY_ENTRY = {
    "type": "object",
    "required": ["capability", "servers", "tools", "stability", "verification", "notes"],
    "properties": {
        "capability": {"type": "string"},
        "servers": STRING_LIST,
        "tools": STRING_LIST,
        "stability": {"type": "string", "enum": ["stable", "provisional", "admin"]},
        "verification": {"type": "string"},
        "notes": {"type": "string"},
    },
    "additionalProperties": False,
}

SERVER_ENTRY = {
    "type": "object",
    "required": ["stability", "default_enabled", "tools", "n_tools"],
    "properties": {
        "stability": {"type": "string"},
        "default_enabled": {"type": "boolean"},
        "tools": STRING_LIST,
        "n_tools": NON_NEGATIVE_INT,
        "note": {"type": "string"},
    },
    "additionalProperties": False,
}

SWEEP_ROW = {
    "type": "object",
    "required": [
        "distance",
        "effective_distance",
        "n_checks",
        "n_qubits",
        "error_rate",
        "logical_error_rate",
        "wilson_95",
        "logical_errors",
        "trials",
    ],
    "properties": {
        "distance": POSITIVE_INT,
        "effective_distance": EFFECTIVE_DISTANCE,
        "n_checks": POSITIVE_INT,
        "n_qubits": POSITIVE_INT,
        "error_rate": PROBABILITY,
        "logical_error_rate": PROBABILITY,
        "wilson_95": UNIT_INTERVAL_PAIR,
        "logical_errors": NON_NEGATIVE_INT,
        "trials": POSITIVE_INT,
    },
    "additionalProperties": False,
}

LICENSE_BLOCK = {
    "type": "object",
    "required": [
        "tier",
        "distance_limit",
        "gpu_allowed",
        "gnn_allowed",
        "commercial_status",
        "enforcement_mode",
        "license_evidence",
        "raw",
    ],
    "properties": {
        "tier": {"type": "string"},
        "distance_limit": NULLABLE_INT,
        "gpu_allowed": {"type": "boolean"},
        "gnn_allowed": {"type": "boolean"},
        "commercial_status": {
            "type": "string",
            "enum": ["community", "evaluation", "commercial", "expired", "unknown"],
        },
        "enforcement_mode": {"type": "string", "enum": ["enforced", "permissive"]},
        "license_evidence": {
            "type": "object",
            "required": ["key_status", "is_expired"],
            "properties": {
                "key_status": {"type": "string"},
                "is_expired": {"type": "boolean"},
                "subject": {"type": ["string", "null"]},
                "customer_id": {"type": ["string", "null"]},
                "issued_at": {"type": ["integer", "number", "string", "null"]},
                "expires_at": {"type": ["integer", "number", "string", "null"]},
            },
            "additionalProperties": False,
        },
        "raw": FREE_OBJECT,
    },
    "additionalProperties": False,
}


def _obj(
    properties: dict[str, Any],
    required: list[str] | None = None,
    *,
    additional: bool = False,
    title: str | None = None,
    description: str | None = None,
) -> dict[str, Any]:
    # Every tool may attach human-readable warnings; the envelope lifts
    # them into its own ``warnings`` array as well.
    properties = {**properties, "warnings": STRING_LIST}
    schema: dict[str, Any] = {"type": "object", "properties": properties}
    if required is not None:
        schema["required"] = required
    schema["additionalProperties"] = additional
    if title:
        schema["title"] = title
    if description:
        schema["description"] = description
    return schema


# ---------------------------------------------------------------------------
# Stable library surface (8 tools)
# ---------------------------------------------------------------------------

LIBRARY_RESULT_SCHEMAS: dict[str, dict[str, Any]] = {
    "list_code_families": _obj(
        {
            "families": {
                "type": "object",
                "additionalProperties": _obj(
                    {
                        "generator": {"type": "string"},
                        "code_factory": NULLABLE_STRING,
                        "source": {"type": "string", "enum": ["wheel", "plugin"]},
                        "available": {"type": "boolean"},
                        "description": {"type": "string"},
                        "single_decode": {"type": "boolean"},
                        "health": FAMILY_HEALTH,
                    },
                    ["generator", "code_factory", "source", "available", "description", "single_decode", "health"],
                ),
            },
            "reference_manual": DOI,
            "qector_version": {"type": "string"},
        },
        ["families", "reference_manual", "qector_version"],
        title="ListCodeFamiliesResult",
    ),
    "list_decoders": _obj(
        {
            "decoders": {
                "type": "object",
                "additionalProperties": _obj(
                    {
                        "class": {"type": "string"},
                        "status": {"type": "string", "enum": ["stable"]},
                        "graphlike_only": {"type": "boolean"},
                    },
                    ["class", "status", "graphlike_only"],
                ),
            },
            "reference_manual": DOI,
        },
        ["decoders", "reference_manual"],
        title="ListDecodersResult",
    ),
    "get_license_info": _obj(
        {
            "license": LICENSE_BLOCK,
            "qector_version": {"type": "string"},
            "reference_manual": DOI,
        },
        ["license", "qector_version", "reference_manual"],
        title="GetLicenseInfoResult",
    ),
    "decode_syndrome": _obj(
        {
            "family": {"type": "string"},
            "size": POSITIVE_INT,
            "decoder": {"type": "string"},
            "backend_used": {"type": "string"},
            "qector_version": {"type": "string"},
            "n_checks": POSITIVE_INT,
            "n_qubits": POSITIVE_INT,
            "syndrome": BIT_VECTOR,
            "correction": BIT_VECTOR,
            "hamming_weight": NON_NEGATIVE_INT,
            "syndrome_valid": {"type": "boolean", "const": True},
            "latency_us": {"type": "number", "minimum": 0},
        },
        [
            "family",
            "size",
            "decoder",
            "backend_used",
            "qector_version",
            "n_checks",
            "n_qubits",
            "syndrome",
            "correction",
            "hamming_weight",
            "syndrome_valid",
            "latency_us",
        ],
        title="DecodeSyndromeResult",
    ),
    "decode_single": _obj(
        {
            "family": {"type": "string"},
            "distance": POSITIVE_INT,
            "decoder": {"type": "string"},
            "backend_used": {"type": "string"},
            "qector_version": {"type": "string"},
            "error_rate": PROBABILITY,
            "seed": NON_NEGATIVE_INT,
            "n_qubits": POSITIVE_INT,
            "n_checks": POSITIVE_INT,
            "error": BIT_VECTOR,
            "syndrome": BIT_VECTOR,
            "correction": BIT_VECTOR,
            "error_weight": NON_NEGATIVE_INT,
            "correction_weight": NON_NEGATIVE_INT,
            "syndrome_valid": {"type": "boolean", "const": True},
            "logical_failure": NULLABLE_BOOL,
            "logical_scoring": {"type": "string"},
            "effective_distance": {"oneOf": [EFFECTIVE_DISTANCE, {"type": "null"}]},
            "latency_us": {"type": "number", "minimum": 0},
        },
        [
            "family",
            "distance",
            "decoder",
            "backend_used",
            "qector_version",
            "error_rate",
            "seed",
            "n_qubits",
            "n_checks",
            "error",
            "syndrome",
            "correction",
            "error_weight",
            "correction_weight",
            "syndrome_valid",
            "logical_failure",
            "logical_scoring",
            "effective_distance",
            "latency_us",
        ],
        title="DecodeSingleResult",
    ),
    "threshold_sweep": _obj(
        {
            "family": {"type": "string"},
            "decoder": {"type": "string"},
            "qector_version": {"type": "string"},
            "results": {"type": "array", "items": SWEEP_ROW, "minItems": 1},
            "harness": _obj(
                {
                    "faithfulness_policy": {"type": "string"},
                    "wall_clock_seconds": {"type": "number", "minimum": 0},
                    "wall_clock_budget_seconds": {"type": "number", "minimum": 0},
                },
                ["faithfulness_policy", "wall_clock_seconds", "wall_clock_budget_seconds"],
            ),
            "artifact": _obj(
                {
                    "path": {"type": "string"},
                    "sha256": SHA256_HEX,
                    "metadata": REQUIRED_METADATA,
                },
                ["path", "sha256", "metadata"],
            ),
            "methodology": {"type": "string"},
            "caveat": {"type": "string"},
        },
        ["family", "decoder", "qector_version", "results", "harness", "artifact", "methodology", "caveat"],
        title="ThresholdSweepResult",
    ),
    "build_code_from_matrix": _obj(
        {
            "family": {"type": "string"},
            "distance": POSITIVE_INT,
            "matrix_shape": {"type": "array", "items": POSITIVE_INT, "minItems": 2, "maxItems": 2},
            "rank": NON_NEGATIVE_INT,
            "n_checks": POSITIVE_INT,
            "n_qubits": POSITIVE_INT,
            "logical_observables": NULLABLE_INT,
            "graphlike": NULLABLE_BOOL,
            "code_built": {"type": "boolean", "const": True},
            "qector_version": {"type": "string"},
            "reference_manual": DOI,
        },
        [
            "family",
            "distance",
            "matrix_shape",
            "rank",
            "n_checks",
            "n_qubits",
            "logical_observables",
            "graphlike",
            "code_built",
            "qector_version",
            "reference_manual",
        ],
        title="BuildCodeFromMatrixResult",
    ),
    "compat_report": _obj(
        {
            "runtime_ok": {"type": "boolean"},
            "qector_decoder_v3": _obj(
                {
                    "installed": {"type": "boolean"},
                    "version": {"type": "string"},
                    "reviewed_window": {"type": "array", "items": {"type": "string"}, "minItems": 2, "maxItems": 2},
                    "in_reviewed_window": {"type": "boolean"},
                    "version_detail": {"type": "string"},
                },
                ["installed", "version", "reviewed_window", "in_reviewed_window", "version_detail"],
            ),
            "numpy": _obj({"installed": {"type": "boolean"}, "version": {"type": "string"}}, ["installed", "version"]),
            "mcp_sdk": _obj(
                {
                    "installed": {"type": "boolean"},
                    "version": {"type": "string"},
                    "supported": {"type": "boolean"},
                    "detail": {"type": "string"},
                },
                ["installed", "version", "supported", "detail"],
            ),
            "python": _obj(
                {
                    "version": {"type": "string"},
                    "supported_window": {"type": "string"},
                    "in_window": {"type": "boolean"},
                },
                ["version", "supported_window", "in_window"],
            ),
            "pymatching_compat": _obj({"available": {"type": "boolean"}}, ["available"]),
            "reference_manual": DOI,
            "provisional_surfaces": {"type": "object", "additionalProperties": {"type": "string"}},
            "network_policy": NETWORK_POLICY,
            "pypi_freshness": PYPI_FRESHNESS,
        },
        [
            "runtime_ok",
            "qector_decoder_v3",
            "numpy",
            "mcp_sdk",
            "python",
            "pymatching_compat",
            "reference_manual",
            "provisional_surfaces",
            "network_policy",
            "pypi_freshness",
        ],
        title="CompatReportResult",
    ),
}

# ---------------------------------------------------------------------------
# Secure server control-plane tools (4 tools)
# ---------------------------------------------------------------------------

SECURE_RESULT_SCHEMAS: dict[str, dict[str, Any]] = {
    "airgap_status": _obj(
        {
            "air_gapped": {"type": "boolean"},
            "mode_source": {"type": "string", "enum": ["default", "environment", "cli"]},
            "guards": _obj(
                {
                    "python_socket": {"type": "boolean"},
                    "python_subprocess": {"type": "boolean"},
                    "urllib": {"type": "boolean"},
                    "env_scrub": {"type": "boolean"},
                    "pypi_freshness": {"type": "string", "enum": ["disabled", "opt_in"]},
                    "wheel_offline_flag": {"type": "boolean"},
                },
                ["python_socket", "python_subprocess", "urllib", "env_scrub", "pypi_freshness", "wheel_offline_flag"],
            ),
            "scrubbed_variables": STRING_LIST,
            "transport": {"type": "string", "enum": ["stdio"]},
            "backend_network_surface": _obj(
                {
                    "wheel": {"type": "string"},
                    "network_capable_symbols": STRING_LIST,
                    "called_by_plugin": {"type": "boolean", "const": False},
                    "embedded_endpoints": STRING_LIST,
                    "python_level_guard_blocks_native_core": {"type": "boolean", "const": False},
                    "recommended_host_controls": STRING_LIST,
                },
                [
                    "wheel",
                    "network_capable_symbols",
                    "called_by_plugin",
                    "embedded_endpoints",
                    "python_level_guard_blocks_native_core",
                    "recommended_host_controls",
                ],
            ),
            "blocked_attempts": NON_NEGATIVE_INT,
            "guard_scope": {"type": "string"},
            "reference_manual": DOI,
        },
        [
            "air_gapped",
            "mode_source",
            "guards",
            "scrubbed_variables",
            "transport",
            "backend_network_surface",
            "blocked_attempts",
            "guard_scope",
            "reference_manual",
        ],
        title="AirgapStatusResult",
    ),
    "integrity_check": _obj(
        {
            "manifest_path": {"type": "string"},
            "manifest_present": {"type": "boolean"},
            "manifest_version": NULLABLE_STRING,
            "strict": {"type": "boolean"},
            "files_checked": NON_NEGATIVE_INT,
            "files_ok": NON_NEGATIVE_INT,
            "mismatched": STRING_LIST,
            "missing": STRING_LIST,
            "unlisted_runtime_files": STRING_LIST,
            "passed": {"type": "boolean"},
            "signature": _obj(
                {
                    "present": {"type": "boolean"},
                    "valid": {"type": "boolean"},
                    "source": {"type": "string", "enum": ["none", "pinned", "release_manifest"]},
                    "fingerprint": {"type": ["string", "null"], "pattern": "^[0-9a-f]{64}$"},
                    "pinned_fingerprint": {"type": ["string", "null"], "pattern": "^[0-9a-f]{64}$"},
                    "reason": NULLABLE_STRING,
                },
                ["present", "valid", "source", "fingerprint", "pinned_fingerprint", "reason"],
            ),
            "runtime_distributions": {
                "type": "object",
                "additionalProperties": {"type": ["string", "null"]},
            },
            "reference_manual": DOI,
        },
        [
            "manifest_path",
            "manifest_present",
            "manifest_version",
            "strict",
            "files_checked",
            "files_ok",
            "mismatched",
            "missing",
            "unlisted_runtime_files",
            "passed",
            "signature",
            "runtime_distributions",
            "reference_manual",
        ],
        title="IntegrityCheckResult",
    ),
    "schema_catalog": _obj(
        {
            "dialect": {"type": "string", "const": SCHEMA_DIALECT},
            "contract_version": {"type": "string"},
            "envelope": FREE_OBJECT,
            "tools": {
                "type": "object",
                "additionalProperties": _obj(
                    {
                        "input_schema": FREE_OBJECT,
                        "output_schema": FREE_OBJECT,
                        "annotations": FREE_OBJECT,
                        "stability": {"type": "string", "enum": ["stable", "provisional", "control"]},
                        "input_sha256": SHA256_HEX,
                        "output_sha256": SHA256_HEX,
                    },
                    ["input_schema", "output_schema", "annotations", "stability", "input_sha256", "output_sha256"],
                ),
            },
            "catalog_sha256": SHA256_HEX,
            "reference_manual": DOI,
        },
        ["dialect", "contract_version", "envelope", "tools", "catalog_sha256", "reference_manual"],
        title="SchemaCatalogResult",
    ),
    "audit_log_status": _obj(
        {
            "enabled": {"type": "boolean"},
            "path": NULLABLE_STRING,
            "records": NON_NEGATIVE_INT,
            "head_sha256": {"type": ["string", "null"], "pattern": "^[0-9a-f]{64}$"},
            "chain_valid": NULLABLE_BOOL,
            "first_invalid_sequence": NULLABLE_INT,
            "keyed": {"type": "boolean"},
            "matches_server_head": NULLABLE_BOOL,
            "record_schema": FREE_OBJECT,
            "reference_manual": DOI,
        },
        ["enabled", "path", "records", "head_sha256", "chain_valid", "first_invalid_sequence", "keyed", "matches_server_head", "record_schema", "reference_manual"],
        title="AuditLogStatusResult",
    ),
}

# ---------------------------------------------------------------------------
# Research surface (29 tools). Top-level keys typed; nested blocks that
# mirror live wheel output remain open objects.
# ---------------------------------------------------------------------------

_RESEARCH_COMMON = {"reference_manual": DOI}

RESEARCH_RESULT_SCHEMAS: dict[str, dict[str, Any]] = {
    "wilson_ci": _obj(
        {"k": NON_NEGATIVE_INT, "n": POSITIVE_INT, "z": {"type": "number"}, "wilson_95": UNIT_INTERVAL_PAIR, **_RESEARCH_COMMON},
        ["k", "n", "z", "wilson_95", "reference_manual"],
    ),
    "wilson_table": _obj(
        {
            "n": POSITIVE_INT,
            "z": {"type": "number"},
            "rows": {
                "type": "array",
                "items": _obj({"k": NON_NEGATIVE_INT, "n": POSITIVE_INT, "wilson_95": UNIT_INTERVAL_PAIR}, ["k", "n", "wilson_95"]),
            },
            **_RESEARCH_COMMON,
        },
        ["n", "z", "rows", "reference_manual"],
    ),
    "logical_coset_score": _obj(
        {
            "failures": NON_NEGATIVE_INT,
            "trials": NON_NEGATIVE_INT,
            "logical_failure_rate": PROBABILITY,
            "wilson_95": UNIT_INTERVAL_PAIR,
            "scoring": {"type": "string"},
        },
        ["failures", "trials", "logical_failure_rate", "wilson_95", "scoring"],
    ),
    "dem_inspect": _obj(
        {
            "summary": _obj(
                {
                    "n_mechanisms": NON_NEGATIVE_INT,
                    "n_detectors": NON_NEGATIVE_INT,
                    "n_observables": NON_NEGATIVE_INT,
                    "weight_histogram": {"type": "object", "additionalProperties": NON_NEGATIVE_INT},
                    "is_graphlike": {"type": "boolean"},
                    "routing": {"type": "string"},
                    "instructions": {"type": "object", "additionalProperties": NON_NEGATIVE_INT},
                },
                ["n_mechanisms", "n_detectors", "n_observables", "weight_histogram", "is_graphlike", "routing", "instructions"],
            ),
            **_RESEARCH_COMMON,
        },
        ["summary", "reference_manual"],
    ),
    "dem_collapse_parallel": _obj(
        {
            "dem_text_bytes": NON_NEGATIVE_INT,
            "collapse": _obj(
                {
                    "graphlike_edges": {
                        "type": "array",
                        "items": _obj(
                            {
                                "detectors": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 2},
                                "kind": {"type": "string", "enum": ["boundary", "edge"]},
                                "p_combined": PROBABILITY,
                                "weight_log": {"type": ["number", "null"]},
                                "n_members": POSITIVE_INT,
                                "members": {
                                    "type": "array",
                                    "items": _obj({"p": {"type": "number"}, "observables": STRING_LIST}, ["p", "observables"]),
                                },
                                "winning_observables": STRING_LIST,
                                "observable_rule": {"type": "string", "enum": ["most_likely", "union", "first"]},
                                "combination_rule": {"type": "string"},
                            },
                            ["detectors", "kind", "p_combined", "weight_log", "n_members", "members", "winning_observables", "observable_rule", "combination_rule"],
                        ),
                    },
                    "hyperedges": {"type": "array", "items": DEM_MECHANISM},
                    "n_graphlike_members": NON_NEGATIVE_INT,
                    "n_unique_edges": NON_NEGATIVE_INT,
                    "n_detector_free": NON_NEGATIVE_INT,
                },
                ["graphlike_edges", "hyperedges", "n_graphlike_members", "n_unique_edges", "n_detector_free"],
            ),
            "manual_worked_example_check": _obj(
                {
                    "p1": PROBABILITY,
                    "p2": PROBABILITY,
                    "expected_p_combined": PROBABILITY,
                    "computed_p_combined": PROBABILITY,
                    "expected_weight_log": {"type": "number"},
                    "computed_weight_log": {"type": ["number", "null"]},
                    "matches": {"type": "boolean"},
                },
                ["p1", "p2", "expected_p_combined", "computed_p_combined", "expected_weight_log", "computed_weight_log", "matches"],
            ),
            **_RESEARCH_COMMON,
        },
        ["dem_text_bytes", "collapse", "manual_worked_example_check", "reference_manual"],
    ),
    "code_family_info": _obj(
        {
            "family": {"type": "string"},
            "size": POSITIVE_INT,
            "n_qubits": POSITIVE_INT,
            "n_checks": POSITIVE_INT,
            "distance": {"type": ["integer", "null"]},
            "max_qubit_degree": NON_NEGATIVE_INT,
            "is_matching_graph": {"type": "boolean"},
            "n_logicals": NON_NEGATIVE_INT,
            "logicals_present": {"type": "boolean"},
            "matrix_shape": {"type": "array", "items": POSITIVE_INT, "minItems": 2, "maxItems": 2},
            "routing": {"type": "string"},
            "health": FAMILY_HEALTH,
            "qector_version": {"type": "string"},
            **_RESEARCH_COMMON,
        },
        ["family", "size", "n_qubits", "n_checks", "distance", "max_qubit_degree", "is_matching_graph", "n_logicals", "logicals_present", "matrix_shape", "routing", "health", "qector_version", "reference_manual"],
    ),
    "code_export_matrices": _obj(
        {
            "family": {"type": "string"},
            "size": POSITIVE_INT,
            "n_qubits": POSITIVE_INT,
            "n_checks": POSITIVE_INT,
            "check_to_qubits": {"type": "array", "items": {"type": "array", "items": NON_NEGATIVE_INT}},
            "parity_check_matrix": BIT_MATRIX,
            "logicals_matrix": {"type": ["array", "null"], "items": BIT_VECTOR},
            "qector_version": {"type": "string"},
            **_RESEARCH_COMMON,
        },
        ["family", "size", "n_qubits", "n_checks", "check_to_qubits", "parity_check_matrix", "logicals_matrix", "qector_version", "reference_manual"],
    ),
    "code_logicals_inspect": _obj(
        {
            "family": {"type": "string"},
            "size": POSITIVE_INT,
            "n_logicals": NON_NEGATIVE_INT,
            "logicals_present": {"type": "boolean"},
            "logicals": BIT_MATRIX,
            "n_qubits": POSITIVE_INT,
            "scoring_note": {"type": "string"},
            **_RESEARCH_COMMON,
        },
        ["family", "size", "n_logicals", "logicals_present", "reference_manual"],
    ),
    "code_distance_check": _obj(
        {
            "family": {"type": "string"},
            "size": POSITIVE_INT,
            "n_qubits": POSITIVE_INT,
            "n_checks": POSITIVE_INT,
            "nominal_distance": {"type": ["integer", "null"]},
            "effective_distance": EFFECTIVE_DISTANCE,
            "distance_verified": {"type": "boolean"},
            "verdict": {"type": "string", "enum": ["verified", "contradicted", "bounded", "unscorable"]},
            "matrix_shape": {"type": "array", "items": POSITIVE_INT, "minItems": 2, "maxItems": 2},
            "check_to_qubits": {"type": "array", "items": {"type": "array", "items": NON_NEGATIVE_INT}},
            "qector_version": {"type": "string"},
            **_RESEARCH_COMMON,
        },
        ["family", "size", "n_qubits", "n_checks", "nominal_distance", "effective_distance", "distance_verified", "verdict", "matrix_shape", "check_to_qubits", "qector_version", "reference_manual"],
    ),
    "pymatching_compat_check": _obj(
        {
            "family": {"type": "string"},
            "size": POSITIVE_INT,
            "comparable": {"type": "boolean"},
            "reason": {"type": "string"},
            "n_qubits": POSITIVE_INT,
            "n_checks": POSITIVE_INT,
            "qector_correction_weight": NON_NEGATIVE_INT,
            "qector_syndrome_valid": {"type": "boolean"},
            "pymatching_compared": {"type": "boolean"},
            "pymatching_correction_weight": NON_NEGATIVE_INT,
            "pymatching_syndrome_valid": {"type": "boolean"},
            "bitwise_equal": {"type": "boolean"},
            "agreement_note": {"type": "string"},
            "pymatching_error": {"type": "string"},
            "pymatching_skipped": {"type": "string"},
            **_RESEARCH_COMMON,
        },
        ["family", "size", "reference_manual"],
    ),
    "sinter_decoder_list": _obj(
        {
            "sinter_exposed": {"type": "boolean"},
            "factory": NULLABLE_STRING,
            "sinter_installed": {"type": "boolean"},
            "sinter_decoders": {"type": "array", "items": _obj({"name": {"type": "string"}, "type": {"type": "string"}}, ["name", "type"])},
            "note": {"type": "string"},
            "error": {"type": "string"},
            **_RESEARCH_COMMON,
        },
        ["sinter_exposed", "factory", "sinter_installed", "sinter_decoders", "reference_manual"],
    ),
    "qiskit_plugin_check": _obj(
        {
            "qiskit_installed": {"type": "boolean"},
            "raw_dict_mode": {"type": "boolean"},
            "note": {"type": "string"},
            "qiskit_plugin_imported": {"type": "boolean"},
            "decode_syndrome_counts_signature": {"type": "string"},
            "error": {"type": "string"},
            **_RESEARCH_COMMON,
        },
        ["qiskit_installed", "raw_dict_mode", "reference_manual"],
    ),
    "hardware_probe": _obj(
        {
            "cuda_available": {"type": "boolean"},
            "cuda_batch_decoder": FREE_OBJECT,
            "opencl_available": {"type": "boolean"},
            "license": FREE_OBJECT,
            "environment": ENVIRONMENT_BLOCK,
            **_RESEARCH_COMMON,
        },
        ["cuda_available", "cuda_batch_decoder", "opencl_available", "license", "environment", "reference_manual"],
    ),
    "license_active_check": _obj(
        {
            "license_active": {"type": "boolean"},
            "tier": {"type": "string"},
            "max_distance": NULLABLE_INT,
            "gpu_enabled": NULLABLE_BOOL,
            "gnn_enabled": NULLABLE_BOOL,
            "source": {"type": "string", "enum": ["live_wheel", "error"]},
            "error": {"type": "string"},
            "info": FREE_OBJECT,
            "environment": ENVIRONMENT_BLOCK,
            **_RESEARCH_COMMON,
        },
        ["license_active", "tier", "max_distance", "source", "reference_manual"],
    ),
    "env_block": _obj(
        {
            "environment": ENVIRONMENT_BLOCK,
            "qector_decoder_v3_present": {"type": "boolean"},
            "qector_decoder_v3_version": {"type": "string"},
            "pypi_freshness": PYPI_FRESHNESS,
            **_RESEARCH_COMMON,
        },
        ["environment", "qector_decoder_v3_present", "qector_decoder_v3_version", "pypi_freshness", "reference_manual"],
    ),
    "compat_report": _obj(
        {
            "runtime_ok": {"type": "boolean"},
            "server": _obj({"name": {"type": "string"}, "version": {"type": "string"}, "kind": {"type": "string"}}, ["name", "version", "kind"]),
            "qector_decoder_v3": _obj({"installed": {"type": "boolean"}, "version": {"type": "string"}, "expected": {"type": "string"}}, ["installed", "version", "expected"]),
            "numpy": _obj({"installed": {"type": "boolean"}, "version": {"type": "string"}}, ["installed", "version"]),
            "mcp_sdk": _obj({"installed": {"type": "boolean"}, "version": {"type": "string"}, "supported": {"type": "boolean"}, "detail": {"type": "string"}}, ["installed", "version", "supported", "detail"]),
            "pymatching_compat": _obj({"available": {"type": "boolean"}}, ["available"]),
            "provisional_surfaces": {"type": "object", "additionalProperties": {"type": "string"}},
            "network_policy": NETWORK_POLICY,
            "pypi_freshness": PYPI_FRESHNESS,
            **_RESEARCH_COMMON,
        },
        ["runtime_ok", "server", "qector_decoder_v3", "numpy", "mcp_sdk", "pymatching_compat", "provisional_surfaces", "network_policy", "pypi_freshness", "reference_manual"],
    ),
    "artifacts_sha256": _obj(
        {
            "files": {
                "type": "array",
                "items": _obj({"path": {"type": "string"}, "size_bytes": NON_NEGATIVE_INT, "sha256": SHA256_HEX}, ["path", "size_bytes", "sha256"]),
            },
            "n_files": NON_NEGATIVE_INT,
            "artifact_root": {"type": "string"},
            **_RESEARCH_COMMON,
        },
        ["files", "n_files", "artifact_root", "reference_manual"],
    ),
    "artifact_metadata_check": _obj(
        {
            "family": {"type": "string"},
            "size": POSITIVE_INT,
            "decoder": {"type": "string"},
            "mode": {"type": "string", "enum": ["template", "checked"]},
            "checked": {"type": "boolean"},
            "required_metadata": REQUIRED_METADATA,
            "required_fields": STRING_LIST,
            "missing_fields": STRING_LIST,
            "matrix_shape": {"type": "array", "items": POSITIVE_INT, "minItems": 2, "maxItems": 2},
            "all_required_fields_present": {"type": "boolean"},
            "artifact_sha256": {"type": ["string", "null"], "pattern": "^[0-9a-f]{64}$"},
            "sidecar_matches": NULLABLE_BOOL,
            **_RESEARCH_COMMON,
        },
        ["family", "size", "decoder", "mode", "checked", "required_metadata", "required_fields", "missing_fields", "matrix_shape", "all_required_fields_present", "artifact_sha256", "sidecar_matches", "reference_manual"],
    ),
    "decode_faithfulness_check": _obj(
        {
            "syndrome_valid": {"type": "boolean"},
            "n_checks": POSITIVE_INT,
            "n_qubits": POSITIVE_INT,
            "correction_weight": NON_NEGATIVE_INT,
            "syndrome_weight": NON_NEGATIVE_INT,
            "computed_syndrome": BIT_VECTOR,
            "syndrome_mismatch_indices": {"type": "array", "items": NON_NEGATIVE_INT},
            "theorem": {"type": "string"},
            **_RESEARCH_COMMON,
        },
        ["syndrome_valid", "n_checks", "n_qubits", "correction_weight", "syndrome_weight", "computed_syndrome", "syndrome_mismatch_indices", "theorem", "reference_manual"],
    ),
    "hot_path_microbench": _obj(
        {
            "family": {"type": "string"},
            "size": POSITIVE_INT,
            "decoder": {"type": "string"},
            "shots_requested": POSITIVE_INT,
            "shots_completed": NON_NEGATIVE_INT,
            "syndrome_invalid": NON_NEGATIVE_INT,
            "latency_us": LATENCY_STATS,
            "warning": {"type": "string"},
            "timed_window": {"type": "string"},
            "warmup_shots": NON_NEGATIVE_INT,
            "scope_note": {"type": "string"},
            "measurement_scope": MEASUREMENT_SCOPE,
            "environment": ENVIRONMENT_BLOCK,
            "qector_version": {"type": "string"},
            **_RESEARCH_COMMON,
        },
        ["family", "size", "decoder", "shots_requested", "shots_completed", "syndrome_invalid", "measurement_scope", "environment", "qector_version", "reference_manual"],
    ),
    "stim_circuit_probe": _obj(
        {
            "summary": _obj(
                {
                    "n_qubits": NON_NEGATIVE_INT,
                    "n_ticks": NON_NEGATIVE_INT,
                    "instruction_counts": {"type": "object", "additionalProperties": NON_NEGATIVE_INT},
                    "rounds_detected": NON_NEGATIVE_INT,
                },
                ["n_qubits", "n_ticks", "instruction_counts", "rounds_detected"],
            ),
            "byte_size": NON_NEGATIVE_INT,
            "note": {"type": "string"},
            **_RESEARCH_COMMON,
        },
        ["summary", "byte_size", "note", "reference_manual"],
    ),
    "sinter_task_template": _obj(
        {
            "family": {"type": "string"},
            "size": POSITIVE_INT,
            "decoder": {"type": "string"},
            "warning": {"type": "string"},
            "task_template": FREE_OBJECT,
            "matrix_shape": {"type": "array", "items": POSITIVE_INT, "minItems": 2, "maxItems": 2},
            "qector_version": {"type": "string"},
            **_RESEARCH_COMMON,
        },
        ["family", "size", "decoder", "task_template", "matrix_shape", "qector_version", "reference_manual"],
    ),
    "workload_hash": _obj(
        {
            "sha256": SHA256_HEX,
            "algorithm": {"type": "string", "const": "sha256"},
            "canonical_json": {"type": "string"},
            "workload_keys": STRING_LIST,
            **_RESEARCH_COMMON,
        },
        ["sha256", "algorithm", "canonical_json", "workload_keys", "reference_manual"],
    ),
    "theorem_lookup": _obj(
        {
            "number": POSITIVE_INT,
            "found": {"type": "boolean"},
            "chapter": {"type": "string"},
            "name": {"type": "string"},
            "statement": {"type": "string"},
            "scope": {"type": "string"},
            "available_numbers": {"type": "array", "items": POSITIVE_INT},
            **_RESEARCH_COMMON,
        },
        ["number", "found", "reference_manual"],
    ),
    "glossary_lookup": _obj(
        {
            "term": {"type": "string"},
            "found": {"type": "boolean"},
            "chapter": {"type": "string"},
            "definition": {"type": "string"},
            "matches": STRING_LIST,
            "available_terms_sample": STRING_LIST,
            "n_terms": NON_NEGATIVE_INT,
            **_RESEARCH_COMMON,
        },
        ["term", "found", "reference_manual"],
    ),
    "reproduction_command_lookup": _obj(
        {
            "section": {"type": "string"},
            "found": {"type": "boolean"},
            "commands": {"type": "object", "additionalProperties": _obj({"section": {"type": "string"}, "title": {"type": "string"}, "command": {"type": "string"}, "description": {"type": "string"}}, ["section", "title", "command", "description"])},
            "matches": {"type": "object", "additionalProperties": _obj({"section": {"type": "string"}, "title": {"type": "string"}, "command": {"type": "string"}, "description": {"type": "string"}}, ["section", "title", "command", "description"])},
            "available_sections": STRING_LIST,
            "chapters": {"type": "string"},
            **_RESEARCH_COMMON,
        },
        ["section", "reference_manual"],
    ),
    "get_capability_matrix": _obj(
        {
            "matrix_version": {"type": "string"},
            "servers": {"type": "object", "additionalProperties": SERVER_ENTRY},
            "capabilities": {"type": "array", "items": CAPABILITY_ENTRY},
            "n_capabilities": NON_NEGATIVE_INT,
            **_RESEARCH_COMMON,
        },
        ["matrix_version", "servers", "capabilities", "n_capabilities", "reference_manual"],
    ),
    "get_evidence_policy": _obj(
        {
            "policy_version": {"type": "string"},
            "result_statuses": {"type": "array", "items": FREE_OBJECT},
            "stable_error_codes": STRING_LIST,
            "agent_must": STRING_LIST,
            "agent_must_not": STRING_LIST,
            **_RESEARCH_COMMON,
        },
        ["policy_version", "result_statuses", "stable_error_codes", "agent_must", "agent_must_not", "reference_manual"],
    ),
    "get_runtime_provenance": _obj(
        {
            "server": {"type": "string"},
            "server_version": {"type": "string"},
            "qector_decoder_v3": {"type": "string"},
            "qector_decoder_v3_present": {"type": "boolean"},
            "mcp_protocol": {"type": "string"},
            "mcp_sdk": {"type": "string"},
            "environment": ENVIRONMENT_BLOCK,
            "stability": {"type": "string"},
            "pypi_freshness": PYPI_FRESHNESS,
            **_RESEARCH_COMMON,
        },
        ["server", "server_version", "qector_decoder_v3", "qector_decoder_v3_present", "mcp_protocol", "mcp_sdk", "environment", "stability", "pypi_freshness", "reference_manual"],
    ),
}

# ---------------------------------------------------------------------------
# Admin surface (3 tools)
# ---------------------------------------------------------------------------

ADMIN_RESULT_SCHEMAS: dict[str, dict[str, Any]] = {
    "system_setup": _obj(
        {
            "status": {"type": "string", "enum": ["dry_run_pending_approval", "ready", "configured"]},
            "user_approbation_required": {"type": "boolean"},
            "user_approbation_granted": {"type": "boolean"},
            "confirmation_message": {"type": "string"},
            "actions_planned": STRING_LIST,
            "actions_executed": {"type": "array", "items": FREE_OBJECT},
            "diagnostics": FREE_OBJECT,
            "validation_result": FREE_OBJECT,
            "network_policy": NETWORK_POLICY,
            **_RESEARCH_COMMON,
        },
        ["status", "user_approbation_required", "user_approbation_granted", "actions_planned", "diagnostics", "network_policy", "reference_manual"],
    ),
    "configure_claude_desktop": {"type": "object", "additionalProperties": True},
    "workbench_probe": {"type": "object", "additionalProperties": True},
}

ALL_RESULT_SCHEMAS: dict[str, dict[str, Any]] = {
    **LIBRARY_RESULT_SCHEMAS,
    **SECURE_RESULT_SCHEMAS,
    **RESEARCH_RESULT_SCHEMAS,
    **ADMIN_RESULT_SCHEMAS,
}


def result_schema_for(tool_name: str, *, surface: str | None = None) -> dict[str, Any]:
    """Return the result schema for *tool_name*.

    ``compat_report`` exists on both the library and the research server
    with different shapes; pass ``surface="research"`` to select the
    research shape. Unknown tools get an open object so the envelope still
    validates structurally.
    """
    if tool_name == "compat_report" and surface == "research":
        return RESEARCH_RESULT_SCHEMAS["compat_report"]
    if surface == "library" and tool_name in LIBRARY_RESULT_SCHEMAS:
        return LIBRARY_RESULT_SCHEMAS[tool_name]
    if surface == "research" and tool_name in RESEARCH_RESULT_SCHEMAS:
        return RESEARCH_RESULT_SCHEMAS[tool_name]
    return ALL_RESULT_SCHEMAS.get(tool_name, {"type": "object", "additionalProperties": True})
