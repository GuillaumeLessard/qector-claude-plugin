"""MCP Python SDK compatibility layer for QECTOR servers.

QECTOR 2.0.0 supports two SDK generations at once:

* the patched ``mcp`` 1.x line (``>=1.30,<2``), whose pydantic models use
  camelCase field names (``inputSchema``) and whose low-level ``Server``
  registers handlers with decorators (``@server.list_tools()``); and
* the ``mcp`` 2.x line (``>=2.0,<3``), whose models moved to snake_case
  field names (``input_schema``) with camelCase *aliases*, and whose
  low-level ``Server`` takes ``on_list_tools`` / ``on_call_tool``
  callbacks at construction time.

Every QECTOR server goes through this module instead of touching the SDK
directly, so a single code base runs unmodified on either generation.
Construction always uses the wire (camelCase) names, which both
generations accept; attribute access goes through the ``tool_*`` helpers
below, which try the 2.x name first and fall back to the 1.x name.

The module is deliberately tiny and dependency-free beyond ``mcp`` itself
so it can be audited in one sitting.
"""

from __future__ import annotations

import asyncio
import importlib.metadata
import json
from typing import Any, Awaitable, Callable, Iterable, Mapping, Sequence

from mcp.types import (
    CallToolResult,
    ServerCapabilities,
    TextContent,
    Tool,
    ToolAnnotations,
    ToolsCapability,
)

try:  # pragma: no cover - resolved once per process
    SDK_VERSION = importlib.metadata.version("mcp")
except importlib.metadata.PackageNotFoundError:  # pragma: no cover
    SDK_VERSION = "unknown"


def _major(version: str) -> int:
    head = version.split(".", 1)[0]
    digits = "".join(ch for ch in head if ch.isdigit())
    return int(digits) if digits else 0


SDK_MAJOR = _major(SDK_VERSION)
# Field-name generation is detected from the model itself, never guessed
# from the version string, so a backport or a pre-release cannot fool it.
SDK_SNAKE_CASE = "input_schema" in getattr(Tool, "model_fields", {})

SUPPORTED_SDK_RANGE = ">=1.30,<3"


def sdk_supported() -> tuple[bool, str]:
    """Return (supported, detail) for the installed ``mcp`` distribution."""
    parts: list[int] = []
    for chunk in SDK_VERSION.split("."):
        digits = "".join(ch for ch in chunk if ch.isdigit())
        if not digits:
            break
        parts.append(int(digits))
    if len(parts) < 2:
        return False, f"could not parse mcp version {SDK_VERSION!r}"
    major, minor = parts[0], parts[1]
    if major == 1 and minor >= 30:
        return True, f"mcp {SDK_VERSION} (1.x patched line)"
    if major == 2:
        return True, f"mcp {SDK_VERSION} (2.x line)"
    return False, (
        f"mcp {SDK_VERSION} is outside the supported range {SUPPORTED_SDK_RANGE}; "
        "versions before 1.27.2 carry CVE-2026-52869/52870/59950"
    )


# ---------------------------------------------------------------------------
# Model construction (wire names work on both generations)
# ---------------------------------------------------------------------------


def make_annotations(
    *,
    read_only: bool,
    destructive: bool,
    idempotent: bool,
    open_world: bool,
) -> ToolAnnotations:
    return ToolAnnotations(
        readOnlyHint=read_only,
        destructiveHint=destructive,
        idempotentHint=idempotent,
        openWorldHint=open_world,
    )


def make_tool(
    *,
    name: str,
    description: str,
    input_schema: Mapping[str, Any],
    output_schema: Mapping[str, Any] | None = None,
    annotations: ToolAnnotations | None = None,
    title: str | None = None,
) -> Tool:
    kwargs: dict[str, Any] = {
        "name": name,
        "description": description,
        "inputSchema": dict(input_schema),
    }
    if output_schema is not None:
        kwargs["outputSchema"] = dict(output_schema)
    if annotations is not None:
        kwargs["annotations"] = annotations
    if title is not None:
        kwargs["title"] = title
    return Tool(**kwargs)


def make_call_tool_result(
    payload: Mapping[str, Any], *, is_error: bool
) -> CallToolResult:
    """Return text + structured content for one envelope.

    The JSON text is canonical (sorted keys, no NaN) so a client that only
    reads ``content[0].text`` sees exactly what ``structuredContent`` holds.
    """
    text = json.dumps(payload, sort_keys=True, allow_nan=False)
    return CallToolResult(
        content=[TextContent(type="text", text=text)],
        structuredContent=dict(payload),
        isError=is_error,
    )


