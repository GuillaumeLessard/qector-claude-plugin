# QECTOR Claude Plugin

Local quantum-error-correction engineering for Claude Code, built for
`qector-decoder-v3` by Guillaume Lessard / iD01t Productions.

The primary product surface is the app-free library MCP server shipped in
`mcp/mcp_server_library.py`. It runs locally against the published
`qector-decoder-v3==1.0.0` wheel and does not require QECTOR Workbench.

## Quick Start

```bash
# 1. Clone and install
git clone https://github.com/GuillaumeLessard/qector-claude-plugin.git
cd qector-claude-plugin
python -m pip install -r requirements.txt
python scripts/qector_runtime_check.py

# 2. Validate and launch with Claude Code
claude plugin validate "<PLUGIN_ROOT>" --strict
claude --plugin-dir "<PLUGIN_ROOT>"

# 3. Or install from GitHub marketplace
claude plugin marketplace add GuillaumeLessard/qector-claude-plugin
claude plugin install qector@qector-tools
```

## What Ships

- **28 strict-math QEC skills** grounded in the QECTOR reference-manual contract
- **5 focused agents**: researcher, developer, validator, sysadmin, hardware engineer
- **13 reproducible commands**: setup, desktop connector, facts, math theorems, reproduction, decode, sweeps, benchmarks, Wilson CI, DEM parsing, code inspection, Sinter, and MCP validation
- **2 local stdio MCP servers**: an 8-tool frozen library surface and a 29-tool Provisional bench companion (including first-time system setup with user approbation, zero-friction Claude Desktop connector, and Appendix D reproduction workflows), both with explicit schemas and fail-closed error handling
- **Public F2 ground-truth helpers** and device-local validation tests
- **Claude Code marketplace metadata** in `.claude-plugin/marketplace.json` (v1.0.2)

## Skills & Agents Reference

### Skills (`skills/`, 28 total)
| Skill | Purpose |
|-------|---------|
| `qector-core` | Core QEC primitives, decoding workflows, F2 algebra |
| `qector-architecture` | Rust/PyO3 core + Python layer FFI, module map, threading/memory model |
| `qector-batch-decoding` | Batch/streaming/GPU decoding, bit-identity contract |
| `qector-bp-osd` | Belief propagation with ordered-statistics post-processing |
| `qector-codes-builder` | Building and inspecting QEC codes from the v1.0.0 library |
| `qector-decoders-deep-dive` | Per-decoder internals and theorem inheritance |
| `qector-dem-pipeline` | Detector error model parsing, collapse, priors, routing |
| `qector-deployment` | Deployment modes, security posture, production checklist |
| `qector-developer` | SDK integration, wiring MCP servers into applications |
| `qector-educator` | Tutorial generation, concept explanation, learning paths |
| `qector-glossary` | QECTOR terminology, notation, and symbols |
| `qector-hardware-engineer` | Device characterization, noise modeling, hardware constraints |
| `qector-ler-methodology` | Logical error rate methodology, Wilson CI, artifact metadata |
| `qector-licensing` | License tiers, key activation, tier enforcement |
| `qector-math-foundations` | Strict mathematical ground rules for every QECTOR claim |
| `qector-orchestration` | Routing, dispatch, decoder recommendation policy |
| `qector-pymatching-compat` | PyMatching-compatible shim, one-line decoder swap |
| `qector-release-engineering` | Packaging, wheel-only distribution, release gates |
| `qector-reproducibility` | Reproducibility and claim boundaries |
| `qector-researcher` | Literature review, experiment design, threshold analysis |
| `qector-roadmap` | Roadmap and Provisional-to-stable promotion path |
| `qector-services` | REST/gRPC/MCP/metrics service surfaces |
| `qector-sinter` | Sinter decoder entry points, community benchmark harness |
| `qector-space-time` | Space-time and streaming decoding, detector lattice |
| `qector-sysadmin` | Runtime health, resource bounds, deployment hygiene |
| `qector-testing-strategy` | Validation layers, test policy, cross-decoder equivalence |
| `qector-two-stage-css` | Two-stage CSS decoding for depolarising noise |
| `qector-workbench` | Optional QECTOR Workbench desktop application |

### Agents (`agents/`, 5 total)
| Agent | Specialization |
|-------|----------------|
| `qec-researcher.md` | Academic research, paper reproduction, threshold sweeps |
| `qec-developer.md` | Code integration, API design, performance tuning |
| `qec-validator.md` | Formal verification, mathematical proof checking |
| `qec-sysadmin.md` | Operations, monitoring, incident response |
| `qec-hardware-engineer.md` | Physical qubit characterization, cryogenic systems |

