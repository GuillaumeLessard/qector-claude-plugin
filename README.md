# QECTOR Claude Plugin

Local quantum-error-correction engineering for Claude Code, built for
`qector-decoder-v3` by Guillaume Lessard / iD01t Productions.

The primary product surface is the app-free library MCP server shipped in
`mcp/mcp_server_library.py`. It runs locally against the published
`qector-decoder-v3==1.0.0` wheel and does not require QECTOR Workbench.

## Quick Start

```bash
# 1. Clone this plugin and its companion toolbox
git clone https://github.com/GuillaumeLessard/qector-claude-plugin.git
git clone https://github.com/GuillaumeLessard/qector-claude-skills.git
cd qector-claude-plugin
python -m pip install -r requirements.txt
python ../qector-claude-skills/bin/qector_runtime_check.py

# 2. Validate and launch with Claude Code
claude plugin validate "<PLUGIN_ROOT>" --strict
claude --plugin-dir "<PLUGIN_ROOT>"

# 3. Or install from GitHub marketplace
claude plugin marketplace add GuillaumeLessard/qector-claude-plugin
claude plugin install qector@qector-tools
```

## What Ships

- **7 strict-math QEC skills** grounded in the QECTOR reference-manual contract
- **5 focused agents**: researcher, developer, validator, sysadmin, hardware engineer
- **3 reproducible commands**: runtime inspection, math obligations, local LER sweeps
- **1 local stdio MCP server** with explicit schemas and fail-closed error handling
- **2 hook helpers** in `scripts/` (session banner, local tool-usage log)
- **Claude Code marketplace metadata** in `.claude-plugin/marketplace.json`

Runtime validation CLIs, the F2 ground-truth helpers, and the device-local
tests ship in the companion repository
[`GuillaumeLessard/qector-claude-skills`](https://github.com/GuillaumeLessard/qector-claude-skills).

## Skills & Agents Reference

### Skills (`skills/`)
| Skill | Purpose |
|-------|---------|
| `qector-core` | Core QEC primitives, decoding workflows, F2 algebra |
| `qector-researcher` | Literature review, experiment design, threshold analysis |
| `qector-developer` | SDK integration, decoder benchmarking, CI/CD for QEC |
| `qector-validator` | Mathematical obligation checks, device-local proof runs |
| `qector-sysadmin` | Runtime health, resource bounds, deployment hygiene |
| `qector-hardware-engineer` | Device characterization, noise modeling, hardware constraints |
| `qector-educator` | Tutorial generation, concept explanation, learning paths |

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
python ../qector-claude-skills/bin/qector_runtime_check.py
```

The runtime is supported in system Python and in a virtual environment:

```text
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python ..\qector-claude-skills\bin\qector_runtime_check.py
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

The public mathematical source is `qector_math_ground_truth.py` in the
`qector-claude-skills` repository. Run the local validation procedures there with:

```text
python bin/run_manual_math_validation.py
python -m unittest discover -s tests -v
```

For a fresh local sweep, write artifacts outside this repository:

```text
python ../qector-claude-skills/bin/run_threshold_sweep.py --family rotated_surface --distances 3 5 --error-rates 0.05 --trials 100 --seed 42 --out ..\qector-artifacts\device_sweep.json
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
- `scripts/`: hook helpers executed by `hooks/hooks.json` (never a `bin/`
  directory - claude.ai-hosted plugins may not ship top-level `bin/`
  executables).
- `skills/`: QECTOR domain skills.
- `agents/`: custom QEC agents.
- `commands/`: local slash-command workflows.
- `mcp/`: standalone server and client templates.
- `docs/`: public user documentation.
- `hooks/`: event-driven hook declarations.

Runtime/validation CLI scripts, the ground truth, and the tests live in the
companion [`qector-claude-skills`](https://github.com/GuillaumeLessard/qector-claude-skills)
repository.

## Packaging and Distribution

This repository is a multi-skill Claude Code plugin that is also hosted on
claude.ai. Two hosting rules drive the repository layout:

1. The claude.ai skill uploader accepts exactly one top-level folder and
   rejects ZIP entries that contain Windows backslashes (the "Zip file contains
   path with invalid characters" error). Never upload this whole repository as
   a single custom skill.
2. claude.ai-hosted plugins may not ship a top-level `bin/` directory, because
   such executables are added to PATH on the CLI but are not shown on the admin
   approval surface. Executable entry points must be declared via hooks,
   commands, or `mcpServers` instead. This plugin keeps its hook helpers in
   `scripts/` (declared in `hooks/hooks.json`) and its MCP server in `mcp/`
   (declared in `.mcp.json`); all standalone CLI scripts live in the separate
   `qector-claude-skills` repository.

Use `bin/pro_pack.py` in the `qector-claude-skills` repository to produce the
archives. It writes every ZIP entry name with forward slashes (`/`) and
filters out Windows-reserved characters (`< > : " | ? *`) and control bytes:

```text
cd qector-claude-skills
python bin/pro_pack.py --plugin-dir ..\qector-claude-plugin --all
```

This produces two verified archives under `dist/`:

- `qector-qector-core-skill.zip` — a single-skill ZIP for the claude.ai
  custom-skill uploader. It contains one top-level `qector-core/` folder with
  `SKILL.md` at its root. Upload this file directly; do not rename it to a
  multi-skill bundle.
- `qector-claude-plugin-v1.0.0.zip` — the full plugin ZIP for the Claude Code
  plugin flow (`claude --plugin-dir`) and for claude.ai plugin upload. It
  preserves the `.claude-plugin/`, `skills/`, `hooks/`, `scripts/`, and MCP
  server layout, and contains no `bin/` directory.

Each archive is accompanied by a `.sha256` sidecar. Regenerate them whenever a
skill or its references change:

```text
python bin/pro_pack.py --plugin-dir ..\qector-claude-plugin --skill qector-core      # single-skill only
python bin/pro_pack.py --plugin-dir ..\qector-claude-plugin --plugin                 # full plugin only
```

For the public repository, install from GitHub instead of shipping an archive:

```text
claude plugin marketplace add GuillaumeLessard/qector-claude-plugin
claude plugin install qector@qector-tools
```


Author: Guillaume Lessard / iD01t Productions, ORCID `0009-0000-3465-3753`.
