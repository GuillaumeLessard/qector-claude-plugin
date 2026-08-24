# Anthropic Marketplace Submission — QECTOR Claude Plugin v1.0.6

## Two Anthropic marketplaces — choose both

| Marketplace | What it is | Submission flow | Our status |
|:------------|:-----------|:----------------|:-----------|
| **`anthropics/claude-plugins-official`** | "Official, Anthropic-managed directory of high quality Claude Code Plugins." | Inclusion is **at Anthropic's discretion** (per the official docs). No self-serve form. Discovery via `/plugin > Discover` and `claude.com/plugins`. | Not yet submitted. Action below. |
| **`anthropics/claude-plugins-community`** | "Community-contributed plugins for Claude Cowork and Claude Code." Every entry has passed Anthropic's automated validation and safety screening, synced nightly. Each plugin is pinned to a specific commit SHA. | Self-serve via **`https://clau.de/plugin-directory-submission`** (in-app form on `claude.ai`). | **Ready to submit.** Full payload below. |

Submission URL for the community marketplace:
**https://clau.de/plugin-directory-submission**

Install commands once published:

```bash
claude plugin marketplace add anthropics/claude-plugins-community
claude plugin install qector@claude-community
```

---

## 1. Community marketplace submission — ready to paste

The `clau.de/plugin-directory-submission` form is an in-app form on
`claude.ai`. Below is the complete payload to paste. The form's
fields map 1-to-1 to the values below; the `source.sha` is the
current `main` HEAD of the QECTOR repo (the marketplace syncs
nightly, so re-pinning happens on its own after each new release).

### Form fields

