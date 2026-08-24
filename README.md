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

### Prerequisites

| Requirement | How to check | Expected |
|:------------|:-------------|:---------|
| **Python** 3.9–3.13 | `python --version` and `py -3 --version` (Windows) | `3.11.x` or `3.12.x` recommended; `3.14+` is rejected on purpose |
| **pip** | `python -m pip --version` | any recent |
| **Claude Code** ≥2.0 or **Claude Desktop** ≥0.10.0 | `claude --version` | `2.1.x` / `1.34+` |

> **Python with spaces in path** (e.g. `Anthropic Skills and agents`) is now handled — the Desktop extension in `v1.0.6` uses `python` directly (no `${__dirname}` launcher) and the Code plugin uses `scripts/qector-python`. If you still see `Server disconnected`, set `QECTOR_PYTHON` (see Troubleshooting).

### Option A — Claude Code (marketplace, 30 s)

```bash
# 1. Add the marketplace (once)
claude plugin marketplace add GuillaumeLessard/qector-claude-plugin

# 2. Install the plugin
claude plugin install qector@qector-tools
# When prompted for Python interpreter: leave empty for auto-resolve,
# or paste an absolute path like C:\Program Files\Python311\python.exe

# 3. Verify
claude plugin list                          # → qector@qector-tools 1.0.6 enabled
claude plugin validate . --strict           # → ✔ Validation passed
python scripts/qector_runtime_check.py      # → status: ok, mcp 1.29.0
```

### Option B — Claude Desktop (single click)

**Via UI (recommended):**

1. Download `qector-claude-desktop-1.0.6.mcpb` from the [release page](https://github.com/GuillaumeLessard/qector-claude-plugin/releases/tag/v1.0.6).
2. Claude Desktop → Settings → Extensions → Advanced settings → **Install Extension** → select the `.mcpb` → **Enable**.
3. **Fully quit** Claude Desktop (system tray → Quit) and reopen — the extension needs a full restart to load the 8-tool safe profile.

**Via script (same result, auditable):**

```bash
python scripts/configure_claude_desktop.py --check-only   # preview, no changes
python scripts/configure_claude_desktop.py --confirm      # writes claude_desktop_config.json + installs extension
# Restart Desktop afterwards
```

**Verify Desktop:**

- `C:\Users\<you>\AppData\Roaming\Claude\claude_desktop_config.json` contains `qector-library` (if you used the script) and `extensions-installations.json` contains `ant.dir.gh.guillaumelessard.qector`.
- `C:\Users\<you>\AppData\Local\Claude\logs\mcp.log` shows `QECTOR Server started and connected → initialize → tools/list → result` (no `Server disconnected`).

### Option C — From source (auditable, offline)

```bash
git clone https://github.com/GuillaumeLessard/qector-claude-plugin.git
cd qector-claude-plugin

# Install for every Python you use (Windows has both 3.11 and 3.12 via py launcher)
python -m pip install -r requirements.txt          # → numpy 2.2.6, mcp 1.29.0, qector 1.0.0
py -3 -m pip install -r requirements.txt           # ← do this too if py -3 exists

# Verify
python scripts/qector_runtime_check.py             # → status: ok, failures: []
python scripts/qector_system_setup.py --check-only # → dry_run_pending_approval
python scripts/qector_system_setup.py --confirm    # → ready, theorem_1_faithful: true
```

### Troubleshooting

| Symptom | Cause | Fix |
|:--------|:------|:----|
| `Server disconnected` / `Unable to connect to extension server` | Old `mcp 1.26.0` on one Python, or missing `scripts/` in installed extension, or path with spaces on old builds | `py -3 -m pip show mcp` and `python -m pip show mcp` must both be `≥1.28.1` — run `py -3 -m pip install -r requirements.txt --upgrade` for each. Re-run `python scripts/configure_claude_desktop.py --confirm` (now correctly copies launchers) and **fully restart** Desktop. If still failing, set the extension's **Python interpreter** field to `C:\Program Files\Python311\python.exe` (or `C:\Program Files\Python312\python.exe`). |
| `No Python 3.9-3.13 interpreter found` | `python` not on PATH or only 3.14 available | Install Python 3.11/3.12 from python.org and/or set `QECTOR_PYTHON=C:\Program Files\Python311\python.exe` (environment variable or extension's interpreter field). |
| `This extension may not work until all requirements are met` | Desktop version <0.10.0 or Python missing | Update Desktop (≥0.10.0, current 1.34+ is fine) and ensure `mcp`/`qector` installed for the Python Desktop actually uses (`py -3` on Windows). |
| `qector-decoder-v3 not found` | `pip` installed to wrong Python | Run `python -m pip install -r requirements.txt` **and** `py -3 -m pip install -r requirements.txt` — check both with `* -m pip show qector-decoder-v3`. |

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
| `dist/qector-claude-plugin-1.0.6.zip` | `46ae976105d9813ef615985f30fe23cd76cf2ca11d63ee5de86758e4402903c5` |
| `dist/qector-claude-plugin-source-1.0.6.zip` | `4370c322b9e2fa083f841ee7a15e1468b6f991702db56d4779bd8ddb530def11` |
| `dist/qector-claude-desktop-1.0.6.mcpb` | `fbf9bb9a1254d4867093279a07b715041862f8c9ce71aff1201409b6cccc616c` |

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
| MCP runtime | `mcp>=1.28.1,<2` |
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

