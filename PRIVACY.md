# Privacy Notice

Effective date: 2026-08-17

The canonical online privacy policy is
<https://qector.store/privacy>. This repository notice describes the behavior
of the QECTOR Claude plugin package. It does not replace the privacy terms of
Anthropic, Claude, a hosting provider, or a separately operated connector.

## Local plugin mode

- The library MCP server is local stdio software and does not intentionally
  upload syndromes, parity matrices, circuits, credentials, or artifacts.
- The SessionStart hook prints a local runtime banner only.
- The PostToolUse hook records the local QECTOR tool name and timestamp for
  debugging. It does not record tool arguments or result payloads.
- Threshold artifacts are written to a location selected by the local user.
- The local user controls Python, Claude, operating-system, and dependency
  logs that may exist outside this repository.

## Hosted connector mode

The optional Streamable HTTP connector is deployed and operated by the person
or organization hosting it. Requests, network metadata, reverse-proxy logs,
container logs, and retained artifacts are controlled by that operator and
their hosting provider. The connector does not add product analytics or sell
user data. Operators must configure TLS, access controls, retention, and
authentication for their deployment.

When the connector is registered with claude.ai or Cowork, Anthropic's service
terms and privacy documentation also apply to that hosted session.

## Contact

For privacy questions or requests concerning QECTOR-operated services, contact
<admin@qector.store>. The canonical policy and any updated retention details
are maintained at <https://qector.store/privacy>.
