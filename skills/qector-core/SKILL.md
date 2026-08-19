---
name: qector-core
description: >-
  Core domain knowledge and verified facts for the QECTOR quantum
  error correction platform. Covers the supported app-free
  qector-decoder-v3 library MCP server (8 tools), the companion
  qector-bench MCP server (25 tools, Provisional), the optional
  QECTOR Workbench MCP server, and the eight strict-math
  ground-truth rules. Load whenever a request involves quantum
  error correction, decoders, code families, thresholds,
  syndromes, benchmarking, or the QECTOR MCP tool surface.
  Enforces the strict-math ground-truth rules
  (qector-math-foundations) and prevents API hallucination by
  grounding every tool name, decoder, and API signature in what
  was actually verified.
---

# QECTOR Core - Verified Platform Facts

Ground every answer in the verified facts below. If a request
references a tool, decoder, or API that is not listed here or in
`references/qector_verified_api.md`, say "not verified in this
package" rather than inventing behavior. All mathematical claims
must satisfy the rules in `qector-math-foundations` (strict
ground truth).

## Library MCP server (the 8-tool frozen surface)

`mcp/mcp_server_library.py` exposes exactly **eight tools**, all
verified on the shipped `qector-decoder-v3==1.0.0` wheel:

| Tool                       | Purpose                                                  |
| -------------------------- | -------------------------------------------------------- |
| `list_code_families`       | List code families and live qector 1.0.0 availability    |
| `list_decoders`            | List the five stable decoder classes                     |
| `get_license_info`         | Read the live offline QECTOR license tier and gates      |
| `decode_syndrome`          | Decode a binary syndrome; fail unless `H c = s (mod 2)`  |
| `decode_single`            | One seeded code-capacity decode (Theorems 1 + 2 checks)  |
| `threshold_sweep`          | Code-capacity LER sweep with Wilson 95% + SHA-256 sidecar |
| `build_code_from_matrix`   | Validate and build a binary parity-check matrix           |
| `compat_report`            | Live package compatibility and Provisional boundaries     |

The library server is **frozen at 8 tools** under the 1.0.0 API
freeze note; never invent additional library tools.

## Bench MCP server (the Provisional companion, 25 tools)

`mcp/mcp_server_qector_bench.py` adds 25 **Provisional** tools that
the 8-tool library surface does not cover. Register it in
`qector-bench` (see `.mcp.json`).

| Tool                          | Reference manual chapter |
| ----------------------------- | ------------------------ |
| `wilson_ci`                   | 15.2 (Wilson formula)     |
| `wilson_table`                | 15.2                      |
| `logical_coset_score`         | 3.2 (Theorem 2)          |
| `dem_inspect`                 | 14 (DEM pipeline)         |
| `dem_collapse_parallel`       | 14.1 (collapse rule)      |
| `code_family_info`            | 4 (Table 4.1)             |
| `code_export_matrices`        | 16.1 (stable API)         |
| `code_logicals_inspect`       | 3.2, 16.1                 |
| `code_distance_check`         | 16.1                      |
| `pymatching_compat_check`     | 17.1 (PyMatching shim)    |
| `sinter_decoder_list`         | 17.2 (sinter entry points)|
| `qiskit_plugin_check`         | 17.3 (Qiskit plugin)      |
| `hardware_probe`              | 18, 20 (license + hw)     |
| `license_active_check`        | 18.1 (env + tier)         |
| `env_block`                   | 22.3 (metadata)           |
| `workbench_probe`             | 17.5 (Workbench)          |
| `artifacts_sha256`            | 22.3 (sidecar)            |
| `artifact_metadata_check`     | 22.3 (metadata block)     |
| `decode_faithfulness_check`   | 3.1 (Theorem 1)           |
| `hot_path_microbench`         | 22.1, 22.5 (cold/hot)     |
| `stim_circuit_probe`          | Stim subset parser, no Stim required |
| `sinter_task_template`        | 17.2 (sinter task, generates only) |
| `workload_hash`               | 22.3 (artifact sidecar SHA-256) |
| `theorem_lookup`              | Appendix (theorems 1-16)  |
| `glossary_lookup`             | Appendix B (glossary)     |

The bench server exposes **25 tools**, not 20; the five rows above
were previously undocumented here. Every bench tool returns
`reference_manual: 10.5281/zenodo.21941046` in its payload.

## Optional Workbench MCP (device-local)

The optional QECTOR Workbench desktop app is **absent from the
shipped `qector-decoder-v3` wheel** (file listing, pip RECORD,
`--mcp` grep). Launch `QectorWorkbench-Portable.exe --mcp` only
when the app is installed. Its exact tools, version, license,
and hardware status are device-local and must be negotiated with
`initialize` and `tools/list`. `qector-bench.workbench_probe` is
the live probe wrapper; `scripts/probe_workbench_mcp.py` is the
command-line equivalent.

