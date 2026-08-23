# Architecture

QECTOR separates tool access by stability and privilege.

| Surface | Server | Default | Tools | Purpose |
| --- | --- | --- | --- | --- |
| Stable | `qector-library` | Yes | 8 | Verified decode, code construction, threshold sweep, runtime information |
| Research | `qector-research` | No | 29 | Provisional methodology, DEM, code inspection, reproducibility, hardware probes, evidence layer |
| Admin | `qector-admin` | No | 3 | Dependency setup, Desktop configuration, approved Workbench probe |

Claude Code enables only `qector-library`. Claude Desktop's MCPB extension runs
`mcp/mcp_server_desktop.py --profile safe`, which exposes the same 8 stable
tools. The Desktop `research` profile is available for a deliberate local
deployment; admin operations always remain in a separate server.

Every MCP transport response uses the `QECTORToolResult` envelope defined in
`mcp/qector_mcp_contract.py`. The envelope separates runtime verification,
reference-only results, measurements, and errors so agents do not inflate a
claim beyond its evidence.
