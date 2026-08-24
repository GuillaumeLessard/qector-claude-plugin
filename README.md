# QECTOR Claude Plugin

**Verified quantum error correction for Claude. Local, deterministic, and
mathematically guaranteed on every machine you work on.**

QECTOR integrates the published `qector-decoder-v3==1.0.0` engine with
Claude Code and Claude Desktop, turning both into a production grade QEC
engineering environment. Every correction returned by an MCP server is
verified against the parity relation `H c = s (mod 2)` before it leaves
the process, every claim carries a machine checkable provenance class,
and the default configuration performs no network request of any kind.

> **4 MCP servers · 8 stable / 29 research / 3 admin tools · 11 commands
> · 5 agents · 28 skills · zero egress by default**

> **Latest release — [v1.0.6](RELEASE_NOTES_v1.0.6.md)** · Claude.ai
> marketplace compliance (launchers to `scripts/`, canonical manifests),
> environment-agnostic `/qec-setup`, deterministic artifacts. See the
> [release announcement](RELEASE_BODY_v1.0.6.md).

---

## Why v1.0.6

Version 1.0.6 completes the portability and compliance story that 1.0.5
started, then layers on marketplace correctness and universal setup. Two
problems drove it: modern operating systems no longer hand you Python on a
predictable command name (macOS, Debian, Ubuntu, and Fedora ship `python3`
without bare `python`, while Windows adds its own resolver quirks), and the
claude.ai marketplace approval pipeline rejects plugins that ship
executables in `bin/`. This release retires both failure classes, permanently.

**1. A universal, compliant launcher ships inside every artifact.**

* The plugin archive, the source distribution, and the Desktop bundle all
  carry `scripts/qector-python` (POSIX sh) and `scripts/qector-python.cmd`
  (Windows). They live in `scripts/`, not `bin/`: claude.ai-hosted plugins
  may not ship `bin/` executables because they land on PATH without ever
  appearing on the admin approval surface. A validator now hard-fails any
  build that reintroduces `bin/`.
* Resolution is governed, not guessed. An administrator pinned interpreter
  wins first, then `python3`, then `python`, with the Windows `py` launcher
  tried ahead of them all.
* The supported window is enforced, not documented. Only Python 3.9
  through 3.13 executes, matching the published native wheel matrix; an
  out of range machine receives precise remediation guidance instead of
  a deep import crash.
* Pinning is first class on both surfaces. Set `QECTOR_PYTHON` to an
  absolute interpreter path and every launcher honors it above discovery.

**2. The marketplace surface is canonical.**

Both `plugin.json` and `marketplace.json` use only documented fields and a
relative same-repo plugin source — the form every official marketplace uses
and the only form every sync path can resolve. The Desktop MCPB carries a
`win32` platform override so Windows always selects the `.cmd` launcher.

**3. Setup works in every environment.**

`/qec-setup` detects sandboxed and remote environments (claude.ai code
execution, Cowork, containers without a project checkout) and falls back to
native diagnostics instead of dead ending on a missing local script — and it
reports honestly which path it used.

## Platform support

| Surface | Install path | Status |
|:--------|:-------------|:-------|
| Claude Code CLI | marketplace plugin over local stdio | ✅ Windows, macOS, Linux |
| Claude Desktop | `.mcpb` bundle with single click install | ✅ Windows, macOS |
| Web, iOS, Android, Cowork | hosted remote connector (Streamable HTTP with OAuth) | 🗺️ roadmap 1.1.x |
| Air gapped and restricted estates | local stdio, fully offline default | ✅ |

Local stdio cannot reach web or mobile by architecture; the hosted
connector is the engineered path to those surfaces and lands in 1.1.x.

## Installation

**Claude Code, from the marketplace**

```bash
claude plugin marketplace add GuillaumeLessard/qector-claude-plugin
claude plugin install qector@qector-tools
```

Optionally pin your interpreter when prompted, or leave it empty and let
the shipped launcher resolve one.

**Claude Desktop, single click**

Download `qector-claude-desktop-1.0.6.mcpb` from the release page, open
Settings → Extensions → Advanced settings → Install Extension, choose the
bundle, and restart. Prefer scripted control?

```bash
python scripts/configure_claude_desktop.py --check-only   # preview
python scripts/configure_claude_desktop.py --confirm      # apply
```

**From source**

```bash
git clone https://github.com/GuillaumeLessard/qector-claude-plugin.git
cd qector-claude-plugin
python -m pip install -r requirements.txt   # Python 3.9 to 3.13
python scripts/qector_runtime_check.py      # verify the runtime
```

## The QECTOR surface

