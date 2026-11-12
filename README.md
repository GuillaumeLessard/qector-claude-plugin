<p align="center">
  <img src="https://raw.githubusercontent.com/GuillaumeLessard/.github/main/profile/logo_banner.png" alt="QECTOR" width="70%" />
</p>

# QECTOR Claude Plugin 2.0.1

**Air-gapped, schema-validated, audited quantum error correction for
Claude Code and Claude Desktop, built on `qector-decoder-v3==1.0.1`.**

Every correction returned by an MCP tool is checked against the parity
relation `H c = s (mod 2)` before it leaves the process. Every request is
validated against a JSON Schema 2020-12 input schema before any decoder
code runs, and every response is validated against the tool's advertised
output schema before it is written. The default server opens no listening socket,
launches no process, verifies its own files at startup, and can keep a
hash-chained audit log.

> **1 secure MCP server (12 tools default, 41 in research profile) · 3
> standalone servers · 11 commands · 5 agents · 28 skills · contract 2.0 ·
> `mcp` 1.30+ and 2.x · Python 3.10–3.13 · air-gapped by default**

## Why 2.0.0

The 1.0.x line made claims its process could not enforce. 2.0.0 turns
those claims into mechanisms and states what remains:

| | 1.0.6 | 2.0.0 |
|:--|:--|:--|
| Network | "zero egress" in the docs; `check_pypi=true` opened a connection | in-process guard installed before the first MCP frame (defence in depth; host egress rule documented for a hard guarantee); PyPI check refused |
| Validation | SDK-dependent input check, no output check | own Draft 2020-12 validator both ways; 91 committed schema files |
| Integrity | none | `INTEGRITY.json` verified at startup, strict by default |
| Audit | none | optional hash-chained JSONL log |
| SDK | `mcp==1.26.0` (3 CVEs), broke on `mcp` 2.x | `mcp>=1.30,<3`; same wire output on both generations |
| Release | three different trees labelled 1.0.6 | deterministic builder that refuses a dirty tree, hashed `requirements.lock`, per-archive manifest + `RELEASE_COMMIT`, Ed25519-signed manifests and `SHA256SUMS`, Sigstore log entry |
| Honesty about the wheel | not mentioned | native TLS client and billing endpoint disclosed in `airgap_status` and SECURITY.md |
| Wheel defects | `color_code` d=3 (1 check, no logicals) exposed as decodable; `rotated_surface` labelled distance d while a weight-2 error is undetectable | per-family health probe with a checked `effective_distance` (exact for graphlike codes via the matching graph's shortest odd-parity cycle, bounded enumeration otherwise; never the wheel's label); degenerate refused, weak warned on every result; a corrected `rotated_surface_corrected` family built by the plugin and verified at construction (`mcp/qector_codes.py`). 2.0.1 pins `qector-decoder-v3==1.0.1`, which fixes these families upstream; the probe now verifies every one at its label |
| Shipped bugs | `sinter_task_template` crashed on every call; DEM collapse ignored the 3rd+ mechanism | fixed, with regression tests |

## Installation

**Claude Code**

```bash
claude plugin marketplace add GuillaumeLessard/qector-claude-plugin
claude plugin install qector@qector-tools
```

The plugin registers `qector-secure` (`mcp/mcp_server_secure.py --profile
safe`, `QECTOR_AIR_GAPPED=1`). Interpreter resolution goes through
`scripts/qector-python` (`QECTOR_PYTHON` → `python3.13`…`python3.10` →
`python3` → `python` → well-known Homebrew / python.org / pyenv locations,
3.10–3.13), a POSIX `sh` script.

*Windows (Claude Code):* a plugin manifest has one `command` for every
platform and a `sh` script is not a Win32 executable, so on native Windows
the plugin's server starts only where `sh` is on `PATH` (Git for Windows
with "Unix tools" selected, or WSL). Otherwise register the server once
by hand with the Windows launcher, which also serves the hooks:

```text
claude mcp add qector-secure -e QECTOR_AIR_GAPPED=1 -e QECTOR_INTEGRITY_STRICT=1 -e QECTOR_SILENT=1 -- cmd /c "<plugin root>\scripts\qector-python.cmd" "<plugin root>\mcp\mcp_server_secure.py" --profile safe
```

The Claude Desktop extension does not have this limitation: its manifest
carries a `win32` override that launches `scripts/qector-python.ps1`
through `powershell.exe`.

The hooks (`hooks/hooks.json`) run in shell form, which Claude Code
executes with Git Bash on Windows; without Git for Windows they report an
error on each session start and the (optional) usage log is not written.
The server itself is unaffected.

**Claude Desktop**

Install `qector-claude-desktop-2.0.1.mcpb` (Settings → Extensions →
Advanced → Install Extension). The bundle runs the same secure server in
strict-integrity mode; the optional *Audit log directory* setting enables
the hash-chained log. A platform-specific bundle with the runtime vendored
into `server/lib` can be built with `scripts/build_release.py --desktop
--bundle-lib <wheelhouse>`.

**Air-gapped laboratory**

