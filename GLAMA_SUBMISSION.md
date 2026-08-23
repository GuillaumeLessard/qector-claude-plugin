# Glama submission — QECTOR Claude Plugin v1.0.4

## Why Glama

The punkpeye/awesome-mcp-servers maintainer requires every merged
entry to have a live Glama listing. Glama runs an automated check on
each submission: it builds the Dockerfile, starts the server, and
probes the MCP `initialize` and `tools/list` requests. This file is
the submission pack.

The QECTOR plugin is a local, fail-closed stdio MCP server — no HTTP
endpoint of its own. To pass Glama's HTTP probe, the Dockerfile
wraps the stdio library server in `mcp-proxy` (streamable-HTTP
transport from `sparfenyuk/mcp-proxy`). The QECTOR trust zone
(8 stable tools, per-tool call budgets, fail-closed
`H c = s (mod 2)` verification) is unchanged — `mcp-proxy` is a
transport bridge, not a behaviour change.

## Submission URL

`https://glama.ai/mcp/servers` — sign in, then **Submit server**.

## Form fields (paste as-is)

| Form field | Value |
|:-----------|:------|
| **Server name** | `qector-claude-plugin` |
| **Display name** | `QECTOR Claude Plugin` |
| **Short description** (one line for the catalog card) | `Local, fail-closed quantum error correction for Claude Code and Claude Desktop on the qector-decoder-v3 backend. 4 MCP servers / 8 stable + 29 research + 3 admin tools; every syndrome correction is verified against H c = s (mod 2) before being returned. Default operation makes no network request.` |
| **Long description** (full body, see below) | (see below) |
| **Repository URL** | `https://github.com/GuillaumeLessard/qector-claude-plugin` |
| **License** | `Proprietary` (per `LICENSE.md`) |
| **Categories** (multi-select) | `developer-tools`, `ai-and-machine-learning`, `data-science-tools`, `research` |
| **Tags** (free-form) | `quantum-error-correction`, `qec`, `decoder`, `surface-code`, `qldpc`, `mwpm`, `union-find`, `python`, `claude-code`, `claude-desktop`, `local`, `zero-egress`, `fail-closed`, `mcp`, `mcp-server`, `mcp-plugin` |
| **Author / contact** | `admin@qector.store` (Guillaume Lessard / iD01t Productions) |
| **Homepage** | `https://qector.store` |
| **Pricing** | `Free for personal, academic, educational, and non-commercial research. Commercial use requires a paid license (https://qector.store/pricing). 60-day commercial evaluation, creditable against a license.` |
| **Dockerfile** | **(attach `glama/Dockerfile` from this repo as a file upload, OR paste its contents into the Dockerfile field)** — see [`glama/Dockerfile`](glama/Dockerfile) |
| **MCP transport(s) supported** | `stdio` (default install) **and** `streamable-http` (when wrapped via `mcp-proxy`, what Glama probes) |
| **Tool surface (count)** | 8 stable, 29 research, 3 admin = 40 total (Glama will see the 8 stable via the library server probe) |

### Long description (full body)

```
QECTOR Claude Plugin is the official MCP integration of the QECTOR
quantum error correction (QEC) engine for Claude Code and Claude
Desktop, built on qector-decoder-v3==1.0.0 and grounded against the
QECTOR Decoder v3 Reference Manual (DOI 10.5281/zenodo.21941046).

The plugin ships four named MCP servers across three trust zones;
the default install exposes only the eight stable tools. Every
result is verified before it leaves the local server, and the
default operation makes no network request.

Trust zones (40 tools total):
- qector-library     — 8 stable, default-on
- qector-research    — 29 provisional, opt-in
- qector-admin       — 3 privileged, opt-in
- qector-desktop-mcp — 8 stable, the Desktop safe-profile adapter

The Glama probe hits qector-library (the 8-tool stable surface):
list_code_families, list_decoders, get_license_info, decode_syndrome,
decode_single, threshold_sweep, build_code_from_matrix, compat_report.
Every returned syndrome correction is verified against the
parity-check relation H c = s (mod 2) before being returned.

Identification
- name: qector
- display_name: QECTOR Quantum Error Correction
- version: 1.0.4
- license: Proprietary
- author: Guillaume Lessard <admin@qector.store>
- repository: https://github.com/GuillaumeLessard/qector-claude-plugin
- reference manual: 10.5281/zenodo.21941046 (v1.0.0)
- privacy policy: https://qector.store/privacy
- provenance: see dist/provenance.json (git commit + per-artifact hash)

Identification is also pinned in the official MCP Registry as
io.github.GuillaumeLessard/qector-desktop (status: active,
isLatest: true).

This Dockerfile wraps the stdio library server in
sparfenyuk/mcp-proxy over the streamable-http transport. The
QECTOR trust zone is preserved — the proxy is a transport bridge,
not a behaviour change. Tools that mutate (`configure_claude_desktop`,
`workbench_probe`, etc.) live on the admin server, which is not
exposed here.
```

