"""Shared MCP result, error, schema, budget and validation contracts for QECTOR.

Contract version 2.0 (QECTOR Claude Plugin 2.0.0):

* every tool carries a JSON Schema 2020-12 ``inputSchema`` and a per-tool
  ``outputSchema`` (the ``QECTORToolResult`` envelope with the ``result``
  slot specialised from ``qector_schemas.py``);
* every call is validated **on the way in** (arguments against the input
  schema) and **on the way out** (envelope against the output schema)
  with the ``jsonschema`` Draft 2020-12 validator; the SDK's own
  validation is not relied upon;
* error codes are a closed set (``STABLE_ERROR_CODES``) and are derived
  from exception *classes* first, message heuristics last;
* per-process call budgets and a per-minute token bucket protect the
  local machine from a looping agent;
* the module is SDK-generation neutral through ``qector_mcp_compat``.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from pathlib import Path
from typing import Any, Iterable, Mapping

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError, ValidationError

from mcp.types import Tool, ToolAnnotations

from qector_mcp_compat import (
    make_annotations,
    make_call_tool_result,
    rebuild_tool,
    sorted_tools,
    tool_input_schema,
)
from qector_schemas import SCHEMA_DIALECT, SCHEMA_ID_BASE, result_schema_for

CONTRACT_VERSION = "2.0"

# ---------------------------------------------------------------------------
# Exceptions shared by every server
# ---------------------------------------------------------------------------


class QECTORResourceLimitError(RuntimeError):
    """Raised when a per-process tool call budget or rate limit is exhausted."""


class QECTORNetworkDisabledError(RuntimeError):
    """Raised when a network-capable path is requested in air-gapped mode."""


class QECTORSchemaError(ValueError):
    """Raised when tool arguments fail JSON Schema validation."""

    MAX_MESSAGE = 400

    def __init__(self, tool_name: str, message: str, path: str) -> None:
        if len(message) > self.MAX_MESSAGE:
            message = message[: self.MAX_MESSAGE - 3] + "..."
        super().__init__(f"{tool_name}: {message} (at {path or '$'})")
        self.tool_name = tool_name
        self.path = path


class QECTORContractViolation(RuntimeError):
    """Raised when a tool result does not satisfy its advertised output schema."""


class QECTORAuditWriteError(OSError):
    """Raised when a call result could not be appended to the audit log (fail closed → IO_ERROR)."""


class QECTORUnknownToolError(ValueError):
    """Raised when a client names a tool the server does not advertise."""


class QECTORIntegrityError(RuntimeError):
    """Raised when the runtime file set does not match the integrity manifest."""


# ---------------------------------------------------------------------------
# Call budgets (per process) and rate limits (per minute)
# ---------------------------------------------------------------------------

# Zero or a missing env override means "use the default"; a negative env
# value disables the budget for that tool (explicit operator override).
_CALL_BUDGET_DEFAULTS = {
    "threshold_sweep": 8,
    "decode_single": 64,
    "decode_syndrome": 256,
    "build_code_from_matrix": 32,
    "hot_path_microbench": 4,
    "system_setup": 2,
    "configure_claude_desktop": 2,
    "workbench_probe": 2,
    "integrity_check": 16,
}
# Calls per rolling 60 s window, any tool. Protects a local laptop from an
# agent loop even for cheap read-only tools.
_RATE_LIMIT_DEFAULT = 600
_TRUE = {"1", "true", "yes", "on"}


def env_flag(name: str, default: bool = False) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in _TRUE


class _CallBudget:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counts: dict[str, int] = {}
        self._window: list[float] = []

    def consume(self, tool_name: str) -> None:
        limit = _budget_for(tool_name)
        rate_limit = _rate_limit()
        now = time.monotonic()
        with self._lock:
            if rate_limit is not None:
                cutoff = now - 60.0
                self._window = [stamp for stamp in self._window if stamp > cutoff]
                if len(self._window) >= rate_limit:
                    raise QECTORResourceLimitError(
                        f"rate limit of {rate_limit} tool calls per 60 s exceeded; "
                        "wait before retrying or raise QECTOR_MCP_RATE_LIMIT_PER_MINUTE"
                    )
                self._window.append(now)
            if limit is None:
                return
            count = self._counts.get(tool_name, 0) + 1
            if count > limit:
                raise QECTORResourceLimitError(
                    f"tool {tool_name!r} exceeded the per-process call limit "
                    f"of {limit}; restart the MCP server or raise "
                    f"QECTOR_MCP_MAX_CALLS_{tool_name.upper()}"
                )
            self._counts[tool_name] = count

    def refund(self, tool_name: str) -> None:
        with self._lock:
            if self._counts.get(tool_name, 0) > 0:
                self._counts[tool_name] -= 1
            if self._window:
                self._window.pop()

    def reset(self) -> None:
        with self._lock:
            self._counts.clear()
            self._window.clear()

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return dict(self._counts)


_PROCESS_BUDGET = _CallBudget()


def _budget_for(tool_name: str) -> int | None:
    env_name = f"QECTOR_MCP_MAX_CALLS_{tool_name.upper()}"
    raw = os.environ.get(env_name)
    if raw is not None:
        try:
            value = int(raw)
        except ValueError as exc:
            raise QECTORResourceLimitError(f"{env_name} must be an integer") from exc
        if value < 0:
            return None
        return value
    return _CALL_BUDGET_DEFAULTS.get(tool_name)


def _rate_limit() -> int | None:
    raw = os.environ.get("QECTOR_MCP_RATE_LIMIT_PER_MINUTE")
    if raw is None:
        return _RATE_LIMIT_DEFAULT
    try:
        value = int(raw)
    except ValueError as exc:
        raise QECTORResourceLimitError(
            "QECTOR_MCP_RATE_LIMIT_PER_MINUTE must be an integer"
        ) from exc
    return None if value <= 0 else value


def consume_call_budget(tool_name: str) -> None:
    """Charge one call against the process budget and rate limit."""
    _PROCESS_BUDGET.consume(tool_name)


def refund_call_budget(tool_name: str) -> None:
    """Give back one call when a tool rejected its input before doing any work.

    Prevents an agent (or a prompt injection) from exhausting a budget with
    deliberately invalid requests; only validation failures are refunded,
    never completed or partially executed work.
    """
    _PROCESS_BUDGET.refund(tool_name)


def reset_call_budget() -> None:
    """Test helper: clear the process-local call counters."""
    _PROCESS_BUDGET.reset()


def call_budget_snapshot() -> dict[str, int]:
    return _PROCESS_BUDGET.snapshot()


def call_budget_defaults() -> dict[str, int]:
    return dict(_CALL_BUDGET_DEFAULTS)


# ---------------------------------------------------------------------------
# Envelope schema
# ---------------------------------------------------------------------------

RESULT_STATUSES = ("verified", "reference_only", "measured", "not_checked", "error")
VERIFICATION_STATUSES = ("verified", "not_checked", "failed", "not_applicable", "reference_only")
CLAIM_CLASSES = (
    "runtime_verified",
    "verification_failed",
    "reference_only",
    "machine_scoped_measurement",
    "metadata_or_unverified",
    "none",
)
STABLE_ERROR_CODES = (
    "INVALID_INPUT",
    "UNKNOWN_TOOL",
    "RESOURCE_LIMIT",
    "LICENSE_DENIED",
    "BACKEND_UNAVAILABLE",
    "DEPENDENCY_MISSING",
    "VERIFICATION_FAILED",
    "CONTRACT_VIOLATION",
    "INTEGRITY_FAILED",
    "IO_ERROR",
    "NETWORK_DISABLED",
    "NETWORK_REQUIRED",
    "PERMISSION_DENIED",
    "PROTOCOL_ERROR",
    "RUNTIME_ERROR",
)

ERROR_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "code": {"type": "string", "enum": list(STABLE_ERROR_CODES)},
        "type": {"type": "string"},
        "message": {"type": "string"},
        "path": {"type": "string"},
    },
    "required": ["code", "type", "message"],
    "additionalProperties": False,
}

RESULT_OUTPUT_SCHEMA: dict[str, Any] = {
    "$schema": SCHEMA_DIALECT,
    "$id": SCHEMA_ID_BASE + "envelope.schema.json",
    "type": "object",
    "title": "QECTORToolResult",
    "description": "Machine-verifiable QECTOR MCP result envelope (contract 2.0).",
    "required": [
        "contract_version",
        "tool",
        "status",
        "claim_class",
        "provenance",
        "runtime",
        "scope",
        "verification",
        "artifact",
        "warnings",
        "result",
    ],
    "properties": {
        "contract_version": {"type": "string", "const": CONTRACT_VERSION},
        "tool": {"type": "string", "pattern": "^[a-z][a-z0-9_]{0,63}$"},
        "status": {"type": "string", "enum": list(RESULT_STATUSES)},
        "claim_class": {"type": "string", "enum": list(CLAIM_CLASSES)},
        "provenance": {
            "type": "object",
            "required": ["server", "server_version", "reference_manual", "mcp_sdk"],
            "properties": {
                "server": {"type": "string"},
                "server_version": {"type": "string"},
                "reference_manual": {"type": ["string", "null"]},
                "mcp_sdk": {"type": "string"},
                "contract_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
            },
            "additionalProperties": False,
        },
        "runtime": {
            "type": "object",
            "properties": {
                "qector_decoder_v3": {"type": ["string", "null"]},
                "elapsed_ms": {"type": "number", "minimum": 0},
            },
            "additionalProperties": False,
        },
        "scope": {
            "type": "object",
            "required": ["tool", "stability", "network", "performance_claim"],
            "properties": {
                "tool": {"type": "string"},
                "stability": {"type": "string", "enum": ["stable", "provisional", "admin", "control"]},
                "network": {
                    "type": "string",
                    "enum": [
                        "local_only",
                        "opt_in_pypi_freshness",
                        "disabled_air_gapped",
                        "package_installation_after_explicit_confirmation",
                        "local_process_only",
                    ],
                },
                "performance_claim": {"type": "string", "enum": ["none", "machine_scoped"]},
            },
            "additionalProperties": False,
        },
        "verification": {
            "type": "object",
            "required": ["status", "checks"],
            "properties": {
                "status": {"type": "string", "enum": list(VERIFICATION_STATUSES)},
                "checks": {"type": "array", "items": {"type": "string"}},
            },
            "additionalProperties": False,
        },
        "artifact": {"type": ["object", "null"], "additionalProperties": True},
        "warnings": {"type": "array", "items": {"type": "string"}},
        "audit": {
            "type": ["object", "null"],
            "properties": {
                "sequence": {"type": "integer", "minimum": 1},
                "record_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
            },
            "required": ["sequence", "record_sha256"],
            "additionalProperties": False,
        },
        "result": {"type": "object", "additionalProperties": True},
        "error": ERROR_SCHEMA,
    },
    "additionalProperties": False,
}


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def schema_sha256(schema: Mapping[str, Any]) -> str:
    return hashlib.sha256(canonical_json(schema).encode("utf-8")).hexdigest()


ENVELOPE_SCHEMA_SHA256 = schema_sha256(RESULT_OUTPUT_SCHEMA)


def output_schema_for(tool_name: str, *, surface: str | None = None) -> dict[str, Any]:
    """Envelope schema specialised with the tool's result schema.

    Error envelopes carry an empty ``result`` object, so the specialised
    ``result`` slot is a union of the typed result schema and ``{}``.
    """
    typed = result_schema_for(tool_name, surface=surface)
    schema = json.loads(json.dumps(RESULT_OUTPUT_SCHEMA))
    schema["$id"] = f"{SCHEMA_ID_BASE}{tool_name}.output.schema.json"
    schema["title"] = f"QECTORToolResult<{tool_name}>"
    schema["properties"]["result"] = {
        "oneOf": [
            typed,
            {
                "type": "object",
                "additionalProperties": False,
                "maxProperties": 0,
                "description": "Empty result carried by an error envelope.",
            },
        ]
    }
    return schema


# ---------------------------------------------------------------------------
# Tool classification
# ---------------------------------------------------------------------------

_REFERENCE_TOOLS = {"theorem_lookup", "glossary_lookup", "reproduction_command_lookup"}
_MEASURED_TOOLS = {"threshold_sweep", "hot_path_microbench", "hardware_probe"}
# Tools whose result may be labelled ``verified``: each one runs a check in
# this process (Theorem 1 parity gate, Theorem 2 coset scoring, or the
# SHA-256 manifest). Inventory and construction tools (build_code_from_matrix
# reports rank and shape; system_setup performs actions) verify nothing and
# therefore stay ``not_checked`` however successful they are.
_VERIFIED_TOOLS = {
    "decode_syndrome",
    "decode_single",
    "decode_faithfulness_check",
    "integrity_check",
}
# Check tools answer a yes/no question; a "no" is a verified answer, not a
# failure of the tool. The key named here carries that answer.
_ANSWER_TOOLS = {"decode_faithfulness_check": "syndrome_valid"}
_WRITING_TOOLS = {"threshold_sweep", "system_setup", "configure_claude_desktop", "workbench_probe"}
_NON_IDEMPOTENT_TOOLS = {
    "threshold_sweep",
    "system_setup",
    "configure_claude_desktop",
    "hot_path_microbench",
    "workbench_probe",
}
_OPEN_WORLD_TOOLS = {"compat_report", "env_block", "get_runtime_provenance", "system_setup", "workbench_probe"}
_DESTRUCTIVE_TOOLS = {"system_setup", "configure_claude_desktop"}
CONTROL_TOOLS = {"airgap_status", "integrity_check", "schema_catalog", "audit_log_status"}


def tool_annotations(tool_name: str) -> ToolAnnotations:
    """Return MCP behavioral hints for a QECTOR tool."""
    return make_annotations(
        read_only=tool_name not in _WRITING_TOOLS,
        destructive=tool_name in _DESTRUCTIVE_TOOLS,
        idempotent=tool_name not in _NON_IDEMPOTENT_TOOLS,
        open_world=tool_name in _OPEN_WORLD_TOOLS,
    )


def _normalize_input_schema(tool: Tool) -> dict[str, Any]:
    input_schema = tool_input_schema(tool)
    input_schema.setdefault("$schema", SCHEMA_DIALECT)
    input_schema.setdefault("$id", f"{SCHEMA_ID_BASE}{tool.name}.input.schema.json")
    input_schema.setdefault("title", tool.name)
    input_schema.setdefault("type", "object")
    input_schema.setdefault("properties", {})
    input_schema.setdefault("additionalProperties", False)
    Draft202012Validator.check_schema(input_schema)
    return input_schema


def apply_tool_contract(tools: Iterable[Tool], *, surface: str | None = None) -> list[Tool]:
    """Attach normalized input schemas, per-tool output schemas and annotations.

    The returned list is sorted by tool name so ``tools/list`` is
    deterministic across processes, SDK generations and Python versions.
    Schemas are checked against the 2020-12 meta-schema; a malformed
    schema fails at import time, never at call time.
    """
    normalized: list[Tool] = []
    for tool in tools:
        output_schema = output_schema_for(tool.name, surface=surface)
        Draft202012Validator.check_schema(output_schema)
        normalized.append(
            rebuild_tool(
                tool,
                input_schema=_normalize_input_schema(tool),
                output_schema=output_schema,
                annotations=tool.annotations or tool_annotations(tool.name),
            )
        )
    return sorted_tools(normalized)


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

_VALIDATOR_CACHE: dict[str, Draft202012Validator] = {}
_FORMAT_CHECKER = FormatChecker()


def _validator(schema: Mapping[str, Any]) -> Draft202012Validator:
    key = schema_sha256(schema)
    validator = _VALIDATOR_CACHE.get(key)
    if validator is None:
        validator = Draft202012Validator(dict(schema), format_checker=_FORMAT_CHECKER)
        _VALIDATOR_CACHE[key] = validator
    return validator


def _json_path(error: ValidationError) -> str:
    return "$" + "".join(
        f"[{part}]" if isinstance(part, int) else f".{part}" for part in error.absolute_path
    )


def validate_arguments(tool: Tool, arguments: Mapping[str, Any] | None) -> dict[str, Any]:
    """Validate *arguments* against the tool's input schema.

    Returns a plain ``dict`` copy. Raises :class:`QECTORSchemaError` with the
    first violation (deterministic ordering by path) on failure.
    """
    payload = dict(arguments or {})
    try:
        canonical_json(payload)
    except (TypeError, ValueError) as exc:
        raise QECTORSchemaError(tool.name, f"arguments are not JSON-serialisable: {exc}", "$") from exc
    validator = _validator(tool_input_schema(tool))
    # Take the first error lazily: iter_errors is a generator, so a 10^5-item
    # array with an out-of-range element fails in microseconds instead of
    # materialising one ValidationError per element. Keyword evaluation
    # order is fixed for a given schema, so the reported error is stable.
    first = next(iter(validator.iter_errors(payload)), None)
    if first is not None:
        raise QECTORSchemaError(tool.name, first.message, _json_path(first))
    return payload


def validate_envelope(tool: Tool, envelope: Mapping[str, Any]) -> None:
    """Validate an outgoing envelope against the tool's advertised output schema."""
    from qector_mcp_compat import tool_output_schema

    schema = tool_output_schema(tool)
    if schema is None:
        raise QECTORContractViolation(f"{tool.name}: tool advertises no outputSchema")
    validator = _validator(schema)
    first = next(iter(validator.iter_errors(dict(envelope))), None)
    if first is not None:
        raise QECTORContractViolation(
            f"{tool.name}: result violates its outputSchema at {_json_path(first)}: {first.message}"
        )


