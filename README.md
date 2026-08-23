# QECTOR Claude Plugin

QECTOR is a local, fail closed quantum error correction integration for
**Claude Code** and **Claude Desktop**, built on the published
`qector-decoder-v3==1.0.0` wheel and grounded against the QECTOR Decoder
v3 Reference Manual (DOI `10.5281/zenodo.21941046`). Every correction
returned by an MCP server is verified against `H c = s (mod 2)` before it
leaves the process, and the default operation makes no network request.

> **4 MCP servers · 8 stable / 29 research / 3 admin tools · 11 commands
> · 5 agents · 28 skills · zero egress by default**

## Surfaces

| Surface | Install path | Status |
|:--------|:-------------|:-------|
| Claude Code CLI | marketplace plugin, local stdio | ✅ Windows, macOS, Linux |
| Claude Desktop | `.mcpb` bundle, one click install | ✅ Windows, macOS |
| Web, iOS, Android, Cowork | hosted remote connector (Streamable HTTP + OAuth) | 🗺️ planned 1.1.x |
| Air gapped / restricted enterprise | local stdio, fully offline default | ✅ |

Local stdio plugins cannot reach web or mobile by design; the hosted
connector roadmap item is the path to those surfaces.

## New in v1.0.5

* **Cross platform Python launchers.** `bin/qector-python` (POSIX sh) and
  `bin/qector-python.cmd` (Windows) ship inside every archive and resolve
  `$QECTOR_PYTHON` → `python3` → `python` (`py -3` first on Windows).
  Interpreters outside the supported **Python 3.9 to 3.13** window are
  skipped, so a machine whose default `python` is 3.14 fails fast with
  guidance instead of crashing at wheel import time.
* **Interpreter pinning.** `userConfig.python_path` in the plugin manifest
  and `user_config.python_path` in the Desktop manifest feed the launcher
  through `QECTOR_PYTHON`.
* **MCPB platform overrides.** The Desktop bundle selects the `.cmd`
  launcher on win32 and the sh launcher elsewhere; bundled runtime builds
  (`--runtime-root`) drop the overrides so that interpreter always wins.
* **Staleness guards.** The bundle validator rejects any standalone skill
  zip whose version differs from the release version, and verifies
  launcher presence inside the current MCPB.
* **Dependency free release gate.** `scripts/release_validate.py`
  resolves inherited server versions statically, so it runs green on a
  bare interpreter without the `mcp` SDK installed.

## Quick start

**1. Install the runtime**

```bash
git clone https://github.com/GuillaumeLessard/qector-claude-plugin.git
cd qector-claude-plugin
python -m pip install -r requirements.txt   # Python 3.9 to 3.13
python scripts/qector_runtime_check.py
```

**2. Install as a Claude Code marketplace plugin**

```bash
claude plugin marketplace add GuillaumeLessard/qector-claude-plugin
claude plugin install qector@qector-tools
```

Optionally pin your interpreter when prompted (`userConfig.python_path`),
or leave it empty to let `bin/qector-python` auto resolve.

## MCP servers

| Server | Purpose | Tools | Default |
|:-------|:--------|:------|:--------|
| `qector-library` | Frozen stable decoding surface | **8** | ✅ |
| `qector-research` | Provisional research and evidence tools | **29** | opt in |
| `qector-admin` | Privileged local operations | **3** | opt in + confirm |
| `qector-desktop-mcp` | Claude Desktop safe profile adapter | **8** | ✅ Desktop |

Every stable decode verifies its output before returning: syndrome
decoders check `H c = s (mod 2)`, threshold sweeps ship Wilson 95%
intervals with hashed JSON artifacts, and `build_code_from_matrix`
validates dimensions and code family first. Research and admin servers
are never auto enabled; admin additionally requires
`QECTOR_ADMIN_ENABLED=1` plus `confirm=true` per call.

## Commands, agents, skills

* **Commands (11):** `/qec-setup`, `/qec-facts`, `/qec-theorem`,
  `/qec-reproduce`, `/qec-threshold-sweep`, `/qec-wilson`, `/qec-dem`,
  `/qec-code-inspect`, `/qec-benchmark`, `/qec-sinter`,
  `/qec-validate-mcp`
