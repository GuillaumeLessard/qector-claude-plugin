# QECTOR Claude Plugin 2.0.0 — release notes

**Theme: mechanisms instead of claims.** The 1.0.x line said "zero egress,
every result verified, eight stable tools". 2.0.0 keeps the mathematics
(the parity gate `H c = s (mod 2)` and logical-coset Wilson scoring are
unchanged and re-tested against the live wheel) and replaces every
security statement with an enforced control that a reviewer can exercise
from the client.

## Headline changes

1. **`qector-secure`** is the default server for Claude Code and Claude
   Desktop. Twelve tools in the safe profile: the eight stable decoding
   tools plus `airgap_status`, `integrity_check`, `schema_catalog` and
   `audit_log_status`.
2. **Air-gapped by default.** Non-loopback sockets, `urllib` and
   `subprocess` fail closed inside the process; billing variables are
   scrubbed; the opt-in PyPI check returns `disabled` with no connection
   attempted. `--allow-network` / `QECTOR_AIR_GAPPED=0` is the only way
   out and is logged.
3. **Validated both ways.** JSON Schema 2020-12 on every request (stable
   `INVALID_INPUT` with a JSON path) and on every response
   (`CONTRACT_VIOLATION` instead of a malformed result). Ninety-one schema
   files are committed under `schemas/` and kept in sync by CI.
4. **Integrity, signatures and audit.** `INTEGRITY.json` is verified at
   startup before any decoder module is imported (strict by default, a
   missing manifest refuses to start); every archive's manifest and the
   release `SHA256SUMS` are Ed25519-signed, with the key fingerprint
   published and pinnable on the lab host; an optional hash-chained JSONL
   audit log (HMAC option) records every call with argument digests only.
5. **Two SDK generations.** `mcp>=1.30,<3`: the patched 1.x line and the
   2.x line produce identical wire output through
   `mcp/qector_mcp_compat.py`. Known-vulnerable SDKs are refused at start.
6. **Laboratory install path.** `requirements.lock`, cross-platform
   wheelhouse builder with `SHA256SUMS`, offline installers for POSIX and
   Windows, and a Desktop bundle option that vendors the runtime into
   `server/lib` as the MCPB `python` type expects.
7. **Honest wheel reporting.** The decoder wheel's native TLS client and
   Stripe metering endpoint are disclosed; degenerate code constructions
   in the wheel (`color_code` d=3, unchecked qubits in `heavy_hex` and
   `color_code` d≥5) are detected and refused or warned, never scored
   silently. The wheel's distance labels are checked, not trusted: a
   bounded minimum-logical-weight search (`effective_distance`) found that
   `rotated_surface_code(d)` has duplicate parity-check columns at every d
   (an undetectable weight-2 logical error), so that family is reported
   `weak` with the witness on every result and `code_distance_check`
   returns `contradicted`; `toric` and `repetition` verify as labelled.

## Fixed defects (all with regression tests)

| Defect in 1.0.6 | Fix |
|:----------------|:----|
| `sinter_task_template` raised `TypeError` on every call | missing argument restored |
| `dem_collapse_parallel` ignored the third and later parallel mechanisms | n-member independent-XOR combination, `combination_rule` reported |
| `decode_faithfulness_check.residual_weight` was `weight(c)` renamed | replaced by `computed_syndrome` and `syndrome_mismatch_indices` |
| `license_active_check` hard-coded Community/Pro/Enterprise limits | live wheel values only, `source` field |
| `importlib.metadata` used without import in the research server | imported |
| `hot_path_microbench` accepted decoders whose constructor signature does not match | explicit allow-list, graphlike check, violations surfaced as warnings |
| Artifacts written inside the install directory | per-user data directory |
| Four archives, three different trees, mismatched published hashes | deterministic in-memory builder, per-archive manifest, lockfile |
| Python 3.9 advertised but unsupported by the SDK | launchers and manifests say 3.10–3.13 |
| Duplicate "Privileged Operations" section in SECURITY.md | rewritten document |

## Breaking changes

- Default server name and tool count (`qector-secure`, 12).
- Envelope contract 2.0 (`contract_version`, `tool`, `provenance.mcp_sdk`,
  new error codes).
- `check_pypi=true` is refused unless `QECTOR_AIR_GAPPED=0`.
- Python 3.9 dropped; `mcp` pin raised to `>=1.30,<3`.

## Verification performed for this release

- 158 unit, contract and live-stdio tests pass on CPython 3.11, 3.12 and
  3.13 with `mcp` 1.30.0 and with `mcp` 2.3.0
  (`python -m unittest discover -s tests`), clean under
  `-W error::ResourceWarning`.
- `mcp/tests/test_mcp_stdio.py`: 5/5 servers answer `initialize`,
  `tools/list` and a sample `tools/call` with a contract-2.0 envelope.
- `scripts/release_validate.py`, `scripts/validate_source.py`,
  `scripts/export_schemas.py --check`,
  `scripts/generate_integrity_manifest.py --check`, `ruff check .`: clean.
- `scripts/build_release.py --all` then `scripts/validate_plugin_bundle.py`:
  all archives carry a matching `INTEGRITY.json`; `SHA256SUMS` in `dist/`.
- Offline path exercised end to end on the build host:
  `build_wheelhouse.py` → `install_offline.sh` → `qector_runtime_check.py`.
- Every shipped archive is extracted and its secure server booted over
  stdio in strict mode with the pinned key by
  `scripts/validate_plugin_bundle.py`; the build reproduces byte for byte
  from the source archive.
- **Native Windows and macOS runs are automated, not yet executed:** the
  CI `native` job (windows-latest, macos-latest) checks out with Git for
  Windows' default line-ending policy, exercises every launcher, runs the
  suite, builds the archives and boots the Desktop bundle through the
  exact command its manifest names (`scripts/boot_from_manifest.py`).
  On the build host the same script booted the Linux bundle through
  `sh` + launcher with and without a configured interpreter. The job must
  be green on the release commit before publication
  (RELEASE_VALIDATION.md); the README states the Windows constraint of
  the Claude Code plugin.

## Upgrade notes

- Replace `qector-library` with `qector-secure` in hand-written
  `claude_desktop_config.json` entries, or re-run
  `scripts/configure_claude_desktop.py --confirm`.
- Clients that parsed the 1.x envelope must accept the two new required
  keys; nothing was removed.
- Set `QECTOR_AUDIT_DIR` to enable auditing; nothing is written anywhere
  by default.