def check_schema(schema: Mapping[str, Any]) -> None:
    try:
        Draft202012Validator.check_schema(dict(schema))
    except SchemaError as exc:
        raise QECTORContractViolation(f"invalid JSON Schema: {exc.message}") from exc


# ---------------------------------------------------------------------------
# Envelopes
# ---------------------------------------------------------------------------


def _verification_state(tool_name: str, result: Mapping[str, Any]) -> tuple[str, list[str]]:
    if tool_name in _REFERENCE_TOOLS:
        return "reference_only", ["offline_reference_lookup"]
    if tool_name in _MEASURED_TOOLS:
        return "not_checked", ["measurement_scope_recorded"]
    if tool_name in _ANSWER_TOOLS:
        answer_key = _ANSWER_TOOLS[tool_name]
        if answer_key in result:
            return "verified", ["theorem_1_syndrome_faithfulness"]
        return "not_checked", []
    if tool_name in _VERIFIED_TOOLS:
        for key in ("faithful", "theorem_1_faithful", "theorem_1_syndrome_faithful", "passed", "syndrome_valid"):
            if key in result and result[key] is False:
                return "failed", [key]
        checks = ["runtime_contract"]
        if tool_name in {"decode_syndrome", "decode_single"}:
            checks.append("theorem_1_syndrome_faithfulness")
        if tool_name == "decode_single" and result.get("logical_failure") is not None:
            checks.append("theorem_2_logical_coset")
        if tool_name == "integrity_check":
            checks = ["sha256_manifest"]
        return "verified", checks
    return "not_checked", []


