# Security

## Identification

| Field | Value |
|:------|:------|
| Plugin name | `qector` |
| Display name | QECTOR Quantum Error Correction |
| Version | 2.0.1 |
| Contract | `QECTORToolResult` 2.0 (`mcp/qector_mcp_contract.py`, `schemas/`) |
| License | Proprietary — see [LICENSE.md](LICENSE.md) |
| Author | Guillaume Lessard <admin@qector.store> |
| Repository | https://github.com/GuillaumeLessard/qector-claude-plugin |
| Reference manual | DOI `10.5281/zenodo.21941046` (v1.0.0) |
| Privacy policy | https://qector.store/privacy |
| Threat model | [THREAT_MODEL.md](THREAT_MODEL.md) |
| Air-gapped deployment | [AIRGAP.md](AIRGAP.md) |
| Provenance | [PROVENANCE.md](PROVENANCE.md), `INTEGRITY.json`, `dist/provenance.json`, `dist/SHA256SUMS`, SPDX SBOM |

## What changed in 2.0.0 and why

The 1.0.x line described itself as "zero egress" while (a) nothing in the
process prevented egress, (b) the opt-in PyPI check could be triggered by
any client that passed `check_pypi=true`, and (c) the decoder wheel it runs
on carries a native TLS client. 2.0.0 replaces the description with
mechanisms, and states the residual risk instead of hiding it:

| Property | 1.0.6 | 2.0.0 |
|:---------|:------|:------|
| Network posture | documented as offline; no enforcement | **air-gapped by default** (`QECTOR_AIR_GAPPED` unset/1): the public `socket`, `urllib`, `subprocess` and `os.*spawn*`/`os.system`/`os.popen` paths fail closed inside the process; billing variables scrubbed. Defence in depth against the tool surface, not a sandbox (see "Scope of the in-process guards") |
| Input validation | SDK default (varied by SDK version) | **own Draft 2020-12 validator on every call**, stable `INVALID_INPUT` with JSON path |
| Output validation | none | **every envelope validated against the tool's `outputSchema`**; mismatch → `CONTRACT_VIOLATION`, never forwarded |
| Runtime integrity | none | `INTEGRITY.json` (SHA-256 of every runtime file) verified at startup; strict mode refuses to serve a modified tree |
| Audit | none | optional hash-chained JSONL audit log (`QECTOR_AUDIT_DIR`), arguments logged only as SHA-256; optional HMAC key (`QECTOR_AUDIT_HMAC_KEY_FILE`); tail truncation detected by the running server, whole-file rewrite only with the key or external anchoring; a record that cannot be written fails the call closed (`IO_ERROR`, result withheld) |
| SDK | `mcp==1.26.0` (3 open CVEs) in two of four shipped archives | `mcp>=1.30,<3`; refuses to start on a vulnerable SDK unless overridden |
| Release consistency | three different trees labelled 1.0.6 | one deterministic builder; per-archive `INTEGRITY.json`; `requirements.lock` |
| Degenerate wheel codes | exposed as decodable | detected (`family_health`), refused or warned, never silently scored |

## Trust boundaries

Five named MCP servers share one contract. The default install exposes
**12 tools** (8 stable + 4 control-plane) over local stdio.

| Server | Entry point | Tools | Default | Trust zone |
|:-------|:------------|------:|:--------|:-----------|
| `qector-secure` | `mcp/mcp_server_secure.py --profile safe` | 12 | **Claude Code and Claude Desktop default** | Tier 1: air-gapped, schema-validated in and out, integrity-checked, audited |
| `qector-secure --profile research` | same, `--profile research` | 41 | opt-in | Tier 2: adds the 29 provisional research tools behind the same control plane |
| `qector-library` | `mcp/mcp_server_library.py` | 8 | legacy / embedded use | Tier 1 math; same validation, no control-plane tools |
| `qector-research` | `mcp/mcp_server_qector_bench.py` | 29 | opt-in | Tier 2 |
| `qector-admin` | `mcp/mcp_server_admin.py` | 3 | opt-in (`QECTOR_ADMIN_ENABLED=1` + `confirm=true`) | Tier 3: only server allowed to launch processes; pip is refused in air-gapped mode without an offline wheelhouse |

