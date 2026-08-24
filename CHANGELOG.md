# Changelog

## 1.0.6 - 2026-08-23

Claude.ai marketplace compliance and environment-agnostic setup release.

- **Canonical marketplace manifests**: `marketplace.json` now uses the relative
  same-repo plugin source (`"source": "./"`) — the form every official
  marketplace uses — plus documented fields only (`homepage`, `repository`,
  `keywords`, owner `url`). Removed the `userConfig` block from `plugin.json`
  (newest, least-standard field absent from the strict sync schema); interpreter
  pinning still works via the `QECTOR_PYTHON` environment variable.
- **Launchers moved from `bin/` to `scripts/`**: claude.ai-hosted plugins may
  not ship `bin/` executables (they land on PATH without appearing on the admin
  approval surface). Both launchers now live in `scripts/` with the exec bit
  preserved (git mode `100755`, zip attr `0o755`). All references updated:
  `plugin.json`, `.mcp.json`, `hooks/hooks.json`, MCPB manifest (+ win32
  override), builder whitelists, and the bundle validator.
- **`bin/` ban guard**: `validate_plugin_bundle.py` now hard-fails if any
  `bin/` entry appears in the plugin zip, source zip, or Desktop MCPB — the
  directory can never regress into a release.
- **`/qec-setup` environment-agnostic**: the command now detects sandboxed /
  remote / cloud environments (no project checkout) and falls back to native
  Bash diagnostics instead of dead-ending on the missing
  `scripts/qector_system_setup.py`. It never claims the script ran when it
  used the fallback path.

## 1.0.5 - 2026-08-23

Cross-platform launcher release. Every entry point now resolves a Python 3
interpreter through a shipped launcher instead of assuming a bare `python`
exists on PATH, which failed on stock macOS, Debian, and Fedora.

- **`scripts/qector-python` (POSIX sh) and `scripts/qector-python.cmd` (Windows)**
  launchers ship in the plugin archive, the source archive, and the Desktop
  MCPB. Resolution order is `QECTOR_PYTHON` -> `python3` -> `python` (`py -3`
  first on Windows). Candidates are range-checked against the supported
  **Python 3.9-3.13** window, so a machine whose default `python` is 3.14 is
  skipped rather than crashed into at wheel-import time, and exhaustion
  exits 127 with install guidance. Zip entries under `bin/` are stamped
  `0755` so the launcher stays executable after extraction.
- **`userConfig.python_path`** (Claude Code) and **`user_config.python_path`**
  (Desktop MCPB, with a `win32` `platform_overrides` block that selects the
  `.cmd` launcher) let users pin an interpreter; the resolved value reaches
  the launchers through the `QECTOR_PYTHON` environment variable.
- `plugin.json` and the MCPB manifest now point `command` at the launcher;
  `hooks/hooks.json` SessionStart and PostToolUse commands quote and route
  through it as well.
- **Standalone skill zip staleness guard**: `validate_plugin_bundle.py` now
  fails if any `*-skill*.zip` in `dist/` declares a plugin version other than
  the release version. The stale v1.0.2 `qector-qector-core-skill.zip` (which
  advertised the retired `/qec-decode` and `/qec-desktop-connector` commands)
  has been removed from `dist/`; regenerate it from the current
  `skills/qector-core/` if a claude.ai upload is needed again.
- `release_validate.py` resolves inherited `SERVER_VERSION` values
  statically (source scan, no module imports), so the release gate runs
  green on a bare interpreter without the `mcp` SDK installed.
- Author contact unified on `admin@qector.store` in `plugin.json`.
- The Desktop MCPB builder drops `platform_overrides` when
  `--runtime-root` bundles a full interpreter, so the bundled runtime always
  wins on every platform.

## 1.0.4 - 2026-08-23

Production-ready release. Completes the remaining 1.0.3 hardening items
and adds process-local call budgets so an agent cannot loop mutating or
expensive tools without a ceiling.

- **Per-process call budgets** on `threshold_sweep` (8), `decode_single`
  (64), `decode_syndrome` (256), `build_code_from_matrix` (32),
  `hot_path_microbench` (4), `system_setup` (2),
  `configure_claude_desktop` (2), and `workbench_probe` (2). Exhaustion
  returns `RESOURCE_LIMIT`. Override with `QECTOR_MCP_MAX_CALLS_<TOOL>`.
- **Tighter MCP resource defaults**: `QECTOR_MCP_MAX_TRIALS` 10_000,
  `QECTOR_MCP_MAX_SWEEP_POINTS` 64.
- **Admin tools removed from the research schema.** Implementations stay
  importable by `qector-admin`; `tools/list` on `qector-research` is 29
  provisional tools only.
- **Canonical release artifacts** from `scripts/build_release.py`:
  `qector-claude-plugin-source-1.0.4.zip`,
  `qector-claude-plugin-1.0.4.zip`,
  `qector-claude-desktop-1.0.4.mcpb`, plus `SHA256SUMS`, SBOM, and
  provenance. The bundle validator matches those names.
- **CI** runs source, unit, ruff, and artifact gates. The MCP Registry
  publish workflow now uploads the canonical Desktop MCPB.
- **Public claims** aligned: 8 stable / 29 research / 3 admin tools,
  11 commands, 5 agents, 28 skills. Skills, agents, and the user manual
  no longer advertise retired `/qec-decode` or `/qec-desktop-connector`,
  or admin tools on the research server.
- **Plugin archive includes `scripts/`** so SessionStart and PostToolUse
  hooks resolve `qector_session_start.py` and `qector_tool_log.py` after
  marketplace install. Also ships `docs/`, `governance/`, and
  `CLAUDE_DESKTOP.md`.