def _result_class(tool_name: str, verification_status: str) -> tuple[str, str]:
    if verification_status == "verified":
        return "verified", "runtime_verified"
    if verification_status == "failed":
        return "error", "verification_failed"
    if verification_status == "reference_only":
        return "reference_only", "reference_only"
    if tool_name in _MEASURED_TOOLS:
        return "measured", "machine_scoped_measurement"
    return "not_checked", "metadata_or_unverified"


def _scope(tool_name: str, stability: str) -> dict[str, Any]:
    network = "local_only"
    if tool_name in {"compat_report", "env_block", "get_runtime_provenance"}:
        network = "disabled_air_gapped" if env_flag("QECTOR_AIR_GAPPED", True) else "opt_in_pypi_freshness"
    elif tool_name == "system_setup":
        network = "package_installation_after_explicit_confirmation"
    elif tool_name == "workbench_probe":
        network = "local_process_only"
    return {
        "tool": tool_name,
        "stability": stability,
        "network": network,
        "performance_claim": "machine_scoped" if tool_name in _MEASURED_TOOLS else "none",
    }


def _sdk_version() -> str:
    from qector_mcp_compat import SDK_VERSION

    return SDK_VERSION


def result_envelope(
    result: Mapping[str, Any],
    *,
    tool_name: str,
    server_name: str,
    server_version: str,
    stability: str,
    elapsed_ms: float | None = None,
) -> dict[str, Any]:
    """Wrap a raw tool result in the common public result contract."""
    # Normalise before anything else: NaN/Infinity have no JSON encoding, so a
    # result carrying one is a contract violation reported as such rather than
    # a serialisation exception escaping the envelope.
    try:
        result = json_safe(dict(result))
    except ValueError as exc:
        raise QECTORContractViolation(
            f"{tool_name}: result is not JSON-encodable ({exc}); non-finite floats must be reported as null"
        ) from exc
    verification_status, checks = _verification_state(tool_name, result)
    status, claim_class = _result_class(tool_name, verification_status)
    reference_manual = result.get("reference_manual")
    warnings_value = result.get("warnings", [])
    if isinstance(warnings_value, list):
        warnings = [str(item) for item in warnings_value]
    elif warnings_value:
        warnings = [str(warnings_value)]
    else:
        warnings = []
    runtime: dict[str, Any] = {
        "qector_decoder_v3": result.get("qector_version") or result.get("qector_decoder_v3_version"),
    }
    if elapsed_ms is not None:
        runtime["elapsed_ms"] = round(float(elapsed_ms), 3)
    envelope: dict[str, Any] = {
        "contract_version": CONTRACT_VERSION,
        "tool": tool_name,
        "status": status,
        "claim_class": claim_class,
        "provenance": {
            "server": server_name,
            "server_version": server_version,
            "reference_manual": reference_manual if isinstance(reference_manual, str) else None,
            "mcp_sdk": _sdk_version(),
            "contract_sha256": ENVELOPE_SCHEMA_SHA256,
        },
        "runtime": runtime,
        "scope": _scope(tool_name, stability),
        "verification": {"status": verification_status, "checks": checks},
        "artifact": result.get("artifact") if isinstance(result.get("artifact"), dict) else None,
        "warnings": warnings,
        "result": json_safe(dict(result)),
    }
    if status == "error":
        # The result is kept: a failed in-process check is diagnosed from it
        # (which files mismatched, which syndrome bits differ). ``result`` is
        # ``{}`` only for errors raised before a result existed.
        integrity = tool_name == "integrity_check"
        envelope["error"] = {
            "code": "INTEGRITY_FAILED" if integrity else "VERIFICATION_FAILED",
            "type": "QECTORIntegrityError" if integrity else "QECTORFaithfulnessError",
            "message": f"{tool_name} reported a failed verification check: {checks}",
        }
    return envelope


