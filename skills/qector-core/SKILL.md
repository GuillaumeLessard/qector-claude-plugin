---
name: qector-core
description: >-
  Core domain knowledge and verified facts for the QECTOR quantum error
  correction platform. Covers the supported app-free qector-decoder-v3 library
  MCP server first, plus the optional QECTOR Workbench MCP server.
  Load whenever a request involves quantum error
  correction, decoders, code families, thresholds, syndromes, benchmarking, or
  the QECTOR MCP tool surface. Enforces the strict-math ground-truth rules
  (skills/qector-math-foundations) and prevents API hallucination by grounding
  every tool name, decoder, and API signature in what was actually verified.
---

# QECTOR Core - Verified Platform Facts

Ground every answer in the verified facts below. If a request references a
tool, decoder, or API that is not listed here or in
`references/qector_verified_api.md`, say "not verified in this package" rather
than inventing behavior. All mathematical claims must satisfy the rules in
`skills/qector-math-foundations` (strict ground truth).

## Library-first surfaces

1. **qector-decoder-v3 - app-free library path.** Install with
   `python -m pip install -r requirements.txt`. Full tool surface via `mcp/mcp_server_library.py`
   (library MCP server: list_code_families, list_decoders, get_license_info,
   decode_syndrome, decode_single, threshold_sweep, build_code_from_matrix,
   compat_report). Valid alone; this is the preferred development path.
2. **QECTOR Workbench MCP server - optional desktop extension.** Launch
   `QectorWorkbench-Portable.exe --mcp` only when the app is installed. Its
   exact tools, version, license, and hardware status are device-local and must
   be negotiated with `initialize` and `tools/list`. Fully optional: nothing
   about the library surface depends on it.

## Device-Local Wire Contract

- Library server: 8 tools, pinned production runtime `mcp==1.26.0` using the
  low-level `mcp.server.Server` adapter. See `mcp/VALIDATION_REPORT.md` for
  the fresh validation protocol.
- Workbench negotiation is required on every device before any Workbench tool
  name is used. No Workbench transcript or hardware snapshot is bundled.

## Code families and decoders (exact strings)

- Library: generator functions `generate_repetition_code_checks(d)`,
  `generate_ring_code_checks(n)`, `generate_surface_code_checks(d)` (legacy
  toric-weight-4, NOT graphlike - use `codes.rotated_surface_code` for a
  graphlike surface code), plus `codes.rotated_surface_code`,
  `codes.unrotated_surface_code`, `codes.toric_code`, `codes.heavy_hex_code`,
  `codes.color_code`, `codes.hypergraph_product`, `codes.from_parity_check_matrix`.
- Optional Workbench families and names are device-local; confirm them with
  `initialize` and `tools/list` before use.
- Library stable decoders:
  `union_find` (UnionFindDecoder), `fast_union_find`
  (FastUnionFindDecoder), `blossom` (BlossomDecoder, exact MWPM),
  `sparse_blossom` (SparseBlossomDecoder), `native_auto` (NativeAutoDecoder).
  Provisional in the wheel: BpOsdDecoder, batch/streaming/GPU decoders
  (manual 16.2).

## Ground rules

1. **Strict math first**: read `skills/qector-math-foundations` before any
   number is produced. H c == s (mod 2) is checked after every decode
   (Theorem 1); LER reports need 95% Wilson intervals; never compare
   code_capacity vs circuit_level numbers. The graphlike `codes` families
   (`rotated_surface_code`, `unrotated_surface_code`, `toric_code`,
   `heavy_hex_code`, `color_code`) are single-sector matching-graph codes with
   `H H^T != 0` (e.g. `rotated_surface_code(5)` has a 12 x 25 H), so they use
   the arbitrary-matrix/logical-coset branch of Theorem 2, never the
   self-orthogonal branch.
2. **No invented tools/APIs.** Only the library's 8 tools are callable by
   default. Workbench tools are callable only after that device's `tools/list`
   response has been inspected.
3. **No speed superlatives** without a dated, reproducible artifact (manual
   chapter 22.5).
4. **No CPU/GPU assumptions**: use `cuda_is_available()` for a direct-wheel
   hardware probe. Workbench hardware tools are optional and device-local;
   licensing is a separate gate.
5. **Zero egress**: decode locally; never upload .stim/.npy/parity matrices
   to web APIs.
