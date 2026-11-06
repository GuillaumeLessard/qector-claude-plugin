# Proposal to Anthropic — QECTOR as a reviewed, air-gapped scientific MCP server

**From:** Guillaume Lessard, iD01t Productions (<admin@qector.store>)
**Subject:** QECTOR Claude Plugin 2.0.1 — request for review and inclusion;
offer to collaborate on a verifiable-science MCP profile
**Artifacts:** `qector-claude-plugin-2.0.1.zip`,
`qector-claude-desktop-2.0.1.mcpb`, `qector-claude-plugin-source-2.0.1.zip`,
`SHA256SUMS`, `INTEGRITY.json`, SPDX SBOM, `schemas/`

## 1. What this is

QECTOR is a local MCP integration of a quantum-error-correction decoder
(`qector-decoder-v3==1.0.1`, Rust/PyO3) for Claude Code and Claude Desktop.
Its purpose is narrow and checkable: decode syndromes, build codes, run
threshold sweeps, and return results whose correctness class is explicit.
Every correction is verified against `H c = s (mod 2)` in-process before it
is returned; every logical-error rate carries a 95 % Wilson interval and a
SHA-256-hashed artifact. The mathematics is grounded in a published
reference manual (DOI 10.5281/zenodo.21941046) whose sixteen theorems have
executable proof obligations in `tests/test_reference_manual_math.py`.

## 2. What 2.0.0 does that most MCP servers do not

| Property | Mechanism | How a reviewer checks it in five minutes |
|:---------|:----------|:-----------------------------------------|
| Air-gapped by default | Public Python entry points (`socket`, `getaddrinfo`, `create_connection`, `urlopen`, `subprocess.Popen`, `os.system`/`popen`/`spawn*`) fail closed for non-loopback endpoints; billing env vars scrubbed; PyPI check returns `disabled`. Stated as defence in depth, not a sandbox | call `airgap_status` (read `guard_scope`); call `compat_report` with `check_pypi: true` and observe `disabled` with no connection; `strings` the wheel and compare with `backend_network_surface` |
| Schema-validated both ways | Draft 2020-12 validation of arguments **and** of the finished envelope; 91 committed schema files; `CONTRACT_VIOLATION` instead of malformed output | send `{"syndrome":[0,2,0,0]}` → `INVALID_INPUT` at `$.syndrome[1]`; `scripts/export_schemas.py --check` |
| Integrity-checked | `INTEGRITY.json` (SHA-256 of all runtime files) verified at startup; strict mode refuses a modified tree | edit one byte of `mcp/mcp_server_secure.py`, restart → exit code 3 |
| Audited | hash-chained JSONL, argument digests only, optional HMAC key, truncation detected by the running server | set `QECTOR_AUDIT_DIR`, call tools, call `audit_log_status`; edit or truncate the file and watch `chain_valid` go false |
| Bounded | per-tool call budgets, 600 calls/min, 2 MiB request cap, size ceilings on every array | loop a tool → `RESOURCE_LIMIT` |
| Honest result classes | `verified` / `measured` / `reference_only` / `not_checked` / `error`, with `verification.checks` naming the theorem that ran | `decode_single` on a family without logicals → `logical_failure: null` and a warning, never a fabricated rate |
| Honest about the backend | the wheel's native TLS client and Stripe endpoint are disclosed; degenerate wheel constructions are refused; the wheel's distance labels are checked by a bounded minimum-logical-weight search and contradicted when wrong | `list_code_families` → `color_code.health.status == "degenerate"`; `code_distance_check(rotated_surface, 5)` → `verdict: "contradicted"`, `effective_distance.min_logical_weight == 2` |
| Two SDK generations | `mcp>=1.30,<3`, identical wire output | CI matrix; `provenance.mcp_sdk` in every envelope |
| Reproducible, signed releases | deterministic builder that refuses a dirty tree, `RELEASE_COMMIT` in every archive, hashed `requirements.lock`, SPDX SBOM with per-package checksums, Ed25519 `INTEGRITY.json.sig` / `SHA256SUMS.sig` (fingerprint published in SECURITY.md), Sigstore transparency entry from the release workflow | rebuild from the *source zip* → identical `SHA256SUMS`; `sign_release.py --verify dist --pubkey <key>` |
| Stdio only | no HTTP/SSE/WebSocket code path in the package | `grep -r streamable_http mcp/` returns nothing |

