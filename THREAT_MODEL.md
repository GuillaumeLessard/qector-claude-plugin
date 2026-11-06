# Threat model — QECTOR Claude Plugin 2.0.1

## Assets

1. **Workload confidentiality.** Syndromes, parity-check matrices, DEM
   text and Stim circuits a laboratory feeds to the tools. These can
   encode unpublished device data.
2. **Result integrity.** The claim that a returned correction satisfies
   `H c = s (mod 2)` and that a logical-error rate was scored on the
   logical coset with a Wilson interval. A wrong claim silently corrupts a
   research record.
3. **Host integrity.** The laptop or lab host running Claude Code / Claude
   Desktop: its files, its network, its credentials.
4. **Release integrity.** That the archive a user installs is the archive
   that was reviewed.

## Actors

| Actor | Capability | Intent considered |
|:------|:-----------|:------------------|
| Model (Claude) | Any `tools/call` with any arguments, any frequency | Non-adversarial but fallible: malformed arguments, loops, over-claiming results, prompt-injected into calling admin tools |
| Prompt injector | Content the model reads (documents, web pages) | Steer the model into `check_pypi=true`, `system_setup`, path traversal, exfiltration via tool arguments |
| Local unprivileged process | Same user account | Tamper with installed files or the audit log |
| Supply chain | PyPI, GitHub release pipeline | Substitute a dependency or an archive |
| Decoder wheel vendor code | Native code inside the process | Metering/telemetry paths that could reach the network |

Out of scope: a root-level attacker on the host, hardware side channels,
and the client (Claude Code / Desktop) itself.

## Controls, mapped

| Threat | Control | Where | Verified by |
|:-------|:--------|:------|:------------|
| Exfiltration through a tool's network path | Air-gap guard: non-loopback `socket.connect/bind/sendto`, `getaddrinfo`, `create_connection`, `urllib.request.urlopen` raise `QECTORNetworkDisabledError` (envelope code `NETWORK_DISABLED`); the only network-capable option, `check_pypi=true`, is short-circuited before any socket and reports `pypi_freshness.status: "disabled"` with a warning | `mcp/qector_airgap.py` | `tests/test_secure_server.py::test_socket_guard_blocks_egress_but_allows_loopback`, `test_pypi_check_is_refused_without_network` |
| Metering path armed by inherited environment | `STRIPE_*`, `QECTOR_STRIPE_CUSTOMER_ID`, `QECTOR_LICENSE_PRIVATE_KEY_B64` removed from `os.environ` at startup | `qector_airgap.install` | `test_billing_variables_are_scrubbed` |
| Native TLS client in the wheel | **Residual.** Disclosed in `airgap_status`, SECURITY.md; host egress policy required by AIRGAP.md; static test proves the plugin never references the symbols | `tests/test_airgap.py` | static grep |
| Process launch from a tool | `subprocess.Popen`, `os.system`, `os.popen`, `os.posix_spawn*`, `os.spawn*` raise `PermissionError` in every server except `qector-admin`; no tool accepts a command | `qector_airgap.install(allow_subprocess=False)` | `test_subprocess_and_urllib_guards` |
| Malformed / hostile arguments | Draft 2020-12 validation before dispatch; `additionalProperties: false`; bounded `maxItems`/`maximum`; request-size cap; lazy first-error so pathological arrays fail fast | `qector_mcp_contract.validate_arguments`, `mcp_server_secure._check_request_size` | `test_additional_property_is_invalid_input`, `test_huge_array_fails_fast`, `test_oversized_request_is_refused_before_decoding` |
| Over-claiming results | Envelope `status`/`claim_class`/`verification.checks`; `verified` only when the parity gate ran; degenerate wheel codes refused; weak codes warned | `result_envelope`, `family_health` | `LibraryFixTests`, `test_valid_decode_is_verified_and_audited` |
| Result shape drift / half-formed output | Output validated against the advertised `outputSchema`; failure → `CONTRACT_VIOLATION` with empty result | `validate_envelope` | `test_output_contract_violation_is_reported_not_forwarded` |
| Agent loops | Per-tool call budgets, 600 calls/min rate limit | `_CallBudget` | `test_rate_limit_is_enforced`, `test_call_budget_enforced` |
| Path traversal in artifact paths | Resolved path must stay under `QECTOR_ARTIFACT_DIR`; default root is the per-user data dir for every server (library and research share `default_data_dir()`), never the install dir | `_artifact_path`, `_approved_artifact_path` | `TestArtifactRootContainment`, `test_artifact_root_is_outside_install_dir` |
| Tampered install | `INTEGRITY.json` verified at startup, strict by default; `integrity_check` tool re-verifies on demand; `INTEGRITY.json.sig` (Ed25519) proves origin when the published key is pinned via `QECTOR_INTEGRITY_PUBKEY` | `qector_integrity`, `qector_signing` | `test_integrity_manifest_roundtrip_and_strict_gate`, `tests/test_signing.py` |
| Tampered audit trail | Hash chain: each record binds the previous digest; the running server compares the file with the head it wrote (detects tail truncation); optional HMAC key makes recomputation impossible without the key; corrupt chain refuses appends | `qector_audit` | `test_audit_chain_is_valid_and_detects_tampering`, `test_audit_truncation_and_hmac` |
| Vulnerable SDK | `mcp>=1.30,<3` required; start refused otherwise | `qector_mcp_compat.sdk_supported` | `test_unsupported_sdk_versions_are_named` |
| Inconsistent releases | One deterministic builder that refuses a dirty tree, fixed zip timestamps, `RELEASE_COMMIT` + per-archive `INTEGRITY.json`, hashed `requirements.lock`, SPDX SBOM with per-package checksums, signed `SHA256SUMS` + Sigstore transparency entry | `scripts/build_release.py`, `scripts/sign_release.py` | `scripts/validate_plugin_bundle.py`, `sign_release.py --verify` |
| Dependency substitution in the lab | `requirements.lock` carries every published wheel digest (pip hash-checking mode); offline wheelhouse with `SHA256SUMS`; installer verifies before `pip install --no-index` | `requirements.lock`, `scripts/build_wheelhouse.py`, `scripts/install_offline.*` | `test_lockfile_is_hashed_and_sbom_has_checksums`, CI offline job |
| Information leak in error text | Home directory redacted, message capped | `_safe_message` | `test_home_directory_is_redacted_from_error_messages` |

