---
description: Print the verified QECTOR platform fact sheet (surfaces, decoders, code families, MCP entry points, strict-math and honesty rules).
---

Read `skills/qector-core/SKILL.md`, `skills/qector-math-foundations/SKILL.md` and
`skills/qector-core/references/qector_verified_api.md`, then present the verified
fact summary:

- Supported surfaces:
    - Library `qector-decoder-v3` (app-free): MCP server `mcp/mcp_server_library.py`
    (8 tools: list_code_families, list_decoders, get_license_info, decode_syndrome,
    decode_single, threshold_sweep, build_code_from_matrix, compat_report);
    hook helpers in `scripts/`; standalone CLI tooling lives in the
    separate `qector-claude-skills` repository.
  - Workbench MCP (optional): `QectorWorkbench-Portable.exe --mcp`; negotiate its
    exact tool surface with `initialize` and `tools/list` on the target device.
- Code families and decoders: exact names from the files - never invent.
- Strict-math ground rules (skill `qector-math-foundations`): H c = s (mod 2)
  after every decode; LER scored on the logical coset; 95% Wilson intervals;
  code_capacity vs circuit_level never mixed; safe wording only; required artifact
  metadata + SHA-256 for every artifact.
- Ground rules: no invented tools, no unqualified speed claims, GPU/license read
  from `get_license_info` and target-device hardware probes, zero-egress security.