| MCP server | Purpose | Tools | Default |
|:-----------|:--------|:------|:--------|
| `qector-library` | Frozen stable decoding surface, every result verified | **8** | ✅ enabled |
| `qector-research` | Provisional research and evidence tooling | **29** | explicit opt in |
| `qector-admin` | Privileged local operations with double confirmation | **3** | explicit opt in |
| `qector-desktop-mcp` | Claude Desktop safe profile adapter | **8** | ✅ on Desktop |

Alongside the servers: **11 slash commands** for setup, facts, theorems,
reproduction, threshold sweeps, Wilson intervals, detector error models,
code inspection, benchmarking, sinter templates, and validation;
**5 specialized agents** (researcher, developer, validator, sysadmin,
hardware engineer); and **28 skills** spanning math foundations,
architecture, BP OSD, two stage CSS, space time codes, decoders deep
dive, DEM pipelines, LER methodology, pymatching compatibility, batch
decoding, reproducibility, testing strategy, deployment, release
engineering, licensing, education, and operations.

## Artifacts and integrity

The builder is deterministic: fixed timestamps make every rebuild bit
identical, so the hashes below are stable forever.

| Artifact | SHA-256 |
|:---------|:--------|
| `dist/qector-claude-plugin-1.0.6.zip` | `e1660a45e87e62d5b74f561273ff7cac2a5367a70b8418f1f9c80ea69591de7f` |
| `dist/qector-claude-plugin-source-1.0.6.zip` | `e0e04d94546799acda0d8f3258bc8911b8125c4bf2b78bb80c04d3e49588dc59` |
| `dist/qector-claude-desktop-1.0.6.mcpb` | `5b6b4c247ef6159dc92441023fd08a0dc800894a220ba8a61b4143bde92190ff` |

Per artifact sidecars, a combined `SHA256SUMS`, an SPDX 2.3 SBOM, and
provenance records binding each file to its release commit and runtime
pins live under `dist/`. The MCP Registry descriptor in `server.json`
matches the Desktop bundle byte for byte.

## System requirements

| Component | Requirement |
|:----------|:------------|
| Python | 3.9 through 3.13, enforced by the shipped launchers |
| Platforms | Windows, macOS, Linux |
| Backend engine | `qector-decoder-v3==1.0.0`, native Rust / PyO3 wheels |
| MCP runtime | `mcp==1.26.0` |
| Scientific stack | `numpy>=1.26,<2.3`, `cryptography>=48.0.1,<50` |
| Network | none by default; one explicit PyPI freshness check exists |
| GPU | optional at most; no portable performance claims are published |

## Security and privacy

The default installation exposes exactly eight stable tools over local
stdio. Research and administrative servers require deliberate enabling,
privileged operations demand per call confirmation, and every process
enforces its own call budgets so a runaway agent hits a ceiling instead
of your machine. Session hooks persist nothing beyond a tool name and a
timestamp. Full trust boundaries, risk classifications, scanner guidance,
and advisory posture are documented in [SECURITY.md](SECURITY.md), with
the network stance in [PRIVACY.md](PRIVACY.md).

## Documentation

| Document | Path |
|:---------|:-----|
| User manual | [docs/User_Manual.md](docs/User_Manual.md) |
| MCP API reference | [MCP_API.md](MCP_API.md) |
| v1.0.6 release announcement | [RELEASE_BODY_v1.0.6.md](RELEASE_BODY_v1.0.6.md) |
| Release notes | [RELEASE_NOTES_v1.0.6.md](RELEASE_NOTES_v1.0.6.md) |
| Changelog | [CHANGELOG.md](CHANGELOG.md) |
| Desktop setup | [CLAUDE_DESKTOP.md](CLAUDE_DESKTOP.md) |
| Validation gates | [RELEASE_VALIDATION.md](RELEASE_VALIDATION.md) |

## Development

```bash
python -m unittest discover -s tests -v     # mathematical + protocol suite
python scripts/validate_source.py           # source structure gate
python scripts/validate_plugin_bundle.py    # built bundle gate
python scripts/release_validate.py          # metadata cross check, zero deps
python scripts/build_release.py --all       # deterministic artifacts
```

CI enforces the same gates on every push to main. Tagging with `v*`
additionally builds all artifacts, publishes the GitHub release, and
updates the MCP Registry entry automatically.

## License

Proprietary. Copyright © 2026 Guillaume Lessard / iD01t Productions. See
[LICENSE.md](LICENSE.md). The `qector-decoder-v3` backend is free for
personal, academic, educational, and non commercial research; commercial
use requires a license from
[qector.store/pricing](https://qector.store/pricing).

## Contact

Website <https://www.qector.store> · Licensing <admin@qector.store> ·
Support <admin@qector.store> · Security disclosure
<admin@qector.store> (private)

<p align="center">
<strong>QECTOR Claude Plugin v1.0.6</strong><br/>
Built on <code>qector-decoder-v3</code> v1.0.0 · Rust / PyO3 core<br/>
Every correction verified against <code>H c = s (mod 2)</code>
</p>