* **Agents (5):** researcher, developer, validator, sysadmin,
  hardware engineer
* **Skills (28):** core, math foundations, architecture, codes builder,
  BP OSD, two stage CSS, space time, decoders deep dive, DEM pipeline,
  sinter, LER methodology, pymatching compat, batch decoding,
  orchestration, reproducibility, testing strategy, deployment, release
  engineering, licensing, services, educator, developer, researcher,
  hardware engineer, sysadmin, glossary, roadmap, workbench

## Artifacts and integrity

Deterministic builder: fixed DOS timestamps make rebuilds hash stable.

| Artifact | SHA-256 |
|:---------|:--------|
| `dist/qector-claude-plugin-1.0.5.zip` | `623be5a3ca77fa503256fe5edf3df8574d6000e82594d6a24dd5473c5562b51b` |
| `dist/qector-claude-plugin-source-1.0.5.zip` | `cb0b11a3fc53ce69008529b0946dd3b8267e0ec612b661b645a4c64d49e023a9` |
| `dist/qector-claude-desktop-1.0.5.mcpb` | `edb08d37b241253a3c35b95a6df73e48d622b711b56a1b91602b3f66f5e955ab` |

Per file sidecars, combined `SHA256SUMS`, an SPDX 2.3 SBOM, and
`provenance.json` live under `dist/`; `server.json` carries the registry
descriptor whose `fileSha256` matches the Desktop bundle byte for byte.

## System requirements

| Component | Requirement |
|:----------|:------------|
| Python | 3.9 to 3.13, enforced by the shipped launchers |
| OS | Windows, macOS, Linux |
| Backend | `qector-decoder-v3==1.0.0` (Rust / PyO3 wheels) |
| MCP runtime | `mcp==1.26.0` |
| Scientific stack | `numpy>=1.26,<2.3`, `cryptography>=48.0.1,<50` |
| Network | none by default; one opt in PyPI freshness check |
| GPU | none required; no portable speed claims are made |

## Security and privacy

Default install exposes only the 8 stable tools over local stdio.
Research and admin surfaces are explicit opt ins with per process call
budgets. See [SECURITY.md](SECURITY.md) for trust boundaries, per tool
risk classification, scanner notes, and advisory status;
[PRIVACY.md](PRIVACY.md) documents the single opt in PyPI endpoint.
Session hooks record only a tool name and timestamp.

## Documentation

| Document | Path |
|:---------|:-----|
| User Manual | [docs/User_Manual.md](docs/User_Manual.md) |
| MCP API | [MCP_API.md](MCP_API.md) |
| Release notes | [RELEASE_NOTES_v1.0.5.md](RELEASE_NOTES_v1.0.5.md) |
| Changelog | [CHANGELOG.md](CHANGELOG.md) |
| Desktop setup | [CLAUDE_DESKTOP.md](CLAUDE_DESKTOP.md) |
| Validation gates | [RELEASE_VALIDATION.md](RELEASE_VALIDATION.md) |

## Development

```bash
python -m unittest discover -s tests -v     # math + protocol tests
python scripts/validate_source.py           # source structure gate
python scripts/validate_plugin_bundle.py    # built bundle gate
python scripts/release_validate.py          # version + manifest cross check
python scripts/build_release.py --all       # deterministic artifacts
```

CI runs the same gates on every push to main; tagging `v*` additionally
publishes artifacts and updates the MCP Registry entry automatically.

## License

Proprietary, Copyright © 2026 Guillaume Lessard / iD01t Productions. See
[LICENSE.md](LICENSE.md). The `qector-decoder-v3` backend is free for
personal, academic, educational, and non commercial research; commercial
use requires a paid license from
[qector.store/pricing](https://qector.store/pricing).

## Contact

Website <https://www.qector.store> · Licensing and support
<admin@qector.store> · Security disclosure <admin@qector.store> (private)

<p align="center"><strong>QECTOR Claude Plugin v1.0.5</strong><br/>
Built on <code>qector-decoder-v3</code> v1.0.0 (Rust / PyO3 core)</p>

