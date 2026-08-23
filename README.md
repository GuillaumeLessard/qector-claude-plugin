# QECTOR Claude Plugin

QECTOR is a local, fail-closed **quantum error correction (QEC)** integration
for **Claude Code** and **Claude Desktop**, built on `qector-decoder-v3==1.0.0`
and the QECTOR Decoder v3 Reference Manual (DOI: `10.5281/zenodo.21941046`).
Every correction returned by this plugin is verified against
**H c = s (mod 2)** before it leaves the local server, and the default
operation makes **no network request**.

> **4 MCP servers · 8 stable / 29 research / 3 admin tools · 11 commands
> · 5 agents · 28 skills · zero-egress default**

---

## 🚀 Quick Start

**1. Install the runtime**

```bash
git clone https://github.com/GuillaumeLessard/qector-claude-plugin.git
cd qector-claude-plugin
python -m pip install -r requirements.txt
python scripts/qector_runtime_check.py
```

**2. Install as a Claude Code marketplace plugin**

```bash
claude plugin marketplace add GuillaumeLessard/qector-claude-plugin
claude plugin install qector@qector-tools
```

The default install exposes only `qector-library` (8 stable tools). Opt-in
research and admin surfaces are added explicitly — see the trust-zone
table below.

**3. Install the local Claude Desktop extension (Windows / macOS / Linux)**

The Claude Desktop manifest lives under `.claude-desktop-extension/` and
points at `mcp/mcp_server_desktop.py --profile safe`. The local installer
records the exact Python interpreter used, so Windows `PATH` ambiguity
cannot break the install:

```bash
python scripts/configure_claude_desktop.py --check-only   # dry run
python scripts/configure_claude_desktop.py --confirm      # write config
```

A native Windows command is also shipped:

```cmd
.\scripts\install_windows_connector.cmd
```

---

## 🔬 What ships in this release

### MCP servers (4)

| Server | Purpose | Tools | Default |
|:-------|:--------|:------|:--------|
| `qector-library` | Frozen stable decoding surface | **8** | ✅ |
| `qector-research` | Provisional research / evidence tools | **29** | opt-in |
| `qector-admin` | Privileged local operations | **3** | opt-in |
| `qector-desktop-mcp` | Claude Desktop safe profile | **8** | ✅ (Desktop) |

`qector-library` is the authoritative default surface. Every tool on it
verifies its output before returning: syndrome decoders check
**H c = s (mod 2)**, threshold sweeps ship Wilson 95% intervals with
SHA-256-stamped JSON artifacts, and `build_code_from_matrix` validates
dimensions and code family before allocating a parity-check matrix.

The research and admin servers are **never** auto-enabled. They are added
only by an explicit `--with-research` or `--with-admin` flag combined
with a `confirm=true` argument on every call.

### Commands (11)

`/qec-setup`, `/qec-facts`, `/qec-theorem`, `/qec-reproduce`,
`/qec-threshold-sweep`, `/qec-wilson`, `/qec-dem`, `/qec-code-inspect`,
`/qec-benchmark`, `/qec-sinter`, `/qec-validate-mcp`.

### Agents (5)

`qec-researcher`, `qec-developer`, `qec-validator`, `qec-sysadmin`,
`qec-hardware-engineer`.

### Skills (28)

`qector-core`, `qector-architecture`, `qector-math-foundations`,
`qector-codes-builder`, `qector-bp-osd`, `qector-two-stage-css`,
`qector-space-time`, `qector-decoders-deep-dive`, `qector-dem-pipeline`,
`qector-sinter`, `qector-ler-methodology`, `qector-pymatching-compat`,
`qector-batch-decoding`, `qector-orchestration`, `qector-reproducibility`,
`qector-testing-strategy`, `qector-deployment`, `qector-release-engineering`,
`qector-licensing`, `qector-services`, `qector-glossary`, `qector-educator`,
`qector-researcher`, `qector-developer`, `qector-sysadmin`,
`qector-hardware-engineer`, `qector-roadmap`, `qector-workbench`.

---

## 🛡️ Trust zones

The 40 tools split into three named trust zones, plus the Desktop safe
profile which re-exports the 8 stable tools through a separate adapter.
No tool calls the network by default.