_EXCEPTION_CODES: tuple[tuple[type, str], ...] = (
    (QECTORSchemaError, "INVALID_INPUT"),
    (QECTORUnknownToolError, "UNKNOWN_TOOL"),
    (QECTORResourceLimitError, "RESOURCE_LIMIT"),
    (QECTORNetworkDisabledError, "NETWORK_DISABLED"),
    (QECTORContractViolation, "CONTRACT_VIOLATION"),
    (QECTORIntegrityError, "INTEGRITY_FAILED"),
    (QECTORAuditWriteError, "IO_ERROR"),
    (PermissionError, "PERMISSION_DENIED"),
    (ImportError, "DEPENDENCY_MISSING"),
)


def error_code(exc: Exception) -> str:
    """Map exceptions to stable, client-safe QECTOR error codes."""
    for exc_type, code in _EXCEPTION_CODES:
        if isinstance(exc, exc_type):
            return code
    class_name = exc.__class__.__name__.lower()
    message = str(exc).lower()
    # Each server defines its own QECTORInputError / QECTORArtifactError
    # classes; map them by name before any message heuristic so an input
    # error whose text mentions "exceed" or "limit" is never misfiled.
    if class_name.endswith("inputerror"):
        return "INVALID_INPUT"
    if class_name.endswith("artifacterror"):
        return "IO_ERROR"
    if "license" in class_name or "license" in message:
        return "LICENSE_DENIED"
    if "network" in class_name or "pypi" in message or "urllib" in class_name:
        if "disabled" in message or "air-gapped" in message or "offline" in message:
            return "NETWORK_DISABLED"
        return "NETWORK_REQUIRED"
    if "protocol" in class_name or "jsonrpc" in message or "json-rpc" in message:
        return "PROTOCOL_ERROR"
    if "resource" in class_name or "limit" in class_name or "exceed" in message or "limit" in message:
        return "RESOURCE_LIMIT"
    if "faithfulness" in class_name or "verification" in message:
        return "VERIFICATION_FAILED"
    if "permission" in class_name or "approbation" in message:
        return "PERMISSION_DENIED"
    if "unsupported" in class_name or "unavailable" in message:
        return "BACKEND_UNAVAILABLE"
    if "import" in class_name or "dependency" in message:
        return "DEPENDENCY_MISSING"
    if "artifact" in class_name or isinstance(exc, OSError):
        return "IO_ERROR"
    if "input" in class_name or isinstance(exc, (TypeError, ValueError, KeyError)):
        return "INVALID_INPUT"
    return "RUNTIME_ERROR"


