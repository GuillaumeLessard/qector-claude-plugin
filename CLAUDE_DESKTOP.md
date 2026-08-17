# Claude Desktop Setup

This is the top-level Claude Desktop entry guide for the QECTOR plugin.

## Quick setup

1. Install the pinned runtime with the same Python interpreter Claude Desktop
   will launch:

   ```text
   python -m pip install -r <PLUGIN_ROOT>/requirements.txt
   ```

2. Merge the `qector-library` server from
   [`mcp/claude_desktop_config.json`](mcp/claude_desktop_config.json) into the
   desktop app MCP configuration.
3. Replace `<PLUGIN_ROOT>` with the package directory on the target machine.
   This token is never replaced in the repository.
4. Keep `QECTOR_SILENT=1`, then fully restart Claude Desktop.
5. Confirm that `qector-library` exposes these eight tools:

   ```text
   list_code_families
   list_decoders
   get_license_info
   decode_syndrome
   decode_single
   threshold_sweep
   build_code_from_matrix
   compat_report
   ```

The complete setup, verification, hosted connector, and troubleshooting guide
is [`mcp/CLAUDE_DESKTOP.md`](mcp/CLAUDE_DESKTOP.md).
