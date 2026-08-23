# Claude Desktop MCP Setup

QECTOR uses local stdio servers. Start with the stable `qector-library` server;
it exposes 8 tools and is the only profile included by default.

## Manual Entry

Merge the entry from `claude_desktop_config.json` into Claude Desktop's
`mcpServers` object. Replace `<PYTHON_EXECUTABLE>` with the exact interpreter
path and `<PLUGIN_ROOT>` with the local repository path. Keep
`QECTOR_SILENT=1` and `PYTHONUNBUFFERED=1` so stdout remains valid MCP JSON-RPC.

On Windows, use an absolute `python.exe` path. The bare `python` command in the
template is portable but may resolve differently in the Desktop process.

## Optional Servers

`research_mcp_config.example.json` defines the 29-tool `qector-research`
profile. `admin_mcp_config.example.json` defines the three-tool
`qector-admin` profile. Do not enable admin until you understand its package,
configuration, and executable-approval safeguards.

The packaged Desktop extension runs `mcp_server_desktop.py --profile safe` and
therefore does not expose research or admin tools. A Desktop extension has one
entry point; use Developer MCP configuration for separate opt-in servers.

## Check Before Use

```text
python scripts/qector_runtime_check.py
python mcp/tests/test_mcp_stdio.py --server qector-library
```

The server waits for a JSON-RPC client; running it directly does not open a
browser or HTTP port.
