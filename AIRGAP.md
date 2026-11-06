# Air-gapped and laboratory deployment

This guide takes a QECTOR 2.0.1 install from a connected build host to a
machine with no network, verifies it, and explains exactly what the
in-process guards do and do not guarantee.

## 1. On the connected build host

```bash
git clone https://github.com/GuillaumeLessard/qector-claude-plugin.git
cd qector-claude-plugin
python -m venv .venv && . .venv/bin/activate
python -m pip install -r requirements.lock

# Run the full gate set (all must pass)
python scripts/release_validate.py
python scripts/validate_source.py
python scripts/export_schemas.py --check
python scripts/generate_integrity_manifest.py --check
QECTOR_SILENT=1 python -m unittest discover -s tests -v

# Build the wheelhouse for the lab target (examples)
python scripts/build_wheelhouse.py --out wheelhouse-linux   # same platform as this host
python scripts/build_wheelhouse.py --out wheelhouse-win --platform win_amd64 --python-version 3.12
python scripts/build_wheelhouse.py --out wheelhouse-mac --platform macosx_14_0_arm64 --python-version 3.12

# Build the release archives (deterministic; INTEGRITY.json inside each)
python scripts/build_release.py --all
# Optional: a Desktop bundle with the runtime vendored into server/lib
python scripts/build_release.py --desktop --bundle-lib wheelhouse-linux
```

Carry to the lab: `dist/qector-claude-plugin-2.0.1.zip` (Claude Code) or
`dist/qector-claude-desktop-2.0.1*.mcpb` (Claude Desktop), the matching
`wheelhouse-*` directory, `dist/SHA256SUMS` and `dist/SHA256SUMS.sig`.
Write the signing-key fingerprint from SECURITY.md
(`6726953ded0a01a4a15cc92d460178f71aa2568c59ee969fc4efe8812c8299dc`) in the lab notebook from an independent source
(the published SECURITY.md or the Sigstore log), not from the USB stick.

## 2. On the air-gapped lab machine

```bash
sha256sum -c SHA256SUMS                       # archives
python3 scripts/sign_release.py --verify . --pubkey kYwkMApz4zMgQmJsOya1UZuByvnuikzlxQkQiA8NOJg=   # origin (run from the extracted source archive)
unzip qector-claude-plugin-source-2.0.1.zip -d qector   # the source archive carries the full gate set incl. tests/;
# the plugin zip (what Claude Code installs) carries everything except tests/ and .github/
cd qector
sh scripts/install_offline.sh /media/usb/wheelhouse-linux ./.venv-qector
# Windows: powershell -ExecutionPolicy Bypass -File scripts\install_offline.ps1 -Wheelhouse D:\wheelhouse-win
```

The installer verifies every wheel against the wheelhouse `SHA256SUMS`,
creates a virtual environment, installs with `pip --no-index --find-links`,
runs `scripts/qector_runtime_check.py` and checks `INTEGRITY.json`.

Point the launcher at the environment: set `QECTOR_PYTHON` to the venv's
interpreter (the `.mcp.json` / Desktop manifest route every start through
`scripts/qector-python`, which honours `QECTOR_PYTHON` first).

## 3. Configure the host (required for a hard guarantee)

The Python-level guard in `mcp/qector_airgap.py` makes the public Python
network and process-launch entry points fail closed. It is defence in depth
against the tool surface, not a sandbox: code already executing in the
process could still use the private `_socket` module, `ctypes` or
`os.fork`+`os.exec*`, and the decoder wheel's **native Rust core** has its
own TLS client (for an explicit, never-called metering function) that
Python cannot intercept. Therefore:

- run on a host with no default route, or in a network namespace without
  egress, or with a firewall rule denying outbound TCP from the interpreter;
- never set `QECTOR_AIR_GAPPED=0` or pass `--allow-network`;
- do not register `qector-admin` on lab machines (it is the only server
  allowed to launch processes; its `system_setup` needs `offline_wheelhouse`
  anyway);
