# PulseMCP submission — QECTOR Claude Plugin v1.0.5

> **Status:** Queued. PulseMCP's submit page
> (`https://www.pulsemcp.com/submit`) is currently showing
> *"Apologies, submissions and changes are temporarily paused"*. We
> are not accepting new MCP server or client submissions until the
> directory pipeline overhaul is complete. This file is the
> ready-to-paste submission payload — re-submit it the moment
> PulseMCP reopens without rewriting it.

---

## 1. Server name (display)

**QECTOR Claude Plugin**

## 2. One-line description (for the directory card)

Local, fail-closed quantum error correction for Claude Code and Claude Desktop — `qector-decoder-v3` backend, every correction verified against `H c = s (mod 2)`.

## 3. Long description (for the directory page)

**QECTOR Claude Plugin** is the official MCP integration of the QECTOR
quantum error correction (QEC) engine for **Claude Code** and **Claude
Desktop**, built on `qector-decoder-v3==1.0.0` and grounded against the
QECTOR Decoder v3 Reference Manual (DOI `10.5281/zenodo.21941046`).

The plugin ships four named MCP servers across three trust zones — the
default install exposes only the eight stable tools. Every result is
verified before it leaves the local server, and the default operation
makes **no network request**.

- **qector-library** — 8 stable tools (default): `list_code_families`,
  `list_decoders`, `get_license_info`, `decode_syndrome`,
  `decode_single`, `threshold_sweep`, `build_code_from_matrix`,
  `compat_report`. Every result is checked against the parity-check
  relation `H c = s (mod 2)` before being returned.
- **qector-research** — 29 provisional tools (opt-in): Wilson 95% CI
  tables, DEM inspection, code-family introspection, hardware probes,
  micro-benchmarks, theorem and glossary lookup, reproduction
  workflows, and the three-tool evidence layer
  (`get_capability_matrix`, `get_evidence_policy`,
  `get_runtime_provenance`).
- **qector-admin** — 3 privileged tools (opt-in, `QECTOR_ADMIN_ENABLED=1`
  required + per-call `confirm=true`): `system_setup`,
  `configure_claude_desktop`, `workbench_probe` (with SHA-256
  approval of the launched binary).
- **qector-desktop-mcp** — 8 stable tools re-exported by the Desktop
  safe-profile adapter.

### Per-process call budgets

The MCP processes enforce their own ceilings because there is no
external rate limiter. Exhaustion returns `RESOURCE_LIMIT` and the
process stays up. Defaults are intentionally conservative; every
ceiling is overridable per-tool with
`QECTOR_MCP_MAX_CALLS_<TOOL_NAME>` and disable-able with `-1`.

| Tool | Default | Why it is limited |
|------|---------|-------------------|
| `threshold_sweep` | 8 | writes hashed artifacts; large LER grid |
| `decode_single` | 64 | seeded decode loop; can be retried |
| `decode_syndrome` | 256 | per-call decode compute |
| `build_code_from_matrix` | 32 | arbitrary parity-check matrix |
| `hot_path_microbench` | 4 | machine-scoped; no portable claim |
| `system_setup` | 2 | can install packages, write dirs |
| `configure_claude_desktop` | 2 | rewrites Claude Desktop config |
| `workbench_probe` | 2 | launches a local executable |

### What this plugin does NOT do

- No outbound network by default. The only network call is the
  explicit opt-in PyPI freshness check
  (`compat_report(check_pypi=true)` / `env_block(check_pypi=true)`).
- No `eval` / `exec` / dynamic `__import__` / `importlib` on caller
  input. The repository has zero hits for any of these patterns.
- No `eval`, `exec`, `__import__`, or `importlib.import_module` on
  caller input.
- The default 8-tool surface is subprocess-free, file-write-free, and
  network-free.

### Identification and provenance