### Commands (`commands/`, 13 total)
| Command | Description |
|---------|-------------|
| `/qec-desktop-connector` | Zero-friction Claude Desktop MCP configuration with backup & path safety |
| `/qec-setup` | Guided first-time setup and diagnostic audit with user approbation gate |
| `/qec-facts` | Quick reference: codes, decoders, thresholds, and strict-math rules |
| `/qec-theorem` | Look up exact formulations and proof obligations for Theorems 1-16 |
| `/qec-reproduce` | Reference manual Appendix D (D.1-D.6) reproduction workflows |
| `/qec-decode` | Single-shot syndrome decoding asserting $H c \equiv s \pmod 2$ |
| `/qec-threshold-sweep` | Run local LER sweeps with Wilson 95% confidence intervals |
| `/qec-wilson` | Compute Wilson 95% score confidence intervals and comparison tables |
| `/qec-dem` | Inspect Detector Error Models (DEM), Stim circuits, and parallel fault collapse |
| `/qec-code-inspect` | Verify code parameters $[[n,k,d]]$, transversals, and check matrices |
| `/qec-benchmark` | Measure decoder latency and throughput microbenchmarks |
| `/qec-sinter` | Generate Sinter task templates and benchmark configuration |
| `/qec-validate-mcp` | Validate tool schemas, JSON-RPC transport, and health reports across both servers |

### Hooks (`hooks/`)
- `hooks.json` — Event-driven automation for skill/agent lifecycle

Supported runtime: Python 3.9 or newer, `qector-decoder-v3==1.0.0`,
`mcp==1.26.0`. Install the pinned dependencies with the same interpreter that
will launch the MCP server:

```text
python -m pip install -r requirements.txt
python scripts/qector_runtime_check.py
```

The runtime is supported in system Python and in a virtual environment:

```text
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python scripts/qector_runtime_check.py
```

The runtime check is device-local and produces no bundled evidence.

## Standalone MCP Servers

### 1. Library Server (`mcp/mcp_server_library.py` — 8 Frozen Stable Tools)

Launch the library server directly:

```text
python mcp/mcp_server_library.py
```

The frozen stable surface exposes exactly these eight tools:

1. `list_code_families`: List all registered quantum code families.
2. `list_decoders`: List available decoder backends and algorithm contracts.
3. `get_license_info`: Current license tier, maximum distance, and capabilities.
4. `decode_syndrome`: Decode a specific binary syndrome vector, strictly asserting $H c \equiv s \pmod 2$.
5. `decode_single`: Single-shot physical error simulation and decoding test.
6. `threshold_sweep`: Multi-distance, multi-error-rate logical error rate (LER) sweep with Wilson 95% CI.
7. `build_code_from_matrix`: Construct and validate a custom code from a binary parity check matrix.
8. `compat_report`: Runtime environment, wheel version, and dependency compatibility audit.

### 2. Bench & Provisional Server (`mcp/mcp_server_qector_bench.py` — 28 Tools)

Launch the bench companion server:

```text
python mcp/mcp_server_qector_bench.py
```

The bench companion provides 28 specialized research, inspection, reproducibility, and setup tools:

