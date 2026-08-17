# QECTOR Claude Skills — All-In-One

The complete quantum-error-correction engineering kit for Claude, built for
`qector-decoder-v3` by Guillaume Lessard / iD01t Productions.

This repository is the **source of truth** for the hosted plugin surface
(skills, agents, commands, hooks, app-free MCP server, hosted connector). The
claude.ai-hosted plugin and its prebuilt archives are published separately in
[`GuillaumeLessard/qector-claude-plugin`](https://github.com/GuillaumeLessard/qector-claude-plugin).

## Why Two Repositories?

claude.ai-hosted plugins may not ship a top-level `bin/` directory, because
such executables are added to PATH on the CLI but are not shown on the admin
approval surface. Executable entry points must be declared via hooks,
commands, or `mcpServers` instead.

- This repository is the **source**: the hosted-plugin surface plus the
  `mcp/connector/` deployment kit.
- The **plugin** repository ships only the hosted-plugin surface (`scripts/`
  hook helpers, `mcp/` server, skills, agents, commands) and the prebuilt
  upload archives in `dist/`.

## Quick Start

```bash
# 1. Clone
git clone https://github.com/GuillaumeLessard/qector-claude-skills.git
cd qector-claude-skills
python -m pip install -r requirements.txt

# 2. Validate and launch with Claude Code (this repo works as a local plugin)
claude plugin validate "<PLUGIN_ROOT>" --strict
claude --plugin-dir "<PLUGIN_ROOT>"

# 3. Or install the hosted plugin from the GitHub marketplace
claude plugin marketplace add GuillaumeLessard/qector-claude-plugin
claude plugin install qector@qector-tools
```

## What Ships

- **24 skills**: 8 strict-math QEC skills grounded in the QECTOR
  reference-manual contract plus 16 official Anthropic skills (document
  processing, design, development, and web tooling)
- **5 focused agents**: researcher, developer, validator, sysadmin, hardware engineer
- **3 reproducible commands**: runtime inspection, math obligations, local LER sweeps
- **1 local stdio MCP server** with explicit schemas and fail-closed error handling
- **1 hosted custom connector** (`mcp/connector/`): Streamable HTTP MCP
  endpoint with `/health`, optional bearer auth, and a Docker image - register
  it in claude.ai as a custom connector
- **2 hook helpers** in `scripts/` (session banner, local tool-usage log)
- **Claude Code marketplace metadata** in `.claude-plugin/marketplace.json`

## Skills & Agents Reference

### Skills (`skills/`) — QECTOR
| Skill | Purpose |
|-------|---------|
| `qector-core` | Core QEC primitives, decoding workflows, F2 algebra |
| `qector-researcher` | Literature review, experiment design, threshold analysis |
| `qector-developer` | SDK integration, decoder benchmarking, CI/CD for QEC |
| `qector-validator` | Mathematical obligation checks, device-local proof runs |
| `qector-sysadmin` | Runtime health, resource bounds, deployment hygiene |
| `qector-hardware-engineer` | Device characterization, noise modeling, hardware constraints |
| `qector-educator` | Tutorial generation, concept explanation, learning paths |
| `run-qector` | Headless Workbench controller: benchmark jobs, .stim/.dem runs, artifact export |

### Skills (`skills/`) — Official Anthropic
| Skill | Purpose |
|-------|---------|
| `docx` | Word document creation and editing |
| `xlsx` | Excel spreadsheet creation and recalculation |
| `pptx` | PowerPoint presentation creation |
| `pdf` | PDF generation, inspection, and conversion |
| `doc-coauthoring` | Co-authoring with versioned change tracking |
| `canvas-design` | Claude Canvas design patterns and fonts |
| `frontend-design` | Frontend UI design and implementation |
| `web-artifacts-builder` | Web artifact scaffolding and delivery |
| `webapp-testing` | Web app end-to-end testing workflows |
| `algorithmic-art` | Generative algorithmic art |
| `theme-factory` | Custom Claude Code theme creation |
| `slack-gif-creator` | Slack GIF creation workflows |
| `internal-comms` | Internal communication writing |
| `claude-api` | Claude API and SDK integration |
| `skill-creator` | Agent skills authoring, evaluation, and assets |
| `mcp-builder` | MCP server design and implementation |

Official skills retain their own licenses; see `THIRD_PARTY_NOTICES.md`.

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
- `hooks.json` — SessionStart banner and PostToolUse usage log, backed by the
  helpers in `scripts/`.

## Runtime

Supported runtime: Python 3.9 or newer, `qector-decoder-v3==1.0.0`,
`mcp==1.26.0`. Install the pinned dependencies with the same interpreter that
will launch the MCP server:

```text
python -m pip install -r requirements.txt
```

The runtime is supported in system Python and in a virtual environment.

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

The root `.mcp.json` uses `${CLAUDE_PLUGIN_ROOT}` and is ready for plugin-local
execution. For Claude Desktop or a generic MCP client, copy
`mcp/claude_desktop_config.json`, replace `<PLUGIN_ROOT>` with the package's
absolute path, and perform `initialize` and `tools/list` before using any tool.

## Mathematical Contract

- All binary algebra is over F2.
- Corrections must satisfy `H c = s (mod 2)` before logical scoring.
- Logical outcomes use the logical coset, not raw correction equality.
- LER reports include Wilson 95% intervals and a noise-model tag.
- `code_capacity` and `circuit_level` results are not comparable.
- Performance, hardware, GPU, threshold, and license state are device-local.
- Fresh artifacts belong outside the plugin and use an external `.sha256` sidecar.

The F2 obligations are validated device-local against the reference manual;
the validation tooling is internal and not distributed in this repository.

## Optional Features

Stim/DEM workflows are not required by the library MCP server. Install the
published optional extra only when needed:

```text
python -m pip install "qector-decoder-v3[stim]==1.0.0"
```

QECTOR Workbench is a separate optional application. Its tool names, schemas,
hardware, and license state must be negotiated on the target device; no
Workbench tool is part of the standalone library contract.

## Packaging and Distribution

Prebuilt archives are generated from this repository's source and shipped in
the companion
[`qector-claude-plugin`](https://github.com/GuillaumeLessard/qector-claude-plugin)
repository under `dist/` with `.sha256` sidecars:

- `qector-qector-core-skill.zip` — a single-skill ZIP for the claude.ai
  custom-skill uploader. It contains one top-level `qector-core/` folder with
  `SKILL.md` at its root. Upload this file directly; do not rename it to a
  multi-skill bundle.
- `qector-claude-plugin-v1.0.0.zip` — the full plugin ZIP for the Claude Code
  plugin flow (`claude --plugin-dir`) and for claude.ai plugin upload. It
  preserves the `.claude-plugin/`, `skills/`, `agents/`, `commands/`,
  `hooks/`, `scripts/`, and `mcp/` layout, and contains no `bin/` directory.

Two hosting rules drive the layout:

1. The claude.ai skill uploader accepts exactly one top-level folder and
   rejects ZIP entries that contain Windows backslashes (the "Zip file contains
   path with invalid characters" error). Never upload this whole repository as
   a single custom skill.
2. claude.ai-hosted plugins may not ship a top-level `bin/` directory, because
   such executables are added to PATH on the CLI but are not shown on the admin
   approval surface. Executable entry points must be declared via hooks,
   commands, or `mcpServers` instead.

For the public plugin, install from GitHub instead of shipping an archive:

```text
claude plugin marketplace add GuillaumeLessard/qector-claude-plugin
claude plugin install qector@qector-tools
```

## Repository Layout

- `.claude-plugin/`: plugin and marketplace manifests.
- `skills/`: 24 QECTOR and official Anthropic skills.
- `agents/`: custom QEC agents.
- `commands/`: local slash-command workflows.
- `hooks/` + `scripts/`: hook declarations and their helpers (the hosted
  plugin's executable entry points).
- `mcp/`: standalone server and client templates, plus the hosted connector
  deployment kit (`mcp/connector/`).
- `docs/`: the public user manual.

## Security And Legal

The default server is local stdio. Do not send circuits, syndromes, matrices,
credentials, or generated artifacts to external services; zero-egress is
enforced by the skills and agents in this package.

This project is provided **AS IS** and without warranty to the maximum extent
permitted by applicable law. See `DISCLAIMER.md`. The upstream
`qector-decoder-v3` package and all third-party dependencies retain their own
licenses and terms.

Author: Guillaume Lessard / iD01t Productions, ORCID `0009-0000-3465-3753`.