Every MCP response carries `server_name`, `server_version`, and a
stable `status` code from the closed set documented in
`MCP_API.md`. Per-artifact SHA-256 digests and a git commit are
embedded in the `provenance.json` shipped with every release.
License: Proprietary. Reference manual:
`10.5281/zenodo.21941046` (v1.0.0).

## 4. Repository URL

`https://github.com/GuillaumeLessard/qector-claude-plugin`

## 5. Installation

**Claude Code (marketplace)**

```bash
claude plugin marketplace add GuillaumeLessard/qector-claude-plugin
claude plugin install qector@qector-tools
```

**Claude Desktop**

The Desktop installer is bundled in the plugin zip and the
`qector-claude-desktop-1.0.5.mcpb` is the artifact Claude Desktop's
MCP Registry downloads automatically:

```bash
python scripts/configure_claude_desktop.py --check-only   # dry run
python scripts/configure_claude_desktop.py --confirm      # write config
```

A native Windows command is also shipped:

```cmd
.\scripts\install_windows_connector.cmd
```

**Source install (from the public source archive)**

```bash
python -m pip install -r requirements.txt
python scripts/qector_runtime_check.py
```

## 6. Tags / categories (PulseMCP uses these)

- `quantum`
- `quantum-computing`
- `quantum-error-correction`
- `qec`
- `decoder`
- `surface-code`
- `qldpc`
- `mwpm`
- `union-find`
- `stim`
- `sinter`
- `python`
- `claude-code`
- `claude-desktop`
- `local`
- `zero-egress`
- `fail-closed`

## 7. Author / contact

- Name: Guillaume Lessard / iD01t Productions
- Email: <admin@qector.store>
- Website: <https://qector.store>
- Pricing: <https://qector.store/pricing>
- Security disclosure: <admin@qector.store> (private)

## 8. License

Proprietary. Free for personal, academic, educational, and
non-commercial research. Commercial use (company R&D, SaaS, hosted
API, OEM, redistribution) requires a paid license — see
[qector.store/pricing](https://qector.store/pricing). 60-day
commercial evaluation, creditable against a license.

## 9. Identifier for cross-references

- GitHub: `GuillaumeLessard/qector-claude-plugin`
- Official MCP Registry: `io.github.GuillaumeLessard/qector-desktop`
- PolicyLayer catalog: `com.policylayer/qector-claude-plugin`
- v1.0.5 MCPB SHA-256: `dc529600bae2f4ab1f13921737f20ded89fb41e5ce99dcabce5c2bc8ae0ed4c6`
- v1.0.5 release: `https://github.com/GuillaumeLessard/qector-claude-plugin/releases/tag/v1.0.5`

## 10. Submission checklist

- [x] Repository is public
- [x] `server.json` validates against the official MCP Registry schema
- [x] `mcp-publisher publish` succeeded (`io.github.GuillaumeLessard/qector-desktop`, v1.0.5, `status: active`, `isLatest: true`)
- [x] Release v1.0.5 page lists all 9 assets with SHA-256 sidecars
- [x] SBOM (`qector-claude-plugin-1.0.5.sbom.json`, SPDX-2.3) attached
- [x] Provenance JSON attached (git commit + per-artifact hash)
- [x] SECURITY.md has Identification, Trust Boundaries, Tool Risk Classification, Static Scanner Notes, and Dependabot non-exposure sections
- [x] Per-process call budgets documented
- [x] Identification block: `name: qector`, `display_name: QECTOR Quantum Error Correction`, `version: 1.0.5`, `license: Proprietary`, `author: Guillaume Lessard`, `repository: github.com/GuillaumeLessard/qector-claude-plugin`, `documentation: 10.5281/zenodo.21941046`
- [x] No eval/exec/__import__/importlib on caller input
- [x] No outbound network in default operation
- [x] No proprietary source files in the public tree (`src/*.rs` is not present)
- [x] Source distribution (`qector-claude-plugin-source-1.0.5.zip`) excludes `tests/`, `mcp/tests/`, `.github/`, `presentations/`, `conftest.py`, scratch probes
