# QECTOR for Claude Desktop

This extension runs the QECTOR secure server (`mcp/mcp_server_secure.py
--profile safe`): eight stable tools for code discovery, decoder discovery,
licence inspection, verified decoding, threshold sweeps, matrix validation and
compatibility reporting, plus four control-plane tools (`airgap_status`,
`integrity_check`, `schema_catalog`, `audit_log_status`).

Decoded corrections are fail-closed: QECTOR returns them only after verifying
`H c = s (mod 2)`. Threshold results include Wilson 95% intervals and hashed
artifact metadata. Every request and response is validated against JSON
Schema 2020-12.

The server is air-gapped by default and uses local stdio only: non-loopback
sockets, subprocess launches and the opt-in PyPI check are refused inside the
process, and the bundled `INTEGRITY.json` is verified at every start. Set the
optional audit-log directory to keep a hash-chained record of tool calls.

The 29-tool research profile and 3-tool administrative profile are not
included in this extension. Configure them as separate Developer MCP servers
only after reviewing `SECURITY.md` and `MCP_API.md`.
