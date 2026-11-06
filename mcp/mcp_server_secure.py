"""qector-secure: the hardened, air-gapped QECTOR MCP server (2.0.0).

This is the single entry point recommended for laboratories, regulated
estates and the Claude Desktop bundle. It re-exports the eight stable
library tools (and, with ``--profile research``, the 29 provisional
research tools) behind one control plane that enforces:

* **Schema validation both ways.** Arguments are validated against the
  tool's JSON Schema 2020-12 ``inputSchema`` before any decoder code runs;
  the finished envelope is validated against the tool's advertised
  ``outputSchema`` before it is written to the client. Either failure is
  a stable error (``INVALID_INPUT`` / ``CONTRACT_VIOLATION``), never a
  stack trace and never a half-shaped result.
* **Air-gap by default.** ``qector_airgap.install()`` runs before the
  first byte of MCP traffic: non-loopback sockets, ``urllib`` and
  ``subprocess`` fail closed, billing variables are scrubbed, and the
  opt-in PyPI check is refused with ``NETWORK_DISABLED``.
  ``--allow-network`` is the only way to lift it, and it is logged. The
  opt-in PyPI check then reports ``pypi_freshness.status: "disabled"`` with
  a warning (not an error envelope); ``NETWORK_DISABLED`` is the error code
  a tool returns if a network path were ever reached despite that.
* **Runtime integrity.** ``INTEGRITY.json`` (SHA-256 of every runtime
  file) is verified at startup; strict mode (the default) refuses to serve
  from a modified or unmanifested tree. Releases ship ``INTEGRITY.json.sig``
  (Ed25519); pin the published key with ``QECTOR_INTEGRITY_PUBKEY`` and the
  gate also proves origin, not only consistency.
* **Hash-chained audit log** (``QECTOR_AUDIT_DIR`` / ``--audit-dir``):
  one append-only JSONL record per call, each bound to the previous
  record's digest; arguments are logged only as a SHA-256.
* **Resource ceilings.** Request size cap, per-tool call budgets and a
  per-minute rate limit shared with the library server.
* **Transport.** Local stdio only. There is intentionally no HTTP, SSE or
  WebSocket listener in this process; see SECURITY.md for why.

Four control-plane tools make the posture inspectable from the client:
``airgap_status``, ``integrity_check``, ``schema_catalog`` and
``audit_log_status``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

_MCP_DIR = Path(__file__).resolve().parent
_ROOT = _MCP_DIR.parent
if str(_MCP_DIR) not in sys.path:
    sys.path.insert(0, str(_MCP_DIR))

import qector_airgap  # noqa: E402
import qector_integrity  # noqa: E402
from qector_audit import AuditLog, QECTORAuditError, audit_log_from_env  # noqa: E402
from qector_mcp_compat import (  # noqa: E402
    SDK_VERSION,
    build_server,
    make_tool,
    rebuild_tool,
    run_stdio,
    sdk_supported,
    tool_annotations_dict,
    tool_input_schema,
    tool_output_schema,
)
from qector_mcp_contract import (  # noqa: E402
    CONTRACT_VERSION,
    RESULT_OUTPUT_SCHEMA,
    QECTORAuditWriteError,
    QECTORIntegrityError,
    QECTORSchemaError,
    QECTORUnknownToolError,
    apply_tool_contract,
    call_tool_result,
    canonical_json,
    consume_call_budget,
    env_flag,
    error_envelope,
    result_envelope,
    schema_sha256,
    validate_arguments,
    validate_envelope,
)
from qector_schemas import SCHEMA_DIALECT  # noqa: E402

# The decoder-facing modules are imported in configure() only AFTER the
# integrity gate has verified them, so a modified mcp_server_library.py can
# never execute before its hash has been checked. ``library`` is bound
# there; ``research`` is bound by assemble_tools() when the profile asks.
library: Any = None

SERVER_NAME = "qector-secure-mcp"
SERVER_VERSION = "2.0.1"
REF_DOI = "10.5281/zenodo.21941046"
PROFILES = ("safe", "research")
RESEARCH_COMPAT_ALIAS = "research_compat_report"
DEFAULT_MAX_REQUEST_BYTES = 2 * 1024 * 1024

EXIT_BAD_ARGUMENTS = 2
EXIT_INTEGRITY = 3
EXIT_SDK = 4
EXIT_AUDIT = 5
EXIT_DEPENDENCY = 6


class QECTORDependencyError(RuntimeError):
    """Raised when the decoder wheel or numpy cannot be imported."""


class SecureServerState:
    """Process-wide configuration resolved once in :func:`configure`."""

    def __init__(self) -> None:
        self.profile = "safe"
        self.max_request_bytes = DEFAULT_MAX_REQUEST_BYTES
        self.strict_integrity = True
        self.integrity_manifest: Path | None = None
        self.integrity_pubkey: str | None = None
        self.integrity_report: dict[str, Any] | None = None
        self.audit: AuditLog = AuditLog(None, server=SERVER_NAME, server_version=SERVER_VERSION)
        self.tools: list[Any] = []
        self.tool_by_name: dict[str, Any] = {}
        self.stability: dict[str, str] = {}
        self.research: Any = None


STATE = SecureServerState()


# ---------------------------------------------------------------------------
# Control-plane tools
# ---------------------------------------------------------------------------


def airgap_status() -> dict[str, Any]:
    status = qector_airgap.status()
    status["reference_manual"] = REF_DOI
    return status


def integrity_check() -> dict[str, Any]:
    report = qector_integrity.verify(
        _ROOT,
        strict=STATE.strict_integrity,
        manifest_path=STATE.integrity_manifest,
        pinned_public_key=STATE.integrity_pubkey,
    )
    STATE.integrity_report = report
    report = dict(report)
    report["reference_manual"] = REF_DOI
    if report["passed"] and not report["signature"]["valid"]:
        report["warnings"] = [
            "runtime files match INTEGRITY.json but no valid signature proves its origin "
            f"({report['signature']['reason']}); pin QECTOR_INTEGRITY_PUBKEY on a signed release for origin proof"
        ]
    if not report["passed"]:
        report["warnings"] = [
            "runtime files differ from INTEGRITY.json; the server is running unverified code"
            if report["manifest_present"]
            else "INTEGRITY.json is absent; run scripts/generate_integrity_manifest.py before release"
        ]
    return report


def schema_catalog() -> dict[str, Any]:
    tools: dict[str, Any] = {}
    for tool in STATE.tools:
        input_schema = tool_input_schema(tool)
        output_schema = tool_output_schema(tool) or {}
        tools[tool.name] = {
            "input_schema": input_schema,
            "output_schema": output_schema,
            "annotations": tool_annotations_dict(tool) or {},
            "stability": STATE.stability.get(tool.name, "stable"),
            "input_sha256": schema_sha256(input_schema),
            "output_sha256": schema_sha256(output_schema),
        }
    catalog = {
        "dialect": SCHEMA_DIALECT,
        "contract_version": CONTRACT_VERSION,
        "envelope": RESULT_OUTPUT_SCHEMA,
        "tools": tools,
    }
    catalog["catalog_sha256"] = hashlib.sha256(canonical_json(catalog).encode("utf-8")).hexdigest()
    catalog["reference_manual"] = REF_DOI
    return catalog


def audit_log_status() -> dict[str, Any]:
    status = STATE.audit.status()
    status["reference_manual"] = REF_DOI
    return status


CONTROL_FUNCTIONS: dict[str, Callable[..., dict[str, Any]]] = {
    "airgap_status": airgap_status,
    "integrity_check": integrity_check,
    "schema_catalog": schema_catalog,
    "audit_log_status": audit_log_status,
}


def _control_tool_schema() -> list[Any]:
    empty = {"type": "object", "properties": {}, "additionalProperties": False}
    return [
        make_tool(
            name="airgap_status",
            description=(
                "Report the live network posture of this server process: air-gap mode and its source, "
                "which Python-level guards are installed, scrubbed billing variables, blocked attempts, "
                "and an honest statement of the decoder wheel's native network surface that Python "
                "guards cannot intercept."
            ),
            input_schema=empty,
        ),
        make_tool(
            name="integrity_check",
            description=(
                "Re-verify every runtime file against INTEGRITY.json (SHA-256) and list installed "
                "runtime distributions. verified status means the manifest matched completely."
            ),
            input_schema=empty,
        ),
        make_tool(
            name="schema_catalog",
            description=(
                "Return the JSON Schema 2020-12 input and output schemas, annotations and stability "
                "class of every tool this server advertises, with per-schema and whole-catalog SHA-256 "
                "digests for offline review."
            ),
            input_schema=empty,
        ),
        make_tool(
            name="audit_log_status",
            description=(
                "Report whether hash-chained auditing is enabled, the record count, the chain head "
                "digest, chain validity and the audit record schema."
            ),
            input_schema=empty,
        ),
    ]


# ---------------------------------------------------------------------------
# Tool assembly
# ---------------------------------------------------------------------------


def _load_library() -> Any:
    global library
    if library is None:
        try:
            import mcp_server_library as _library
        except (ImportError, RuntimeError) as exc:
            raise QECTORDependencyError(
                f"decoder runtime unavailable: {exc}. Install requirements.lock "
                "(scripts/install_offline.sh on an air-gapped host)."
            ) from exc

        if _library.SERVER_VERSION != SERVER_VERSION:
            raise RuntimeError(
                f"mcp_server_library.py reports {_library.SERVER_VERSION}; the secure server is {SERVER_VERSION}"
            )
        library = _library
    return library


def _load_research():
    try:
        import mcp_server_qector_bench as research
    except ImportError as exc:
        raise _load_library().QECTORInputError(
            "research profile requires mcp/mcp_server_qector_bench.py; "
            "the safe Desktop MCPB does not bundle the research server"
        ) from exc
    return research


def assemble_tools(profile: str) -> tuple[list[Any], dict[str, str], Any]:
    """Return (tools, stability-by-name, research module or None) for *profile*."""
    if profile not in PROFILES:
        raise ValueError(f"profile must be one of {PROFILES}")
    lib = _load_library()
    tools: list[Any] = list(lib.TOOLS)
    stability = {tool.name: "stable" for tool in tools}
    control = apply_tool_contract(_control_tool_schema(), surface="control")
    tools.extend(control)
    stability.update({tool.name: "control" for tool in control})
    research = None
    if profile == "research":
        research = _load_research()
        library_names = set(stability)
        for tool in research.TOOLS:
            name = RESEARCH_COMPAT_ALIAS if tool.name in library_names else tool.name
            if name != tool.name:
                tool = rebuild_tool(tool, name=name)
            tools.append(tool)
            stability[name] = "provisional"
    tools = sorted(tools, key=lambda item: item.name)
    names = [tool.name for tool in tools]
    if len(names) != len(set(names)):
        raise RuntimeError(f"duplicate tool names after assembly: {names}")
    return tools, stability, research


def dispatch_tool(name: str, arguments: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Synchronous dispatch for tests and for the MCP adapter (post-validation)."""
    if name in CONTROL_FUNCTIONS:
        consume_call_budget(name)
        return CONTROL_FUNCTIONS[name]()
    lib = _load_library()
    if name in lib.TOOL_FUNCTIONS:
        return lib.dispatch_tool(name, arguments)
    if STATE.research is not None:
        if name == RESEARCH_COMPAT_ALIAS:
            return STATE.research.dispatch_tool("compat_report", arguments)
        if name in STATE.research.TOOL_FUNCTIONS:
            return STATE.research.dispatch_tool(name, arguments)
    raise QECTORUnknownToolError(f"Unknown tool {name!r}; choose one of {sorted(STATE.tool_by_name)}")


