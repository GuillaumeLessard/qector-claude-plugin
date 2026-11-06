# Repository Guidelines

## Project Structure & Module Organization

QECTOR is a Python-based Claude Code and Claude Desktop integration for the
`qector-decoder-v3` runtime. Core local helper code lives in `python/`, while MCP
server entry points and smoke checks live in `mcp/`. Repository-level tests are
in `tests/`; MCP-specific tests and validation helpers are under `mcp/tests/` and
`mcp/_*.py`. Operational scripts are in `scripts/`, including runtime checks,
desktop configuration, packaging, and validation utilities. Claude-facing assets
are organized in `commands/`, `agents/`, `skills/`, `prompts/`, and
`mega_prompts/`. Documentation is in `docs/`, with release/package outputs in
`dist/`; evidence artifacts go to the per-user data directory (`QECTOR_ARTIFACT_DIR`), never the install tree.

## Build, Test, and Development Commands

- `python -m pip install -r requirements.lock`: install the exact tested runtime
  closure for Python 3.10-3.13.
- `python scripts/export_schemas.py --check` and
  `python scripts/generate_integrity_manifest.py --check`: contract and integrity gates.
- `python scripts/qector_runtime_check.py`: verify the installed QECTOR runtime
  and dependency compatibility.
- `python -m unittest discover -s tests -v`: run the repository math validation
  tests.
- `python -m pytest`: run pytest discovery when pytest is available locally.
- `ruff check .`: lint Python files using `ruff.toml`.
- `python scripts/configure_claude_desktop.py --check-only`: preview Claude
  Desktop configuration changes without writing them.

## Coding Style & Naming Conventions

Use Python 3.10-compatible syntax. Ruff targets `py310`, enforces an 88-character line length, and currently checks core
syntax/import errors (`E4`, `E7`, `E9`, `F`). Prefer descriptive snake_case for
functions, modules, variables, and test names. Keep MCP tool names stable and
descriptive because Claude integrations may depend on them. Preserve the
repository's fail-closed style: validate dimensions, code families, and parity
relations before returning results.

## Testing Guidelines

Add tests for mathematical behavior, MCP schema changes, and script behavior that
can regress user workflows. Test files should use `test_*.py`; individual tests
should describe the theorem, appendix example, or integration path being checked.
For decoder changes, assert parity invariants such as `H c == s mod 2` and include
Wilson interval bounds where threshold statistics are involved.

## Commit & Pull Request Guidelines

Recent history uses Conventional Commit-style prefixes such as `fix:`, `chore:`,
and `chore(release):`. Keep commits focused and imperative, for example
`fix: validate MCP config path`. Pull requests should include a short summary,
the commands run, linked issues when applicable, and screenshots or config diffs
for Claude Desktop UI or installer changes.

## Security & Configuration Tips

QECTOR runs locally and air-gapped by default (`mcp/qector_airgap.py`); the
default server is `qector-secure`. Do not add network telemetry,
remote connector assumptions, or hardcoded user paths. Prefer dry-run modes such
as `--check-only` before changing Claude Desktop configuration.