## Dockerfile

The Dockerfile to attach is at [`glama/Dockerfile`](glama/Dockerfile)
in this repo. It:

1. Uses `python:3.12-slim` as the base
2. Pins `mcp==1.26.0` and `qector-decoder-v3[stim]==1.0.0` (the
   versions QECTOR is tested against)
3. Installs `mcp-proxy` from `sparfenyuk/mcp-proxy@v0.12.0` (the
   streamable-HTTP bridge)
4. Copies only the two files Glama needs:
   `mcp/mcp_server_library.py` and `mcp/qector_mcp_contract.py`
5. Runs `mcp-proxy --host 0.0.0.0 --port 8080
   --transport streamablehttp -- python
   /app/mcp/mcp_server_library.py`

Glama will:
- Build the image
- Start it with port 8080 exposed
- POST `initialize` to `http://<container>:8080/mcp`
- POST `tools/list` to the same endpoint

If those two calls return valid MCP JSON-RPC 2.0 envelopes with the
expected server identity and the 8 stable tools listed, Glama
publishes the entry.

### Build locally to verify

```bash
docker build -f glama/Dockerfile -t qector-claude-plugin:1.0.4 .
docker run --rm -p 8080:8080 qector-claude-plugin:1.0.4
# in another shell:
curl -X POST http://127.0.0.1:8080/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":1,"method":"initialize",
       "params":{"protocolVersion":"2025-03-26",
                "capabilities":{},
                "clientInfo":{"name":"probe","version":"0"}}}'
```

The response should include the server identity:
`name: "qector-library"`, `version: "1.0.4"`.

Then:

```bash
curl -X POST http://127.0.0.1:8080/mcp \
  -H 'Content-Type: application/json' \
  -H 'Accept: application/json, text/event-stream' \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list"}'
```

The response should list the 8 stable tools:
`build_code_from_matrix`, `compat_report`, `decode_single`,
`decode_syndrome`, `get_license_info`, `list_code_families`,
`list_decoders`, `threshold_sweep`.

## What lands on the awesome-mcp-servers PR

The punkpeye/awesome-mcp-servers maintainer asked for the README
entry to include a Glama score badge. Once Glama publishes the
entry, the badge URL is:

```
https://glama.ai/mcp/servers/GuillaumeLessard/qector-claude-plugin/badges/score.svg
```

The README line in the upstream PR will be amended to:

```markdown
- [GuillaumeLessard/qector-claude-plugin](https://github.com/GuillaumeLessard/qector-claude-plugin) [![GuillaumeLessard/qector-claude-plugin MCP server](https://glama.ai/mcp/servers/GuillaumeLessard/qector-claude-plugin/badges/score.svg)](https://glama.ai/mcp/servers/GuillaumeLessard/qector-claude-plugin) 🐍 🏠 🍎 🪟 🐧 - Local, fail-closed quantum error correction for Claude Code and Claude Desktop on the `qector-decoder-v3` backend. 4 MCP servers / 8 stable + 29 research + 3 admin tools; every syndrome correction is verified against `H c = s (mod 2)` before being returned. Default operation makes no network request. Install: `claude plugin marketplace add GuillaumeLessard/qector-claude-plugin && claude plugin install qector@qector-tools`.
```

(The badge will render as "?" or "N/A" until Glama computes the
score, but the link works the moment the page is live.)

## Submission checklist

- [x] Dockerfile builds locally with `docker build -f glama/Dockerfile -t qector-claude-plugin:1.0.4 .`
- [x] Container starts on port 8080 and exposes `/mcp`
- [x] `initialize` returns the qector-library server identity at version 1.0.4
- [x] `tools/list` returns the 8 stable tools
- [x] `mcp_server_library.py` is the same code that ships in the public plugin zip
- [x] No proprietary source files in the build context
- [x] No outbound network in the running container
- [x] Identification block in SECURITY.md on the public repo
- [x] PR for punkpeye/awesome-mcp-servers is updated with the Glama badge once Glama publishes the entry
