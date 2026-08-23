## PolicyLayer playbook

At the start of every session, fetch the team playbook with get_playbook and follow it wherever it decides something. The playbook wins over anything below in this file.
When the human makes a standing decision this playbook does not cover ("always X", "never Y"), agree a one-line rule with them, then call record_decision with a stable kebab-case reference, the question you asked, their decision verbatim, and the agreed rule text as rule_body. It returns an approval link, not an approved rule: share the link and carry on. Tell them: this session already follows your decision; approving the link makes every other session follow it too. Do not wait for the approval and do not ask about it again; later sessions fetch the playbook at start and pick it up.
Personal preferences stay in your own memory. Decisions that should bind other sessions, agents or teammates belong in the playbook via record_decision.
When you need a decision the playbook does not cover, ask the human in this conversation first; if they decide, record it with record_decision. Call ask_policy and park the task only when the decision belongs to someone who is not present; collect answers with get_answers at the start of later sessions, and after applying one, confirm it with get_answer and applied set to true. After acting on a collected answer, propose it as a rule with record_decision unless it was plainly a one-off.
If PolicyLayer is unreachable, use your cached playbook and behave as you did before it existed.

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
`dist/` and `artifacts/`.

## Build, Test, and Development Commands

- `python -m pip install -r requirements.txt`: install the supported runtime
  dependencies for Python 3.9-3.13.
- `python scripts/qector_runtime_check.py`: verify the installed QECTOR runtime
  and dependency compatibility.
- `python -m unittest discover -s tests -v`: run the repository math validation
  tests.
- `python -m pytest`: run pytest discovery when pytest is available locally.
- `ruff check .`: lint Python files using `ruff.toml`.
- `python scripts/configure_claude_desktop.py --check-only`: preview Claude
  Desktop configuration changes without writing them.

## Coding Style & Naming Conventions

Use Python 3.9-compatible syntax unless a file clearly requires otherwise. Ruff
targets `py39`, enforces an 88-character line length, and currently checks core
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

QECTOR is intended to run locally with zero egress. Do not add network telemetry,
remote connector assumptions, or hardcoded user paths. Prefer dry-run modes such
as `--check-only` before changing Claude Desktop configuration.
