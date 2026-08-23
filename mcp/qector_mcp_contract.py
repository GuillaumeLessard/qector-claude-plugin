"""Shared MCP result, error, schema, and behavior contracts for QECTOR."""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any, Iterable, Mapping

from mcp.types import CallToolResult, TextContent, Tool, ToolAnnotations


class QECTORResourceLimitError(RuntimeError):
    """Raised when a per-process tool call budget is exhausted."""


# Per-process ceilings for tools that write, launch, or run unbounded
# compute. Zero or a missing env override means "use the default"; a
# negative env value disables the budget for that tool (operator override).
_CALL_BUDGET_DEFAULTS = {
    "threshold_sweep": 8,
    "decode_single": 64,
    "decode_syndrome": 256,
    "build_code_from_matrix": 32,
    "hot_path_microbench": 4,
    "system_setup": 2,
    "configure_claude_desktop": 2,
    "workbench_probe": 2,
}


class _CallBudget:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counts: dict[str, int] = {}

    def consume(self, tool_name: str) -> None:
        limit = _budget_for(tool_name)
        if limit is None:
            return
        with self._lock:
            count = self._counts.get(tool_name, 0) + 1
            if count > limit:
                raise QECTORResourceLimitError(
                    f"tool {tool_name!r} exceeded the per-process call limit "
                    f"of {limit}; restart the MCP server or raise "
                    f"QECTOR_MCP_MAX_CALLS_{tool_name.upper()}"
                )
            self._counts[tool_name] = count

    def reset(self) -> None:
        with self._lock:
            self._counts.clear()

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
            raise QECTORResourceLimitError(
                f"{env_name} must be an integer"
            ) from exc
        if value < 0:
            return None
        return value
    return _CALL_BUDGET_DEFAULTS.get(tool_name)


def consume_call_budget(tool_name: str) -> None:
    """Charge one call against the process budget for *tool_name*."""
    _PROCESS_BUDGET.consume(tool_name)


def reset_call_budget() -> None:
    """Test helper: clear the process-local call counters."""
    _PROCESS_BUDGET.reset()


def call_budget_snapshot() -> dict[str, int]:
    return _PROCESS_BUDGET.snapshot()

RESULT_STATUSES = (
    "verified",
    "reference_only",
    "measured",
    "not_checked",
    "error",
)
VERIFICATION_STATUSES = (
    "verified",
    "not_checked",
    "failed",
    "not_applicable",
    "reference_only",
)

RESULT_OUTPUT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "title": "QECTORToolResult",
    "description": "Machine-verifiable QECTOR MCP result envelope.",
    "required": [
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
        "status": {"type": "string", "enum": list(RESULT_STATUSES)},
        "claim_class": {"type": "string"},
        "provenance": {"type": "object", "additionalProperties": True},
        "runtime": {"type": "object", "additionalProperties": True},
        "scope": {"type": "object", "additionalProperties": True},
        "verification": {
            "type": "object",
            "required": ["status", "checks"],
            "properties": {
                "status": {
                    "type": "string",
                    "enum": list(VERIFICATION_STATUSES),
                },
                "checks": {"type": "array", "items": {"type": "string"}},
            },
            "additionalProperties": True,
        },
        "artifact": {"type": ["object", "null"], "additionalProperties": True},
        "warnings": {"type": "array", "items": {"type": "string"}},
        "result": {"type": "object", "additionalProperties": True},
        "error": {
            "type": "object",
            "properties": {
                "code": {"type": "string"},
                "type": {"type": "string"},
                "message": {"type": "string"},
            },
            "required": ["code", "type", "message"],
            "additionalProperties": False,
        },
    },
    "additionalProperties": False,
}

_REFERENCE_TOOLS = {
    "theorem_lookup",
    "glossary_lookup",
    "reproduction_command_lookup",
}
_MEASURED_TOOLS = {
    "threshold_sweep",
    "hot_path_microbench",
    "hardware_probe",
}
_VERIFIED_TOOLS = {
    "decode_syndrome",
    "decode_single",
    "decode_faithfulness_check",
    "build_code_from_matrix",
    "system_setup",
}
_WRITING_TOOLS = {
    "threshold_sweep",
    "system_setup",
    "configure_claude_desktop",
    "workbench_probe",
}
_NON_IDEMPOTENT_TOOLS = {
    "threshold_sweep",
    "system_setup",
    "configure_claude_desktop",
    "hot_path_microbench",
    "workbench_probe",
}
_OPEN_WORLD_TOOLS = {
    "compat_report",
    "env_block",
    "get_runtime_provenance",
    "system_setup",
    "workbench_probe",
}


def tool_annotations(tool_name: str) -> ToolAnnotations:
    """Return MCP behavioral hints for a QECTOR tool."""
    return ToolAnnotations(
        readOnlyHint=tool_name not in _WRITING_TOOLS,
        destructiveHint=tool_name in {"system_setup", "configure_claude_desktop"},
        idempotentHint=tool_name not in _NON_IDEMPOTENT_TOOLS,
        openWorldHint=tool_name in _OPEN_WORLD_TOOLS,
    )


