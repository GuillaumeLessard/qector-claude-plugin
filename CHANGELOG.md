# Changelog

## 2.0.1 - 2026-11-05

Re-pin to `qector-decoder-v3==1.0.1`, which fixes upstream the wheel defects
2.0.0 detected and worked around. No tool was added, removed or renamed; the
only schema change is one new boolean in `airgap_status`.

### Changed

- **Licensing skill matches 1.0.1 entitlements.** `qector-licensing` now
  states that Pro tokens (trial, Pro, Pro Perpetual, Team, Pilot) unlock the
  GPU batch decoders and Enterprise tokens (Lab, Enterprise) raise the
  distance tier to 63; distance caps are advisory unless `QECTOR_ENFORCE=1`.
- **Lock pinned to the published PyPI 1.0.1 wheels.** `requirements.lock`
  carries the SHA-256 digests of all 18 wheels as published by the release
  workflow (Trusted Publishing, with provenance), and the bundled
  wheelhouse uses the PyPI cp313 manylinux wheel byte for byte.
- **Backend pinned to `qector-decoder-v3==1.0.1`** (`requirements.txt`,
  `requirements.lock`, `release-manifest.json`, runtime checks, the library
  server's reviewed window `[1.0.1, 1.1.0)`). The lock pins the exact SHA-256
  of the six Linux x86_64 wheels (CPython 3.9-3.14) from the 1.0.1 release
  build; re-run `scripts/update_lock.py` once all 18 wheels are on PyPI to add
  the Windows and macOS digests.
- **Code families now verify upstream.** With 1.0.1 the live distance probe
  reports `ok` at the labelled distance for `rotated_surface`,
  `unrotated_surface`, `heavy_hex`, `toric`, `repetition`, `ring` and
  `color_code` (1.0.0: rotated distance 2, unrotated and colour k = 0,
  heavy_hex 2d - 1). `rotated_surface_corrected` stays for request
  compatibility. Descriptions, skills and `docs/UPSTREAM_ISSUE_*` updated;
  the issue is marked fixed.
- **`color_code` is no longer offered to `decode_single`.** In 1.0.1 it is the
  real 6.6.6 code, which is not graphlike; `list_code_families` now sets
  `single_decode: false` for any non-graphlike family and says why, instead of
  advertising a decode the matching decoders refuse.
- **Sinter skill** reflects the 1.0.1 factory (five presets, distinct entry
  points).

### Added

- **Native-core offline flag.** In air-gapped mode the plugin sets
  `QECTOR_OFFLINE=1` before any decoder call; qector-decoder-v3 1.0.1 then
  refuses every billing call inside its Rust core before a socket is opened,
  the layer the Python socket guard cannot reach. Reported as
  `airgap_status.guards.wheel_offline_flag`.
- **Test fixtures for defective families.** The weak / degenerate /
  contradicted verdict paths were covered by the broken 1.0.0 families; they
  are now covered by explicit test-only fixtures (duplicate column, unchecked
  qubit, single check), so the coverage survives the upstream fix.

## 2.0.0 - 2026-11-02

Major release. Full audit of the 1.0.6 archives, every gap found closed, no
placeholders. Breaking changes are marked **[breaking]**.

### Audit findings that drove the release

- The four 1.0.6 artifacts were not one release: the source zip and the
  Desktop MCPB pinned `mcp>=1.28.1,<2` while the repository and plugin zips
  pinned `mcp==1.26.0` (CVE-2026-52869/52870/59950); README and
  `server.json` published hashes that matched none of the delivered files.
- All four servers failed to import on `mcp` 2.x (`Tool.inputSchema` →
  `input_schema`), eight weeks after 2.0.0 shipped.
- `sinter_task_template` raised `TypeError` on every call;
  `dem_collapse_parallel` combined only the first two of n parallel
  mechanisms; `decode_faithfulness_check.residual_weight` was a constant;
  `license_active_check` hard-coded a tier table while claiming "no
  hard-coded tier"; `importlib.metadata` was used without being imported.
- "Zero egress" was documentation, not enforcement: `check_pypi=true`
  opened a connection from the default server, `NETWORK_DISABLED` was never
  raised, and the decoder wheel's native core (Rust `rustls`/`ureq`,
  `https://api.stripe.com/v1/billing/meter_events`, REST/gRPC/metrics
  servers) was never disclosed.