- **Desktop MCPB layout**: `icon.png` and `README.md` sit at the bundle
  root (matching the manifest). The safe MCPB does not bundle research
  or admin servers; `--profile research` fails closed if the research
  module is absent.
- **Library artifact root** defaults to the plugin `artifacts/` directory,
  not process cwd. `QECTOR_ARTIFACT_DIR` still overrides.
- **Installer `python_path`** must be an existing Python 3 interpreter;
  arbitrary binaries are rejected before they are written into Claude
  Desktop configuration.
- **Deterministic release archives**: zip entries use a fixed timestamp so
  SHA-256 sidecars and `server.json` `fileSha256` stay stable across rebuilds.

## 1.0.3 - 2026-08-22

Production-readiness hardening pass. No new public surface; no behavior
changes that justify a version bump on their own. All changes ship under
the existing 1.0.3 release tag.

- **Split `scripts/test_structure.py` into a source validator and a bundle
  validator.** `scripts/validate_source.py` checks skills, agents, commands,
  hooks, plugin and Desktop manifests, MCP config templates, and tree
  cleanliness. It never requires `dist/` to exist, so a fresh source clone
  validates cleanly. `scripts/validate_plugin_bundle.py` is the companion
  that checks the contents and SHA-256 sidecars of built artifacts in
  `dist/`; it reports informational when `dist/` is absent. The original
  `scripts/test_structure.py` becomes a thin two-phase wrapper so existing
  CI / docs references keep working.
- **Version unification.** Every version-bearing file is now `1.0.3`:
  `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`,
  `.claude-desktop-extension/manifest.json`, `release-manifest.json`
  (including the Desktop MCPB artifact name), and `SERVER_VERSION` in
  `mcp_server_library.py`, `mcp_server_qector_bench.py`,
  `mcp_server_desktop.py`, and `mcp_server_admin.py`.
  `scripts/release_validate.py` now cross-checks all four Python servers
  in addition to the JSON manifests.
- **Hooks portability.** `hooks/hooks.json` no longer hard-codes
  `python3`; it uses `python` to match the rest of the plugin and to
  avoid the native Windows regression the changelog for the previous
  release called out.
- **Evidence layer in the provisional surface.** Three new read-only
  tools live in the research (bench) server, *not* in the 8-tool
  frozen library surface:
  - `get_capability_matrix` — maps coarse-grained QECTOR workflows
    onto the servers that serve them, including the trust zone.
  - `get_evidence_policy` — declares the meaning of every result
    status, the closed list of stable error codes, and the agent
    must / must-not rules.
  - `get_runtime_provenance` — the live runtime block for the
    server process, with opt-in PyPI freshness.
  Library stays at the eight promised tools; the frozen API contract
  is preserved.
- **`hot_path_microbench` now emits a structured `measurement_scope`
  block** (machine / OS / Python / CPU / RAM / backend / decoder_class
  / code_family / noise_model / seed / workload_hash) on every result,
  including the early-exit "no successful decodes" branch.
- **Build-script hygiene.** `scripts/pro_pack.py` and
  `scripts/build_release.py` now refuse to include the
  `scratch_probe_*.py` files at repo root, and `.gitignore` covers
  them so they no longer appear as untracked working-tree noise.
- **Test coverage.** `tests/test_production_readiness.py` exercises the
  contract surface (envelope shape, error code taxonomy, MCP tool
  contract, manifest version consistency, hooks launcher portability,
  `system_setup` profile allowlist, `tool_artifacts_sha256` path
  containment, evidence layer shape) without requiring
  `qector-decoder-v3` to be installed.

## 1.0.3 - 2026-08-21

- **Portability**: `.mcp.json` and `.claude-plugin/plugin.json` now invoke
  `python3` instead of bare `python`. Stock macOS and modern Linux distros
  (Ubuntu 20.04+, Debian, Fedora, Arch) ship `python3` but not `python`, so
  the previous default silently failed to launch `qector-library` /
  `qector-bench` for every Claude Code user on those systems. Windows users
  invoking through native Claude Code (outside WSL) without a `python3`
  alias should either run inside WSL or use the Claude Desktop installer,
  which pins the exact resolved interpreter path automatically and is
  unaffected by this change.
- **Fixed drift risk**: `scripts/configure_claude_desktop.py` was pointing
  installed configs at a stale `dist/qector-claude-plugin-v1.0.2/` snapshot
  on at least one machine instead of the live `mcp/` source tree, meaning
  source edits silently would not take effect until a manual rebuild. The
  script already resolved paths relative to its own location (dynamic, no
  hardcoded machine paths) — confirmed correct and re-verified end-to-end.
- **Docs**: removed a leaked machine-specific example path from the root
  `CLAUDE_DESKTOP.md`; both `CLAUDE_DESKTOP.md` and the main `README.md` now
  lead with the automated, cross-platform `configure_claude_desktop.py`
  installer instead of manual JSON editing, and explicitly warn against
  adding QECTOR as a remote "Custom Connector" (it is a local, offline MCP
  server with no sign-in service — that flow always fails with an OAuth
  registration error).
- Corrected a stale `mcp==1.2.0` figure in `README.md`'s requirements line;
  the pinned, tested version is `mcp==1.26.0` (matches `requirements.txt`).
- `.gitignore`: added the transient `dist/qector-claude-plugin-v*/` extracted
  build directory and local `brand/exports/` output so packaging runs never
  leave stray untracked directories to accidentally `git add`.
- Rebuilt and re-signed release archives (`dist/qector-claude-plugin-v1.0.3.zip`,
  `dist/qector-qector-core-skill.zip`) with fresh SHA-256 sidecars; removed
  the superseded `v1.0.2` archives.
- Bumped `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, and
  `.claude-desktop-extension/manifest.json` to `1.0.3`.

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