def apply_tool_contract(tools: Iterable[Tool]) -> list[Tool]:
    """Attach the shared output schema and behavior annotations to tools.

    The returned list is sorted by tool name so ``tools/list`` is
    deterministic across processes and Python versions.
    """
    normalized: list[Tool] = []
    for tool in tools:
        input_schema = dict(tool.inputSchema)
        input_schema.setdefault("$schema", "https://json-schema.org/draft/2020-12/schema")
        input_schema.setdefault("title", tool.name)
        input_schema.setdefault("additionalProperties", False)
        normalized.append(
            tool.model_copy(
                update={
                    "inputSchema": input_schema,
                    "outputSchema": RESULT_OUTPUT_SCHEMA,
                    "annotations": tool.annotations or tool_annotations(tool.name),
                }
            )
        )
    return sorted(normalized, key=lambda item: item.name)


def _verification_state(tool_name: str, result: Mapping[str, Any]) -> tuple[str, list[str]]:
    if tool_name in _REFERENCE_TOOLS:
        return "reference_only", ["offline_reference_lookup"]
    if tool_name in _MEASURED_TOOLS:
        return "not_checked", ["measurement_scope_recorded"]
    if tool_name in _VERIFIED_TOOLS:
        for key in (
            "faithful",
            "theorem_1_faithful",
            "theorem_1_syndrome_faithful",
            "passed",
        ):
            if key in result and result[key] is False:
                return "failed", [key]
        return "verified", ["runtime_contract"]
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
    if tool_name in {"compat_report", "env_block"}:
        network = "opt_in_pypi_freshness"
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


def result_envelope(
    result: Mapping[str, Any],
    *,
    tool_name: str,
    server_name: str,
    server_version: str,
    stability: str,
) -> dict[str, Any]:
    """Wrap a raw tool result in the common public result contract."""
    verification_status, checks = _verification_state(tool_name, result)
    status, claim_class = _result_class(tool_name, verification_status)
    reference_manual = result.get("reference_manual")
    warnings_value = result.get("warnings", [])
    warnings = (
        [str(item) for item in warnings_value]
        if isinstance(warnings_value, list)
        else [str(warnings_value)]
        if warnings_value
        else []
    )
    return {
        "status": status,
        "claim_class": claim_class,
        "provenance": {
            "server": server_name,
            "server_version": server_version,
            "reference_manual": reference_manual,
        },
        "runtime": {
            "qector_decoder_v3": result.get("qector_version")
            or result.get("qector_decoder_v3_version"),
        },
        "scope": _scope(tool_name, stability),
        "verification": {
            "status": verification_status,
            "checks": checks,
        },
        "artifact": result.get("artifact"),
        "warnings": warnings,
        "result": dict(result),
    }


def error_code(exc: Exception) -> str:
    """Map exceptions to stable, client-safe QECTOR error codes."""
    class_name = exc.__class__.__name__.lower()
    message = str(exc).lower()
    if "license" in class_name or "license" in message:
        return "LICENSE_DENIED"
    if "network" in class_name or "pypi" in message or "urllib" in class_name:
        if "disabled" in message or "air-gapped" in message or "offline" in message:
            return "NETWORK_DISABLED"
        return "NETWORK_REQUIRED"
    if "protocol" in class_name or "jsonrpc" in message or "json-rpc" in message:
        return "PROTOCOL_ERROR"
    if (
        "resource" in class_name
        or "limit" in class_name
        or "exceed" in message
        or "limit" in message
    ):
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
    if "input" in class_name or isinstance(exc, (TypeError, ValueError)):
        return "INVALID_INPUT"
    return "RUNTIME_ERROR"


def error_envelope(
    exc: Exception,
    *,
    tool_name: str,
    server_name: str,
    server_version: str,
    stability: str,
) -> dict[str, Any]:
    return {
        "status": "error",
        "claim_class": "none",
        "provenance": {
            "server": server_name,
            "server_version": server_version,
            "reference_manual": None,
        },
        "runtime": {},
        "scope": _scope(tool_name, stability),
        "verification": {"status": "not_checked", "checks": []},
        "artifact": None,
        "warnings": [],
        "result": {},
        "error": {
            "code": error_code(exc),
            "type": exc.__class__.__name__,
            "message": str(exc),
        },
    }


def call_tool_result(envelope: Mapping[str, Any], *, is_error: bool = False) -> CallToolResult:
    """Return both readable text and MCP structured content for a response."""
    json_safe_envelope = json.loads(json.dumps(envelope, sort_keys=True, default=_json_default))
    return CallToolResult(
        content=[
            TextContent(
                type="text",
                text=json.dumps(json_safe_envelope, sort_keys=True),
            )
        ],
        structuredContent=json_safe_envelope,
        isError=is_error or json_safe_envelope.get("status") == "error",
    )


def _json_default(value: Any) -> str:
    if isinstance(value, Path):
        return str(value)
    return str(value)
