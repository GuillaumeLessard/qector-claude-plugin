---
description: Validate live MCP connectivity of the QECTOR servers (library first-class, workbench optional) - initialize handshake + mcp_status + tools/list diff, then a pass/warn/fail verdict.
---

Run a live MCP handshake against the QECTOR library server and report a verdict.

Primary target (always available): the LIBRARY server, `python mcp/mcp_server_library.py`.
It exposes 8 tools (list_code_families, list_decoders, get_license_info,
decode_syndrome, decode_single, threshold_sweep, build_code_from_matrix,
compat_report). Verify: initialize -> `qector-decoder-v3-mcp` with the plugin
version from `release-manifest.json`; tools/list returns exactly those 8 names.

Companion target: the RESEARCH server, `python mcp/mcp_server_qector_bench.py`.
It exposes 29 provisional tools (evidence layer, methodology, DEM, code
inspection, reproducibility). Verify: initialize -> `qector-research-mcp`;
tools/list returns exactly those 29 names. Admin tools are not in this list.

Optional target (only if the Workbench app is installed and separately configured): spawn
`QectorWorkbench-Portable.exe --mcp`, negotiate `initialize`, and inspect the
device's own `tools/list` response. Do not assume a tool count, version,
hardware status, or license state from another machine.

Checks and verdicts:
- Library handshake ok with 8 tools -> PASS.
- Research handshake ok with 29 tools -> PASS.
- Workbench present and the negotiated surface is internally consistent -> PASS;
  app missing -> note "not installed - library path fully sufficient", do NOT fail.
- Any unexpected tools/list entry relative to the target's documented release ->
  WARN (list the diffs).

Output one verdict per check with the raw response pointer, then a one-line overall
verdict. Per `skills/qector-math-foundations`, mark any number you cannot trace as
"not verified".
