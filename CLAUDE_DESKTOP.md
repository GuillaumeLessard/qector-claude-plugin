# Claude Desktop Setup

This is the top-level Claude Desktop entry guide for the QECTOR plugin.

## Quick setup

1. Install the pinned runtime with the same Python interpreter Claude Desktop will launch:

   ```text
   python -m pip install -r <PLUGIN_ROOT>/requirements.txt
   ```

2. Merge the `qector-library` and `qector-bench` server entries from [`mcp/claude_desktop_config.json`](mcp/claude_desktop_config.json) into your desktop app MCP configuration (`%APPDATA%\Claude\claude_desktop_config.json` on Windows).
3. Replace `<PLUGIN_ROOT>` with the absolute path to this package (e.g. `C:/Users/Admin/Desktop/QECTOR Maths/Anthropic Skills and agents`).
4. Replace `python` with the full path to your Python interpreter (e.g. `C:\\Program Files\\Python312\\python.exe`) to avoid Windows PATH ambiguity.
5. Keep `QECTOR_SILENT=1`, then fully restart Claude Desktop.
6. Confirm that Claude Desktop connects to both servers:
   - `qector-library` (8 frozen tools: `list_code_families`, `list_decoders`, `get_license_info`, `decode_syndrome`, `decode_single`, `threshold_sweep`, `build_code_from_matrix`, `compat_report`).
   - `qector-bench` (28 research tools: `system_setup`, `reproduction_command_lookup`, `theorem_lookup`, `glossary_lookup`, `wilson_ci`, `dem_inspect`, `hardware_probe`, etc.).

The complete setup, verification, and troubleshooting guide is [`mcp/CLAUDE_DESKTOP.md`](mcp/CLAUDE_DESKTOP.md).
