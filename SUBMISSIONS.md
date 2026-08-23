# MCP Directory Submissions — QECTOR Claude Plugin

This file tracks every public directory and registry where the QECTOR
Claude Plugin v1.0.4 has been published or is queued for submission. It
is the single source of truth for "where is QECTOR listed?".

## Live (active, public)

| Directory | Identifier | URL | Method | Status | First published |
|:----------|:-----------|:----|:-------|:-------|:----------------|
| Official MCP Registry | `io.github.GuillaumeLessard/qector-desktop` | https://registry.modelcontextprotocol.io/v0/servers?search=GuillaumeLessard | `mcp-publisher publish` via CI workflow `.github/workflows/publish-mcp-registry.yml` on tag push | active, `isLatest: true`, `status: "active"` | 2026-08-23 (v1.0.4) |
| GitHub Release | v1.0.4 | https://github.com/GuillaumeLessard/qector-claude-plugin/releases/tag/v1.0.4 | `gh release create` (CI auto-creates on tag push; manually uploaded extra assets) | 9 assets, all SHA-256s match `dist/` | 2026-08-23 |
| PolicyLayer (free `/v0` tier) | `com.policylayer/qector-claude-plugin` | https://policylayer.com/tools/qector-claude-plugin | Picked up automatically by PolicyLayer's periodic re-scan of the public GitHub repo | Tracked; will refresh on next re-scan cycle (currently shows v1.0.2 snapshot) | 2026-08-20 (catalog entry) |
| Glama (mirror) | `qector-claude-plugin` | https://glama.ai/mcp/servers | Mirrors the official MCP Registry; picked up automatically | Auto-mirrored from the Registry | 2026-08-23 |
| mcp.so (mirror) | `qector-claude-plugin` | https://mcp.so/ | Mirrors the official MCP Registry; picked up automatically | Auto-mirrored from the Registry | 2026-08-23 |

## Submitted (PR/issue open, awaiting review)

| Directory | PR/issue | URL | Method | Status |
|:----------|:---------|:----|:-------|:-------|
| awesome-mcp-servers (punkpeye) | PR #12705 | https://github.com/punkpeye/awesome-mcp-servers/pull/12705 | Forked `qectorlab/awesome-mcp-servers`, added one entry to the 🔬 Research section, opened a PR against `punkpeye/awesome-mcp-servers:main` | **PR open**, awaiting maintainer review |

## Queued (not yet submitted — directory closed or waiting for some condition)

| Directory | Why queued | Submission pack | When to submit |
|:----------|:-----------|:----------------|:---------------|
| PulseMCP | PulseMCP is currently closed for submissions per their `/submit` page: *"submissions and changes are temporarily paused. Until mid-August, we are not accepting new MCP server or client submissions."* | [`PULSEMCP_SUBMISSION.md`](PULSEMCP_SUBMISSION.md) | Re-submit as soon as PulseMCP reopens. The submission pack is ready to paste. |

## Optional future directories (no action taken)

| Directory | Notes |
|:----------|:------|
| mcpservers.org | Community list maintained as a GitHub repo. Open a PR if/when the maintainers want a QECTOR entry. |
| Cline MCP marketplace | `cline.bot/mcp-marketplace` — surface via submission form when it's open to local stdio plugins. |
| Cursor directory | Surfaced through in-app MCP browser; auto-populates from npm/PyPI plus manual listings. |
| Anthropic Claude.ai Connectors directory | The Claude Desktop / Claude Code in-app discovery already resolves MCP servers from the official Registry. |

## How to verify the official Registry entry

```bash
curl -s "https://registry.modelcontextprotocol.io/v0/servers?search=GuillaumeLessard" \
  | python -m json.tool
```

Expected (truncated):

```json
{
  "servers": [{
    "server": {
      "name": "io.github.GuillaumeLessard/qector-desktop",
      "title": "QECTOR Quantum Error Correction",
      "version": "1.0.4",
      "websiteUrl": "https://qector.store",
      "packages": [{
        "registryType": "mcpb",
        "identifier": "https://github.com/GuillaumeLessard/qector-claude-plugin/releases/download/v1.0.4/qector-claude-desktop-1.0.4.mcpb",
        "version": "1.0.4",
        "fileSha256": "e1301f88761addaa705408cb055ae8362b07f6d2825483f153104777aeee6a64",
        "transport": { "type": "stdio" }
      }]
    },
    "_meta": {
      "io.modelcontextprotocol.registry/official": {
        "status": "active",
        "isLatest": true
      }
    }
  }],
  "metadata": { "count": 1 }
}
```

## How to verify the PolicyLayer entry

```bash
curl -s "https://api.policylayer.com/v0/servers/qector-claude-plugin" \
  | python -m json.tool
```

The catalog re-scans the public GitHub repo periodically. The free
`/v0` tier is read-only; a re-scan is not triggerable from the client
side. Their paid `/v1` tier adds webhooks + change feed for
faster updates.

## Notes for future maintainers

- The official MCP Registry is the **authoritative** listing; everything else
  is downstream of it.
- `server.json` in the repo root is the source of truth for the Registry
  pointer. `scripts/build_release.py` patches it after every Desktop MCPB
  build so the `fileSha256` and the `identifier` URL stay in sync with
  the actual release asset.
- The CI workflow `.github/workflows/publish-mcp-registry.yml` runs on
  every `v*` tag push. It re-builds the artifacts, re-computes the
  SHA-256, re-patches `server.json`, then publishes via
  `mcp-publisher` (GitHub OIDC).
- If you want to update the Glama entry description, the mcp.so
  description, etc., those mirrors typically re-pull from the official
  Registry within 24 hours of any change. There is no separate
  submission to make.
- PulseMCP reopens "until mid-August" per their own banner; that
  language was on their submit page as of the v1.0.4 cut.
