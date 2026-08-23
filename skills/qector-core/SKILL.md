---
name: qector-core
description: >-
  Core domain knowledge and verified facts for the QECTOR quantum
  error correction platform (plugin v1.0.5, decoder wheel 1.0.0).
  Covers the app-free library MCP server (8 stable tools), the
  opt-in research server (29 provisional tools including the
  evidence layer), the privileged admin server (3 tools), 11
  slash commands, 5 specialized agents, and mathematical grounding
  against all 16 Theorems and Appendices A-E from Reference
  Manual v1.0.0 (DOI 10.5281/zenodo.21941046). Enforces strict-math
  obligations (H c = s mod 2, logical coset scoring, Wilson 95% CI)
  and local-by-default operation with an opt-in PyPI freshness check.
---

# QECTOR Core - Verified Platform Facts (plugin v1.0.5)

Ground every answer in the verified facts below. If a request references a tool,
decoder, command, or API that is not listed here or in
`references/qector_verified_api.md`, state that it is not verified rather than
inventing behavior. All mathematical claims must strictly adhere to
`qector-math-foundations` and the QECTOR Decoder v3 Reference Manual v1.0.0
(DOI `10.5281/zenodo.21941046`).

## 1. Guided First-Time Setup & Audit

For first-time environment installation with explicit user safety approbation:

- **CLI Interface** (preferred):
  - `python scripts/qector_system_setup.py --check-only` (read-only diagnostic audit).
  - `python scripts/qector_system_setup.py --confirm` (installs the fixed production profile, creates `artifacts/`, and runs live in-process Theorem 1 verification).
- **MCP Tool Interface** (`qector-admin` only):
  - Disabled unless `QECTOR_ADMIN_ENABLED=1` is set in the server environment.
  - `system_setup(confirm=false)` is rejected; every admin call requires `confirm=true`.
  - `system_setup(confirm=true, profile=production|developer|optional-stim|optional-qiskit)` installs a fixed package profile. Arbitrary package specifications are not accepted.
  - Per-process call budget: 2. See `SECURITY.md`.

## 2. Library MCP Server (The 8-Tool Frozen Surface)

`mcp/mcp_server_library.py` exposes exactly **8 frozen tools**, verified on the
shipped `qector-decoder-v3==1.0.0` wheel:

| Tool | Purpose |
| :--- | :--- |
| `list_code_families` | List registered quantum code families and availability |
| `list_decoders` | List the five stable decoder classes and algorithm contracts |
| `get_license_info` | Read the live offline QECTOR license tier, distance limits, and gates |
| `decode_syndrome` | Decode a binary syndrome vector; fail unless $H c \equiv s \pmod 2$ |
| `decode_single` | Single-shot seeded code-capacity simulation (Theorems 1 & 2 verified) |
| `threshold_sweep` | Code-capacity LER sweep with Wilson 95% CI and external `.sha256` sidecar |
| `build_code_from_matrix` | Validate and build a quantum code from a binary parity-check matrix |
| `compat_report` | Live package compatibility and runtime environment report |

The library server is **frozen at 8 tools** under the 1.0.0 API freeze note;
never invent additional library tools.

## 3. Research MCP Server (29 Provisional Tools)

`mcp/mcp_server_qector_bench.py` is registered as `qector-research`. It is
**not enabled by default**. It adds 29 provisional tools for methodology,
inspection, reproducibility, and the evidence layer. Administrative tools
(`system_setup`, `configure_claude_desktop`, `workbench_probe`) live on
`qector-admin`, not here.