## Residual risks (stated, not hidden)

0. The in-process guards wrap the public Python entry points only. Code
   already running inside the interpreter (not reachable through any tool
   argument) can still use the private `_socket` module, `ctypes` or
   `os.fork`+`os.exec*`. They are defence in depth against the tool
   surface, not a sandbox; `airgap_status.guard_scope` says so.
1. The decoder wheel's native core can open TLS connections if one of its
   own functions is called. The plugin never calls them, and the
   environment that would authenticate such a call is scrubbed, but only a
   host egress policy makes this impossible. Labs must apply one.
2. `INTEGRITY.json.sig` proves origin only when the verifier pins the
   published key (`QECTOR_INTEGRITY_PUBKEY`, `sign_release.py --pubkey`).
   Without pinning, an attacker who rewrites code, manifest, signature and
   embedded key together produces a self-consistent archive; the
   transparency-log entry and the fingerprint in SECURITY.md are what make
   that detectable. The signing private key lives outside the repository
   and outside lab hosts.
3. The audit log is append-only by convention and hash-chained, not
   write-once at the filesystem level. Without `QECTOR_AUDIT_HMAC_KEY_FILE`
   a same-user attacker who can stop the server can rewrite the whole file
   and recompute every digest; with the key they cannot. Tail truncation is
   detected while the server runs, not after it exits. Anchor
   `head_sha256` externally (WORM store, lab notebook) per session.
   Argument digests of low-entropy arguments are dictionary-reversible; the
   digest binds the record to the call rather than hiding it.
4. Vendored `server/lib` in a bundled Desktop build is not covered by
   `INTEGRITY.json` (size); it is covered by the wheelhouse `SHA256SUMS`
   it was built from and by the bundle's own `.sha256` sidecar.
