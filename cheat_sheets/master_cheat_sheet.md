# QECTOR Library MCP Cheat Sheet

## Default App-Free Surface

The bundled `qector-library` server is the supported local MCP surface. It
does not require QECTOR Workbench and exposes exactly these eight tools:

`list_code_families`, `list_decoders`, `get_license_info`, `decode_syndrome`,
`decode_single`, `threshold_sweep`, `build_code_from_matrix`, `compat_report`.

| Role | Library focus | Primary tools |
| :--- | :--- | :--- |
| Researcher | seeded LER and code-family analysis | `list_code_families`, `list_decoders`, `decode_single`, `threshold_sweep` |
| Developer | integration and contract checks | `compat_report`, `decode_syndrome`, `list_decoders`, `get_license_info` |
| Educator | small binary examples | `build_code_from_matrix`, `decode_syndrome`, `decode_single` |
| Sysadmin | runtime and feature state | `compat_report`, `get_license_info`, `list_decoders` |
| Hardware engineer | explicit local checks and matrix validation | `list_code_families`, `build_code_from_matrix`, `decode_syndrome` |

## Optional Workbench

Workbench is separate from this package. Its tool names, count, version,
hardware, and license state are device-local. Call `initialize` and
`tools/list` before using any Workbench name; no Workbench name is part of the
library MCP contract.

## Configurations

- Claude Code: root `.mcp.json`; `${CLAUDE_PLUGIN_ROOT}` is resolved by the plugin runtime.
- Claude Desktop: replace `<PLUGIN_ROOT>` in `mcp/claude_desktop_config.json`.
- Generic MCP clients: replace `<PLUGIN_ROOT>` in `mcp/mcp_config.json`.

## Strict Math

- Check `H c = s (mod 2)` after every decode (Theorem 1).
- Score logical cosets, never raw correction equality (Theorem 2).
- Attach a Wilson 95% interval to every LER.
- Tag `code_capacity` and `circuit_level`; never compare across tags.
- `random_error(p, rng=rng)` takes a NumPy generator, not `seed=`.
- Read license and hardware state from the active target; never hard-code it.

DEM, Stim, batch, GPU, and other provisional direct-wheel surfaces require
separate dependency/API checks and are not added to the eight-tool MCP surface.
