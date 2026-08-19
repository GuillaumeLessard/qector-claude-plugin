# QECTOR Quantum Error Correction
**Professional Claude Code & Claude Desktop Integration**

QECTOR is a high-performance, strictly verified quantum error correction engineering and research environment built for `qector-decoder-v3`. By mathematically enforcing $H c \equiv s \pmod 2$ across 10 code families and 5 distinct MWPM/BP-OSD backends, QECTOR ensures fail-closed integrity for enterprise and academic quantum research.

This repository provides the official integration for **Claude Code** and **Claude Desktop (Windows/macOS/Linux)**, completely offline with zero-egress security.

***

## 🚀 Quick Start

**1. Clone and Install**
```bash
git clone https://github.com/GuillaumeLessard/qector-claude-plugin.git
cd qector-claude-plugin
python -m pip install -r requirements.txt
python scripts/qector_runtime_check.py
```

**2. Claude Desktop GUI Installer (Windows)**
Instantly registers QECTOR as a first-class Extension inside Claude Desktop Settings.
```cmd
.\scripts\install_windows_connector.cmd
```

**3. Claude Code Marketplace Integration**
```bash
claude plugin marketplace add GuillaumeLessard/qector-claude-plugin
claude plugin install qector@qector-tools
```

***

## 🧩 Architecture

**MCP Servers**
Two local stdio Model Context Protocol (MCP) servers run against the `qector-decoder-v3` core:
*   `qector-library` (8 stable tools): Core decoding, code generation, and licensing.
*   `qector-bench` (29 research tools): Threshold sweeps, Stim/DEM analysis, Wilson intervals, Sinter shims, and system setup.

**Claude Desktop Extension**
Fully integrated custom connector extension (`manifest_version: 0.3`). Displays native UI controls, documentation, and the QECTOR icon directly within Claude Desktop's **Settings → Connectors** menu.

***

## 📚 Ecosystem

**Commands (13 Slash Commands)**
*   `/qec-desktop-connector` : Zero-friction Claude Desktop MCP configuration.
*   `/qec-setup` : Guided first-time setup and diagnostic audit.
*   `/qec-facts` : Quick reference for codes, decoders, and strict-math rules.
*   `/qec-theorem` : Formulations and proof obligations for Theorems 1-16.
*   `/qec-reproduce` : Reference manual Appendix D reproduction workflows.
*   `/qec-decode` : Single-shot syndrome decoding asserting parity.
*   `/qec-threshold-sweep` : LER sweeps with exact Wilson 95% confidence intervals.
*   `/qec-wilson` : Wilson 95% score interval calculator.
*   `/qec-dem` : Detector Error Models (DEM) and Stim circuit inspection.
*   `/qec-code-inspect` : Verify code parameters $[[n,k,d]]$ and check matrices.
*   `/qec-benchmark` : Decoder latency and throughput microbenchmarks.
*   `/qec-sinter` : Sinter task templates and benchmark configuration.
*   `/qec-validate-mcp` : Validate tool schemas, JSON-RPC transport, and health.

**Agents (5 Specialized Personas)**
*   `qec-researcher` : Academic research, paper reproduction, threshold sweeps.
*   `qec-developer` : Code integration, API design, performance tuning.
*   `qec-validator` : Formal verification, mathematical proof checking.
*   `qec-sysadmin` : Operations, zero-egress monitoring, incident response.
*   `qec-hardware-engineer` : Physical qubit characterization, cryogenic constraints.

**Skills (28 Domain Primitives)**
Comprehensive instruction sets covering `qector-core`, `qector-architecture`, `qector-bp-osd`, `qector-codes-builder`, `qector-math-foundations`, `qector-orchestration`, `qector-sinter`, `qector-dem-pipeline`, and more.

***

## 🛡️ Core Engineering Guidelines

1.  **Mathematical Strictness**: Every single syndrome decoding must verify $H c \equiv s \pmod 2$. Approximations are rejected.
2.  **Zero-Egress Security**: Operations run 100% locally. The plugin never transmits QEC simulation telemetry to the cloud, protecting proprietary hardware IP.
3.  **Fail-Closed Design**: Mismatched matrix dimensions, unrecognized code families, or invalid distance requests immediately raise deterministic errors rather than silently corrupting the quantum state.
4.  **Statistical Rigor**: All LER threshold sweeps include exact Wilson 95% binomial score intervals. Point estimates without bounds are rejected.

***

**Requirements**: Python 3.10+, `qector-decoder-v3==1.0.0`, `mcp==1.2.0`, `numpy`.
**Documentation**: See the `QECTOR_Reference_Manual_v1.0.0.pdf` (DOI: 10.5281/zenodo.21941046).
