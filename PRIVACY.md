# Privacy Notice

Effective date: 2026-11-02

The canonical online privacy policy is <https://qector.store/privacy>. This
repository notice describes the QECTOR Claude plugin package only; it does not
replace Anthropic, Claude, operating-system, or hosting-provider terms.

## Default Local, Air-Gapped Operation

- `qector-secure` (the Claude Code and Claude Desktop default) and every
  standalone server run over local stdio only. No listening socket is opened.
- No network request is made by default. In air-gapped mode
  (`QECTOR_AIR_GAPPED` unset or `1`, the default) the public Python socket
  entry points refuse non-loopback endpoints and the opt-in PyPI check
  returns `pypi_freshness.status: "disabled"` without attempting a
  connection. This is an in-process guard, not a sandbox; see AIRGAP.md
  for the host controls a hard guarantee needs.
- Syndromes, parity matrices, circuits, tool arguments, and artifacts are not
  uploaded by the QECTOR plugin.
- Session hooks write only a local tool name and timestamp to
  `<per-user data dir>/claude_plugin_usage.log` (`QECTOR_DATA_DIR` relocates
  it); they do not record tool arguments or result payloads. The session-start
  hook reads `QECTOR_EXE` only to report whether a Workbench executable is
  configured.
- Threshold artifacts and SHA-256 evidence remain on the local device under
  the configured artifact directory (default: the per-user data directory).
- The optional audit log (`QECTOR_AUDIT_DIR`, off by default) stores the tool
  name, timestamps, status, error code, elapsed time and **SHA-256 digests**
  of the arguments and of the result envelope. It never stores arguments or
  results themselves.

## Explicit Opt-In Network Check

Only when the operator sets `QECTOR_AIR_GAPPED=0` (or starts the secure server
with `--allow-network`), `compat_report`, `research_compat_report`,
`env_block` and `get_runtime_provenance` with `check_pypi=true` may make one
outbound HTTPS request per process to:

```text
https://pypi.org/pypi/qector-decoder-v3/json
```

The request checks the published package version only. It does not send QEC
workload data, matrices, syndromes, artifacts, credentials, or tool results.

## Decoder Backend Disclosure

The `qector-decoder-v3` wheel contains an explicit, never-automatic usage
metering function that would contact Stripe's billing API if a licence holder
called it with their own credentials. The plugin never calls it, removes the
credentials it would read (`STRIPE_SECRET_KEY`, `QECTOR_STRIPE_CUSTOMER_ID`,
`QECTOR_LICENSE_PRIVATE_KEY_B64`, …) from the server process, and reports the
situation through the `airgap_status` tool. See SECURITY.md and AIRGAP.md.

## Administrative Surface

`qector-admin` is disabled unless `QECTOR_ADMIN_ENABLED=1` is set in its local
server environment. It can install fixed dependency profiles (from an offline
wheelhouse when air-gapped), change local Claude Desktop configuration, or
launch a user-approved Workbench binary. Each operation also requires
`confirm=true`. These are local system actions, not telemetry or remote
processing.

## Contact

For privacy questions concerning QECTOR-operated services, contact
<admin@qector.store>.