Everything above is enforced by code shipped in the archive and covered by
the test suite (unit, contract and live-stdio conformance) that runs on
Python 3.10–3.13 against both SDK generations. There are no placeholders, no
mock results and no "coming soon" tools.

## 3. What we are asking

1. **Review and listing** of `qector` in the Anthropic plugin directory
   (community, and official at Anthropic's discretion) and of
   `io.github.GuillaumeLessard/qector-desktop` in the MCP Registry, with
   the 2.0.1 artifacts above. We will pin the submission to the release
   commit and keep the nightly-sync branch identical to it.
2. **A feedback loop with the plugin/MCP review team** on three things we
   believe are generally useful and would like to align with Anthropic's
   direction rather than invent alone:
   - a *verifiable-result envelope* convention (`status` / `claim_class` /
     `verification.checks`) so a model cannot upgrade a measurement into a
     verified fact; our contract 2.0 is one concrete, schema-published
     candidate;
   - an *air-gap posture* that a client can query and a reviewer can test
     (`airgap_status`-style control-plane tools), including the honest
     reporting of native-code network surfaces that Python guards cannot
     intercept;
   - a *per-archive integrity manifest + signed release* pattern for MCPB
     bundles and plugins (Ed25519 detached signatures plus a Sigstore
     transparency entry are shipped today); we would like to know which
     format Anthropic's tooling prefers to consume.
3. **Optional technical collaboration** on a reference "scientific MCP
   server" profile for regulated laboratories (no egress, audited,
   schema-validated), with QECTOR as the first worked example and the test
   suite as a reusable harness.

## 4. What we are not claiming

- We do not claim portable performance numbers; `measured` results are
  single-machine samples by construction and say so.
- We do not claim the Python-level guard is a sandbox or that it blocks
  the decoder wheel's compiled TLS client; we say what it wraps (the
  public Python entry points reachable from the tool surface), what it
  does not (`_socket`, `ctypes`, `os.fork`+`exec`, native code), and we
  require a host egress control for a hard guarantee (AIRGAP.md,
  THREAT_MODEL.md).
- We do not claim the keyless audit chain resists a same-user rewrite
  after the server exits; the HMAC option and external anchoring are
  documented for that.
- We do not claim an archive's embedded signature proves origin on its
  own; only a key pinned out-of-band (fingerprint in SECURITY.md, Sigstore
  log) does, and the server reports which of the two it checked.
- We do not claim the `INTEGRITY.json` manifest resists an attacker who
  can rewrite both manifest and code; release signing is the next step
  and we would welcome guidance on the format Anthropic prefers.
- The decoder backend is proprietary and source-available; the plugin,
  its skills, agents, commands, contract, schemas and tests are fully
  inspectable in the source archive, which contains the complete tree. Commercial use of the backend requires a licence from
  qector.store; research and personal use are free.

## 5. How to reproduce our verification

`REVIEWER_GUIDE.md` in every archive is the ten-minute version of this section with expected outputs.

```bash
unzip qector-claude-plugin-source-2.0.1.zip -d qector && cd qector
python -m venv .venv && . .venv/bin/activate
python -m pip install -r requirements.lock
python scripts/release_validate.py && python scripts/validate_source.py
python scripts/export_schemas.py --check && python scripts/generate_integrity_manifest.py --check
QECTOR_SILENT=1 python -m unittest discover -s tests -v
python mcp/tests/test_mcp_stdio.py
python -m pip install "mcp>=2,<3" && QECTOR_SILENT=1 python -m unittest discover -s tests   # second SDK generation
python scripts/build_release.py --all && python scripts/validate_plugin_bundle.py
sha256sum -c dist/SHA256SUMS
python scripts/sign_release.py --verify <dir with the published archives> --pubkey kYwkMApz4zMgQmJsOya1UZuByvnuikzlxQkQiA8NOJg=
```

## 6. Contact and commitments

- Security contact: <admin@qector.store>; acknowledgement within 72 hours,
  high-severity fix target 30 days (SECURITY.md).
- We will track the MCP specification and the `mcp` SDK; the compat layer
  is designed so the next SDK major can be added without touching tool
  code.
- We will keep the schema catalog, integrity manifest and lockfile as
  release-blocking CI gates, so the artifact Anthropic reviews is the
  artifact users install.

Guillaume Lessard
iD01t Productions — QECTOR
