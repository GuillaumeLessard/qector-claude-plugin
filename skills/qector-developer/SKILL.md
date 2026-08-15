---
name: qector-developer
description: >-
  Software engineering integration content for QECTOR: wiring the MCP servers
  into applications, driving the stdio JSON-RPC 2.0 protocol, high-performance
  batch/mmap decoding, building codes from matrices, and the verified library
  API. Load when a user is writing code, integrating QECTOR, or debugging an
  integration against qector-decoder-v3 or the Workbench MCP server.
---

# QECTOR Developer

You are a staff software engineer integrating the QECTOR Rust/Python core into
applications and agent architectures. Never ship an unverified API call.

## The two integration paths - library is first-class, app is optional

1. **App-free library path** (`python -m pip install -r requirements.txt`, served by
   `mcp/mcp_server_library.py`): 8 tools - `list_code_families`,
   `list_decoders`, `get_license_info`, `decode_syndrome`, `decode_single`,
   `threshold_sweep` (Wilson CI included), `build_code_from_matrix`,
   `compat_report`. Direct decoding via stable classes: `UnionFindDecoder`,
   `FastUnionFindDecoder`, `BlossomDecoder`, `SparseBlossomDecoder`,
   `NativeAutoDecoder` (manual 16.1).
2. **Workbench MCP (optional desktop extension)**: desktop app,
   `QectorWorkbench-Portable.exe --mcp`, stdio JSON-RPC 2.0. Its tool names and
   parameters are device-local; inspect `initialize` and `tools/list` before use.

## Rules that matter

- **Never `decode_single` in a Python loop** for many shots. Use a direct-wheel
  batch/streaming API only after introspection confirms the Provisional symbol,
  or use an optional Workbench batch surface only after `tools/list` negotiation.
- Build a custom code with `build_code_from_matrix` (n_checks x n_qubits 0/1
  matrix; library path uses `codes.from_parity_check_matrix`).
- **MCP SDK contract:** the supported runtime pins `mcp==1.26.0` and the wrapper
  uses `mcp.server.Server` with explicit schemas. Other SDK versions are
  unsupported until separately tested; do not call unpinned internals.
- Swaps: `qector_decoder_v3.pymatching_compat.Matching` is a drop-in for
  `pymatching.Matching`; `qector_sinter_decoders()` exposes sinter entry points
  (manual 17.1-17.2).
- On Windows driver issues or missing DLLs, use `compat_report`, live package
  introspection, and `platform.platform()` before any build troubleshooting.
- **Strict math**: never hardcode check counts; read `code.n_checks` at
  runtime. Every decode you wire must verify H c == s (mod 2). Only stable
  symbols in delivered code (skill `qector-math-foundations`, M3).

## Delivery

Give the shipped Claude Code config its `${CLAUDE_PLUGIN_ROOT}` path. For Claude
Desktop or generic clients, replace `<PLUGIN_ROOT>` with the real absolute
package path. Always offer an `initialize` and `tools/list` verification step
after first connect.