| Tool | Reference Manual Category & Chapter |
| :--- | :--- |
| `reproduction_command_lookup` | Appendix D (D.1–D.6) reproduction command workflows |
| `theorem_lookup` | Appendix A/C (Theorems 1–16 exact formulations and obligations) |
| `glossary_lookup` | Appendix B (Glossary of notation and symbols) |
| `wilson_ci` | Chapter 15.2 (Wilson 95% binomial score confidence interval) |
| `wilson_table` | Chapter 15.2 (Comparative Wilson interval tables) |
| `logical_coset_score` | Chapter 3.2 (Theorem 2 logical coset error scoring) |
| `dem_inspect` | Chapter 14 (Detector Error Model inspection and hyperedges) |
| `dem_collapse_parallel` | Chapter 14.1 (Parallel fault mechanism collapse rule) |
| `code_family_info` | Chapter 4 (Table 4.1 code family parameters) |
| `code_export_matrices` | Chapter 16.1 (Stable parity-check and logical matrix export) |
| `code_logicals_inspect` | Chapters 3.2, 16.1 (Transversal logical operator inspection) |
| `code_distance_check` | Chapter 16.1 (Distance and check weight verification) |
| `pymatching_compat_check` | Chapter 17.1 (PyMatching drop-in shim compatibility) |
| `sinter_decoder_list` | Chapter 17.2 (Sinter community benchmark entry points) |
| `qiskit_plugin_check` | Chapter 17.3 (Qiskit plugin interface check) |
| `hardware_probe` | Chapters 18, 20 (Local CPU/GPU hardware capability probe) |
| `license_active_check` | Chapter 18.1 (Active license tier and feature gates) |
| `env_block` | Chapter 22.3 (Reproducible environment metadata block) |
| `compat_report` | Chapters 16.2, 17.1 (Runtime compatibility report) |
| `artifacts_sha256` | Chapter 22.3 (SHA-256 constrained to `QECTOR_ARTIFACT_DIR`) |
| `artifact_metadata_check` | Chapter 22.3 (Artifact metadata schema verification) |
| `decode_faithfulness_check` | Chapter 3.1 (Theorem 1 syndrome faithfulness gate) |
| `hot_path_microbench` | Chapters 22.1, 22.5 (Machine-scoped microbenchmark) |
| `stim_circuit_probe` | Circuit inspection (Stim subset parser without Stim required) |
| `sinter_task_template` | Chapter 17.2 (Sinter task script template generation) |
| `workload_hash` | Chapter 22.3 (Workload and syndrome buffer SHA-256 hash) |
| `get_capability_matrix` | Evidence layer: workflow-to-server map |
| `get_evidence_policy` | Evidence layer: result statuses and error codes |
| `get_runtime_provenance` | Evidence layer: live runtime block |

Every research tool returns `reference_manual: 10.5281/zenodo.21941046` in its payload.

## 4. Reproducible Slash Commands (`commands/`, 11 Total)

| Command | Workflow |
| :--- | :--- |
| `/qec-setup` | Guided first-time setup & diagnostic audit with user approbation gate |
| `/qec-facts` | Quick reference: codes, decoders, thresholds, and strict-math rules |
| `/qec-theorem` | Exact formulations and proof obligations for Theorems 1–16 |
| `/qec-reproduce` | Reference manual Appendix D (D.1–D.6) reproduction workflows |
| `/qec-threshold-sweep` | Local LER sweeps with Wilson 95% intervals and sidecars |
| `/qec-wilson` | Analytical Wilson 95% score confidence intervals ($z=1.95996$) |
| `/qec-dem` | Detector Error Model parsing, parallel collapse, and Stim circuits |
| `/qec-code-inspect` | Code parameters $[[n,k,d]]$, transversals, and check matrices |
| `/qec-benchmark` | Decoder latency and throughput microbenchmarks |
| `/qec-sinter` | Sinter task template generation and configuration |
| `/qec-validate-mcp` | MCP tool and schema validation across library and research servers |

Decode a syndrome with the library tool `decode_syndrome`, not a slash command.
Configure Claude Desktop with `scripts/configure_claude_desktop.py` or the
admin tool `configure_claude_desktop` after `QECTOR_ADMIN_ENABLED=1`.

