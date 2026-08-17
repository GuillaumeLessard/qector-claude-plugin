# QECTOR Claude — Quantum Error Correction for Claude

A **verified** quantum-error-correction engineering kit for [Claude Code](https://claude.com/claude-code) and claude.ai, built on the
[`qector-decoder-v3`](https://qector.store) wheel by **Guillaume Lessard / iD01t Productions**.

Everything in this package is grounded in the published `qector-decoder-v3==1.0.0` API:
the eight MCP tools are the verified stable contract, and any surface that is
provisional or non-frozen is explicitly labelled as such. No invented APIs, no
fabricated benchmark numbers.

This repository is the **source of truth**. The claude.ai-hosted plugin and its
prebuilt upload archives live in
[`GuillaumeLessard/qector-claude-plugin`](https://github.com/GuillaumeLessard/qector-claude-plugin).

---

## Table of Contents

- [Why Two Repositories?](#why-two-repositories)
- [Features](#features)
- [Installation](#installation)
- [Requirements](#requirements)
- [What's Inside](#whats-inside)
- [The MCP Server](#the-mcp-server)
- [Hosted Connector for claude.ai](#hosted-connector-for-claudeai)
- [Verified-API Doctrine](#verified-api-doctrine)
- [Mathematical Contract](#mathematical-contract)
- [Optional Features](#optional-features)
- [Packaging and Distribution](#packaging-and-distribution)
- [Repository Layout](#repository-layout)
- [Security and Legal](#security-and-legal)
- [Licensing](#licensing)

## Why Two Repositories?

claude.ai-hosted plugins may not ship a top-level `bin/` directory: such
executables are added to PATH on the CLI but are not shown on the admin approval
surface. Executable entry points must be declared via hooks, commands, or
`mcpServers` instead.

- **This repository (`qector-claude-skills`)** — the source: the full hosted-plugin
  surface plus the `mcp/connector/` deployment kit for the hosted HTTP connector.
- **[`qector-claude-plugin`](https://github.com/GuillaumeLessard/qector-claude-plugin)** —
  the consumer surface: the plugin contents (skills, agents, commands, hooks,
  MCP server) and the prebuilt upload archives in `dist/` with `.sha256` sidecars.

## Features

- **24 skills** — 8 QECTOR domain skills grounded in the reference-manual
  contract plus 16 official Anthropic skills (document processing, design,
  development, and web tooling).
- **5 specialized agents** — researcher, developer, validator, sysadmin, and
  hardware engineer.
- **3 reproducible commands** — facts reference, local LER sweeps, MCP validation.
- **1 local stdio MCP server** — exactly eight tools, explicit JSON schemas,
  fail-closed error handling, and `H c = s (mod 2)` verification on every decode.
- **1 hosted custom connector** — Streamable HTTP MCP endpoint with `/health`,
  optional bearer auth, and a Docker image for claude.ai.
- **Zero-egress by default** — circuits, syndromes, matrices, and artifacts
  never leave the device through the library server.

## Installation

### Option A — Claude Code marketplace (recommended for users)

```bash
claude plugin marketplace add GuillaumeLessard/qector-claude-plugin
claude plugin install qector@qector-tools
```

The plugin is installed at user scope with strict validation. Verify the MCP
handshake inside Claude Code with the `qec-validate-mcp` command.

### Option B — Local development (this repository)

```bash
git clone https://github.com/GuillaumeLessard/qector-claude-skills.git
cd qector-claude-skills
python -m pip install -r requirements.txt

claude plugin validate "<PLUGIN_ROOT>" --strict
claude --plugin-dir "<PLUGIN_ROOT>"
```

The root `.mcp.json` uses `${CLAUDE_PLUGIN_ROOT}` and is ready for plugin-local
execution. For Claude Desktop or a generic MCP client, copy
`mcp/claude_desktop_config.json`, replace `<PLUGIN_ROOT>` with the package's
absolute path, and perform `initialize` and `tools/list` before using any tool.

### Option C — claude.ai (web)

1. Download `dist/qector-claude-plugin-v1.0.0.zip` from the
   [plugin repository](https://github.com/GuillaumeLessard/qector-claude-plugin).
2. Upload it as a plugin on claude.ai. See
   [Packaging and Distribution](#packaging-and-distribution) for the single-skill
   archive used by the custom-skill uploader.

## Requirements

| Component | Version |
|---|---|
| Python | 3.9 or newer (tested on 3.12) |
| `qector-decoder-v3` | `==1.0.0` (pinned in `requirements.txt`) |
| `mcp` | `==1.26.0` (pinned in `requirements.txt`) |

Install with the same interpreter that will launch the MCP server, in system
Python or a virtual environment:

```text
python -m pip install -r requirements.txt
```

Stim/DEM workflows are optional; see [Optional Features](#optional-features).

## What's Inside

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
| `run-qector` | Headless Workbench controller: benchmark jobs, `.stim`/`.dem` runs, artifact export |

### Skills (`skills/`) — Official Anthropic

`docx`, `xlsx`, `pptx`, `pdf`, `doc-coauthoring`, `canvas-design`,
`frontend-design`, `web-artifacts-builder`, `webapp-testing`,
`algorithmic-art`, `theme-factory`, `slack-gif-creator`, `internal-comms`,
`claude-api`, `skill-creator`, `mcp-builder`.

Official skills retain their own licenses; see `THIRD_PARTY_NOTICES.md`.

### Agents (`agents/`)

| Agent | Specialization |
|-------|----------------|
| `qec-researcher` | Academic research, paper reproduction, threshold sweeps |
| `qec-developer` | Code integration, API design, performance tuning |
| `qec-validator` | Formal verification, mathematical proof checking |
| `qec-sysadmin` | Operations, monitoring, incident response |
| `qec-hardware-engineer` | Physical qubit characterization, cryogenic systems |

### Commands (`commands/`)

| Command | Description |
|---------|-------------|
| `qec-facts` | Quick reference: codes, decoders, thresholds |
| `qec-threshold-sweep` | Run local LER sweeps with Wilson 95% intervals |
| `qec-validate-mcp` | Validate MCP server tools and schemas |

### Hooks (`hooks/`)

`hooks.json` — SessionStart banner and PostToolUse usage log, backed by the
helpers in `scripts/`.

## The MCP Server

Launch the library server directly:

```text
python mcp/mcp_server_library.py
```

The transport is **local stdio only**. The server exposes exactly eight tools:

| Tool | Description |
|------|-------------|
| `list_code_families` | Enumerate supported code families |
| `list_decoders` | Enumerate available decoders |
| `get_license_info` | Report license state |
| `decode_syndrome` | Decode a syndrome array |
| `decode_single` | Decode a single decode request |
| `threshold_sweep` | Run LER sweeps with Wilson 95% intervals |
| `build_code_from_matrix` | Build a code from a parity-check matrix |
| `compat_report` | Report pymatching / sinter compatibility |

The server validates binary inputs, enforces resource bounds, checks every
correction against `H c = s (mod 2)` before logical scoring, and returns MCP
tool errors without exposing tracebacks.

## Hosted Connector for claude.ai

`mcp/connector/` contains a Streamable HTTP MCP connector for hosted use:

- `qector_connector_server.py` — FastAPI server exposing the library tools over HTTP.
- `Dockerfile` + `requirements-connector.txt` — build and run the container.
- `.env.example` — configuration template.
- `/health` endpoint and optional `QECTOR_CONNECTOR_TOKEN` bearer auth.

Deploy the container on any Docker host (Render, Railway, Fly, AKS, ...),
then register `https://<host>/mcp` as a **custom connector** in claude.ai.
See `mcp/connector/README.md` for the full walkthrough.

## Verified-API Doctrine

- **The eight MCP tools are the stable contract.** Everything an agent writes
  against them is safe to ship.
- **Verified-but-non-frozen surfaces exist.** The wheel also contains a working
  `rest_api` HTTP surface (`/decode`, `/health`, `/version`,
  `/api/license/activate`, `/api/license/info`), top-level exports
  (`get_decoder`, `get_decoder_pool`, `clear_decoder_cache`, `decode_mmap`,
  `opencl_is_available`, `run_grpc_server`, `start_metrics_server`), and a
  Workbench MCP server — all real, all present in the shipped wheel, all
  classified **provisional / non-frozen** (changelog 0.7.0 → 1.0.0). Skills
  referencing them mark them provisional and never present them as contract.
- **No invented APIs.** Skills verify every symbol against the installed wheel
  before using it, and the docs ship a verified API reference
  (`skills/qector-core/references/qector_verified_api.md`).
- **No fabricated data.** Benchmark numbers, LER values, and exports must trace
  to real decodes.

## Mathematical Contract

- All binary algebra is over **F2**.
- Corrections must satisfy `H c = s (mod 2)` before logical scoring.
- Logical outcomes use the **logical coset**, not raw correction equality.
- LER reports include **Wilson 95% intervals** and a noise-model tag.
- `code_capacity` and `circuit_level` results are **not comparable**.
- Performance, hardware, GPU, threshold, and license state are **device-local**.
- Fresh artifacts belong outside the plugin and use an external `.sha256` sidecar.

The F2 obligations are validated device-local against the reference manual; the
validation tooling is internal and not distributed in this repository.

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
the [plugin repository](https://github.com/GuillaumeLessard/qector-claude-plugin)
under `dist/` with `.sha256` sidecars:

- `qector-qector-core-skill.zip` — a **single-skill** ZIP for the claude.ai
  custom-skill uploader. It contains one top-level `qector-core/` folder with
  `SKILL.md` at its root. Upload this file directly; do not rename it to a
  multi-skill bundle.
- `qector-claude-plugin-v1.0.0.zip` — the **full plugin** ZIP for the Claude
  Code plugin flow (`claude --plugin-dir`) and for claude.ai plugin upload. It
  preserves the `.claude-plugin/`, `skills/`, `agents/`, `commands/`, `hooks/`,
  `scripts/`, and `mcp/` layout, and contains no `bin/` directory.

Two hosting rules drive the layout:

1. The claude.ai skill uploader accepts exactly one top-level folder and
   rejects ZIP entries that contain Windows backslashes (the "Zip file contains
   path with invalid characters" error). Never upload this whole repository as
   a single custom skill.
2. claude.ai-hosted plugins may not ship a top-level `bin/` directory, because
   such executables are added to PATH on the CLI but are not shown on the admin
   approval surface. Executable entry points must be declared via hooks,
   commands, or `mcpServers` instead.

## Repository Layout

- `.claude-plugin/` — plugin and marketplace manifests.
- `skills/` — 24 QECTOR and official Anthropic skills.
- `agents/` — custom QEC agents.
- `commands/` — local slash-command workflows.
- `hooks/` + `scripts/` — hook declarations and their helpers (the hosted
  plugin's executable entry points).
- `mcp/` — standalone server, client templates, and the hosted connector
  deployment kit (`mcp/connector/`).
- `docs/` — the public user manual (`User_Manual.md`).

## Security and Legal

The default server is **local stdio**. Do not send circuits, syndromes,
matrices, credentials, or generated artifacts to external services; zero-egress
is enforced by the skills and agents in this package.

This project is provided **AS IS** and without warranty to the maximum extent
permitted by applicable law. See `DISCLAIMER.md`. The upstream
`qector-decoder-v3` package and all third-party dependencies retain their own
licenses and terms.

## Licensing

`qector-decoder-v3` is free for academic, personal, and non-commercial
research. Commercial use requires a licence from
[https://qector.store/pricing](https://qector.store/pricing).

Author: **Guillaume Lessard / iD01t Productions**, ORCID
`0009-0000-3465-3753`.
