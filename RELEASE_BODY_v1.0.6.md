# QECTOR Claude Plugin v1.0.6

**Claude.ai marketplace compliance and environment-agnostic setup release.**

## What changed

### Claude.ai marketplace compliance

- **Canonical marketplace manifests.** `marketplace.json` now declares the plugin with the relative same-repo source (`"source": "./"`) — the form every official marketplace uses — plus documented fields only (`homepage`, `repository`, `keywords`, owner `url`). Removed the `userConfig` block from `plugin.json`; interpreter pinning still works via the `QECTOR_PYTHON` environment variable.

- **Launchers moved from `bin/` to `scripts/`.** claude.ai-hosted plugins may not ship `bin/` executables (they land on PATH without appearing on the admin approval surface). Both launchers now live in `scripts/` with the exec bit preserved (git mode `100755`, zip attr `0o755`). All references updated: `plugin.json`, `.mcp.json`, `hooks/hooks.json`, MCPB manifest (+ win32 override), builder whitelists, and the bundle validator.

- **`bin/` ban guard.** `validate_plugin_bundle.py` now hard-fails if any `bin/` entry appears in the plugin zip, source zip, or Desktop MCPB.

### Environment-agnostic setup

- **`/qec-setup` now works everywhere.** The command detects sandboxed / remote / cloud environments (no project checkout) and falls back to native Bash diagnostics instead of dead-ending on the missing `scripts/qector_system_setup.py`. It never claims the script ran when it used the fallback path.

## Artifact hashes

| Artifact | SHA-256 |
|:---------|:--------|
| `qector-claude-desktop-1.0.6.mcpb` | `5b6b4c247ef6159dc92441023fd08a0dc800894a220ba8a61b4143bde92190ff` |
| `qector-claude-plugin-1.0.6.zip` | `e1660a45e87e62d5b74f561273ff7cac2a5367a70b8418f1f9c80ea69591de7f` |
| `qector-claude-plugin-source-1.0.6.zip` | `e0e04d94546799acda0d8f3258bc8911b8125c4bf2b78bb80c04d3e49588dc59` |

## Verification

- `validate_source.py`: 832/832 passed
- `validate_plugin_bundle.py`: ALL CLEAR (incl. new `bin/` ban guard)
- `release_validate.py`: 15/15 passed
- Unit suite: 74/74 passed (+48 subtests)
- `claude plugin validate . --strict`: passed
- Fresh `claude plugin marketplace add` + `install qector@qector-tools`: exit 0

## Upgrade

**Claude Code:** `/plugin marketplace update qector-tools` then `/plugin install qector@qector-tools`.

**Claude Desktop:** remove the old extension, install `qector-claude-desktop-1.0.6.mcpb` from the release page, restart.

---

**Full Changelog**: https://github.com/GuillaumeLessard/qector-claude-plugin/compare/v1.0.5...v1.0.6