## 5. Specialized Agents (`agents/`, 5 Total)

- `qec-researcher.md`: Academic research, paper reproduction, threshold sweeps, finite-size scaling.
- `qec-developer.md`: Code integration, API design, performance tuning, stdio JSON-RPC 2.0 wiring.
- `qec-validator.md`: Formal verification, mathematical proof checking, local-by-default enforcement.
- `qec-sysadmin.md`: Fleet health triage, environment management, license audits, deployment hygiene.
- `qec-hardware-engineer.md`: Physical qubit characterization, Stim/DEM pipelines, cryogenic constraints.

## 6. Code Families and Decoders (`qector-decoder-v3==1.0.0`)

### Library Code Factories
- `codes.repetition_code(d)`: Repetition code, distance $d$.
- `codes.ring_code(n)`: Ring code, $n$ checks.
- `codes.rotated_surface_code(d)`: **Graphlike** rotated surface code ($k=1$).
- `codes.unrotated_surface_code(d)`: Graphlike unrotated surface code ($k=0$).
- `codes.toric_code(L)`: Toric code on $L \times L$ torus ($k=2$).
- `codes.heavy_hex_code(d)`: Graphlike heavy-hex code.
- `codes.color_code(d)`: Triangular color code ($k=1$).
- `codes.hypergraph_product(A, B)` / `codes.bicycle_code(...)`: qLDPC codes.
- `codes.from_parity_check_matrix(H, name=..., distance=...)`: Custom matrix code.

### Library Stable Decoders (Manual Chapter 16.1)
- `union_find` -> `UnionFindDecoder`
- `fast_union_find` -> `FastUnionFindDecoder`
- `blossom` -> `BlossomDecoder` (exact Minimum-Weight Perfect Matching)
- `sparse_blossom` -> `SparseBlossomDecoder`
- `native_auto` -> `NativeAutoDecoder`

### Provisional Decoders (Manual Chapter 16.2)
`bposd`, `cuda_batch`, `opencl_batch`, `cuda_bposd`, `two_stage`, `ambiguity_cluster`,
`space_time`, `streaming`, `sliding_window`, `auto`, `hybrid_cascade`, `hybrid`, `lookup_table`.

## 7. Strict Math Ground Rules (M0–M8)

1. **Theorem 1 (Syndrome Faithfulness)**: Every returned correction $c$ must satisfy $H c \equiv s \pmod 2$.
2. **Theorem 2 (Logical Coset Scoring)**: Score logical errors on the coset $c \oplus e \in \ker H \setminus \mathrm{im} H^T$ for self-orthogonal checks ($H H^T = 0$). For arbitrary matrices, score using code-provided logical/stabilizer spaces.
3. **Statistical Integrity**: All LER estimates require Wilson 95% score confidence intervals ($z=1.959963985$).
4. **Noise Model Separation**: `code_capacity` and `circuit_level` results are never comparable.
5. **No Speed Superlatives**: Throughput and latency figures are machine-, workload-, and environment-specific.
6. **Local by default**: Decoding and artifact generation remain device-local. The only outbound network operation is the explicit opt-in PyPI freshness check (`compat_report(check_pypi=true)` / `env_block(check_pypi=true)`). Do not call it in an air-gapped environment.

## 8. References & Cross-Skill Navigation

- `references/qector_verified_api.md`: Comprehensive API reference and verified signatures.
- `qector-math-foundations`: Normative mathematical rules and 16 Theorems.
- `qector-decoders-deep-dive`: In-depth per-decoder mechanics and algorithmic invariants.
- `qector-ler-methodology`: Rigorous LER methodology, Wilson intervals, and artifact hashing.
- `qector-batch-decoding`: Batch/streaming/GPU decoding and Theorem 16 bit-identity.
- `qector-licensing`: Offline license tiers, distance limits, and feature gating.
- `qector-orchestration`: Decoder routing policies and the 7-tier fallback hierarchy.