- Python 3.9 was advertised but impossible (`mcp` requires 3.10+); the MCPB
  `python` server type requires bundled dependencies, which the bundle did
  not carry.
- The wheel's `color_code` family builds a one-check, six-qubit, no-logical
  code at d=3 and leaves one qubit unchecked at d=5; `heavy_hex` leaves one
  qubit unchecked at every size. Both were exposed as ordinary decodable
  families.
- Artifacts were written inside the plugin install directory; `SECURITY.md`
  carried a duplicated section; the Desktop manifest claimed
  `manifest_version` 0.3 fields correctly but shipped different content than
  the repository copy.

### Added

- **`qector-secure`** (`mcp/mcp_server_secure.py`): single hardened entry
  point for Claude Code and Claude Desktop. Air-gap guard installed before
  the first MCP frame, JSON Schema 2020-12 validation of every request and
  every response, `INTEGRITY.json` verification at startup (strict by
  default), optional hash-chained audit log, request-size cap, per-minute
  rate limit, deterministic sorted `tools/list`, stdio only. Profiles `safe`
  (12 tools) and `research` (41 tools).
- Control-plane tools `airgap_status`, `integrity_check`, `schema_catalog`,
  `audit_log_status`.
- `mcp/qector_mcp_compat.py`: one code base for `mcp>=1.30,<2` and
  `mcp>=2,<3`; CI runs both.
- `mcp/qector_schemas.py` + `schemas/` (91 files): typed result schema for
  all 44 tools, envelope schema, audit-record schema, digests index;
  `scripts/export_schemas.py --check` prevents drift.
- `mcp/qector_airgap.py`: loopback-only socket subclass, guarded
  `getaddrinfo` / `create_connection` / `urlopen`, subprocess guard,
  scrubbing of `STRIPE_*`, `QECTOR_STRIPE_CUSTOMER_ID`,
  `QECTOR_LICENSE_PRIVATE_KEY_B64`; honest status including the wheel's
  native surface.
- `mcp/qector_audit.py`: append-only JSONL with SHA-256 chain; arguments
  stored only as digests; `verify_chain` names the first invalid record.
- `mcp/qector_integrity.py` + `scripts/generate_integrity_manifest.py`.
- `mcp/qector_signing.py` + `scripts/sign_release.py`: Ed25519 signatures over
  every archive's `INTEGRITY.json` and over `dist/SHA256SUMS`; pinned-key
  verification in `qector-secure` (`QECTOR_INTEGRITY_PUBKEY`); Sigstore
  keyless signature of `SHA256SUMS` in the publish workflow; `RELEASE_COMMIT`
  in every archive; hashed `requirements.lock`; SBOM package checksums.
- Offline laboratory path: `requirements.lock` (exact closure),
  `scripts/build_wheelhouse.py` (cross-platform download with
  `SHA256SUMS`), `scripts/install_offline.sh` / `.ps1`,
  `scripts/update_lock.py`, `system_setup(offline_wheelhouse=...)`.
- Family health probe (`ok` / `unscored` / `weak` / `degenerate`) in
  `list_code_families` and `code_family_info`; degenerate constructions
  are refused, weak ones decode with a warning carried in the envelope.
- `THREAT_MODEL.md`, `AIRGAP.md`, `ANTHROPIC_COLLABORATION_PROPOSAL.md`,
  rewritten `SECURITY.md`, `MCP_API.md`, `README.md`.