def _check_request_size(name: str, arguments: Mapping[str, Any] | None) -> None:
    try:
        size = len(canonical_json(dict(arguments or {})).encode("utf-8"))
    except (TypeError, ValueError) as exc:
        raise QECTORSchemaError(name, f"arguments are not JSON-serialisable: {exc}", "$") from exc
    if size > STATE.max_request_bytes:
        raise QECTORSchemaError(
            name,
            f"request payload is {size} bytes; the limit is {STATE.max_request_bytes} "
            "(QECTOR_MCP_MAX_REQUEST_BYTES)",
            "$",
        )


async def _dispatch_mcp_call(name: str, arguments: Mapping[str, Any] | None):
    started = time.perf_counter()
    tool = STATE.tool_by_name.get(name)
    envelope: dict[str, Any]
    try:
        if tool is None:
            raise QECTORUnknownToolError(f"Unknown tool {name!r}; choose one of {sorted(STATE.tool_by_name)}")
        _check_request_size(name, arguments)
        validated = validate_arguments(tool, arguments)
        result = dispatch_tool(name, validated)
        raw_name = "compat_report" if name == RESEARCH_COMPAT_ALIAS else name
        envelope = result_envelope(
            result,
            tool_name=raw_name,
            server_name=SERVER_NAME,
            server_version=SERVER_VERSION,
            stability=STATE.stability.get(name, "stable"),
            elapsed_ms=(time.perf_counter() - started) * 1e3,
        )
        envelope["tool"] = name
        envelope["scope"]["tool"] = name
        validate_envelope(tool, envelope)
        is_error = envelope.get("status") == "error"
    except Exception as exc:
        envelope = error_envelope(
            exc,
            tool_name=name if tool is not None else "unknown_tool",
            server_name=SERVER_NAME,
            server_version=SERVER_VERSION,
            stability=STATE.stability.get(name, "stable"),
            elapsed_ms=(time.perf_counter() - started) * 1e3,
        )
        is_error = True
    try:
        audit_ref = STATE.audit.append(
            tool=name,
            arguments=arguments,
            envelope=envelope,
            elapsed_ms=(time.perf_counter() - started) * 1e3,
        )
    except (OSError, ValueError, QECTORAuditError) as exc:
        # Fail closed: a call that cannot be recorded is not returned as a
        # success. The client gets an IO_ERROR envelope and the operator a
        # stderr line; the chain head in memory is unchanged.
        _stderr(f"ERROR: audit log append failed for {name}: {exc.__class__.__name__}: {exc}")
        envelope = error_envelope(
            QECTORAuditWriteError(f"audit log append failed ({exc.__class__.__name__}); the call result was withheld"),
            tool_name=name if tool is not None else "unknown_tool",
            server_name=SERVER_NAME,
            server_version=SERVER_VERSION,
            stability=STATE.stability.get(name, "stable"),
            elapsed_ms=(time.perf_counter() - started) * 1e3,
        )
        is_error = True
        audit_ref = None
    if audit_ref is not None:
        envelope["audit"] = audit_ref
    return call_tool_result(envelope, is_error=is_error)


# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------


def _stderr(message: str) -> None:
    try:
        sys.stderr.write(f"[{SERVER_NAME}] {message}\n")
        sys.stderr.flush()
    except (OSError, ValueError):  # pragma: no cover
        pass


def configure(
    *,
    profile: str = "safe",
    allow_network: bool = False,
    audit_dir: str | None = None,
    integrity_manifest: str | None = None,
    strict_integrity: bool | None = None,
    max_request_bytes: int | None = None,
    allow_unsupported_sdk: bool = False,
    integrity_pubkey: str | None = None,
) -> dict[str, Any]:
    """Resolve configuration, install guards and assemble tools.

    Returns the startup report. Raises :class:`QECTORIntegrityError` when
    strict integrity fails and ``RuntimeError`` for an unsupported SDK.
    """
    supported, detail = sdk_supported()
    if not supported and not allow_unsupported_sdk:
        raise RuntimeError(f"refusing to start: {detail}")
    qector_airgap.install(force=False if allow_network else None, source="cli" if allow_network else None)
    if allow_network:
        _stderr("WARNING: --allow-network lifts the air-gap guard; outbound PyPI checks become possible")
    STATE.profile = profile
    STATE.max_request_bytes = int(
        max_request_bytes
        if max_request_bytes is not None
        else int(os.environ.get("QECTOR_MCP_MAX_REQUEST_BYTES", str(DEFAULT_MAX_REQUEST_BYTES)))
    )
    if STATE.max_request_bytes <= 0:
        raise ValueError("max request bytes must be positive")
    manifest_path = Path(integrity_manifest).expanduser().resolve() if integrity_manifest else _ROOT / qector_integrity.MANIFEST_NAME
    STATE.integrity_manifest = manifest_path
    if strict_integrity is None:
        # Strict unless the operator opts out explicitly. A missing manifest is
        # therefore fatal by default: deleting INTEGRITY.json must not turn
        # the gate off.
        strict_integrity = env_flag("QECTOR_INTEGRITY_STRICT", True)
    STATE.strict_integrity = bool(strict_integrity)
    pinned = (integrity_pubkey or os.environ.get("QECTOR_INTEGRITY_PUBKEY", "")).strip()
    STATE.integrity_pubkey = pinned if pinned and not pinned.startswith("${") else None
    report = qector_integrity.verify(
        _ROOT, strict=STATE.strict_integrity, manifest_path=manifest_path, pinned_public_key=STATE.integrity_pubkey
    )
    STATE.integrity_report = report
    if not report["passed"]:
        problems = report["mismatched"] + report["missing"] + report["unlisted_runtime_files"]
        if not problems and not report["signature"]["valid"]:
            problems = [f"signature: {report['signature']['reason']}"]
        if STATE.strict_integrity:
            if not report["manifest_present"]:
                raise QECTORIntegrityError(
                    f"{qector_integrity.MANIFEST_NAME} is missing at {manifest_path}; run "
                    "scripts/generate_integrity_manifest.py or start with --no-strict-integrity "
                    "on a development tree"
                )
            raise QECTORIntegrityError(
                "runtime files do not match INTEGRITY.json: " + ", ".join(problems[:10])
                + (" ..." if len(problems) > 10 else "")
            )
        _stderr(
            "WARNING: integrity manifest "
            + ("mismatch: " + ", ".join(problems[:5]) if report["manifest_present"] else "absent")
            + "; serving unverified tree (non-strict mode)"
        )
    if audit_dir:
        os.environ["QECTOR_AUDIT_DIR"] = audit_dir
    STATE.audit = audit_log_from_env(server=SERVER_NAME, server_version=SERVER_VERSION)
    # Integrity verified above: decoder-facing modules may now be imported.
    _load_library()
    STATE.tools, STATE.stability, STATE.research = assemble_tools(profile)
    STATE.tool_by_name = {tool.name: tool for tool in STATE.tools}
    return {
        "server": SERVER_NAME,
        "server_version": SERVER_VERSION,
        "profile": profile,
        "tools": [tool.name for tool in STATE.tools],
        "sdk": detail,
        "air_gapped": qector_airgap.is_air_gapped(),
        "integrity_passed": report["passed"],
        "integrity_signature": report["signature"],
        "strict_integrity": STATE.strict_integrity,
        "audit_enabled": STATE.audit.enabled,
        "max_request_bytes": STATE.max_request_bytes,
    }


