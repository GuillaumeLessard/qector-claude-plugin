<p align="center">
  <img src=".claude-desktop-extension/logo.png" alt="QECTOR Logo" width="80%" />
</p>

<h1 align="center">QECTOR Claude Plugin</h1>

<p align="center">
  <strong>Professional Claude Code &amp; Claude Desktop Integration</strong><br/>
  <em>2 MCP Servers · 37 Tools · 13 Slash Commands · 5 Agents · 28 Skills</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-1.0.2-0078D4?style=for-the-badge&logo=anthropic&logoColor=white" alt="Version"/>
  <img src="https://img.shields.io/badge/backend-qector--decoder--v3_1.0.0-E44D26?style=for-the-badge&logo=rust&logoColor=white" alt="Backend"/>
  <img src="https://img.shields.io/badge/python-≥3.9-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/MCP_Tools-37-8A2BE2?style=for-the-badge" alt="MCP Tools"/>
  <img src="https://img.shields.io/badge/binaries-Windows_|_macOS_|_Linux-success?style=for-the-badge" alt="Platform"/>
  <img src="https://img.shields.io/badge/license-Source--Available-FFA500?style=for-the-badge" alt="License"/>
</p>

<p align="center">
  <a href="https://www.qector.store">Website</a> ·
  <a href="#-quick-start">Quick Start</a> ·
  <a href="#-ecosystem">Ecosystem</a> ·
  <a href="#-commands-13">Commands</a> ·
  <a href="CHANGELOG.md">CHANGELOG</a> ·
  <a href="#-license">License</a>
</p>

---

## 📖 Overview

**QECTOR Claude Plugin** is the official integration of the QECTOR quantum error correction (QEC) engineering and research environment for **Claude Code** and **Claude Desktop**. Built on `qector-decoder-v3`, it mathematically enforces $H c \equiv s \pmod 2$ across 10 code families and 5 MWPM/BP-OSD backends, ensuring fail-closed integrity for enterprise and academic quantum research.

> **Zero Egress · Strict Math · Fail-Closed**
> The plugin runs 100% locally and never transmits QEC simulation telemetry to the cloud.