- 57 new tests (`tests/test_secure_server.py`, `tests/test_airgap.py`,
  `tests/test_contract_v2.py`, secure-server stdio conformance).

### Changed

- **[breaking]** Default MCP server is `qector-secure` (12 tools) instead of
  `qector-library` (8). The Desktop bundle runs the secure server;
  `mcp_server_desktop.py` is a compatibility shim.
- **[breaking]** Air-gapped mode is the default. `check_pypi=true` now
  returns `pypi_freshness.status: "disabled"` unless `QECTOR_AIR_GAPPED=0`.
- **[breaking]** Envelope contract 2.0: new required keys
  `contract_version` and `tool`; `provenance.mcp_sdk`; optional
  `runtime.elapsed_ms` and `audit`; new error codes `UNKNOWN_TOOL`,
  `CONTRACT_VIOLATION`, `INTEGRITY_FAILED`; `scope.network` may be
  `disabled_air_gapped`.
- **[breaking]** Supported Python is 3.10–3.13; launchers reject 3.9.
- **[breaking]** `requirements.txt` pins `mcp>=1.30,<3` and adds
  `jsonschema>=4.18,<5`.
- Default artifact root is the per-user data directory, not the install
  directory.
- `list_decoders` reports `graphlike_only`; `decode_faithfulness_check`
  reports `computed_syndrome` and `syndrome_mismatch_indices`;
  `dem_collapse_parallel` reports `combination_rule`;
  `license_active_check` reports `source: live_wheel` and no tier table;
  `hot_path_microbench` accepts only check-list-constructor decoders and
  warns on faithfulness violations instead of hiding them.
- `scripts/build_release.py` assembles archives in memory, writes a
  per-archive `INTEGRITY.json`, generates an SPDX SBOM over the full
  locked closure, and can vendor the runtime into `server/lib`
  (`--bundle-lib`). The source archive now ships `tests/` and `.github/`.
- MCP Registry descriptor and workflows updated for 2.0.0; CI matrix
  Python 3.10–3.13 × `mcp` 1.x / 2.x.
- Final adversarial pass (pre-release hardening, all with regression
  tests): `INTEGRITY.json` entries are validated before any file is opened
  (relative, traversal-free runtime paths with hex digests only; a
  non-object `files` member is a manifest mismatch), so an unsigned
  manifest can no longer make the verifier hash files outside the install
  root; a malformed `QECTOR_INTEGRITY_PUBKEY` is reported as a
  configuration error instead of a traceback; a tool result carrying
  NaN/Infinity is returned as `CONTRACT_VIOLATION` rather than escaping
  the envelope as a serialisation exception; an audit-log write failure
  fails closed (`IO_ERROR`, result withheld) instead of propagating out of
  the dispatcher; `integrity_check` reports the manifest path relative to
  the install root (no home directory in envelopes); CI installs the
  hashed lock in `--require-hashes` mode with lint tooling on a separate
  line and keeps the 1.x leg on the locked `mcp==1.30.0`; test processes
  and sockets are closed deterministically (suite runs clean under
  `-W error::ResourceWarning`).

