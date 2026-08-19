# Claude Desktop Setup

This package supports Claude Desktop through the local library MCP server. The
desktop app reads MCP servers from its own user configuration file; it does not
automatically consume a Claude Code plugin directory or `${CLAUDE_PLUGIN_ROOT}`.

## 1. Install the runtime

Use the same Python interpreter that Claude Desktop will launch:

```text
python -m pip install -r <PLUGIN_ROOT>/requirements.txt
```

`<PLUGIN_ROOT>` is a documentation token only. Replace it with the package
directory on the target machine. Do not commit the replacement path to this
repository.

Confirm the interpreter can import the pinned runtime:

```text
python -c "import importlib.metadata as m; import qector_decoder_v3; print(m.version('mcp'))"
```

If `python` is not the interpreter used by your system, set the `command` in
the configuration to the interpreter command available on that machine.

**Windows-specific pitfall:** Claude Desktop resolves `python` using its own
process environment, which can differ from an interactive terminal's `PATH`
if multiple Python installs are present (e.g. a Microsoft Store shim, a
`py.exe` launcher install, and a standalone install can all coexist). A
`python` that works in your terminal is not proof Claude Desktop's spawned
process resolves to the same interpreter. Confirm the exact executable and
pin it explicitly:

```text
python -c "import sys; print(sys.executable)"
```

Then set `command` to that full path (e.g.
`"C:\\Program Files\\Python312\\python.exe"`) instead of the bare `python`
token. This removes PATH-resolution ambiguity entirely and is the recommended
setting on Windows. Symptom of this specific failure: the plugin's skills and
slash commands load normally (they come from the plugin manifest, not the
MCP server), but no `qector-library` / `qector-bench` tools ever appear, and
`%APPDATA%\Claude\logs\mcp-server-qector-library.log` shows
`ModuleNotFoundError` for a dependency you know is installed — that mismatch
between "installed" and "not found" is the tell that two different
interpreters are involved.

## 2. Configure the desktop app

1. Open Claude Desktop's MCP configuration file (`%APPDATA%\Claude\claude_desktop_config.json` on Windows).
2. Merge the `qector-library` and `qector-bench` entries from
   [`claude_desktop_config.json`](claude_desktop_config.json) into the existing
   `mcpServers` object. Do not overwrite other servers.
3. Replace `<PLUGIN_ROOT>` in the copied entry with the package's absolute
   directory. JSON accepts forward slashes on Windows; if backslashes are
   used, escape them as `\\`.
4. Keep `QECTOR_SILENT=1`. Any startup text on stdout would corrupt the MCP
   stdio protocol.
5. Fully quit and restart Claude Desktop.

The resulting entry has this shape, with both tokens replaced locally
(`<PYTHON_EXECUTABLE>` per the pitfall above, `<PLUGIN_ROOT>` per step 3):

```json
{
  "mcpServers": {
    "qector-library": {
      "command": "<PYTHON_EXECUTABLE>",
      "args": ["<PLUGIN_ROOT>/mcp/mcp_server_library.py"],
      "env": {
        "QECTOR_SILENT": "1"
      }
    },
    "qector-bench": {
      "command": "<PYTHON_EXECUTABLE>",
      "args": ["<PLUGIN_ROOT>/mcp/mcp_server_qector_bench.py"],
      "env": {
        "QECTOR_SILENT": "1"
      }
    }
  }
}
```

## 3. Verify before use

In Claude Desktop, confirm that both `qector-library` and `qector-bench` are connected:
- `qector-library` provides 8 frozen stable tools (`list_code_families`, `list_decoders`, `get_license_info`, `decode_syndrome`, `decode_single`, `threshold_sweep`, `build_code_from_matrix`, `compat_report`).
- `qector-bench` provides 28 specialized research/reproducibility tools (including `system_setup`, `reproduction_command_lookup`, `theorem_lookup`, `glossary_lookup`, `wilson_ci`, `dem_inspect`, `hardware_probe`, etc.).

The first protocol checks must be:

1. `initialize`
2. `tools/list`
3. `list_code_families` and `system_setup(confirm=false)`

If the server is unavailable, run the following from the package directory to
separate Python/dependency issues from Claude Desktop configuration issues:

```text
python mcp/mcp_server_library.py
```

That process is intentionally a stdio server and waits for an MCP client. Do
not expect a browser page or HTTP port from this command.

## Privacy and path hygiene

The local server is zero-egress by default. It does not upload syndromes,
matrices, circuits, or artifacts. This repository contains no user-specific
absolute paths; all local package references use `${CLAUDE_PLUGIN_ROOT}` or the
`<PLUGIN_ROOT>` setup token.
