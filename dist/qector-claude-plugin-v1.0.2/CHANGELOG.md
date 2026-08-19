# Changelog

## 1.0.2 - 2026-08-19

- Added guided first-time system setup tool (`system_setup`, 28th tool in `mcp_server_qector_bench.py` and CLI `scripts/qector_system_setup.py`) with explicit user approbation safety gate (`confirm=False` dry-run audit, `confirm=True` execution).
- Added `reproduction_command_lookup` (27th tool in `mcp_server_qector_bench.py`) implementing Reference Manual Appendix D (D.1 through D.6) reproduction workflows.
- Expanded reproducible slash command suite from 3 to 12 commands: `/qec-setup`, `/qec-facts`, `/qec-theorem`, `/qec-reproduce`, `/qec-decode`, `/qec-threshold-sweep`, `/qec-wilson`, `/qec-dem`, `/qec-code-inspect`, `/qec-benchmark`, `/qec-sinter`, and `/qec-validate-mcp`.
- Completed full mathematical grounding against all 16 Theorems, 27 Chapters, and 5 Appendices (A: Notation/Symbols, B: Glossary, C: Evidence Index, D: Reproduction Commands, E: Worked Numerical Examples) from `QectorDecoder_v3_Reference_Manual_v1.0.0.pdf` (DOI: 10.5281/zenodo.21941046).
- Standardized MCP JSON configuration files (`mcp/mcp_config.json`, `mcp/claude_desktop_config.json`) and fixed python path resolution in unit test suites.
- Bumped plugin and marketplace release version to `1.0.2`.

## 1.0.1 - 2026-08-19

- Fixed `plugin.json` (root and `.claude-plugin/`) to register the `qector-bench`
  MCP server alongside `qector-library`, matching `.mcp.json` and the 20-tool
  bench surface documented in `skills/qector-core/SKILL.md`. Previously the
  bench server was never registered when the plugin was installed via
  `claude --plugin-dir` or the marketplace flow.
- Fixed `hooks/hooks.json` `PostToolUse` matcher regex, which referenced a
  non-existent `qector-workbench` server name instead of `qector-bench`, so
  tool-use logging silently never fired for any of the 20 bench tools.
- Fixed `README.md` and `mcp/VALIDATION_REPORT.md`, which referenced a `bin/`
  directory that does not exist; all runtime/validation/packaging scripts
  (`qector_runtime_check.py`, `run_manual_math_validation.py`,
  `run_threshold_sweep.py`, `pro_pack.py`, `probe_workbench_mcp.py`) live in
  `scripts/`. Every documented command using `bin/` would have failed as
  written. `scripts/pro_pack.py`'s own docstring had the same stale `bin/`
  path and has been corrected.
- Deprecated the duplicate root-level `plugin.json` and `marketplace.json`
  (renamed to `plugin.json.deprecated` / `marketplace.json.deprecated`).
  `.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json` are now
  the single source of truth: `scripts/pro_pack.py` already read the release
  version from `.claude-plugin/plugin.json`, and the Claude Code plugin spec
  expects manifests inside `.claude-plugin/`, so the root copies were the
  redundant ones. `scripts/pro_pack.py` now excludes `*.deprecated` files
  from packaged archives. The two `.deprecated` files are safe to delete
  outright (`git rm plugin.json.deprecated marketplace.json.deprecated`);
  they were kept as a paper trail only because file deletion wasn't available
  in this pass.
- **Critical**: `.claude/settings.local.json` shipped with
  `"disabledMcpjsonServers": ["qector-library"]`, actively disabling the
  plugin's primary 8-tool library MCP server, and the file was not in
  `.gitignore`, so it would have been tracked and shipped as-is — anyone
  installing the plugin fresh would have had the core server disabled by
  default. Cleared the file to `{}` and added
  `.claude/settings.local.json` to `.gitignore` (this file is meant to be a
  personal, untracked override per Claude Code convention, analogous to
  `.env.local`). If this file is already committed to git history, run
  `git rm --cached .claude/settings.local.json` once to stop tracking it.
- Fixed five more `bin/` -> `scripts/` occurrences of the same stale-path bug
  found in `agents/qec-validator.md`, `prompts/qector_researcher_prompt.md`,
  `prompts/qector_sysadmin_prompt.md`, `mega_prompts/threshold_discovery.md`,
  `presentations/Developer_Onboarding.md` (x2), and
  `docs/MATH_VALIDATION.md`. Every `.md` file in the repository (skills,
  agents, commands, prompts, mega_prompts, cheat sheets, presentations,
  governance, docs) has now been read and checked for this pattern; none
  remain.
- Added `scripts/rebuild_and_validate.bat`: a one-command Windows runner that
  clears stale `dist/` archives, runs the runtime check, unit tests, ruff
  lint/format, `scripts/pro_pack.py --all`, and `claude plugin validate
  --strict` in order, stopping at the first failure. This performs the last
  local validation gate that cannot be executed from this session (no shell
  access to the user's machine).

## 1.0.0 - 2026-08-15

- Pinned the production library path to the live PyPI wheel `qector-decoder-v3==1.0.0`.
- Pinned the tested MCP runtime to `mcp==1.26.0` and added a low-level stdio adapter.
- Corrected parity-check matrix orientation to `(n_checks, n_qubits)`.
- Added strict binary input validation, graphlike eligibility checks, resource limits,
  fail-closed syndrome verification, and MCP `isError` responses without trace leakage.
- Added hashed raw JSON LER artifacts with Wilson 95% intervals and required metadata.
- Added `qector_math_ground_truth.py` and executable reference-manual proof obligations.
- Made the library server the only default MCP configuration; Workbench is opt-in.
- Aligned public skills, agents, commands, prompts, and documentation with the
  pinned runtime and device-local validation model.
- Removed internal authoring material, machine snapshots, business proposals,
  and proprietary reference documents from the public package.

Performance, GPU, threshold, and universal optimality claims remain workload-scoped;
this plugin does not publish portable speed claims.
