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

---

## Why v1.0.5

Version 1.0.4 assumed the operating system would hand it a usable
interpreter, and the modern world no longer does: macOS, Debian, Ubuntu,
and Fedora ship `python3` without bare `python`, while Windows adds its
own resolver quirks. Version 1.0.5 retires that assumption entirely.

* **A universal launcher ships inside every artifact.** The plugin
  archive, the source distribution, and the Desktop bundle all carry
  `scripts/qector-python` (POSIX sh) and `scripts/qector-python.cmd` (Windows).
* **Resolution is governed, not guessed.** An administrator pinned
  interpreter wins first, then `python3`, then `python`, with the Windows
  py launcher tried ahead of them all.
* **The supported window is enforced, not documented.** Only Python 3.9
  through 3.13 executes, matching the published native wheel matrix; an
  out of range machine receives precise remediation guidance instead of
  a deep import crash.
* **Pinning is first class on both surfaces.** Claude Code prompts via
  user configuration and Claude Desktop via bundle configuration; your
  choice reaches the runtime as `QECTOR_PYTHON` and always supersedes
  discovery.
* **Windows packaging is handled natively.** Platform overrides select
  the command shim inside the Desktop bundle, while bundled runtime
  builds take full control of interpreter selection.

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

Download `qector-claude-desktop-1.0.5.mcpb` from the release page, open
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
| `dist/qector-claude-plugin-1.0.5.zip` | `e7bf953eca77fa503256fe5edf3df8574d6000e82594d6a24dd5473c5562b51b` |
| `dist/qector-claude-plugin-source-1.0.5.zip` | `29db3522fc53ce69008529b0946dd3b8267e0ec612b661b645a4c64d49e023a9` |
| `dist/qector-claude-desktop-1.0.5.mcpb` | `dc529600bae2f4ab1f13921737f20ded89fb41e5ce99dcabce5c2bc8ae0ed4c6` |

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
| v1.0.5 release announcement | [RELEASE_ANNOUNCEMENT_v1.0.5.md](RELEASE_ANNOUNCEMENT_v1.0.5.md) |
| Release notes | [RELEASE_NOTES_v1.0.5.md](RELEASE_NOTES_v1.0.5.md) |
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
<strong>QECTOR Claude Plugin v1.0.5</strong><br/>
Built on <code>qector-decoder-v3</code> v1.0.0 · Rust / PyO3 core<br/>
Every correction verified against <code>H c = s (mod 2)</code>
</p>

