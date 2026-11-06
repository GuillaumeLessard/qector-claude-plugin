"""Explicitly enabled administrative MCP server for QECTOR.

This server is intentionally separate from the stable library and research
servers. It is never registered by default. Every operation requires both
``QECTOR_ADMIN_ENABLED=1`` in the server environment and ``confirm=true`` in
the tool call.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

_MCP_DIR = Path(__file__).resolve().parent
if str(_MCP_DIR) not in sys.path:
    sys.path.insert(0, str(_MCP_DIR))

from qector_mcp_compat import build_server, make_annotations, make_tool, run_stdio  # noqa: E402
from qector_mcp_contract import (  # noqa: E402
    QECTORUnknownToolError,
    apply_tool_contract,
    call_tool_result,
    consume_call_budget,
    error_envelope,
    refund_call_budget,
    result_envelope,
    validate_arguments,
    validate_envelope,
)
import qector_airgap  # noqa: E402

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
    offline_wheelhouse: str | None = None,
) -> dict[str, Any]:
    _require_admin_enabled(confirm)
    return research.tool_system_setup(
        confirm=confirm,
        profile=profile,
        install_requirements=install_requirements,
        create_artifact_dir=create_artifact_dir,
        run_validation_test=run_validation_test,
        offline_wheelhouse=offline_wheelhouse,
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
        "offline_wheelhouse": None,
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
    try:
        return function(**merged)
    except (QECTORAdminPermissionError, research.QECTORInputError, TypeError):
        # A refused call (admin disabled, confirm missing, bad arguments)
        # performed no action and must not spend the per-process budget
        # that a later, properly confirmed call needs.
        refund_call_budget(name)
        raise


def _tool_schema() -> list[Any]:
    admin_annotations = make_annotations(read_only=False, destructive=True, idempotent=False, open_world=False)
    admin_open_world = make_annotations(read_only=False, destructive=True, idempotent=False, open_world=True)
    return [
        make_tool(
            name="system_setup",
            description=(
                "Privileged local setup using a fixed package profile. Disabled "
                "unless QECTOR_ADMIN_ENABLED=1 and confirm=true. In air-gapped mode "
                "(default) package installation requires offline_wheelhouse."
            ),
            input_schema={
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
                    "offline_wheelhouse": {
                        "type": ["string", "null"],
                        "maxLength": 4096,
                        "default": None,
                        "description": (
                            "Directory of pre-downloaded wheels (scripts/build_wheelhouse.py). "
                            "Required for installs in air-gapped mode; pip then runs with --no-index."
                        ),
                    },
                },
                "additionalProperties": False,
            },
            annotations=admin_annotations,
        ),
        make_tool(
            name="configure_claude_desktop",
            description=(
                "Privileged local Claude Desktop configuration. Disabled unless "
                "QECTOR_ADMIN_ENABLED=1 and confirm=true."
            ),
            input_schema={
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
        make_tool(
            name="workbench_probe",
            description=(
                "Privileged local Workbench probe. Requires an approved directory, "
                "an expected SHA-256 digest, and confirm=true."
            ),
            input_schema={
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
            annotations=admin_open_world,
        ),
    ]


TOOLS = apply_tool_contract(_tool_schema(), surface="admin")
TOOL_BY_NAME = {tool.name: tool for tool in TOOLS}


async def _dispatch_mcp_call(name: str, arguments: Mapping[str, Any] | None):
    started = time.perf_counter()
    try:
        tool = TOOL_BY_NAME.get(name)
        if tool is None:
            raise QECTORUnknownToolError(f"Unknown tool {name!r}; choose one of {sorted(TOOL_BY_NAME)}")
        validated = validate_arguments(tool, arguments)
        result = dispatch_tool(name, validated)
        envelope = result_envelope(
            result,
            tool_name=name,
            server_name=SERVER_NAME,
            server_version=SERVER_VERSION,
            stability="admin",
            elapsed_ms=(time.perf_counter() - started) * 1e3,
        )
        validate_envelope(tool, envelope)
        return call_tool_result(envelope)
    except Exception as exc:
        return call_tool_result(
            error_envelope(
                exc,
                tool_name=name if name in TOOL_BY_NAME else "unknown_tool",
                server_name=SERVER_NAME,
                server_version=SERVER_VERSION,
                stability="admin",
                elapsed_ms=(time.perf_counter() - started) * 1e3,
            ),
            is_error=True,
        )


INSTRUCTIONS = (
    "Explicitly enabled QECTOR administrative tools. Every call requires "
    "QECTOR_ADMIN_ENABLED=1 and confirm=true. Package installation is refused "
    "in air-gapped mode unless an offline wheelhouse is supplied."
)


def _build_low_level_server() -> Any:
    async def _list_tools():
        return TOOLS

    return build_server(
        name=SERVER_NAME,
        version=SERVER_VERSION,
        instructions=INSTRUCTIONS,
        list_tools=_list_tools,
        call_tool=_dispatch_mcp_call,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Explicitly enabled QECTOR administrative MCP server")
    parser.add_argument("--transport", choices=("stdio",), default="stdio")
    parser.parse_args(argv)
    # The admin server legitimately launches pip and the approved Workbench
    # binary, so the subprocess guard is not installed; the network guard is.
    qector_airgap.install(allow_subprocess=True)
    server = _build_low_level_server()
    run_stdio(server, name=SERVER_NAME, version=SERVER_VERSION, instructions=INSTRUCTIONS)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