- **Guided First-Time Setup & Installation** (Tool #28: `system_setup`): Audits host environment, pip availability, and dependencies. Prompts for explicit user confirmation before installing packages via `pip install -r requirements.txt`, creating evidence paths, and running in-process Theorem 1 verification.
- **Reference Manual Reproduction** (Tool #27: `reproduction_command_lookup`): Instant offline lookup of reproduction commands from Appendix D (D.1 through D.6).
- **Offline Reference Manual Lookup** (`theorem_lookup`, `glossary_lookup`): Exact theorem formulations (Theorems 1-16) and Appendix B glossary definitions.
- **Strict Methodology** (`wilson_ci`, `wilson_table`, `logical_coset_score`): Exact Wilson 95% score intervals and logical coset scoring (Theorem 2).
- **DEM & Circuit Pipeline** (`dem_inspect`, `dem_collapse_parallel`, `stim_circuit_probe`, `sinter_task_template`): Stim circuit probing, detector error model parsing, parallel edge collapse, and Sinter integration.
- **Code Inspection** (`code_family_info`, `code_export_matrices`, `code_logicals_inspect`, `code_distance_check`): Structural matrix export, transversal logical operator inspection, and distance checking.
- **Ecosystem Shims** (`pymatching_compat_check`, `sinter_decoder_list`, `qiskit_plugin_check`): Drop-in PyMatching and Sinter compatibility verification.
- **Hardware & Workload Integrity** (`hardware_probe`, `license_active_check`, `env_block`, `compat_report`, `workbench_probe`, `artifacts_sha256`, `artifact_metadata_check`, `decode_faithfulness_check`, `hot_path_microbench`, `workload_hash`).

## Guided First-Time System Setup (28th Tool)

For first-time environment setup, run the safety-gated setup script directly or call `system_setup`:

```bash
# 1. Read-only diagnostic probe (dry-run, no changes made)
python scripts/qector_system_setup.py --check-only

# 2. Execute installation with explicit user approbation
python scripts/qector_system_setup.py --confirm
```

## Claude Code

The root `.mcp.json` uses `${CLAUDE_PLUGIN_ROOT}` and is ready for plugin-local
execution. Validate and launch the plugin with:

```text
claude plugin validate "<PLUGIN_ROOT>" --strict
claude --plugin-dir "<PLUGIN_ROOT>"
```

The plugin contains `.claude-plugin/marketplace.json` with marketplace name
`qector-tools`. From the parent directory, test the local marketplace with:

```text
claude plugin marketplace add ./<PLUGIN_ROOT>
claude plugin install qector@qector-tools
```

For the public repository, use:

```text
claude plugin marketplace add GuillaumeLessard/qector-claude-plugin
claude plugin install qector@qector-tools
```

## Other MCP Clients

For Claude Desktop or a generic MCP client, copy the appropriate template:

- `mcp/claude_desktop_config.json`
- `mcp/mcp_config.json`

Replace `<PLUGIN_ROOT>` with the package's absolute path before launch. Then
perform `initialize` and `tools/list` before using any tool.

## Mathematical Contract

- All binary algebra is over F2.
- Corrections must satisfy `H c = s (mod 2)` before logical scoring.
- Logical outcomes use the logical coset, not raw correction equality.
- LER reports include Wilson 95% intervals and a noise-model tag.
- `code_capacity` and `circuit_level` results are not comparable.
- Performance, hardware, GPU, threshold, and license state are device-local.
- Fresh artifacts belong outside the plugin and use an external `.sha256` sidecar.

The public mathematical source is `python/qector_math_ground_truth.py`. Run
the local validation procedures with:

```text
python scripts/run_manual_math_validation.py
python -m pytest tests/ -q
python -m unittest discover -s tests -t . -v
```

All three entry points resolve `python/qector_math_ground_truth.py` the same
way: `pytest` via `conftest.py`, the wrapper script via its own `sys.path`
insert, and `unittest discover` via the `-t .` top-level-dir flag (which
makes it import the suite as `tests.test_reference_manual_math` instead of a
bare top-level module, so `tests/__init__.py`'s path shim applies). Omitting
`-t .` from the `unittest` invocation will fail with
`ModuleNotFoundError: No module named 'qector_math_ground_truth'`.

For a fresh local sweep, write artifacts outside this repository:

```text
python scripts/run_threshold_sweep.py --family rotated_surface --distances 3 5 --error-rates 0.05 --trials 100 --seed 42 --out ..\qector-artifacts\device_sweep.json
```

## Optional Features

Stim/DEM workflows are not required by the library MCP server. Install the
published optional extra only when needed:

```text
python -m pip install "qector-decoder-v3[stim]==1.0.0"
```

QECTOR Workbench is a separate optional application. Its tool names, schemas,
hardware, and license state must be negotiated on the target device; no
Workbench tool is part of the standalone library contract.

## Security And Legal

The default server is local stdio. Do not send circuits, syndromes, matrices,
credentials, or generated artifacts to external services. Review
`governance/security_playbook.md` before deployment.

This plugin is provided **AS IS** and without warranty to the maximum extent
permitted by applicable law. See `DISCLAIMER.md`. The upstream
`qector-decoder-v3` package and all third-party dependencies retain their own
licenses and terms.

## Repository Layout

- `.claude-plugin/`: plugin and marketplace manifests.
- `scripts/`: runtime, validation, and artifact helpers.
- `skills/`: QECTOR domain skills.
- `agents/`: custom QEC agents.
- `commands/`: local slash-command workflows.
- `mcp/`: standalone server and client templates.
- `docs/`: public user and math-validation documentation.
- `tests/`: executable device-local obligations.

## Packaging and Distribution

This repository is a multi-skill Claude Code plugin. Do **not** upload the
whole repository as a single `claude.ai` custom skill — the skill uploader
accepts exactly one top-level folder and rejects ZIP entries that contain
Windows backslashes, which is the cause of the
"Zip file contains path with invalid characters" error.

Use `scripts/pro_pack.py` to produce correctly-formed archives. It writes every
ZIP entry name with forward slashes (`/`) and filters out Windows-reserved
characters (`< > : " | ? *`) and control bytes.

```text
python scripts/pro_pack.py --all
```

This produces two verified archives under `dist/`:

- `qector-qector-core-skill.zip` — a single-skill ZIP for the claude.ai
  custom-skill uploader. It contains one top-level `qector-core/` folder with
  `SKILL.md` at its root. Upload this file directly; do not rename it to a
  multi-skill bundle.
- `qector-claude-plugin-v1.0.2.zip` — the full plugin ZIP for the Claude Code
  marketplace / `claude --plugin-dir` packaging flow. Built by
  `python scripts/pro_pack.py --plugin` (or `--all`). Contains all 28 skills,
  5 agents, 12 commands, hooks, and MCP servers.

Each archive is accompanied by a `.sha256` sidecar. Regenerate them whenever a
skill or its references change:

```text
python scripts/pro_pack.py --skill qector-core      # single-skill only
python scripts/pro_pack.py --plugin                 # full plugin only
```

For the public repository, install from GitHub instead of shipping an archive:

```text
claude plugin marketplace add GuillaumeLessard/qector-claude-plugin
claude plugin install qector@qector-tools
```


Author: Guillaume Lessard / iD01t Productions, ORCID `0009-0000-3465-3753`.