See [AIRGAP.md](AIRGAP.md): build a wheelhouse on a connected host
(`scripts/build_wheelhouse.py`), carry it with `SHA256SUMS`, run
`scripts/install_offline.sh` / `.ps1` on the lab machine, and apply a
host egress rule.

**From source**

```bash
git clone https://github.com/GuillaumeLessard/qector-claude-plugin.git
cd qector-claude-plugin
python -m pip install -r requirements.lock      # exact tested closure (Python 3.10-3.13)
QECTOR_SILENT=1 python scripts/qector_runtime_check.py
```

## The tool surface

| Server | Entry point | Tools | Default |
|:-------|:------------|------:|:--------|
| `qector-secure` | `mcp/mcp_server_secure.py --profile safe` | 12 | ✅ Claude Code & Desktop |
| `qector-secure --profile research` | same | 41 | opt-in |
| `qector-library` | `mcp/mcp_server_library.py` | 8 | legacy |
| `qector-research` | `mcp/mcp_server_qector_bench.py` | 29 | opt-in |
| `qector-admin` | `mcp/mcp_server_admin.py` | 3 | opt-in, `QECTOR_ADMIN_ENABLED=1` |

Control-plane tools of the secure server: `airgap_status`,
`integrity_check`, `schema_catalog`, `audit_log_status`. Full contract in
[MCP_API.md](MCP_API.md); every schema in [`schemas/`](schemas/).

## Verification gates

```bash
python scripts/release_validate.py                 # manifests, pins, disclosures
python scripts/validate_source.py                  # tree shape
python scripts/export_schemas.py --check           # schemas/ in sync with the servers
python scripts/generate_integrity_manifest.py --check
QECTOR_SILENT=1 python -m unittest discover -s tests -v   # unit, contract and live stdio conformance tests
python mcp/tests/test_mcp_stdio.py                 # 5 servers over real stdio
ruff check .
python scripts/build_release.py --all --signing-key <pem> && python scripts/validate_plugin_bundle.py
python scripts/sign_release.py --verify dist --pubkey <published key>     # see SECURITY.md
```

CI runs the suite on Python 3.10–3.13 against both `mcp` 1.x (patched)
and `mcp` 2.x.

## System requirements

| Component | Requirement |
|:----------|:------------|
| Python | 3.10 through 3.13 (the MCP SDK needs 3.10+; the decoder wheels stop at 3.13) |
| Platforms | Linux, macOS; Windows via the Desktop extension, WSL, or Git for Windows (see Installation) |
| Backend | `qector-decoder-v3==1.0.1` (Rust / PyO3 wheel) |
| MCP SDK | `mcp>=1.30,<3` |
| Validation | `jsonschema>=4.18` |
| Network | none required; the plugin's only network-capable option (PyPI check) is refused in air-gapped mode, and the wheel's native TLS client is disclosed, never called (see Security) |

## Security and privacy

[SECURITY.md](SECURITY.md) (trust boundaries, tool classification, startup
gates, the wheel's native network surface), [THREAT_MODEL.md](THREAT_MODEL.md)
(assets, actors, controls, residual risks), [PRIVACY.md](PRIVACY.md),
[AIRGAP.md](AIRGAP.md). Vulnerability reports: <admin@qector.store>.

## Documentation

| Document | Path |
|:---------|:-----|
| Ten-minute reviewer checklist | [REVIEWER_GUIDE.md](REVIEWER_GUIDE.md) |
| MCP API contract 2.0 | [MCP_API.md](MCP_API.md) |
| Air-gapped deployment | [AIRGAP.md](AIRGAP.md) |
| Threat model | [THREAT_MODEL.md](THREAT_MODEL.md) |
| Anthropic collaboration proposal | [ANTHROPIC_COLLABORATION_PROPOSAL.md](ANTHROPIC_COLLABORATION_PROPOSAL.md) |
| Release notes | [RELEASE_NOTES_v2.0.1.md](RELEASE_NOTES_v2.0.1.md) · [RELEASE_NOTES_v2.0.0.md](RELEASE_NOTES_v2.0.0.md) · [CHANGELOG.md](CHANGELOG.md) |
| Upstream wheel defect report (rotated surface distance) | [docs/UPSTREAM_ISSUE_rotated_surface_distance.md](docs/UPSTREAM_ISSUE_rotated_surface_distance.md) · `scripts/probe_wheel_distance.py` |
| User manual | [docs/User_Manual.md](docs/User_Manual.md) |
| Desktop setup | [CLAUDE_DESKTOP.md](CLAUDE_DESKTOP.md) |
| Validation gates | [RELEASE_VALIDATION.md](RELEASE_VALIDATION.md) |

## License

Proprietary. Copyright © 2026 Guillaume Lessard / iD01t Productions. See
[LICENSE.md](LICENSE.md). The `qector-decoder-v3` backend is free for
personal, academic, educational and non-commercial research; commercial
use requires a licence from [qector.store/pricing](https://qector.store/pricing).

Website <https://www.qector.store> · Licensing, support and security
disclosure <admin@qector.store>