| Zone | Count | Default? | Enables on | Risk posture |
|:-----|:------|:---------|:-----------|:-------------|
| Stable (library) | 8 | ✅ | always | every result is verified |
| Research (bench) | 29 | opt-in | `--with-research` | read / compute; Wilson CIs; SHA-256 artifacts |
| Admin | 3 | opt-in | `--with-admin` + `QECTOR_ADMIN_ENABLED=1` | `confirm=true` required per call |

### Per-tool call budgets

The MCP processes enforce their own ceilings because there is no external
rate limiter. The defaults are intentionally conservative; every ceiling
is overridable per-tool with `QECTOR_MCP_MAX_CALLS_<TOOL_NAME>` and
disable-able with `-1`.

| Tool | Default | Why it is limited |
|:-----|:--------|:------------------|
| `threshold_sweep` | 8 | writes hashed artifacts; large LER grid |
| `decode_single` | 64 | seeded decode loop; can be retried |
| `decode_syndrome` | 256 | per-call decode compute |
| `build_code_from_matrix` | 32 | arbitrary parity-check matrix |
| `hot_path_microbench` | 4 | machine-scoped; no portable claim |
| `system_setup` | 2 | can install packages, write dirs |
| `configure_claude_desktop` | 2 | rewrites Claude Desktop config |
| `workbench_probe` | 2 | launches a local executable |

Exhaustion returns `RESOURCE_LIMIT` and the process stays up. See
`SECURITY.md` for the input-size ceilings
(`QECTOR_MCP_MAX_DISTANCE`, `QECTOR_MCP_MAX_TRIALS`,
`QECTOR_MCP_MAX_SWEEP_POINTS`, `QECTOR_MCP_MAX_MATRIX_CELLS`).

### What this plugin does NOT do

- It does not transmit syndromes, parity matrices, circuits, or tool
  arguments anywhere by default. The only outbound network operation is
  the explicit opt-in PyPI freshness check
  (`compat_report(check_pypi=true)` / `env_block(check_pypi=true)`); it
  checks the published package version only and caches the response for
  the server process. See `PRIVACY.md`.
- It does not run untrusted code. The three tools classified as
  "Execute" (`decode_single`, `threshold_sweep`, `build_code_from_matrix`)
  perform scoped QEC math on caller-supplied binary inputs. They never
  spawn subprocesses, never load dynamic modules, and never read or
  write outside `QECTOR_ARTIFACT_DIR`.
- The four "Write" tools are limited to: writing the matrix file the
  caller just built (`code_export_matrices`), writing the local Claude
  Desktop config (`configure_claude_desktop`, requires `confirm=true`),
  and writing a hashed artifact under the configured artifact directory
  (`artifacts_sha256` / `artifact_metadata_check`). None touch arbitrary
  filesystem paths or remote endpoints.

---

## 🏗️ Architecture

```
                  QECTOR Claude Plugin v1.0.5
   ┌──────────────┐ ┌──────────────┐ ┌────────────────┐
   │ 11 Commands  │ │  5 Agents    │ │   28 Skills    │
   └──────┬───────┘ └──────┬───────┘ └────────┬───────┘
                          │
                          ▼
   ┌──────────────────────────────────────────────┐
   │  qector-library   MCP   8 stable tools       │  default
   │  qector-research  MCP  29 provisional tools  │  opt-in
   │  qector-admin     MCP   3 privileged tools   │  opt-in
   │  qector-desktop-mcp     8 safe-profile tools │  Desktop
   └──────────────────────┬───────────────────────┘
                          │  local stdio, zero egress
                          ▼
              ┌────────────────────────┐
              │  qector-decoder-v3     │
              │  1.0.0  (Rust/PyO3)    │
              └────────────────────────┘
```

The four servers share `mcp/qector_mcp_contract.py`, which enforces the
result envelope (`status`, `tool`, `server`, `version`), the closed
list of stable error codes, and the fail-closed default for every
operation.

---

## 📥 Download artifacts

The canonical `1.0.5` release assets live in `dist/`, each with a
SHA-256 sidecar and a combined `SHA256SUMS` file:

