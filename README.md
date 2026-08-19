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
- **3 reproducible commands**: runtime inspection, math obligations, local LER sweeps
- **2 local stdio MCP servers**: an 8-tool frozen library surface and a 25-tool Provisional bench companion, both with explicit schemas and fail-closed error handling
- **Public F2 ground-truth helpers** and device-local validation tests
- **Claude Code marketplace metadata** in `.claude-plugin/marketplace.json`

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

### Agents (`agents/`)
| Agent | Specialization |
|-------|----------------|
| `qec-researcher.md` | Academic research, paper reproduction, threshold sweeps |
| `qec-developer.md` | Code integration, API design, performance tuning |
| `qec-validator.md` | Formal verification, mathematical proof checking |
| `qec-sysadmin.md` | Operations, monitoring, incident response |
| `qec-hardware-engineer.md` | Physical qubit characterization, cryogenic systems |

### Commands (`commands/`)
| Command | Description |
|---------|-------------|
| `qec-facts.md` | Quick reference: codes, decoders, thresholds |
| `qec-threshold-sweep.md` | Run local LER sweeps with Wilson intervals |
| `qec-validate-mcp.md` | Validate MCP server tools and schemas |

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

## Standalone MCP Server

Launch the library server directly:

```text
python mcp/mcp_server_library.py
```

The server exposes exactly these eight tools:

1. `list_code_families`
2. `list_decoders`
3. `get_license_info`
4. `decode_syndrome`
5. `decode_single`
6. `threshold_sweep`
7. `build_code_from_matrix`
8. `compat_report`

The transport is local stdio only. The server validates binary inputs, enforces
resource bounds, checks every correction against `H c = s (mod 2)`, and returns
MCP tool errors without exposing tracebacks.

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
- `qector-claude-plugin-v1.0.1.zip` — the full plugin ZIP for the Claude Code
  plugin flow (`claude --plugin-dir`). It preserves the `.claude-plugin/`,
  `skills/`, `hooks/`, and MCP server layout.

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
