"""Explicitly enabled administrative MCP server for QECTOR.

This server is intentionally separate from the stable library and research
servers. It is never registered by default. Every operation requires both
``QECTOR_ADMIN_ENABLED=1`` in the server environment and ``confirm=true`` in
the tool call.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import os
import re
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

from mcp.types import CallToolResult, ServerCapabilities, Tool, ToolsCapability

_MCP_DIR = Path(__file__).resolve().parent
if str(_MCP_DIR) not in sys.path:
    sys.path.insert(0, str(_MCP_DIR))

from qector_mcp_contract import (  # noqa: E402
    apply_tool_contract,
    call_tool_result,
    consume_call_budget,
    error_envelope,
    result_envelope,
)

import mcp_server_qector_bench as research  # noqa: E402

SERVER_NAME = "qector-admin-mcp"
SERVER_VERSION = research.SERVER_VERSION
_TRUE_VALUES = {"1", "true", "yes", "on"}
_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


class QECTORAdminPermissionError(PermissionError):
    """Raised when a privileged operation has not been explicitly enabled."""


def _require_admin_enabled(confirm: bool) -> None:
    if os.environ.get("QECTOR_ADMIN_ENABLED", "").strip().lower() not in _TRUE_VALUES:
        raise QECTORAdminPermissionError(
            "qector-admin is disabled; set QECTOR_ADMIN_ENABLED=1 in the "
            "server environment before exposing administrative tools"
        )
    if confirm is not True:
        raise QECTORAdminPermissionError(
            "explicit confirmation is required; repeat the call with confirm=true"
        )


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _approved_workbench_path(executable: str, expected_sha256: str) -> Path:
    if not isinstance(executable, str) or not executable.strip():
        raise research.QECTORInputError("executable must be a non-empty path string")
    if not isinstance(expected_sha256, str) or not _SHA256_RE.fullmatch(expected_sha256):
        raise research.QECTORInputError("expected_sha256 must be a 64-character SHA-256 digest")
    root_value = os.environ.get("QECTOR_WORKBENCH_DIR")
    if not root_value:
        raise QECTORAdminPermissionError(
            "QECTOR_WORKBENCH_DIR must name the approved Workbench directory"
        )
    root = Path(root_value).expanduser().resolve()
    candidate = Path(executable).expanduser().resolve()
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise QECTORAdminPermissionError(
            "Workbench executable must remain inside QECTOR_WORKBENCH_DIR"
        ) from exc
    if not candidate.is_file():
        raise research.QECTORInputError(f"Workbench executable not found: {candidate}")
    if not candidate.name.lower().startswith("qector-workbench"):
        raise QECTORAdminPermissionError(
            "Workbench executable name must start with 'qector-workbench'"
        )
    actual_sha256 = _sha256_file(candidate)
    if actual_sha256.lower() != expected_sha256.lower():
        raise QECTORAdminPermissionError(
            "Workbench SHA-256 does not match the user-approved expected_sha256"
        )
    return candidate


def system_setup(
    confirm: bool = False,
    profile: str = "production",
    install_requirements: bool = True,
    create_artifact_dir: bool = True,
    run_validation_test: bool = True,
) -> dict[str, Any]:
    _require_admin_enabled(confirm)
    return research.tool_system_setup(
        confirm=confirm,
        profile=profile,
        install_requirements=install_requirements,
        create_artifact_dir=create_artifact_dir,
        run_validation_test=run_validation_test,
    )


def configure_claude_desktop(
    confirm: bool = False,
    remove: bool = False,
    python_path: str | None = None,
) -> dict[str, Any]:
    _require_admin_enabled(confirm)
    return research.tool_configure_claude_desktop(
        confirm=confirm, remove=remove, python_path=python_path
    )


def workbench_probe(
    executable: str,
    expected_sha256: str,
    confirm: bool = False,
    timeout: float = 60.0,
    list_tools: bool = True,
    limit: int | None = None,
) -> dict[str, Any]:
    _require_admin_enabled(confirm)
    approved_executable = _approved_workbench_path(executable, expected_sha256)
    result = research._subprocess_workbench_probe(
        str(approved_executable), timeout, list_tools, limit
    )
    result["approved_executable_sha256"] = expected_sha256.lower()
    result["approval"] = {
        "environment_flag": "QECTOR_ADMIN_ENABLED",
        "workbench_root": os.environ["QECTOR_WORKBENCH_DIR"],
        "confirm": True,
    }
    return result


TOOL_FUNCTIONS = {
    "system_setup": system_setup,
    "configure_claude_desktop": configure_claude_desktop,
    "workbench_probe": workbench_probe,
}

TOOL_DEFAULTS = {
    "system_setup": {
        "confirm": False,
        "profile": "production",
        "install_requirements": True,
        "create_artifact_dir": True,
        "run_validation_test": True,
    },
    "configure_claude_desktop": {
        "confirm": False,
        "remove": False,
        "python_path": None,
    },
    "workbench_probe": {
        "confirm": False,
        "timeout": 60.0,
        "list_tools": True,
        "limit": None,
    },
}


def dispatch_tool(name: str, arguments: Mapping[str, Any] | None = None) -> dict[str, Any]:
    function = TOOL_FUNCTIONS.get(name)
    if function is None:
        raise research.QECTORInputError(
            f"Unknown tool {name!r}; choose one of {sorted(TOOL_FUNCTIONS)}"
        )
    merged = dict(TOOL_DEFAULTS[name])
    if arguments:
        merged.update(dict(arguments))
    consume_call_budget(name)
    return function(**merged)


def _tool_schema() -> list[Tool]:
    admin_annotations = {
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": False,
        "openWorldHint": False,
    }
    return [
        Tool(
            name="system_setup",
            description=(
                "Privileged local setup using a fixed package profile. Disabled "
                "unless QECTOR_ADMIN_ENABLED=1 and confirm=true."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "confirm": {"type": "boolean", "default": False},
                    "profile": {
                        "type": "string",
                        "enum": sorted(research.SETUP_PROFILES),
                        "default": "production",
                    },
                    "install_requirements": {"type": "boolean", "default": True},
                    "create_artifact_dir": {"type": "boolean", "default": True},
                    "run_validation_test": {"type": "boolean", "default": True},
                },
                "additionalProperties": False,
            },
            annotations=admin_annotations,
        ),
        Tool(
            name="configure_claude_desktop",
            description=(
                "Privileged local Claude Desktop configuration. Disabled unless "
                "QECTOR_ADMIN_ENABLED=1 and confirm=true."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "confirm": {"type": "boolean", "default": False},
                    "remove": {"type": "boolean", "default": False},
                    "python_path": {"type": ["string", "null"], "default": None},
                },
                "additionalProperties": False,
            },
            annotations=admin_annotations,
        ),
        Tool(
            name="workbench_probe",
            description=(
                "Privileged local Workbench probe. Requires an approved directory, "
                "an expected SHA-256 digest, and confirm=true."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "executable": {"type": "string"},
                    "expected_sha256": {
                        "type": "string",
                        "pattern": "^[0-9a-fA-F]{64}$",
                    },
                    "confirm": {"type": "boolean", "default": False},
                    "timeout": {"type": "number", "minimum": 0.1, "maximum": 300, "default": 60.0},
                    "list_tools": {"type": "boolean", "default": True},
                    "limit": {"type": ["integer", "null"], "minimum": 1, "default": None},
                },
                "required": ["executable", "expected_sha256"],
                "additionalProperties": False,
            },
            annotations={**admin_annotations, "openWorldHint": True},
        ),
    ]


TOOLS = apply_tool_contract(_tool_schema())


def _error_payload(exc: Exception) -> dict[str, Any]:
    return {
        "error": {
            "type": exc.__class__.__name__,
            "message": str(exc),
            "verified": False,
        }
    }


async def _dispatch_mcp_call(
    name: str, arguments: Mapping[str, Any] | None
) -> CallToolResult:
    try:
        result = dispatch_tool(name, arguments)
        return call_tool_result(
            result_envelope(
                result,
                tool_name=name,
                server_name=SERVER_NAME,
                server_version=SERVER_VERSION,
                stability="admin",
            )
        )
    except Exception as exc:
        return call_tool_result(
            error_envelope(
                exc,
                tool_name=name,
                server_name=SERVER_NAME,
                server_version=SERVER_VERSION,
                stability="admin",
            ),
            is_error=True,
        )


def _build_low_level_server() -> Any:
    if research._LowLevelServer is None:
        raise RuntimeError("No supported low-level MCP server implementation is installed")
    server = research._LowLevelServer(
        SERVER_NAME,
        version=SERVER_VERSION,
        instructions=(
            "Explicitly enabled QECTOR administrative tools. Every call requires "
            "QECTOR_ADMIN_ENABLED=1 and confirm=true."
        ),
    )

    @server.list_tools()
    async def _list_tools() -> list[Tool]:
        return TOOLS

    @server.call_tool()
    async def _call_tool(
        name: str, arguments: dict[str, Any]
    ) -> CallToolResult:
        return await _dispatch_mcp_call(name, arguments)

    return server


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Explicitly enabled QECTOR administrative MCP server"
    )
    parser.add_argument("--transport", choices=("stdio",), default="stdio")
    parser.parse_args(argv)
    server = _build_low_level_server()
    from mcp.server.models import InitializationOptions
    from mcp.server.stdio import stdio_server

    initialization_options = InitializationOptions(
        server_name=SERVER_NAME,
        server_version=SERVER_VERSION,
        capabilities=ServerCapabilities(tools=ToolsCapability(listChanged=False)),
    )

    async def run_server() -> None:
        async with stdio_server() as (read, write):
            await server.run(read, write, initialization_options)

    asyncio.run(run_server())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