| Artifact | Contents |
|:---------|:---------|
| `qector-claude-plugin-1.0.5.zip` | Claude Code plugin: skills, agents, commands, prompts, hooks, MCP servers, docs |
| `qector-claude-plugin-source-1.0.5.zip` | Public QECTOR source distribution (no test suite, no CI workflows, no internal decks) |
| `qector-claude-desktop-1.0.5.mcpb` | Claude Desktop safe-extension MCPB (8 stable tools, `icon.png` and `README.md` at bundle root) |
| `qector-claude-plugin-1.0.5.sbom.json` | SPDX-2.3 SBOM for the three packages above |
| `provenance.json` | per-artifact SHA-256 + git commit + runtime pin |
| `SHA256SUMS` | combined sidecar file |

`qector-claude-desktop-1.0.5.mcpb` is the artifact listed in
`server.json` and is the one Claude Desktop's MCP Registry downloads.

---

## 📋 System requirements

| Component | Requirement |
|:----------|:------------|
| **Python** | 3.9 – 3.13 (tested on 3.12) |
| **OS** | Windows, macOS, Linux |
| **Backend** | `qector-decoder-v3==1.0.0` |
| **MCP runtime** | `mcp==1.26.0` |
| **Scientific stack** | `numpy>=1.26,<2.3`, `cryptography>=48.0.1,<50` |
| **Network** | none by default; one opt-in PyPI check |
| **GPU** | none — no portable speed claims are made |

---

## 📚 Documentation

| Document | Path |
|:---------|:-----|
| [User Manual](docs/User_Manual.md) | `docs/User_Manual.md` |
| [MCP API](MCP_API.md) | `MCP_API.md` |
| [Security](SECURITY.md) | `SECURITY.md` |
| [Provenance](PROVENANCE.md) | `PROVENANCE.md` |
| [Privacy](PRIVACY.md) | `PRIVACY.md` |
| [Release Validation](RELEASE_VALIDATION.md) | `RELEASE_VALIDATION.md` |
| [Tool Stability](TOOL_STABILITY.md) | `TOOL_STABILITY.md` |
| [Claude Desktop Notes](CLAUDE_DESKTOP.md) | `CLAUDE_DESKTOP.md` |
| [Changelog](CHANGELOG.md) | `CHANGELOG.md` |
| Reference manual (v1.0.0) | DOI `10.5281/zenodo.21941046` |

---

## 🛠️ Development and release

```bash
python -m unittest discover -s tests -v          # mathematical + protocol tests
python scripts/validate_source.py                 # source-only structural check
python scripts/validate_plugin_bundle.py          # built-bundle check
python scripts/release_validate.py                # version + manifest cross-check
ruff check .                                      # lint
python scripts/build_release.py --all             # build all artifacts
```

Build the installable Desktop `.mcpb` on each target platform with an
approved runtime environment:

```bash
python scripts/build_release.py --desktop --runtime-root <venv>
```

The builder is deterministic: a fixed DOS timestamp is stamped on every
zip entry so the artifact hashes are stable across rebuilds.

---

## 📄 License

**Proprietary** — Copyright © 2026 Guillaume Lessard / iD01t Productions.
See [LICENSE.md](LICENSE.md).

The underlying `qector-decoder-v3` backend is separately licensed:

- ✅ **Free** for personal, academic, educational, and non-commercial
  research.
- 💼 **Commercial use** (company R&D, SaaS, hosted API, OEM, redistribution)
  requires a paid license — see [qector.store/pricing](https://qector.store/pricing).
- 🔄 60-day commercial evaluation, creditable against a license.

---

## 🤝 Support & Contact

| | |
|:--|:--|
| **Website** | [www.qector.store](https://www.qector.store) |
| **Commercial licensing** | <admin@qector.store> |
| **Support** | <admin@qector.store> |
| **Pricing** | [qector.store/pricing](https://qector.store/pricing) |
| **Security disclosure** | <admin@qector.store> (private) |

---

<p align="center">
  <strong>QECTOR Claude Plugin v1.0.5</strong><br/>
  Built on <code>qector-decoder-v3</code> v1.0.0 (Rust/PyO3 core)<br/><br/>
  © 2026 Guillaume Lessard / iD01t Productions
</p>