`qector-desktop-mcp` (`mcp/mcp_server_desktop.py`) is a compatibility shim
that runs `qector-secure` under the Desktop server name; 1.x Desktop
configurations keep working.

## Tool risk classification

| Class | Tools | What they actually do |
|:------|:------|:----------------------|
| `control` (read) | `airgap_status`, `integrity_check`, `schema_catalog`, `audit_log_status` | Report the server's own posture. `integrity_check` reads runtime files and hashes them; nothing is written. |
| `read` | `list_code_families`, `list_decoders`, `get_license_info`, `compat_report`, and 28 research tools (`wilson_ci`, `wilson_table`, `logical_coset_score`, `dem_inspect`, `dem_collapse_parallel`, `code_family_info`, `code_export_matrices`, `code_logicals_inspect`, `code_distance_check`, `pymatching_compat_check`, `sinter_decoder_list`, `qiskit_plugin_check`, `hardware_probe`, `license_active_check`, `env_block`, `research_compat_report`, `artifacts_sha256` (reads only inside `QECTOR_ARTIFACT_DIR`), `artifact_metadata_check`, `decode_faithfulness_check`, `stim_circuit_probe`, `sinter_task_template`, `workload_hash`, `theorem_lookup`, `glossary_lookup`, `reproduction_command_lookup`, `get_capability_matrix`, `get_evidence_policy`, `get_runtime_provenance`). `hardware_probe` is listed here for scanner purposes but carries `status: measured` in the envelope because it reports machine-local facts | Pure read / compute on caller-supplied data or the live wheel. No file write, no subprocess, no network. `compat_report`, `research_compat_report`, `env_block` and `get_runtime_provenance` accept `check_pypi`, which is **refused in air-gapped mode** and otherwise makes one GET to `https://pypi.org/pypi/qector-decoder-v3/json`. |
| `compute` | `decode_syndrome`, `decode_single`, `hot_path_microbench` | Scoped QEC math on binary inputs bounded by `QECTOR_MCP_MAX_*`. Every correction is checked against `H c = s (mod 2)` before it is returned. |
| `build` | `build_code_from_matrix` | Validates and constructs an in-memory parity-check matrix; reports GF(2) rank. |
| `write` (local, bounded) | `threshold_sweep` | Writes one JSON artifact plus a `.sha256` sidecar inside `QECTOR_ARTIFACT_DIR` (default: the per-user data directory, never the install directory). Path traversal outside the root is rejected. |
| `privileged` | `system_setup`, `configure_claude_desktop`, `workbench_probe` (admin server only) | Require `QECTOR_ADMIN_ENABLED=1` and `confirm=true`. `system_setup` runs pip only from a fixed profile allowlist and, in air-gapped mode, only from an `offline_wheelhouse` with `--no-index`. `workbench_probe` launches only an executable inside `QECTOR_WORKBENCH_DIR` whose SHA-256 matches the caller-supplied digest. |

### What the plugin does not do

- It never transmits syndromes, parity matrices, circuits, tool arguments
  or artifacts anywhere. The audit log stores a SHA-256 of the arguments,
  not the arguments.
- It never calls `eval`/`exec` and never imports from caller input
  (`tests/test_airgap.py` enforces this statically for every server
  module). The only code paths that launch a process are the admin tool
  implementations (`system_setup` → pip, `workbench_probe` → an approved
  binary). They live in `mcp_server_qector_bench.py` but are dispatched
  only by `qector-admin`; `qector-secure`, `qector-library` and
  `qector-research` install the subprocess guard, so even a reachable
  call would fail closed. `tests/test_airgap.py` asserts that no other
  module references `subprocess`.
- The default servers open **no listening socket**. There is no HTTP, SSE
  or WebSocket transport in this package; `--transport` accepts only
  `stdio`.
