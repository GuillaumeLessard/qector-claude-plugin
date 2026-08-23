# QECTOR Claude Plugin v1.0.5

Cross-platform launcher release. Every entry point resolves a real Python 3
interpreter through shipped launchers, so stock macOS, Debian, and Fedora —
which ship no bare `python` — work without manual PATH surgery.

## What ships

**4 MCP servers · 8 stable / 29 research / 3 admin tools · 11 commands
· 5 agents · 28 skills · zero-egress default** (surface counts unchanged
from 1.0.4)

## Launcher resolution

| Entry point | Before | Now |
|:------------|:-------|:----|
| Claude Code plugin (`plugin.json`, `.mcp.json`) | bare `python` | `${CLAUDE_PLUGIN_ROOT}/scripts/qector-python` |
| SessionStart / PostToolUse hooks | bare `python` | quoted launcher path |
| Desktop MCPB (macOS/Linux) | bare `python` | `${__dirname}/scripts/qector-python` |
| Desktop MCPB (Windows) | bare `python` | `${__dirname}\scripts\qector-python.cmd` via `platform_overrides` |

Resolution order: `QECTOR_PYTHON` -> `python3` -> `python` (`py -3` first on
Windows). Non-Python-3 candidates are skipped; exhaustion exits 127 with
install guidance. Users can pin an interpreter through
`userConfig.python_path` (Claude Code) or `user_config.python_path`
(Desktop); both reach the launchers as `QECTOR_PYTHON`.

## Packaging integrity

- Zip entries under `bin/` carry `0755`; all other entries `0644`; the fixed
  DOS timestamp keeps rebuilds hash-stable.
- The stale v1.0.2 standalone `qector-qector-core-skill.zip` is gone from
  `dist/`, and `validate_plugin_bundle.py` now fails any `*-skill*.zip`
  whose declared version differs from the release version.
- Bundled-runtime MCPB builds (`--runtime-root`) drop `platform_overrides`
  so the bundled interpreter always wins.

## Canonical artifacts (this release)

| Artifact | SHA-256 |
|:---------|:--------|
| `qector-claude-plugin-1.0.5.zip` | `e7bf953eca77fa503256fe5edf3df8574d6000e82594d6a24dd5473c5562b51b` |
| `qector-claude-plugin-source-1.0.5.zip` | `29db3522fc53ce69008529b0946dd3b8267e0ec612b661b645a4c64d49e023a9` |
| `qector-claude-desktop-1.0.5.mcpb` | `dc529600bae2f4ab1f13921737f20ded89fb41e5ce99dcabce5c2bc8ae0ed4c6` |

Per-file `.sha256` sidecars, combined `SHA256SUMS`, SPDX-2.3 SBOM, and
`provenance.json` are regenerated alongside; `server.json` is patched to the
new MCPB digest automatically by `scripts/build_release.py --all`.

## Install

```bash
claude plugin marketplace add GuillaumeLessard/qector-claude-plugin
claude plugin install qector@qector-tools
```

Desktop: install `dist/qector-claude-desktop-1.0.5.mcpb` via
Settings -> Extensions -> Install Extension, then restart Claude Desktop.
Optionally pin the interpreter when prompted (or leave unset to auto-resolve).

## License

Proprietary — Copyright © 2026 Guillaume Lessard / iD01t Productions.
The `qector-decoder-v3` backend remains free for personal, academic,
educational, and non-commercial research; commercial use requires a paid
license (qector.store/pricing).
