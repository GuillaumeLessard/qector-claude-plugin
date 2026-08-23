"""Profiled QECTOR MCP server for a single Claude Desktop entry point.

Claude Code may register the stable library, opt-in research, and privileged
admin servers separately. A Claude Desktop MCPB extension has one entry point,
so this adapter defaults to the eight stable library tools and exposes research
tools only when launched with ``--profile research``.
"""

from __future__ import annotations

import argparse
import asyncio
from typing import Any, Mapping, Sequence

from mcp.types import CallToolResult, ServerCapabilities, Tool, ToolsCapability

import mcp_server_library as library
from qector_mcp_contract import (
    apply_tool_contract,
    call_tool_result,
    error_envelope,
    result_envelope,
)

SERVER_NAME = "qector-desktop-mcp"
SERVER_VERSION = library.SERVER_VERSION

BENCH_COMPAT_ALIAS = "bench_compat_report"
PROFILES = ("safe", "research")


def _load_research_server():
    """Import the opt-in research server, or fail closed if it is absent.

    The published Desktop MCPB ships only the safe profile and does not
    bundle ``mcp_server_qector_bench.py``. A config that asks for
    ``--profile research`` without that module must not crash the process.
    """
    try:
        import mcp_server_qector_bench as bench
    except ImportError as exc:
        raise library.QECTORInputError(
            "research profile requires mcp/mcp_server_qector_bench.py; "
            "the safe Desktop MCPB does not bundle the research server"
        ) from exc
    return bench


def _desktop_tool_schema(profile: str) -> list[Tool]:
    library_names = {tool.name for tool in library.TOOLS}
    tools = list(library.TOOLS)
    if profile == "safe":
        return tools
    bench = _load_research_server()
    for tool in bench.TOOLS:
        name = BENCH_COMPAT_ALIAS if tool.name in library_names else tool.name
        tools.append(
            tool.model_copy(update={"name": name})
        )
    return tools


TOOLS = _desktop_tool_schema("safe")


def dispatch_tool(
    name: str,
    arguments: Mapping[str, Any] | None = None,
    *,
    profile: str = "safe",
) -> dict[str, Any]:
    if name in library.TOOL_FUNCTIONS:
        return library.dispatch_tool(name, arguments)
    if profile != "research":
        raise library.QECTORInputError(
            "research tools require the qector-desktop research profile"
        )
    bench = _load_research_server()
    if name == BENCH_COMPAT_ALIAS:
        return bench.dispatch_tool("compat_report", arguments)
    if name in bench.TOOL_FUNCTIONS:
        return bench.dispatch_tool(name, arguments)
    raise library.QECTORInputError(
        f"Unknown tool {name!r}; choose one of {[tool.name for tool in TOOLS]}"
    )


async def _dispatch_mcp_call(
    name: str, arguments: Mapping[str, Any] | None, profile: str
) -> CallToolResult:
    try:
        result = dispatch_tool(name, arguments, profile=profile)
        raw_name = "compat_report" if name == BENCH_COMPAT_ALIAS else name
        stability = "stable" if raw_name in library.TOOL_FUNCTIONS else "provisional"
        return call_tool_result(
            result_envelope(
                result,
                tool_name=raw_name,
                server_name=SERVER_NAME,
                server_version=SERVER_VERSION,
                stability=stability,
            )
        )
    except Exception as exc:
        return call_tool_result(
            error_envelope(
                exc,
                tool_name=name,
                server_name=SERVER_NAME,
                server_version=SERVER_VERSION,
                stability="stable" if profile == "safe" else "provisional",
            ),
            is_error=True,
        )


def _build_low_level_server(profile: str) -> Any:
    tools = apply_tool_contract(_desktop_tool_schema(profile))
    server = library._LowLevelServer(
        SERVER_NAME,
        version=SERVER_VERSION,
        instructions=(
            "Local QECTOR Desktop server. The safe profile exposes stable library "
            "tools; the explicit research profile also exposes provisional research "
            "tools. Decode outputs are fail-closed verified against H c = s (mod 2)."
        ),
    )

    @server.list_tools()
    async def _list_tools() -> list[Tool]:
        return tools

    @server.call_tool()
    async def _call_tool(
        name: str, arguments: dict[str, Any]
    ) -> CallToolResult:
        return await _dispatch_mcp_call(name, arguments, profile)

    return server


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Profiled QECTOR Claude Desktop MCP server"
    )
    parser.add_argument("--transport", choices=("stdio",), default="stdio")
    parser.add_argument("--profile", choices=PROFILES, default="safe")
    args = parser.parse_args(argv)
    server = _build_low_level_server(args.profile)
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