- It never calls the decoder wheel's network-capable symbols (next
  section).

## Scope of the in-process guards

The guards in `mcp/qector_airgap.py` replace the **public** Python entry
points (`socket.socket`/`socket.SocketType`, `socket.getaddrinfo`, `socket.create_connection`,
`urllib.request.urlopen`, `subprocess.Popen`, `os.system`, `os.popen`,
`os.posix_spawn*`, `os.spawn*`, `os.startfile`). They are designed to stop
anything reachable **through a tool argument** — and no tool accepts a
hostname, a URL, a command or code. They are not a sandbox: code that is
already executing inside the interpreter can still reach the private
`_socket` module, `ctypes`, `os.fork` + `os.exec*`, or the decoder wheel's
compiled TLS client (the guarded class's base type remains reachable to in-process code, like `_socket`). `airgap_status.guard_scope` states this verbatim,
THREAT_MODEL.md lists it as a residual risk, and AIRGAP.md requires a host
egress policy for a hard guarantee.

## Disclosure: the decoder wheel's native network surface

`qector-decoder-v3==1.0.1` is a Rust/PyO3 wheel. Its compiled core contains
a TLS client (`rustls`) and the literal endpoint
`https://api.stripe.com/v1/billing/meter_events`, used by the explicit
`flush_usage()` metering call; the Python layer additionally ships
`stripe_integration.py`, `rest_api.py`, a gRPC server, a Prometheus
metrics server and a Workbench MCP server. **None of these is imported,
referenced or started by this plugin** — `tests/test_airgap.py` greps every
server module for the full symbol list, and `airgap_status` publishes it.
The wheel does not call them on its own either: metering happens only when
`flush_usage()` is invoked explicitly.

Because they are native code, the Python-level guards cannot intercept
them. `airgap_status.backend_network_surface.python_level_guard_blocks_native_core`
is therefore `false`, and [AIRGAP.md](AIRGAP.md) requires a host-level
egress control (no default route, firewall rule, or network namespace) for
deployments that need a hard guarantee. 2.0.0 also removes
`STRIPE_SECRET_KEY`, `QECTOR_STRIPE_CUSTOMER_ID`,
`QECTOR_LICENSE_PRIVATE_KEY_B64` and related variables from the server
process so the metering path cannot be armed by inherited shell state.

## Release signing

Every 2.0.0 archive carries `INTEGRITY.json.sig` and every release carries
`dist/SHA256SUMS.sig`: detached Ed25519 signatures (JSON documents holding
the algorithm, the subject's SHA-256, the public key and the signature).
The publish workflow signs with the key held in the repository secret
`QECTOR_RELEASE_SIGNING_KEY` and additionally records a Sigstore keyless
signature of `SHA256SUMS` (`SHA256SUMS.sigstore.json`) in the public
transparency log.

| Field | Value |
|:------|:------|
| Algorithm | Ed25519 (`cryptography`, already a runtime dependency) |
| Public key (base64) | `kYwkMApz4zMgQmJsOya1UZuByvnuikzlxQkQiA8NOJg=` |
| Fingerprint (SHA-256 of raw key) | `6726953ded0a01a4a15cc92d460178f71aa2568c59ee969fc4efe8812c8299dc` |

Pin the key out-of-band and verify before installing:

```bash
python scripts/sign_release.py --verify dist --pubkey kYwkMApz4zMgQmJsOya1UZuByvnuikzlxQkQiA8NOJg=
```

On the lab host, `QECTOR_INTEGRITY_PUBKEY=<public key>` makes `qector-secure`
require a valid signature under *that* key at every start (`integrity_check`
reports `signature.source: "pinned"`). Without a pinned key the server still
verifies a shipped signature against the key embedded in the archive and
reports `source: "release_manifest"` — consistency, not origin, because an
attacker who rewrites the code can rewrite the embedded key. A development
checkout without a signature starts in strict mode on file hashes alone and
says so in `integrity_check.signature.reason`.

## Built-in resource ceilings

| Ceiling | Default | Override |
|:--------|--------:|:---------|
| `threshold_sweep` calls / process | 8 | `QECTOR_MCP_MAX_CALLS_THRESHOLD_SWEEP` |
| `decode_single` calls / process | 64 | `QECTOR_MCP_MAX_CALLS_DECODE_SINGLE` |
| `decode_syndrome` calls / process | 256 | `QECTOR_MCP_MAX_CALLS_DECODE_SYNDROME` |
| `build_code_from_matrix` calls / process | 32 | `QECTOR_MCP_MAX_CALLS_BUILD_CODE_FROM_MATRIX` |
| `hot_path_microbench` calls / process | 4 | `QECTOR_MCP_MAX_CALLS_HOT_PATH_MICROBENCH` |
| `integrity_check` calls / process | 16 | `QECTOR_MCP_MAX_CALLS_INTEGRITY_CHECK` |
| admin tools calls / process | 2 each | `QECTOR_MCP_MAX_CALLS_<TOOL>` |
| any tool calls / rolling 60 s | 600 | `QECTOR_MCP_RATE_LIMIT_PER_MINUTE` (0 disables) |
| request payload | 2 MiB | `QECTOR_MCP_MAX_REQUEST_BYTES` / `--max-request-bytes` |
| distance / checks / qubits / matrix cells / trials / sweep points | 63 / 10 000 / 100 000 / 1 000 000 / 10 000 / 64 | `QECTOR_MCP_MAX_*` |

Exhaustion returns `RESOURCE_LIMIT`; oversize input returns `INVALID_INPUT`.
A negative call-budget override disables that budget (explicit operator
choice, documented in the audit log through the resulting call pattern).

## Startup gates of `qector-secure`

1. **SDK gate** — `mcp` outside `>=1.30,<3` → exit 4 (`--allow-unsupported-sdk` to override).
2. **Air-gap guard** installed before any MCP traffic (`--allow-network` lifts it and logs a warning on stderr).
3. **Integrity gate** — exit 6 (`EXIT_DEPENDENCY`) if the decoder wheel cannot be imported; otherwise `INTEGRITY.json` verified **before** any decoder-facing module (`mcp_server_library.py`, `mcp_server_qector_bench.py`) is imported; strict by default, including when the manifest is missing (exit 3). `QECTOR_INTEGRITY_STRICT=0` / `--no-strict-integrity` downgrade to a warning for development trees only. Limitation: the control-plane modules themselves (`qector_integrity.py`, `qector_airgap.py`, `qector_mcp_contract.py`, …) execute before they can verify their own hash; they are small, hashed in the manifest, and covered by the release `SHA256SUMS`.
4. **Audit log** opened (or chain-verified if it already exists; a corrupt chain exits 5).
5. **Request handling** — a JSON-RPC message the SDK cannot parse (malformed JSON, >128 nesting levels, a batch array) is answered by the SDK with a `notifications/message` error and no result for that id; every message that reaches the tool layer receives a contract-2.0 envelope.
6. **Tool assembly** — deterministic, sorted `tools/list`; duplicate names are a startup error.

## Runtime dependency advisories

The 1.0.6 archives pinned `mcp==1.26.0`, affected by CVE-2026-52869
(HTTP session principal bypass), CVE-2026-52870 (task handler cross-client
access) and CVE-2026-59950 (WebSocket Host/Origin validation). None of
the affected code paths is used by QECTOR (stdio only, no task handlers),
but shipping a known-vulnerable dependency is not acceptable for a
reviewed plugin. 2.0.0 requires `mcp>=1.30,<3` (both the patched 1.x line
and the 2.x line are tested in CI) and `qector-secure` refuses to start on
an older SDK. `requirements.lock` records the exact tested closure.

## Reporting

Report vulnerabilities privately to <admin@qector.store>. Do not include
licence keys, credentials, private matrices or customer artifacts in
reports. Coordinated disclosure: acknowledgement within 72 hours, fix or
mitigation target 30 days for high severity.