def make_tools_capability() -> ServerCapabilities:
    return ServerCapabilities(tools=ToolsCapability(listChanged=False))


# ---------------------------------------------------------------------------
# Model access (generation-neutral)
# ---------------------------------------------------------------------------


def _get(model: Any, snake: str, camel: str) -> Any:
    if hasattr(model, snake):
        return getattr(model, snake)
    return getattr(model, camel)


def tool_input_schema(tool: Tool) -> dict[str, Any]:
    return dict(_get(tool, "input_schema", "inputSchema") or {})


def tool_output_schema(tool: Tool) -> dict[str, Any] | None:
    value = _get(tool, "output_schema", "outputSchema")
    return dict(value) if value is not None else None


def tool_annotations_dict(tool: Tool) -> dict[str, Any] | None:
    annotations = tool.annotations
    if annotations is None:
        return None
    return annotations.model_dump(by_alias=True, exclude_none=True)


def tool_wire_dict(tool: Tool) -> dict[str, Any]:
    """The tool exactly as it appears on the wire in ``tools/list``."""
    return tool.model_dump(by_alias=True, exclude_none=True)


def result_wire_dict(result: CallToolResult) -> dict[str, Any]:
    return result.model_dump(by_alias=True, exclude_none=True)


def rebuild_tool(
    tool: Tool,
    *,
    input_schema: Mapping[str, Any] | None = None,
    output_schema: Mapping[str, Any] | None = None,
    annotations: ToolAnnotations | None = None,
    name: str | None = None,
) -> Tool:
    """Return a copy of *tool* with the given fields replaced.

    ``model_copy(update=...)`` keys differ between generations, so copies
    are rebuilt from wire names instead.
    """
    return make_tool(
        name=name or tool.name,
        description=tool.description or "",
        input_schema=input_schema if input_schema is not None else tool_input_schema(tool),
        output_schema=output_schema if output_schema is not None else tool_output_schema(tool),
        annotations=annotations if annotations is not None else tool.annotations,
        title=getattr(tool, "title", None),
    )


# ---------------------------------------------------------------------------
# Low-level server wiring
# ---------------------------------------------------------------------------

ListToolsHandler = Callable[[], Awaitable[Sequence[Tool]]]
CallToolHandler = Callable[[str, Mapping[str, Any]], Awaitable[CallToolResult]]


def build_server(
    *,
    name: str,
    version: str,
    instructions: str,
    list_tools: ListToolsHandler,
    call_tool: CallToolHandler,
) -> Any:
    """Create a low-level ``mcp.server.Server`` on either SDK generation.

    Input validation is performed by the QECTOR contract layer, not by the
    SDK, so the SDK's own validation hook is disabled (1.x) or left unset
    (2.x). This keeps the error envelope identical across generations.
    """
    from mcp.server import Server

    if SDK_SNAKE_CASE:
        from mcp.types import ListToolsResult

        async def _on_list_tools(_ctx: Any, _params: Any) -> ListToolsResult:
            return ListToolsResult(tools=list(await list_tools()))

        async def _on_call_tool(_ctx: Any, params: Any) -> CallToolResult:
            arguments = getattr(params, "arguments", None) or {}
            return await call_tool(params.name, dict(arguments))

        return Server(
            name,
            version=version,
            instructions=instructions,
            on_list_tools=_on_list_tools,
            on_call_tool=_on_call_tool,
        )

    server = Server(name, version=version, instructions=instructions)

    @server.list_tools()
    async def _list_tools() -> list[Tool]:
        return list(await list_tools())

    @server.call_tool(validate_input=False)
    async def _call_tool(tool_name: str, arguments: dict[str, Any]) -> CallToolResult:
        return await call_tool(tool_name, arguments or {})

    return server


def run_stdio(server: Any, *, name: str, version: str, instructions: str) -> None:
    """Serve *server* over local stdio until the client closes the pipe."""
    from mcp.server.models import InitializationOptions
    from mcp.server.stdio import stdio_server

    options = InitializationOptions(
        server_name=name,
        server_version=version,
        capabilities=make_tools_capability(),
        instructions=instructions,
    )

    async def _run() -> None:
        async with stdio_server() as (read, write):
            await server.run(read, write, options)

    asyncio.run(_run())


def sorted_tools(tools: Iterable[Tool]) -> list[Tool]:
    return sorted(tools, key=lambda item: item.name)
