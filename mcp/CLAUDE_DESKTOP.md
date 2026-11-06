# Claude Desktop MCP Setup (manual configuration)

QECTOR uses local stdio servers. The packaged Desktop extension
(`qector-claude-desktop-2.0.0.mcpb`, see `../DESKTOP_EXTENSION.md`) runs
`mcp/mcp_server_secure.py --profile safe`: 12 tools (8 stable + 4
control-plane), air-gapped, strict integrity checking with the release
signing key pinned. This page covers the manual alternative through Claude
Desktop's Developer MCP configuration.

## Manual entry

Merge the entry from `claude_desktop_config.json` into Claude Desktop's
`mcpServers` object. Replace `<PYTHON_EXECUTABLE>` with the exact interpreter
path (Python 3.10–3.13 with `requirements.lock` installed) and `<PLUGIN_ROOT>`
with the local repository path. Keep `QECTOR_SILENT=1` and
`PYTHONUNBUFFERED=1` so stdout remains valid MCP JSON-RPC. On Windows use an
absolute `python.exe` path.

## Optional servers

- `research_mcp_config.example.json` runs `mcp_server_secure.py --profile
  research` (41 tools: the safe profile plus the 29 Provisional research
  tools) under the name `qector-research`; set `<APPROVED_AUDIT_DIR>` or
  remove `QECTOR_AUDIT_DIR`.
- `admin_mcp_config.example.json` runs the three-tool `qector-admin` server;
  it stays inert until `QECTOR_ADMIN_ENABLED=1` is set in its environment and
  every call carries `confirm=true`. Do not enable it before reading
  `../SECURITY.md`.
- `workbench_config.example.json` is for the separate Workbench application.

A Desktop extension has one entry point, so research and admin tools are
never exposed by the `.mcpb`; use the Developer MCP configuration above.

## Check before use

```text
python scripts/qector_runtime_check.py
python mcp/tests/test_mcp_stdio.py --server qector-secure
```

The server waits for a JSON-RPC client on stdin; running it directly opens
no browser and no port.