INSTRUCTIONS = (
    "QECTOR secure server: air-gapped by default, every call validated against "
    "JSON Schema 2020-12 on input and output, corrections fail-closed against "
    "H c = s (mod 2), hash-chained audit when QECTOR_AUDIT_DIR is set. Call "
    "airgap_status, integrity_check and schema_catalog to inspect the posture."
)


def build_low_level_server() -> Any:
    async def _list_tools():
        return STATE.tools

    return build_server(
        name=SERVER_NAME,
        version=SERVER_VERSION,
        instructions=INSTRUCTIONS,
        list_tools=_list_tools,
        call_tool=_dispatch_mcp_call,
    )


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="mcp_server_secure.py",
        description="QECTOR secure, air-gapped, schema-validated MCP server (stdio only).",
    )
    parser.add_argument("--transport", choices=("stdio",), default="stdio", help="Only stdio is implemented, by design.")
    parser.add_argument("--profile", choices=PROFILES, default="safe")
    parser.add_argument(
        "--allow-network",
        action="store_true",
        help="Lift the air-gap guard (equivalent to QECTOR_AIR_GAPPED=0). Logged on stderr.",
    )
    parser.add_argument("--audit-dir", default=None, help="Directory for the hash-chained audit log (QECTOR_AUDIT_DIR).")
    parser.add_argument("--integrity-manifest", default=None, help="Path to INTEGRITY.json (default: repository root).")
    parser.add_argument(
        "--integrity-pubkey",
        default=None,
        help="Base64 Ed25519 public key pinned out-of-band (QECTOR_INTEGRITY_PUBKEY); strict mode then requires a valid INTEGRITY.json.sig under it.",
    )
    strict = parser.add_mutually_exclusive_group()
    strict.add_argument(
        "--strict-integrity",
        dest="strict_integrity",
        action="store_true",
        default=None,
        help="Refuse to start unless INTEGRITY.json is present and matches (the default).",
    )
    strict.add_argument(
        "--no-strict-integrity",
        dest="strict_integrity",
        action="store_false",
        help="Development trees only: warn on manifest drift or absence instead of exiting 3.",
    )
    parser.add_argument("--max-request-bytes", type=int, default=None)
    parser.add_argument(
        "--allow-unsupported-sdk",
        action="store_true",
        help="Start even if the installed mcp SDK is outside the tested range (not recommended).",
    )
    parser.add_argument("--print-startup-report", action="store_true", help="Print the startup report as JSON on stderr.")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        report = configure(
            profile=args.profile,
            allow_network=args.allow_network,
            audit_dir=args.audit_dir,
            integrity_manifest=args.integrity_manifest,
            strict_integrity=args.strict_integrity,
            max_request_bytes=args.max_request_bytes,
            allow_unsupported_sdk=args.allow_unsupported_sdk or env_flag("QECTOR_ALLOW_UNSUPPORTED_SDK"),
            integrity_pubkey=args.integrity_pubkey,
        )
    except QECTORIntegrityError as exc:
        _stderr(f"FATAL: {exc}")
        return EXIT_INTEGRITY
    except QECTORAuditError as exc:
        _stderr(f"FATAL: {exc}")
        return EXIT_AUDIT
    except QECTORDependencyError as exc:
        _stderr(f"FATAL: {exc}")
        return EXIT_DEPENDENCY
    except RuntimeError as exc:
        _stderr(f"FATAL: {exc} (installed mcp {SDK_VERSION})")
        return EXIT_SDK
    except (ValueError, OSError) as exc:
        _stderr(f"FATAL: {exc}")
        return EXIT_BAD_ARGUMENTS
    if args.print_startup_report:
        _stderr(json.dumps(report, sort_keys=True))
    server = build_low_level_server()
    run_stdio(server, name=SERVER_NAME, version=SERVER_VERSION, instructions=INSTRUCTIONS)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
