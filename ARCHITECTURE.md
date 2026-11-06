# Architecture

QECTOR separates tool access by stability and privilege, and in 2.0.0 adds a
control plane that every default install goes through.

```
Claude Code / Claude Desktop ──stdio──▶ mcp/mcp_server_secure.py (qector-secure)
                                         │  qector_airgap      guards: sockets, urllib, subprocess, env scrub
                                         │  qector_mcp_contract validate_arguments ▸ dispatch ▸ validate_envelope
                                         │  qector_integrity   INTEGRITY.json at startup
                                         │  qector_audit       hash-chained JSONL (optional)
                                         ├─ mcp_server_library.py      8 stable tools   (always)
                                         ├─ control tools              4               (always)
                                         └─ mcp_server_qector_bench.py 29 research tools (--profile research)
                                 mcp/qector_mcp_compat.py adapts mcp 1.x and 2.x
```

| Surface | Server | Default | Tools | Purpose |
| --- | --- | --- | --- | --- |
| Secure | `qector-secure` (`--profile safe`) | **Yes** | 12 | Verified decode, code construction, threshold sweep, runtime information, plus `airgap_status`, `integrity_check`, `schema_catalog`, `audit_log_status` |
| Secure research | `qector-secure --profile research` | No | 41 | Adds the 29 provisional tools behind the same control plane (`research_compat_report` alias avoids a name clash) |
| Stable (standalone) | `qector-library` | legacy | 8 | Same math, same validation and air-gap guard, no control plane |
| Research (standalone) | `qector-research` | No | 29 | Methodology, DEM, code inspection, reproducibility, hardware probes, evidence layer |
| Admin | `qector-admin` | No | 3 | Dependency setup (offline wheelhouse in air-gapped mode), Desktop configuration, approved Workbench probe; only server allowed to launch processes |

Claude Code enables only `qector-secure`. Claude Desktop's MCPB extension
runs `mcp/mcp_server_secure.py --profile safe` with
`QECTOR_INTEGRITY_STRICT=1`; `mcp/mcp_server_desktop.py` is a shim that keeps
1.x configurations working under the `qector-desktop-mcp` name.

## Modules

| Module | Responsibility |
| --- | --- |
| `mcp/qector_mcp_compat.py` | Construct MCP models with wire names, register handlers on either SDK generation, run stdio |
| `mcp/qector_mcp_contract.py` | Envelope 2.0, closed error-code set, call budgets and rate limit, Draft 2020-12 validation in and out, `apply_tool_contract` |
| `mcp/qector_schemas.py` | Typed `result` schema for every tool; exported to `schemas/` |
| `mcp/qector_airgap.py` | Process guards and the honest `airgap_status` report |
| `mcp/qector_audit.py` | Hash-chained audit log and `verify_chain` |
| `mcp/qector_integrity.py` | `INTEGRITY.json` build/verify |
| `mcp/mcp_server_library.py` | The eight stable tools and `family_health` |
| `mcp/mcp_server_qector_bench.py` | The 29 research tools and the admin tool implementations |
| `mcp/mcp_server_admin.py` | Privileged gate (`QECTOR_ADMIN_ENABLED=1` + `confirm=true`) |
| `mcp/mcp_server_secure.py` | Composition root: configure → guards → integrity → audit → tools |

Every response uses the `QECTORToolResult` envelope. The envelope separates
runtime verification, reference-only results, measurements and errors so
agents do not inflate a claim beyond its evidence; the output schema makes
that separation machine-checkable.
