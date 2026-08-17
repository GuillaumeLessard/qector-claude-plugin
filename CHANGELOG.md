# Changelog

All notable changes to this project are documented in this file.

This is a Claude Code plugin / claude.ai skill bundle built for
`qector-decoder-v3==1.0.0`.

## [1.0.0] - 2026-08-17

Initial release.

### Added

- **24 skills**: 8 QECTOR domain skills grounded in the reference-manual
  contract (`qector-core`, `qector-math-foundations`, `qector-researcher`,
  `qector-developer`, `qector-sysadmin`, `qector-hardware-engineer`,
  `qector-educator`, `run-qector`) plus 16 official Anthropic skills.
- **5 specialized agents**: researcher, developer, validator, sysadmin,
  hardware engineer.
- **3 reproducible commands**: `qec-facts`, `qec-threshold-sweep`,
  `qec-validate-mcp`.
- **Local stdio MCP server** (`mcp/mcp_server_library.py`) exposing exactly
  eight tools with explicit schemas and fail-closed error handling.
- **Hosted connector kit** (`mcp/connector/`): Streamable HTTP MCP endpoint
  with `/health`, optional bearer auth, and a Docker image.
- **Distribution**: GitHub marketplace (`qector@qector-tools`), local
  `--plugin-dir` execution, and prebuilt upload archives in `dist/` with
  `.sha256` sidecars.
- **Legal documents**: proprietary plugin license in `LICENSE.md` and privacy
  notice in `PRIVACY.md`, with third-party terms preserved separately.

### Verified-API doctrine

- Only the eight MCP tools form the stable contract.
- Verified-but-non-frozen wheel surfaces (`rest_api` HTTP routes, gRPC,
  metrics, mmap, decoder pool) are real but labelled provisional in the skill
  documentation. Historical Workbench MCP source is not present in the
  shipped wheel and is not part of the stable contract.
- No invented APIs; every documented symbol is verified against the published
  wheel before it ships.
