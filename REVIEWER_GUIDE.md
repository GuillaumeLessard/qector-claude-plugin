# Reviewer guide — verify QECTOR 2.0.1 in ten minutes

Everything below runs offline except step 1 (pip) and needs only the
published archives, `SHA256SUMS`, `SHA256SUMS.sig` and this file. Expected
outputs are stated; anything else is a defect to report to
<admin@qector.store>.

| # | Command | Expect |
|--:|:--------|:-------|
| 1 | `python -m venv .v && . .v/bin/activate && pip install -r requirements.lock` (from the extracted source zip) | pip runs in hash-checking mode; 31 distributions |
| 2 | `sha256sum -c SHA256SUMS` | `OK` for every artifact |
| 3 | `python scripts/sign_release.py --verify <dir> --pubkey kYwkMApz4zMgQmJsOya1UZuByvnuikzlxQkQiA8NOJg=` | `OK` for `SHA256SUMS.sig` and every archive's `INTEGRITY.json.sig`, fingerprint `6726953ded0a01a4a15cc92d460178f71aa2568c59ee969fc4efe8812c8299dc` (compare with SECURITY.md and the Sigstore log entry) |
| 4 | `python scripts/release_validate.py && python scripts/validate_source.py` | `30 passed, 0 failed` from a git checkout, `29 passed` from the source archive (which deliberately omits the registry-only `server.json`); `ALL CLEAR` (29 from the source archive, which deliberately omits the registry-only `server.json`; 30 from a git checkout) |
| 5 | `python scripts/export_schemas.py --check && python scripts/generate_integrity_manifest.py --check --pubkey <key>` | `schemas/ is in sync (91 files)`; `"passed": true`, `"source": "pinned"` |
| 6 | `QECTOR_SILENT=1 python -m unittest discover -s tests` | `OK` (158 tests; without the wheel and SDK installed the same command reports `OK (skipped=108)`, never errors) — repeat after `pip install "mcp>=2,<3"` for the second SDK generation |
| 7 | `QECTOR_SILENT=1 python mcp/tests/test_mcp_stdio.py` | `PASS: 5/5 servers validated` |
| 8 | `python scripts/build_release.py --all` (from the source zip; no `.git` needed) | the three core artifacts reproduce the published SHA-256 values byte for byte (`RELEASE_COMMIT` supplies the commit) |
| 9 | Start the server and ask it: `scripts/qector-python mcp/mcp_server_secure.py --profile safe` with `QECTOR_INTEGRITY_PUBKEY=<key>`, then `tools/call airgap_status`, `integrity_check`, `compat_report {"check_pypi": true}` | `air_gapped: true`; `passed: true`, `signature.source: "pinned"`; `pypi_freshness.status: "disabled"` with a warning and no connection |
| 10 | Append one byte to `mcp/qector_airgap.py`, start again | `FATAL: runtime files do not match INTEGRITY.json`, exit code 3 |
| 11 | `python scripts/validate_plugin_bundle.py` after step 8 | `ALL CLEAR`; the last section extracts each shipped plugin zip and MCPB and boots its secure server over stdio in strict mode with the shipped pinned key: `12 tools, integrity passed, signature pinned` |
| 12 | `strings` the decoder wheel's `.so` and compare with `airgap_status.backend_network_surface` | `api.stripe.com/v1/billing/meter_events` and `rustls` present in the wheel, listed verbatim by the tool, `called_by_plugin: false`; `grep -rn flush_usage mcp/` returns only the guard's own list |
| 13 | `python scripts/probe_wheel_distance.py` (plugin-free brute force) | `rotated_surface_code` d=3/5/7 `OVERSTATED: true distance 2`; `toric`/`repetition`/`ring` `ok` — the defect the plugin discloses is in the wheel, documented in `docs/UPSTREAM_ISSUE_rotated_surface_distance.md` |
| 14 | `python scripts/boot_from_manifest.py dist/qector-claude-desktop-2.0.1.mcpb` (on any OS) | `BOOT OK`: the bundle starts through the exact command its manifest names for your platform, 12 tools, `integrity_check` passed with `signature: pinned`, `decode_syndrome` verified |

## Reviewing without the wheel, or inside a sandbox

- **Only `requirements.lock` is required.** No `[all]`, `[stim]` or other
  extra of `qector-decoder-v3` is needed by any tool; integrations that
  need `stim`, `pymatching`, `sinter`, `ldpc`, `beliefmatching` or CuPy
  report their absence (`sinter_decoder_list`, `pymatching_compat_check`,
  `qiskit_plugin_check`, `hardware_probe`) and never fail the server.
- **No PyPI access?** The bundled Linux MCPB carries the complete runtime:
  extract it and run everything with
  `PYTHONPATH=<extracted>/server/lib python3.13 ...` (the suite, the
  servers and the probes all work that way; the Linux CI job does the same).
- **Per-command time limits?** `python scripts/run_test_suite.py` runs the
  seven modules one at a time with wall-clock timings (about 25 s in total
  on a laptop; `test_production_readiness` is the longest at ~13 s) and
  prints a combined total identical to `unittest discover`.
- **Without the wheel and SDK** the suite reports `OK (skipped=108)` and
  the stdio test says which modules are missing; neither is a failure.
- `scripts/probe_wheel_distance.py` is exact for every graphlike family
  (shortest odd-parity cycle of the matching graph, cross-checked against
  brute force on small codes), so `heavy_hex` d=5 reads `9`, not
  "none found within the search".

What you will *not* find, by design: a listening socket, an HTTP/SSE/WebSocket
code path, `eval`/`exec`, a telemetry call, a dependency without a hash, a
tool without an input and an output schema, or a claim in SECURITY.md that
the test suite does not exercise.

Known limits are written down rather than hidden: THREAT_MODEL.md
"Residual risks" and the `guard_scope` string returned by `airgap_status`.