| Form field | Value |
|:----------|:------|
| **Plugin name** | `qector` |
| **Short description** | (see below; keep under 280 chars for the discover card) |
| **Long description** | (full body, see below) |
| **Repository URL** | `https://github.com/GuillaumeLessard/qector-claude-plugin` |
| **Git clone URL** (used to pin the SHA) | `https://github.com/GuillaumeLessard/qector-claude-plugin.git` |
| **Pinned commit SHA** (the form asks for a specific SHA; this is the current main HEAD) | `45372d9599eb5c841dcbe07394d8a0fa702f9a7d` |
| **Homepage** | `https://github.com/GuillaumeLessard/qector-claude-plugin` |
| **Category** | `development` (QEC is a research / dev-tools surface; the marketplace's allowed categories are `development`, `productivity`, `security`, `database`, `testing`, `learning`) |
| **Author name** | `Guillaume Lessard` |
| **Author email** | `admin@qector.store` |
| **Author website** | `https://qector.store` |
| **License** | `Proprietary` |
| **Pricing** | Free for personal, academic, educational, and non-commercial research; commercial use requires a paid license. |

### Short description (≤ 280 chars)

```
Local, fail-closed quantum error correction for Claude Code and Claude
Desktop on the qector-decoder-v3 backend. 4 MCP servers / 8 stable +
29 research + 3 admin tools; every syndrome correction is verified
against H c = s (mod 2) before being returned. Zero network by default.
```

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

- qector-library — 8 stable tools (default): list_code_families,
  list_decoders, get_license_info, decode_syndrome, decode_single,
  threshold_sweep, build_code_from_matrix, compat_report. Every
  result is checked against the parity-check relation H c = s (mod 2)
  before being returned.

- qector-research — 29 provisional tools (opt-in): Wilson 95% CI
  tables, DEM inspection, code-family introspection, hardware
  probes, micro-benchmarks, theorem and glossary lookup, reproduction
  workflows, and the three-tool evidence layer
  (get_capability_matrix, get_evidence_policy, get_runtime_provenance).

- qector-admin — 3 privileged tools (opt-in, QECTOR_ADMIN_ENABLED=1
  required + per-call confirm=true): system_setup,
  configure_claude_desktop, workbench_probe (with SHA-256 approval
  of the launched binary).

- qector-desktop-mcp — 8 stable tools re-exported by the Desktop
  safe-profile adapter.

Per-process call budgets (with QECTOR_MCP_MAX_CALLS_<TOOL> override):
threshold_sweep 8, decode_single 64, decode_syndrome 256,
build_code_from_matrix 32, hot_path_microbench 4, system_setup 2,
configure_claude_desktop 2, workbench_probe 2. Exhaustion returns
RESOURCE_LIMIT.

Identification
- name: qector
- display_name: QECTOR Quantum Error Correction
- version: 1.0.6
- license: Proprietary
- author: Guillaume Lessard <admin@qector.store>
- repository: https://github.com/GuillaumeLessard/qector-claude-plugin
- reference manual: 10.5281/zenodo.21941046 (v1.0.0)
- privacy policy: https://qector.store/privacy
- provenance: see dist/provenance.json (git commit + per-artifact hash)

What this plugin does NOT do
- No outbound network by default. The only network call is the
  explicit opt-in PyPI freshness check
  (compat_report(check_pypi=true) / env_block(check_pypi=true)).
- No eval / exec / dynamic __import__ / importlib on caller input.
  The repository has zero hits for any of these patterns.
- The default 8-tool surface is subprocess-free, file-write-free,
  and network-free.

Install
- Claude Code marketplace: claude plugin marketplace add
  GuillaumeLessard/qector-claude-plugin && claude plugin install
  qector@qector-tools
- Claude Desktop: qector-claude-desktop-1.0.6.mcpb is the artifact
  Claude Desktop's MCP Registry serves automatically. Manual install
  via python scripts/configure_claude_desktop.py --confirm.

Canonical artifacts (v1.0.6)
- qector-claude-plugin-1.0.6.zip          e1660a45... (Claude Code plugin)
- qector-claude-plugin-source-1.0.6.zip   e0e04d94... (public source)
- qector-claude-desktop-1.0.6.mcpb        5b6b4c24... (Desktop safe MCPB)
- qector-claude-plugin-1.0.6.sbom.json    (SPDX-2.3 SBOM)
- SHA256SUMS, provenance.json, per-file .sha256 sidecars
```

### Equivalent JSON (the form's underlying data)

This is what the catalog entry will look like once accepted. The
in-app form serializes to this and the read-only mirror at
`anthropics/claude-plugins-community` syncs it nightly.

```json
{
  "name": "qector",
  "description": "Local, fail-closed quantum error correction for Claude Code and Claude Desktop on the qector-decoder-v3 backend. 4 MCP servers / 8 stable + 29 research + 3 admin tools; every syndrome correction is verified against H c = s (mod 2) before being returned. Zero network by default.",
  "author": {
    "name": "Guillaume Lessard",
    "email": "admin@qector.store"
  },
  "homepage": "https://github.com/GuillaumeLessard/qector-claude-plugin",
  "category": "development",
  "source": {
    "source": "url",
    "url": "https://github.com/GuillaumeLessard/qector-claude-plugin.git",
    "sha": "45372d9599eb5c841dcbe07394d8a0fa702f9a7d"
  }
}
```

> The `source.sha` is the current `main` HEAD as of 2026-08-23.
> Re-pin to the `v1.0.6` release commit (`34eabe720571b3f9daf6bb06ad149c0153687d84`)
> if you want a fixed-version pin. The community marketplace syncs
> nightly and re-pins to the latest `main` HEAD by default.

---

## 2. Official marketplace (Anthropic-curated) — request

`anthropics/claude-plugins-official` has no self-serve form. Inclusion
is at Anthropic's discretion per the docs. The right path is to
email or DM the Anthropic team with this same payload and ask for
inclusion. The key signals the official maintainer looks for:

- Active, public, and well-documented repository
- Identification in `SECURITY.md` (we have this — see the
  Identification block, Trust Boundaries, Tool Risk Classification,
  Static Scanner Notes, and Runtime Dependabot Advisories sections)
- Stable, maintained surface with versioned releases (we have v1.0.1,
  v1.0.2, v1.0.6 with per-artifact SHA-256 sidecars)
- License clearly stated (Proprietary, with a per-tier license
  breakdown in `LICENSE.md` and the QEC backend license in
  `release-manifest.json`)
- No proprietary source files in the public tree (verified — no
  `src/*.rs`)
- Provenance and SBOM at every release (we ship
  `provenance.json`, `qector-claude-plugin-1.0.6.sbom.json`, and
  per-artifact `.sha256` sidecars)
- MCP Registry entry live (we are at
  `io.github.GuillaumeLessard/qector-desktop`, v1.0.6, `active`,
  `isLatest: true`)

**Recommended request email template** (one paragraph, signed):

```
Subject: Inclusion request — QECTOR Claude Plugin v1.0.6

Hi Anthropic team,

I'd like to nominate the QECTOR Claude Plugin
(https://github.com/GuillaumeLessard/qector-claude-plugin, v1.0.6)
for inclusion in anthropics/claude-plugins-official.

QECTOR is a local, fail-closed quantum error correction integration
for Claude Code and Claude Desktop, built on the qector-decoder-v3
backend. 4 MCP servers, 8 stable / 29 research / 3 admin tools; every
syndrome correction is verified against H c = s (mod 2) before
being returned. Default operation is local stdio with no network
request.

- Identification and per-tool risk classification: SECURITY.md
- Per-artifact SHA-256 + provenance + SPDX-2.3 SBOM: every release
- MCP Registry entry: io.github.GuillaumeLessard/qector-desktop
  (active, isLatest:true)
- License: Proprietary; the qector-decoder-v3 backend is free for
  personal, academic, educational, and non-commercial research
- Repo activity: 1.0.1, 1.0.2, 1.0.6 tagged; the current main HEAD is
  45372d95

If you need anything else to evaluate the submission, let me know.

Guillaume Lessard <admin@qector.store>
```

The Anthropic team reads their plugin team channel at
`https://anthropic.com/contact` (general) and at the plugin
marketplace docs page
(https://code.claude.com/docs/en/discover-plugins). There is no
guaranteed turnaround; expect weeks to months.

---

## 3. Verify the community marketplace entry once live

After you submit and the catalog syncs (nightly), the entry will be at:

- `https://github.com/anthropics/claude-plugins-community` (read-only
  mirror) — see the `qector` entry in
  `.claude-plugin/marketplace.json`
- `https://claude.com/plugins` — searchable in the Discover tab

To confirm the read-only mirror picked it up:

```bash
curl -sL "https://raw.githubusercontent.com/anthropics/claude-plugins-community/main/.claude-plugin/marketplace.json" \
  | python -c "import json,sys; d=json.load(sys.stdin); print([p['name'] for p in d['plugins'] if p['name']=='qector'])"
```

Expected: `['qector']` once the nightly sync lands.

To install from the community marketplace after it's live:

```bash
claude plugin marketplace add anthropics/claude-plugins-community
claude plugin install qector@claude-community
```

---

## 4. If you don't want to wait for the Anthropic review

There is a non-Anthropic path that works today: QECTOR's own repo
is already a plugin marketplace. Anyone can add it directly with:

```bash
claude plugin marketplace add GuillaumeLessard/qector-claude-plugin
claude plugin install qector@qector-tools
```

This already works. It bypasses the Anthropic-curated catalog and
just uses the GitHub marketplace model directly. The Anthropic
marketplace is the discovery layer on top of this.

---

## 5. Submission checklist

- [x] `name` set to `qector`
- [x] `description` under 280 chars
- [x] `author` block with name + email
- [x] `homepage` set
- [x] `category` set to `development`
- [x] `source` block with `url` + `sha` (current main HEAD)
- [x] Repo is public, `server.json` validates, MCP Registry entry live
- [x] `SECURITY.md` has Identification, Trust Boundaries, Tool Risk
      Classification, Static Scanner Notes
- [x] Per-artifact SHA-256 + provenance + SBOM at every release
- [x] No proprietary source in the public tree
- [x] License clear (Proprietary, with per-tier breakdown)
- [x] `claude-plugin/marketplace.json` + `claude-plugin/plugin.json`
      in the repo at the pinned SHA