This repository is the **app-free plugin** companion to the QECTOR Decoder Workbench desktop application (Windows / Linux). Both v1.0.1 workbench releases are fully compatible with this plugin — see the [Workbench Compatibility](#-workbench-compatibility) section.

---

## 🚀 Quick Start

**1. Clone and install**

```bash
git clone https://github.com/GuillaumeLessard/qector-claude-plugin.git
cd qector-claude-plugin
python -m pip install -r requirements.txt
python scripts/qector_runtime_check.py
```

**2. Claude Desktop GUI installer (Windows)**

Instantly registers QECTOR as a first-class Extension inside Claude Desktop Settings:

```cmd
.\scripts\install_windows_connector.cmd
```

(A PowerShell equivalent ships as `scripts/install_windows_connector.ps1`. Linux and macOS use the Claude Desktop extension in `.claude-desktop-extension/`.)

**3. Claude Code marketplace integration**

```bash
claude plugin marketplace add GuillaumeLessard/qector-claude-plugin
claude plugin install qector@qector-tools
```

**4. Optional: guided system setup (with safety approbation)**

```bash
python scripts/qector_system_setup.py --check-only   # read-only audit, no changes
python scripts/qector_system_setup.py --confirm      # execute after user approval
```

---

## 📥 Downloads

**v1.0.2 release assets** (in `dist/`, each with a `.sha256` sidecar):

| Artifact | Contents |
|:---------|:---------|
| **`qector-claude-plugin-v1.0.2.zip`** | Full plugin package: skills, agents, commands, prompts, MCP servers, docs and scripts |
| **`qector-qector-core-skill.zip`** | Standalone `qector-core` skill bundle |

> **Requirements:** Python 3.9+ (tested on Python 3.12), `qector-decoder-v3==1.0.0`,
> `mcp==1.26.0`, `numpy>=1.26,<2.3`, `cryptography>=48.0.1,<50`. All pinned in
> `requirements.txt` against the published wheel constraints.

---

## 🧩 Ecosystem

### 🤖 MCP Servers (37 Tools)

Two local stdio Model Context Protocol servers run against the `qector-decoder-v3` core:

| Server | Tools | Coverage |
|:-------|:------|:---------|
| **`qector-library`** | **8 stable tools** | Core decoding, code generation, threshold sweeps, and licensing |
| **`qector-bench`** | **29 research tools** | Wilson intervals, Stim/DEM analysis, Sinter shims, theorem/glossary lookup, system setup, and hardware probes |

**`qector-library` tools:** `list_code_families`, `list_decoders`, `get_license_info`, `decode_syndrome`, `decode_single`, `threshold_sweep`, `build_code_from_matrix`, `compat_report`

<details>
<summary><strong>`qector-bench` tools (29)</strong></summary>

`wilson_ci`, `wilson_table`, `logical_coset_score`, `dem_inspect`, `dem_collapse_parallel`, `code_family_info`, `code_export_matrices`, `code_logicals_inspect`, `code_distance_check`, `pymatching_compat_check`, `sinter_decoder_list`, `qiskit_plugin_check`, `hardware_probe`, `license_active_check`, `env_block`, `compat_report`, `workbench_probe`, `artifacts_sha256`, `artifact_metadata_check`, `decode_faithfulness_check`, `hot_path_microbench`, `stim_circuit_probe`, `sinter_task_template`, `workload_hash`, `theorem_lookup`, `glossary_lookup`, `reproduction_command_lookup`, `system_setup`, `configure_claude_desktop`

</details>

### 💬 Commands (13 Slash Commands)

| Command | Description |
|:--------|:------------|
| `/qec-desktop-connector` | Zero-friction Claude Desktop MCP configuration |
| `/qec-setup` | Guided first-time setup and diagnostic audit |
| `/qec-facts` | Quick reference for codes, decoders, and strict-math rules |
| `/qec-theorem` | Formulations and proof obligations for Theorems 1–16 |
| `/qec-reproduce` | Reference manual Appendix D reproduction workflows |
| `/qec-decode` | Single-shot syndrome decoding asserting parity |
| `/qec-threshold-sweep` | LER sweeps with exact Wilson 95% confidence intervals |
| `/qec-wilson` | Wilson 95% score interval calculator |
| `/qec-dem` | Detector Error Models (DEM) and Stim circuit inspection |
| `/qec-code-inspect` | Verify code parameters [[n,k,d]] and check matrices |
| `/qec-benchmark` | Decoder latency and throughput microbenchmarks |
| `/qec-sinter` | Sinter task templates and benchmark configuration |
| `/qec-validate-mcp` | Validate tool schemas, JSON-RPC transport, and health |

### 🎭 Agents (5 Specialized Personas)

| Agent | Focus |
|:------|:------|
| `qec-researcher` | Academic research, paper reproduction, threshold sweeps |
| `qec-developer` | Code integration, API design, performance tuning |
| `qec-validator` | Formal verification, mathematical proof checking |
| `qec-sysadmin` | Operations, zero-egress monitoring, incident response |
| `qec-hardware-engineer` | Physical qubit characterization, cryogenic constraints |

### 🛠️ Skills (28 Domain Primitives)

`qector-core`, `qector-architecture`, `qector-math-foundations`, `qector-codes-builder`, `qector-bp-osd`, `qector-two-stage-css`, `qector-space-time`, `qector-decoders-deep-dive`, `qector-dem-pipeline`, `qector-sinter`, `qector-ler-methodology`, `qector-pymatching-compat`, `qector-batch-decoding`, `qector-orchestration`, `qector-reproducibility`, `qector-testing-strategy`, `qector-deployment`, `qector-release-engineering`, `qector-licensing`, `qector-services`, `qector-glossary`, `qector-educator`, `qector-researcher`, `qector-developer`, `qector-sysadmin`, `qector-hardware-engineer`, `qector-roadmap`, `qector-workbench`

---

### 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────┐
│                 QECTOR Claude Plugin v1.0.2               │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐ │
│  │ 13 Commands │  │  5 Agents    │  │  28 Skills       │ │
│  └──────┬──────┘  └──────┬───────┘  └────────┬─────────┘ │
│         └────────────────┼───────────────────┘           │
│                          ▼                              │
│  ┌─────────────────────────────────────────────┐        │
│  │  qector-library MCP (8 tools)   stdio only  │        │
│  │  qector-bench   MCP (29 tools)  stdio only  │        │
│  └──────────────────────────┬──────────────────┘        │
│                             │                           │
│              ┌──────────────▼──────────────┐            │
│              │  qector-decoder-v3 1.0.0     │            │
│              │  (Rust/PyO3 engine, local)   │            │
│              └─────────────────────────────┘            │
└──────────────────────────────────────────────────────────┘
```

**Claude Desktop Extension** — a fully integrated custom connector
(`manifest_version: 0.3`, in `.claude-desktop-extension/`) that displays native
UI controls, documentation, and the QECTOR icon directly within
**Claude Desktop → Settings → Connectors**.

---

## 🛡️ Core Engineering Guidelines

1. **Mathematical Strictness** — Every single syndrome decoding must verify $H c \equiv s \pmod 2$. Approximations are rejected.
2. **Zero-Egress Security** — Operations run 100% locally. The plugin never transmits QEC simulation telemetry to the cloud, protecting proprietary hardware IP.
3. **Fail-Closed Design** — Mismatched matrix dimensions, unrecognized code families, or invalid distance requests immediately raise deterministic errors rather than silently corrupting the quantum state.
4. **Statistical Rigor** — All LER threshold sweeps include exact Wilson 95% binomial score intervals. Point estimates without bounds are rejected.

The mathematical authority is the QECTOR Decoder v3 reference manual v1.0.0
(DOI: `10.5281/zenodo.21941046`); the plugin is grounded against all 16
Theorems, 27 Chapters, and 5 Appendices.

---

## 🤖 Workbench Compatibility

The official **QECTOR Decoder Workbench** desktop application — both the
**Windows** (`qector-decoder-workbench-windows`, portable `.exe`) and **Linux**
(`qector-decoder-workbench-linux`, AppImage) v1.0.1 releases — is **fully
compatible** with this plugin:

- Both workbench releases bundle the same `qector-decoder-v3 1.0.0` backend this
  plugin pins (`qector-decoder-v3==1.0.0`) — versions match exactly.
- Use the workbench's 85-tool `--mcp` server, this plugin's two stdio MCP
  servers, or all three at once — every transport is local-only with zero
  network egress.
- The plugin's `workbench_probe` tool detects a running workbench and reports
  its version, tool count, and MCP protocol status.
- Workbench artifacts (exports, benchmark reports, deposit sidecars) are
  verified by the plugin's `artifacts_sha256` / `artifact_metadata_check` tools.

| Workbench release | Artifact | Backend |
|:------------------|:---------|:--------|
| Windows v1.0.1 | `QectorWorkbench-Portable.exe` | `qector-decoder-v3 1.0.0` |
| Linux v1.0.1 | `QectorWorkbench-1.0.1-x86_64.AppImage` | `qector-decoder-v3 1.0.0` |

---

## 📋 System Requirements

| Component | Requirement |
|:----------|:------------|
| **Python** | 3.9+ (tested on 3.12; wheel supports CPython 3.9–3.13) |
| **OS** | Windows, macOS, Linux (Claude Desktop / Claude Code) |
| **Backend** | `qector-decoder-v3==1.0.0` |
| **MCP runtime** | `mcp==1.26.0` (with low-level stdio adapter) |
| **Scientific stack** | `numpy>=1.26,<2.3`, `cryptography>=48.0.1,<50` |
| **Network** | None — all servers run over local stdio |
| **GPU** | Optional — workload-scoped; no portable speed claims are published |

---

## 📚 Documentation

| Document | Path |
|:---------|:-----|
| [User Manual](docs/User_Manual.md) | `docs/User_Manual.md` |
| [Math Validation](docs/MATH_VALIDATION.md) | `docs/MATH_VALIDATION.md` |
| [MCP Validation Report](mcp/VALIDATION_REPORT.md) | `mcp/VALIDATION_REPORT.md` |
| [CLAUDE.md](CLAUDE.md) | Agent instructions |
| [CLAUDE_DESKTOP.md](CLAUDE_DESKTOP.md) | Desktop integration notes |
| [CHANGELOG](CHANGELOG.md) | Release history |
| [PRIVACY](PRIVACY.md) | Privacy policy |
| [DISCLAIMER](DISCLAIMER.md) | Disclaimer |
| Reference manual (v1.0.0) | DOI `10.5281/zenodo.21941046` |

---

## 📄 License

Proprietary, **source-available** software. Copyright (c) 2026 Guillaume Lessard
and iD01t Productions. See [LICENSE.md](LICENSE.md).

The underlying `qector-decoder-v3` backend is separately licensed:

- ✅ **Free** for personal, academic, educational, and non-commercial research
- 💼 **Commercial use** (company R&D, SaaS, hosted API, OEM, redistribution) **requires a [paid license](https://qector.store/pricing)**
- 🔄 60-day commercial evaluation available, creditable against a license

---

## 🤝 Support & Contact

| | |
|:--|:--|
| **Website** | [www.qector.store](https://www.qector.store) |
| **Commercial Licensing** | [admin@qector.store](mailto:admin@qector.store) |
| **Support** | [admin@qector.store](mailto:admin@qector.store) |
| **Pricing** | [qector.store/pricing](https://qector.store/pricing) |

---

<p align="center">
  <strong>QECTOR Claude Plugin v1.0.2</strong><br/>
  Built on <code>qector-decoder-v3</code> v1.0.0 (Rust/PyO3 core)<br/><br/>
  © 2026 Guillaume Lessard / iD01t Productions<br/><br/>
  <em>Powered by QECTOR</em>
</p>