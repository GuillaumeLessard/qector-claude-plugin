---
description: Print the verified QECTOR platform fact sheet (surfaces, decoders, code families, MCP entry points, strict-math and honesty rules).
---

Read `skills/qector-core/SKILL.md`, `skills/qector-math-foundations/SKILL.md` and
`skills/qector-core/references/qector_verified_api.md`, then present the verified
fact summary:

- Supported surfaces:
    - Library `qector-decoder-v3` (app-free): MCP server `mcp/mcp_server_library.py`
    (8 frozen tools: list_code_families, list_decoders, get_license_info, decode_syndrome,
    decode_single, threshold_sweep, build_code_from_matrix, compat_report).
    - Bench companion server `mcp/mcp_server_qector_bench.py` (28 tools including
    system_setup with user approbation, reproduction_command_lookup, theorem_lookup,
    glossary_lookup, and full verification suite).
    - Scripts in `scripts/` (e.g. `qector_system_setup.py`, `qector_runtime_check.py`, `run_manual_math_validation.py`, `pro_pack.py`).
  - Workbench MCP (optional): `QectorWorkbench-Portable.exe --mcp`; negotiate its
    exact tool surface with `initialize` and `tools/list` on the target device.
- Code families and decoders: exact names from the files - never invent.
- Strict-math ground rules (skill `qector-math-foundations`): H c = s (mod 2)
  after every decode; LER scored on the logical coset; 95% Wilson intervals;
  code_capacity vs circuit_level never mixed; safe wording only; required artifact
  metadata + SHA-256 for every artifact.
- Ground rules: no invented tools, no unqualified speed claims, GPU/license read
  from `get_license_info` and target-device hardware probes, zero-egress security.