## Code families and decoders (verified exact strings)

### Library code factories

- `codes.repetition_code(d)`
- `codes.ring_code(n)`
- `codes.rotated_surface_code(d)` - **graphlike**, use this for
  a graphlike surface code.
- `codes.unrotated_surface_code(d)` - **graphlike**, but
  `k = 0`, `logicals_matrix()` is `None`.
- `codes.toric_code(L)` - 2 logical qubits.
- `codes.heavy_hex_code(d)` - graphlike.
- `codes.color_code(d)` - 2 logicals.
- `codes.hypergraph_product(A, B)` - qLDPC.
- `codes.bicycle_code(...)` / `codes.bivariate_bicycle_code(...)`
  - qLDPC.
- `codes.from_parity_check_matrix(H, name=..., distance=...)` -
  custom matrix.
- `codes.gf2_rank`, `codes.gf2_kernel`, `codes.css_logicals` -
  utility functions.

### Legacy generators (return `(checks, n_qubits)` tuples)

- `generate_repetition_code_checks(d)`
- `generate_ring_code_checks(n)`
- `generate_surface_code_checks(d)` - **legacy toric-weight-4,
  NOT graphlike**; use `codes.rotated_surface_code` for a
  graphlike surface code.

### Library stable decoders (manual 16.1)

`union_find` -> `UnionFindDecoder`
`fast_union_find` -> `FastUnionFindDecoder`
`blossom` -> `BlossomDecoder` (exact MWPM)
`sparse_blossom` -> `SparseBlossomDecoder`
`native_auto` -> `NativeAutoDecoder`

### Provisional decoders (manual 16.2, labelled)

`bposd` -> `BPOSDDecoder`
`cuda_batch` -> `CUDABatchDecoder`
`opencl_batch` -> `OpenCLBatchDecoder`
`cuda_bposd` -> `CUDABpOsdDecoder`
`two_stage` -> `TwoStageDecoder`
`ambiguity_cluster` -> `AmbiguityClusterDecoder`
`space_time` -> `SpaceTimeDecoder`
`streaming` -> `StreamingDecoder`
`sliding_window` -> `SlidingWindowDecoder`
`auto` -> `AutoDecoder` (7-tier controller)
`hybrid_cascade` -> `HybridCascadeDecoder`
`hybrid` -> `HybridDecoder`
`lookup_table` -> `LookupTableDecoder`

## Ground rules (M0-M8 from `qector-math-foundations`)

1. **Strict math first**: `H c == s (mod 2)` is checked after
   every decode (Theorem 1); LER reports need 95% Wilson
   intervals; never compare `code_capacity` vs `circuit_level`
   numbers. The graphlike `codes` families
   (`rotated_surface_code`, `unrotated_surface_code`,
   `toric_code`, `heavy_hex_code`, `color_code`) are single-
   sector matching-graph codes with `H H^T != 0` (e.g.
   `rotated_surface_code(5)` has a 12 x 25 H), so they use the
   arbitrary-matrix / logical-coset branch of Theorem 2, never
   the self-orthogonal branch.
2. **No invented tools / APIs**. The 8 library tools and 25
   bench tools listed above are callable. Workbench tools are
   callable only after that device's `tools/list` response has
   been inspected. Verified-but-non-frozen wheel surfaces exist
   (`rest_api` HTTP routes, `run_grpc_server`,
   `start_metrics_server`, `decode_mmap`,
   `get_decoder` / `get_decoder_pool` / `clear_decoder_cache`,
   `opencl_is_available`); any code using them is Provisional.
3. **No speed superlatives** without a dated, reproducible
   artifact (manual chapter 22.5).
4. **No CPU / GPU assumptions**: use `cuda_is_available()` for
   a direct-wheel hardware probe. Workbench hardware tools are
   optional and device-local; licensing is a separate gate.
5. **Zero egress**: decode locally; never upload
   `.stim` / `.npy` / parity matrices to web APIs.

## References

- `references/qector_verified_api.md` - the long-form
  verified-API reference (provisional symbols, pymatching shim,
  sinter entry points, optional direct-wheel APIs).
- `qector-math-foundations` - M0 through M8 normative rules.
- `qector-decoders-deep-dive` - per-decoder internals and
  theorem inheritance.
- `qector-ler-methodology` - LER / Wilson / artifact metadata.
- `qector-batch-decoding` - batch / streaming / GPU paths and
  the bit-identity contract.
- `qector-licensing` - tier table and env-var resolution order.
- `qector-orchestration` - the routing policy and the 7-tier
  fallback chain.
