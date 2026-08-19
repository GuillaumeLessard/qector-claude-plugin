# Privacy Notice

Effective date: 2026-08-17

The canonical online privacy policy is <https://qector.store/privacy>. This repository notice describes the behavior of the QECTOR Claude plugin package. It does not replace the privacy terms of Anthropic, Claude, or a hosting provider.

## Local Plugin Mode

- The library MCP server is local stdio software and does not upload syndromes, parity matrices, circuits, credentials, or artifacts.
- The `SessionStart` hook prints a local runtime banner only.
- The `PostToolUse` hook records the local QECTOR tool name and timestamp for local audit logging. It does not record tool arguments or result payloads.
- Threshold artifacts are written device-locally to a location selected by the user.
- Zero network egress is enforced across all decoder and mathematical routines.

## Contact

For privacy questions or requests concerning QECTOR-operated services, contact <admin@qector.store>. The canonical policy and any updated retention details are maintained at <https://qector.store/privacy>.