def error_envelope(
    exc: Exception,
    *,
    tool_name: str,
    server_name: str,
    server_version: str,
    stability: str,
    elapsed_ms: float | None = None,
) -> dict[str, Any]:
    runtime: dict[str, Any] = {}
    if elapsed_ms is not None:
        runtime["elapsed_ms"] = round(float(elapsed_ms), 3)
    error: dict[str, Any] = {
        "code": error_code(exc),
        "type": exc.__class__.__name__,
        "message": _safe_message(exc),
    }
    path = getattr(exc, "path", None)
    if isinstance(path, str) and path:
        error["path"] = path
    return {
        "contract_version": CONTRACT_VERSION,
        "tool": tool_name,
        "status": "error",
        "claim_class": "none",
        "provenance": {
            "server": server_name,
            "server_version": server_version,
            "reference_manual": None,
            "mcp_sdk": _sdk_version(),
            "contract_sha256": ENVELOPE_SCHEMA_SHA256,
        },
        "runtime": runtime,
        "scope": _scope(tool_name, stability),
        "verification": {"status": "not_checked", "checks": []},
        "artifact": None,
        "warnings": [],
        "result": {},
        "error": error,
    }


def redact_home(text: str) -> str:
    """Replace the user's home directory with ``~`` so envelopes never carry the account name."""
    home = str(Path.home())
    if home and home != "/" and home in text:
        return text.replace(home, "~")
    return text