- keep `QECTOR_INTEGRITY_STRICT=1` (the default; only `--no-strict-integrity` / `=0` on a development tree lifts it);
- set `QECTOR_INTEGRITY_PUBKEY=kYwkMApz4zMgQmJsOya1UZuByvnuikzlxQkQiA8NOJg=` so every start also proves the archive's origin, not only its consistency.

## 4. Verify from the client

Ask Claude to call the control-plane tools and read the structured result:

| Tool | Expect |
|:-----|:-------|
| `airgap_status` | `air_gapped: true`, `guards.python_socket: true`, `guards.python_subprocess: true`, `guards.pypi_freshness: "disabled"`, `backend_network_surface.called_by_plugin: false` |
| `integrity_check` | `passed: true`, `mismatched: []`, `missing: []`, `signature.valid: true` with `source: "pinned"` when `QECTOR_INTEGRITY_PUBKEY` is set, envelope `status: "verified"` |
| `compat_report` with `check_pypi: true` | `pypi_freshness.status: "disabled"`, a warning that no connection was attempted |
| `schema_catalog` | one entry per tool; record `catalog_sha256` in the lab notebook |
| `audit_log_status` | `enabled: true` when `QECTOR_AUDIT_DIR` is set; `chain_valid: true` |

From a shell, the same over raw stdio:

```bash
printf '%s\n' \
 '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"lab","version":"1"}}}' \
 '{"jsonrpc":"2.0","method":"notifications/initialized"}' \
 '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"airgap_status","arguments":{}}}' \
 | QECTOR_SILENT=1 ./scripts/qector-python mcp/mcp_server_secure.py --profile safe
```

## 5. Audit log

Set `QECTOR_AUDIT_DIR` (or the Desktop `audit_dir` user setting). Each
tool call appends one JSON line to `<dir>/qector-secure-mcp.audit.jsonl`:

```json
{"sequence":1,"timestamp_ns":...,"server":"qector-secure-mcp","server_version":"2.0.1",
 "tool":"decode_syndrome","arguments_sha256":"...","status":"verified","error_code":null,
 "envelope_sha256":"...","elapsed_ms":0.9,"previous_sha256":"000...0","record_sha256":"..."}
```

Arguments are never stored; only their SHA-256 is (low-entropy arguments
such as `{"distance": 3}` are therefore dictionary-reversible; the digest
binds the record to the call, it does not hide it). `record_sha256` covers
every other field including `previous_sha256`, so editing, deleting or
reordering a line inside the chain is detected by `audit_log_status`
(`chain_valid: false`, `first_invalid_sequence`), and the running server
also detects truncation of the tail because it compares the file with the
head it wrote (`matches_server_head`). What a keyless chain cannot detect
is a whole-file rewrite by the same user after the server has exited. Set
`QECTOR_AUDIT_HMAC_KEY_FILE` to a file holding ≥32 secret bytes kept off the
host (digests become HMAC-SHA256; `keyed: true`), and anchor `head_sha256`
in a WORM store or lab notebook at the end of each session. The schema is
published as `schemas/audit-record.schema.json`.

## 6. Evidence artifacts

`threshold_sweep` writes `<QECTOR_ARTIFACT_DIR>/<name>.json` and a
`.sha256` sidecar. The default root is the per-user data directory
(`%LOCALAPPDATA%\QectorClaudePlugin\artifacts`,
`~/Library/Application Support/QectorClaudePlugin/artifacts`,
`$XDG_DATA_HOME/qector-claude-plugin/artifacts`), never the install
directory. Requested paths that resolve outside the root are refused.

## 7. What the guards cannot do

- Act as a sandbox: they wrap the public Python entry points reachable
  from the tool surface, not `_socket`, `ctypes` or `os.fork`+`os.exec*`.
- Block the wheel's native networking if one of its own functions were
  called (the plugin never calls them; see SECURITY.md).
- Protect against an attacker who can rewrite `INTEGRITY.json` together
  with the code (sign the release assets; see THREAT_MODEL.md). Note also
  that the control-plane modules run before they can verify themselves;
  the decoder-facing modules are imported only after the gate passes.
- Make the audit log write-once at the filesystem level, or prove a
  keyless log was not rewritten after the server exited (use the HMAC key
  and external anchoring above).
