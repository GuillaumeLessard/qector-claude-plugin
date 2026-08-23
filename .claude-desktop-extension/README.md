# QECTOR for Claude Desktop

This extension is the safe, local QECTOR Desktop surface. It runs
`mcp/mcp_server_desktop.py --profile safe` and exposes eight stable tools for
code discovery, decoder discovery, license inspection, verified decoding,
threshold sweeps, matrix validation, and compatibility reporting.

Decoded corrections are fail-closed: QECTOR returns them only after verifying
`H c = s (mod 2)`. Threshold results include Wilson 95% intervals and artifact
metadata.

The default transport is local stdio and makes no network request. The optional
PyPI compatibility freshness check is explicitly requested by a tool argument;
it does not send QEC workloads.

The 29-tool research profile and 3-tool administrative profile are intentionally
not included in this extension. Configure them as separate Developer MCP
servers only after reviewing `SECURITY.md` and `MCP_API.md`.

Claude web and mobile do not load this local extension directly. Use Claude Code
Remote Control for a local session, or deploy a separately reviewed hosted MCP
service.
