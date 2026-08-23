# QECTOR Claude Plugin v1.0.4

Production-ready release. Completes the 1.0.3 hardening pass and adds
process-local call budgets so an agent cannot loop mutating or
expensive tools without a ceiling.

## What ships

**4 MCP servers · 8 stable / 29 research / 3 admin tools · 11 commands
· 5 agents · 28 skills · zero-egress default**

- `qector-library` — **8 stable** tools, default-on, every result verified against `H c = s (mod 2)`.
- `qector-research` — **29 provisional** tools, opt-in (`--with-research`).
- `qector-admin` — **3 privileged** tools, opt-in (`QECTOR_ADMIN_ENABLED=1` + per-call `confirm=true`).
- `qector-desktop-mcp` — **8 stable** tools re-exported by the Desktop safe-profile adapter.

The default install exposes only `qector-library` (or the Desktop safe
profile for Claude Desktop). Research and admin surfaces are added
explicitly.

## Per-process call budgets

The MCP processes enforce their own ceilings because there is no
external rate limiter. Exhaustion returns `RESOURCE_LIMIT` and the
process stays up. Override a single ceiling with
`QECTOR_MCP_MAX_CALLS_<TOOL_NAME>` (uppercase). Set `-1` to disable.

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

Input-size ceilings (`QECTOR_MCP_MAX_DISTANCE`, `QECTOR_MCP_MAX_TRIALS`,
`QECTOR_MCP_MAX_SWEEP_POINTS`, `QECTOR_MCP_MAX_MATRIX_CELLS`) still
apply on every call.

## Identification and security

`SECURITY.md` carries:

- An Identification block with the canonical name, version, license,
  author, repository, reference-manual DOI, and privacy URL.
- A per-tool risk classification table that maps every tool to
  Read / Compute / Build / Write (local) / Launch (privileged).
- A "Static Scanner Notes" section that addresses PolicyLayer,
  MCP Registry, and CodeQL-style audits explicitly.
- A "Runtime Dependabot Advisories (status)" table that documents
  why the three open `mcp==1.26.0` advisories (CVE-2026-59950,
  CVE-2026-52869, CVE-2026-52870) are non-applicable to this
  release — every QECTOR server uses `stdio` transport only, and
  the QECTOR wheel itself does not require `mcp`.

## Canonical artifacts (this release)

| Artifact | SHA-256 |
|:---------|:--------|
| `qector-claude-plugin-1.0.4.zip` | `748b06f92189e7163f8a7a6fd85ebf3e294425bc7ddac0577df56dcead703a1a` |
| `qector-claude-plugin-source-1.0.4.zip` | `43310329dcb249d667b557238544cf77aadbbc786e08f4fd35538813d1f2b9ef` |
| `qector-claude-desktop-1.0.4.mcpb` | `e9be10eca47e4437153fc6432e4ef892207afa3e439b9299492ee3f537aca51c` |

Per-file `.sha256` sidecars, combined `SHA256SUMS`, SPDX-2.3 SBOM, and
`provenance.json` (with git commit + per-artifact hash) are also
attached.

## Install

```bash
# Claude Code
claude plugin marketplace add GuillaumeLessard/qector-claude-plugin
claude plugin install qector@qector-tools

# Claude Desktop (Windows / macOS / Linux)
# The Desktop installer is included in the plugin zip and the
# qector-claude-desktop-1.0.4.mcpb is the artifact Claude Desktop's
# MCP Registry downloads automatically.
```

## License

Proprietary — Copyright © 2026 Guillaume Lessard / iD01t Productions.
See `LICENSE.md` in the source archive. The `qector-decoder-v3` backend
is free for personal, academic, educational, and non-commercial
research; commercial use requires a paid license
(qector.store/pricing).
