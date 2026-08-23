# Privacy Notice

Effective date: 2026-08-21

The canonical online privacy policy is <https://qector.store/privacy>. This
repository notice describes the QECTOR Claude plugin package only; it does not
replace Anthropic, Claude, operating-system, or hosting-provider terms.

## Default Local Operation

- `qector-library` and the Claude Desktop safe profile run over local stdio.
- No network request is made by default.
- Syndromes, parity matrices, circuits, tool arguments, and artifacts are not
  uploaded by the QECTOR plugin.
- Session hooks write only a local tool name and timestamp; they do not record
  tool arguments or result payloads.
- Threshold artifacts and SHA-256 evidence remain on the local device under
  the configured artifact directory.

## Explicit Opt-In Network Check

`compat_report(check_pypi=true)` and
`env_block(check_pypi=true)` may make one outbound HTTPS request to:

```text
https://pypi.org/pypi/qector-decoder-v3/json
```

The request checks the published package version only. It does not send QEC
workload data, matrices, syndromes, artifacts, credentials, or tool results.
The response is cached for the server process. Do not call either option in a
strictly air-gapped environment.

## Administrative Surface

`qector-admin` is disabled unless `QECTOR_ADMIN_ENABLED=1` is set in its local
server environment. It can install fixed dependency profiles, change local
Claude Desktop configuration, or launch a user-approved Workbench binary. Each
operation also requires `confirm=true`. These are local system actions, not
telemetry or remote processing.

## Contact

For privacy questions concerning QECTOR-operated services, contact
<admin@qector.store>.
