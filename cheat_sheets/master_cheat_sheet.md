# QECTOR MCP Cheat Sheet (plugin v1.0.6)

## 1. Default Library Surface (`qector-library` — 8 Frozen Stable Tools)

The frozen `qector-library` server is the authoritative local MCP surface:

`list_code_families`, `list_decoders`, `get_license_info`, `decode_syndrome`,
`decode_single`, `threshold_sweep`, `build_code_from_matrix`, `compat_report`.

| Role | Library focus | Primary tools |
| :--- | :--- | :--- |
| Researcher | seeded LER and code-family analysis | `list_code_families`, `list_decoders`, `decode_single`, `threshold_sweep` |
| Developer | integration and contract checks | `compat_report`, `decode_syndrome`, `list_decoders`, `get_license_info` |
| Educator | small binary examples | `build_code_from_matrix`, `decode_syndrome`, `decode_single` |
| Sysadmin | runtime and feature state | `compat_report`, `get_license_info`, `list_decoders` |
| Hardware engineer | explicit local checks and matrix validation | `list_code_families`, `build_code_from_matrix`, `decode_syndrome` |

## 2. Research Surface (`qector-research` — 29 Provisional Tools)

The companion `qector-research` server is opt-in. It adds 29 research tools:
- **Evidence layer**: `get_capability_matrix`, `get_evidence_policy`, `get_runtime_provenance`.
- **Repro & lookup**: `reproduction_command_lookup`, `theorem_lookup`, `glossary_lookup`.
- **Scoring & Math**: `wilson_ci`, `wilson_table`, `logical_coset_score`.
- **DEM & Circuit**: `dem_inspect`, `dem_collapse_parallel`, `stim_circuit_probe`, `sinter_task_template`.
- **Codes & Distance**: `code_family_info`, `code_export_matrices`, `code_logicals_inspect`, `code_distance_check`.
- **Ecosystem**: `pymatching_compat_check`, `sinter_decoder_list`, `qiskit_plugin_check`.
- **Diagnostics**: `hardware_probe`, `license_active_check`, `env_block`, `compat_report`, `artifacts_sha256`, `artifact_metadata_check`, `decode_faithfulness_check`, `hot_path_microbench`, `workload_hash`.

Administrative tools (`system_setup`, `configure_claude_desktop`, `workbench_probe`) live on `qector-admin` and require `QECTOR_ADMIN_ENABLED=1` plus `confirm=true`.

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
