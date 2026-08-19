# QECTOR Claude Plugin User Manual (v1.0.2)

This public plugin provides local Claude skills, agents, commands, and app-free
MCP servers for the QECTOR quantum-error-correction decoding engine. The
mathematical authority is the QECTOR Decoder v3 reference manual v1.0.0 at DOI
`10.5281/zenodo.21941046`.

## First-Time Guided System Setup (28th Tool)

For a clean, guided first-time environment installation with safety approbation:

```bash
# 1. Audit environment (read-only dry-run, no changes made)
python scripts/qector_system_setup.py --check-only

# 2. Execute installation upon explicit user approbation
python scripts/qector_system_setup.py --confirm
```

Or invoke the `system_setup` tool over the `qector-bench` MCP server:
- Call `system_setup(confirm=false)` to inspect python interpreter, package status, and planned actions.
- Call `system_setup(confirm=true)` once user approbation is granted to execute installation, directory setup, and in-process Theorem 1 verification.

## Standard Installation

Use Python 3.9 or newer (tested on Python 3.12). The app-free library and bench
servers support both system Python and virtual environments.

```bash
python -m pip install -r requirements.txt
python scripts/qector_runtime_check.py
```

Windows virtual environment:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python scripts/qector_runtime_check.py
```

The production runtime pins `qector-decoder-v3==1.0.0` and `mcp==1.26.0`.
The servers run locally against the published wheel without QECTOR Workbench.

Stim/DEM workflows are optional. Install the published extra only when needed:

```bash
python -m pip install "qector-decoder-v3[stim]==1.0.0"
```

## MCP Server Architecture

The plugin provides two local stdio MCP servers:

### 1. Library Server (`mcp/mcp_server_library.py` — 8 Frozen Stable Tools)

The authoritative, frozen library surface exposes:
- `list_code_families`: Registered quantum code families.
- `list_decoders`: Available decoder backends and contracts.
- `get_license_info`: Active license tier and distance limit.
- `decode_syndrome`: Syndrome decoding strictly asserting $H c \equiv s \pmod 2$.
- `decode_single`: Single-shot physical error simulation and decode.
- `threshold_sweep`: Multi-point LER threshold sweep with Wilson 95% CI.
- `build_code_from_matrix`: Construct code from a custom binary parity-check matrix.
- `compat_report`: Live package and runtime compatibility report.

### 2. Bench Companion Server (`mcp/mcp_server_qector_bench.py` — 28 Tools)

Provides 28 specialized research, reproducibility, and setup tools:
- **Guided Setup** (`system_setup`): Safety-gated setup tool with user approbation.
- **Reproduction Lookup** (`reproduction_command_lookup`): Exact Appendix D (D.1-D.6) reproduction commands.
- **Reference Manual Lookup** (`theorem_lookup`, `glossary_lookup`): Theorems 1-16 and Appendix B glossary.
- **Statistical Scoring** (`wilson_ci`, `wilson_table`, `logical_coset_score`): Exact Wilson score intervals and logical coset scoring (Theorem 2).
- **DEM & Circuit Pipeline** (`dem_inspect`, `dem_collapse_parallel`, `stim_circuit_probe`, `sinter_task_template`).
- **Code Structure** (`code_family_info`, `code_export_matrices`, `code_logicals_inspect`, `code_distance_check`).
- **Ecosystem Integration** (`pymatching_compat_check`, `sinter_decoder_list`, `qiskit_plugin_check`).
- **Workload & Runtime Integrity** (`hardware_probe`, `license_active_check`, `env_block`, `compat_report`, `workbench_probe`, `artifacts_sha256`, `artifact_metadata_check`, `decode_faithfulness_check`, `hot_path_microbench`, `workload_hash`).

For Claude Code, use the root `.mcp.json` and validate/launch with
`claude plugin validate "<PLUGIN_ROOT>" --strict` and
`claude --plugin-dir "<PLUGIN_ROOT>"`. For Claude Desktop or another MCP
client, copy `mcp/claude_desktop_config.json`, replace its
`<PLUGIN_ROOT>` path, and run `initialize` followed by `tools/list` before any
tool call. The optional Workbench configuration is a separate example and
must be probed on the target device before use.

The repository also includes `.claude-plugin/marketplace.json`. From the
parent directory, a local marketplace test is:

```text
claude plugin marketplace add ./<PLUGIN_ROOT>
claude plugin install qector@qector-tools
```

For the public GitHub source, use
`claude plugin marketplace add GuillaumeLessard/qector-claude-plugin`.

### Prebuilt archives

A single-skill ZIP for the claude.ai custom-skill uploader and a full plugin
ZIP for `claude --plugin-dir` are generated from `scripts/pro_pack.py` and shipped
under `dist/` with `.sha256` sidecars. See "Packaging and Distribution" in the
repository `README.md` for details.

## Strict Mathematics

- Arithmetic is over F2.
- Every correction is checked against `H c = s (mod 2)` before it is returned.
- Logical scoring uses the logical coset, never raw correction equality.
- LER uses a Wilson 95% interval and a `code_capacity` or `circuit_level` tag.
- Results from different noise-model tags are not comparable.
- Performance, GPU, and hardware claims are device-local and require fresh artifacts.

The public executable ground truth is `python/qector_math_ground_truth.py`;
its device-local obligations are in `tests/test_reference_manual_math.py`.

```text
python scripts/run_manual_math_validation.py
python -m pytest tests/ -q
```

`pytest` reads `conftest.py` automatically and resolves the module above. If
you use `unittest discover` instead, set `PYTHONPATH=python` first, since
`unittest` does not read `conftest.py`.

Threshold work is also device-local:

```text
python scripts/run_threshold_sweep.py --family rotated_surface --distances 3 5 --error-rates 0.05 --trials 100 --seed 42 --out ..\qector-artifacts\device_sweep.json
```

Keep generated artifacts outside the distributed plugin. A low-trial sweep is
a screening estimate, not a converged threshold.

## Public Contents

- `skills/` (28 skills): domain skills for math foundations, decoders, DEM pipeline, batching, architectures, licensing, and verification.
- `agents/` (5 agents): focused QEC subagents (`qec-researcher`, `qec-developer`, `qec-validator`, `qec-sysadmin`, `qec-hardware-engineer`).
- `commands/` (12 slash commands):
  - `/qec-setup`: Guided first-time setup and audit with user approbation safety gate.
  - `/qec-facts`: Verified platform facts, code families, and decoders.
  - `/qec-theorem`: Reference Manual Theorems 1-16 lookup.
  - `/qec-reproduce`: Appendix D (D.1-D.6) reproduction workflows.
  - `/qec-decode`: Single-shot syndrome decode asserting $H c \equiv s \pmod 2$.
  - `/qec-threshold-sweep`: Seeded LER sweeps with Wilson 95% CIs.
  - `/qec-wilson`: Wilson 95% score interval and comparison tables.
  - `/qec-dem`: Detector Error Model parsing, parallel collapse, and Stim circuits.
  - `/qec-code-inspect`: Code parameters $[[n,k,d]]$, transversals, and matrices.
  - `/qec-benchmark`: Latency and throughput microbenchmarks.
  - `/qec-sinter`: Sinter task template generation and configuration.
  - `/qec-validate-mcp`: MCP tool and schema validation.
- `prompts/` and `mega_prompts/`: reusable Claude instructions.
- `mcp/`: library server (8 tools), bench companion (28 tools), configuration examples, and validation protocol.
- `python/qector_math_ground_truth.py` and `tests/`: public executable math obligations.
- `governance/`: zero-egress and provenance rules.

No private transcripts, machine snapshots, internal authoring files, business
proposals, or proprietary reference documents are included.
