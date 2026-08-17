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

## 2. Configure the desktop app

1. Open Claude Desktop's MCP configuration file using the app's settings/help
   location for your operating system.
2. Merge the `qector-library` entry from
   [`claude_desktop_config.json`](claude_desktop_config.json) into the existing
   `mcpServers` object. Do not overwrite other servers.
3. Replace `<PLUGIN_ROOT>` in the copied entry with the package's absolute
   directory. JSON accepts forward slashes on Windows; if backslashes are
   used, escape them as `\\`.
4. Keep `QECTOR_SILENT=1`. Any startup text on stdout would corrupt the MCP
   stdio protocol.
5. Fully quit and restart Claude Desktop.

The resulting entry has this shape, with the token replaced locally:

```json
{
  "mcpServers": {
    "qector-library": {
      "command": "python",
      "args": ["<PLUGIN_ROOT>/mcp/mcp_server_library.py"],
      "env": {
        "QECTOR_SILENT": "1"
      }
    }
  }
}
```

## 3. Verify before use

In Claude Desktop, confirm that `qector-library` is connected and that the
eight tools are visible. The first protocol checks must be:

1. `initialize`
2. `tools/list`
3. `list_code_families`

The expected tool names are:

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

If the server is unavailable, run the following from the package directory to
separate Python/dependency issues from Claude Desktop configuration issues:

```text
python mcp/mcp_server_library.py
```

That process is intentionally a stdio server and waits for an MCP client. Do
not expect a browser page or HTTP port from this command.

## Hosted Claude surfaces

Claude.ai and Cowork cannot launch this package's local stdio process. For
hosted sessions, deploy the Streamable HTTP connector in `mcp/connector/` and
register its HTTPS `/mcp` URL as a custom connector. The connector has its own
deployment guide and must be tested with `/health`, `initialize`, and
`tools/list` before submission or production use.

## Privacy and path hygiene

The local server is zero-egress by default. It does not upload syndromes,
matrices, circuits, or artifacts. This repository contains no user-specific
absolute paths; all local package references use `${CLAUDE_PLUGIN_ROOT}` or the
`<PLUGIN_ROOT>` setup token.