- Fourth review pass (tool logic and Claude-facing content, all with
  regression tests):
  - **Effective distance is checked, never trusted.** The wheel's
    `rotated_surface_code(d)` has duplicate parity-check columns at every
    d, so a weight-2 error is undetectable and flips the logical: the
    family is reported `weak` with the witness, `code_distance_check`
    returns `verdict: contradicted`, and `decode_single` /
    `threshold_sweep` rows carry `effective_distance` from a bounded
    search (`mcp_server_library.effective_distance`). `toric` and
    `repetition` verify as labelled; `heavy_hex` is at least d+1.
  - `hot_path_microbench` times `decoder.decode()` alone after untimed
    warm-up shots (the old window included the verification matmul and
    the cold first call: 6x too slow at d=5); `ci95_mean` is null below
    30 shots and never negative.
  - Research `wilson_ci` no longer applies a floor that inflated the
    interval 5x at n=10^7; `z` must be positive; `k>n` is `INVALID_INPUT`.
  - `verified` is emitted only by tools that run a check;
    `build_code_from_matrix` and `system_setup` are `not_checked`;
    `decode_faithfulness_check` answers are verified results; a failed
    `integrity_check` is `INTEGRITY_FAILED` with its diagnostic payload.
  - Unreachable syndromes (outside `im(H)`) are `INVALID_INPUT`, not a
    `VERIFICATION_FAILED` blaming the decoder; code objects are cached;
    `toric` is capped at size 20 (super-linear constructor);
    `threshold_sweep` has a wall-clock budget with early projection.
  - DEM parser: probabilities validated, Stim `^` decomposition and
    detector cancellation, boundary-edge collapse, `weight_log` null at
    p in {0,1}, `repeat` refused with guidance, unknown targets refused.
  - `artifact_metadata_check` checks a real artifact (fields and
    `.sha256` sidecar) or returns a labelled template; `workload_hash`
    accepts partial workloads; `sinter_decoder_list` finds the factory in
    `qector_decoder_v3.sinter_compat` and distinguishes "sinter not
    installed"; admin refusals refund the budget; `system_setup` uses the
    shared artifact root.
  - Theorem 2 ground truth takes `stabilizer_generators` or
    `logical_observables` explicitly (the rows of H are checks, not the
    sector's stabilizers); `theorem_lookup`, the glossary and the math
    skills say so; a test on `rotated_surface(3)` proves the two forms
    differ there.
  - Commands `/qec-benchmark`, `/qec-code-inspect`, `/qec-sinter`,
    `/qec-wilson` called real tools with argument names the schemas
    reject (every call was `INVALID_INPUT`); rewritten against the
    schemas, with `argument-hint`s. `/qec-theorem` uses the tool's
    theorem titles. Prompts, skills and agents no longer describe a
    two-server `.mcp.json`, place `workbench_probe` on the research
    server, give `color_code` k=2, cite `checksums-sha256.txt`, or claim
    the PyPI check is the only network path; agent tool patterns name
    only registered servers; `mcp/CLAUDE_DESKTOP.md` rewritten; plugin
    icon added (`claude plugin validate` clean apart from the
    repository-only CLAUDE.md note); `CLAUDE.md` left out of the plugin
    archive; hook log location and `QECTOR_EXE` documented in PRIVACY.md.

- Fifth review pass (skills prose; Windows/macOS portability):
  - Skills: `qector-sinter` imported a non-existent top-level symbol and
    listed a fifth shim the wheel's source does not define; `sinter.collect`
    usage corrected (`custom_decoders=` + names); `TwoStageDecoder` signature
    corrected; two-stage CSS is Theorem 15 (seven places said 13);
    `color_code` is non-graphlike at d>=5 and k=0 (glossary, hardware
    engineer, codes builder, verified API); BP-OSD kwargs (`max_bp_iters`,
    `tau`, `plausibility_guard`, module `bp_osd`) that do not exist replaced
    by the verified signatures; `tier_table` result key removed; Workbench
    tool names no longer asserted; `start_metrics_server(addr=)`; REST
    route table; space-time tail arithmetic (0.12, not 5.9e-3); counts
    (ten validation layers, multi-tier chain, no "fifteen backends");
    benchmark-outcome sentence turned into a placeholder template;
    `num_logical_qubits` attribute name; `DemModel` method paths; house
    rule on dashes applied; `qector_system_setup.py` uses the per-user
    artifact root.
  - Portability: `.gitattributes` (`* -text`) so Windows checkouts keep the
    bytes `INTEGRITY.json` hashes; `scripts/qector-python` tries versioned
    interpreters and the Homebrew / python.org / pyenv locations invisible
    to GUI-launched processes on macOS; `qector-python.cmd` rewritten flat
    (no delayed expansion, errors to stderr, `py -3.13`..`-3.10`);
    new `qector-python.ps1`; the MCPB runs `sh` + launcher on POSIX and
    `powershell.exe -File` on win32 (a real executable; `.cmd` files
    cannot be spawned without a shell); the README states the native
    Windows constraint of the Claude Code plugin and the `claude mcp add`
    fallback; installers propagate exit codes and route through the
    launcher; audit log written with `\n` on every platform; the test
    stdio readers have real timeouts on every platform; air-gap guard
    refuses `bind(("", port))` (was treated as loopback, is INADDR_ANY).
  - `docs/UPSTREAM_ISSUE_rotated_surface_distance.md` and
    `scripts/probe_wheel_distance.py` (plugin-free reproducer) document
    the wheel's rotated-surface defect and its fix for the upstream
    maintainers.

- Sixth pass (closing the last gaps that can be closed without a new
  wheel):
  - `rotated_surface_corrected`: the rotated surface code built by the
    plugin (`mcp/qector_codes.py`) with same-type boundary checks, verified
    at construction and refused if the check fails; `source: "plugin"` in
    `list_code_families`; default family of `decode_single`,
    `threshold_sweep` and `scripts/run_threshold_sweep.py`. Sweeps on it
    show distance scaling; the wheel's family stays available and `weak`.
  - `effective_distance` is exact for every graphlike code: the minimum
    logical weight is the shortest odd-parity cycle of the matching graph
    (checks + boundary node, qubits as edges), found by BFS over
    (node, parity) states in milliseconds up to d≈63; enumeration remains
    the fallback. `heavy_hex` is thereby known to have distance 2d−1.
  - Launchers resolve in two passes (interpreter with the runtime first,
    any supported version second; an explicit `QECTOR_PYTHON` always wins).
  - `scripts/boot_from_manifest.py`: extracts a Desktop bundle and spawns
    the exact `command`/`args`/`env` its manifest names for the current
    platform in exec form, then checks tools, integrity (pinned), air gap
    and a verified decode; verified on the Linux bundle with and without
    a configured interpreter.
  - CI `native` job on `windows-latest` and `macos-latest`: autocrlf
    checkout + integrity check, `.cmd`/`.ps1`/POSIX launchers (success and
    fail-closed exit 127), full suite, archive build, bundle validation,
    manifest boot with and without a configured interpreter, offline
    installers (`.sh` with `shasum`, `.ps1`), bundled Desktop artifact boot.
    RELEASE_VALIDATION.md makes a green run on the release commit a
    precondition for publication.

- Reviewer-environment hardening (from two independent reviews of the
  release archive run without the wheel): test discovery skips cleanly
  (`OK (skipped=108)`) instead of erroring when `mcp` or the wheel is
  absent (the SDK detector was fooled by the repository's own `mcp/`
  directory); `mcp/tests/test_mcp_stdio.py` fails fast with the missing
  modules instead of timing out and never prints `PASS` for a partial
  result; `validate_plugin_bundle.py` exits 2 with "nothing to validate"
  when `dist/` is absent; the reviewer guide explains the 29/30
  release-check difference between the source archive and a checkout.

- Third independent review (bundled runtime, sandbox with per-command time
  limits): `scripts/run_test_suite.py` runs the modules one at a time with
  timings; `scripts/probe_wheel_distance.py` is exact for graphlike codes
  (heavy_hex d=5 → 9) and cross-checks against brute force; the reviewer
  guide states that no `[all]`/`[stim]` extra is required and how to run
  everything from the bundled MCPB runtime without PyPI access.

### Removed

- Stale submission drafts (`ANTHROPIC_MARKETPLACE_SUBMISSION.md`,
  `GLAMA_SUBMISSION.md`, `PULSEMCP_SUBMISSION.md`, `SUBMISSIONS.md`) and
  1.0.x release notes carrying hashes that never matched the artifacts.

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