def _safe_message(exc: Exception, limit: int = 2000) -> str:
    """Error text with the user's home directory redacted and length-capped."""
    message = redact_home(str(exc) or exc.__class__.__name__)
    if len(message) > limit:
        message = message[: limit - 3] + "..."
    return message


def json_safe(value: Any) -> Any:
    """Return a JSON-serialisable deep copy (Path -> str, numpy -> builtins)."""
    return json.loads(json.dumps(value, sort_keys=True, default=_json_default, allow_nan=False))


def _json_default(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "tolist"):
        return value.tolist()
    if hasattr(value, "item"):
        return value.item()
    if isinstance(value, (set, frozenset, tuple)):
        return sorted(value) if isinstance(value, (set, frozenset)) else list(value)
    return str(value)


def call_tool_result(envelope: Mapping[str, Any], *, is_error: bool = False):
    """Return both readable text and MCP structured content for a response."""
    try:
        json_safe_envelope = json_safe(dict(envelope))
    except ValueError as exc:
        # Last line of defence: an envelope that cannot be encoded is replaced
        # by a CONTRACT_VIOLATION error envelope that keeps the tool identity.
        scope = envelope.get("scope") if isinstance(envelope.get("scope"), Mapping) else {}
        provenance = envelope.get("provenance") if isinstance(envelope.get("provenance"), Mapping) else {}
        json_safe_envelope = json_safe(
            error_envelope(
                QECTORContractViolation(f"envelope is not JSON-encodable ({exc})"),
                tool_name=str(envelope.get("tool", "unknown_tool")),
                server_name=str(provenance.get("server", "unknown")),
                server_version=str(provenance.get("server_version", "unknown")),
                stability=str(scope.get("stability", "stable")),
            )
        )
        is_error = True
    return make_call_tool_result(
        json_safe_envelope,
        is_error=is_error or json_safe_envelope.get("status") == "error",
    )


def tool_name_is_valid(name: str) -> bool:
    import re

    return bool(re.fullmatch(r"[a-z][a-z0-9_]{0,63}", name or ""))
