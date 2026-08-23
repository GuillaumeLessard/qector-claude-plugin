# Claude Desktop Setup

QECTOR runs locally over stdio. It is not a hosted OAuth Custom Connector and
does not directly install into Claude web or mobile.

## Recommended Installation

Install with the Python environment that contains `requirements.txt`, then
preview changes before writing them:

```bash
python -m pip install -r requirements.txt
python scripts/configure_claude_desktop.py --check-only
python scripts/configure_claude_desktop.py --confirm
```

The installer records the exact Python executable in Claude Desktop's Developer
MCP configuration and installs the 8-tool safe Desktop extension. Restart
Claude Desktop completely after installation.

## Optional Profiles

The default is deliberately limited to `qector-library`. Add profiles only
when their scope is needed:

```bash
python scripts/configure_claude_desktop.py --confirm --with-research
python scripts/configure_claude_desktop.py --confirm --with-admin
```

`qector-research` has 29 provisional read/compute tools. `qector-admin` has
privileged setup, configuration, and Workbench-probe operations. It needs
`QECTOR_ADMIN_ENABLED=1` plus `confirm=true` for every call.

## Manual Configuration

Copy `mcp/claude_desktop_config.json`, replace `<PYTHON_EXECUTABLE>` with the
absolute interpreter path and `<PLUGIN_ROOT>` with this repository directory,
then merge only the `qector-library` entry into `mcpServers`. On Windows,
always use the absolute `python.exe` path rather than relying on `PATH`.

## Verification

```bash
python scripts/qector_runtime_check.py
python mcp/tests/test_mcp_stdio.py --server qector-library
```

For mobile or web control of this local workflow, use Claude Code Remote
Control. A native remote connector requires a separately secured hosted MCP
deployment.
