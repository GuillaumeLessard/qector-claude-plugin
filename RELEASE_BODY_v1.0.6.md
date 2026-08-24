# QECTOR Claude Plugin v1.0.6

**Release date:** 2026-08-23
**Release type:** Claude.ai marketplace compliance hardening + setup robustness
**Full changelog:** https://github.com/GuillaumeLessard/qector-claude-plugin/compare/v1.0.5...v1.0.6

---

## Why this release exists

v1.0.5 introduced the cross-platform launcher in a `bin/` directory. When the
claude.ai-hosted marketplace pipeline (the one Claude Desktop and Claude Code
sync from on hosted/enterprise setups) reviewed the plugin, it flagged a
hard compliance problem: **claude.ai-hosted plugins may not ship `bin/`
executables**. Because `bin/` entries are added to the command PATH when the
plugin loads, but are never shown on the admin approval surface, a plugin
shipping one represents a silent code-execution surface that administrators
cannot see or approve. This is an Anthropic platform policy, not a defect in
the launcher itself.

One more correctness gap surfaced during the same review window: the
`/qec-setup` command hard-required a local `scripts/qector_system_setup.py`.
On a normal machine that works. But in the sandboxed and remote execution
environments Claude also offers (claude.ai code execution, Cowork, containers
without a project checkout), that script does not exist, so the command
dead-ended. That is now fixed, not just patched.

---

## Scope and impact

Who this release affects:

| Audience | Impact |
|:---------|:-------|
| **Everyone** | Launchers relocated from `bin/` to `scripts/` in every artifact type. If you installed v1.0.5, reinstall the v1.0.6 bundle — do not reuse v1.0.5 cache files. |
| **claude.ai-hosted / marketplace users** | This was the direct trigger. The manifests are now canonical and the plugin loads in the strictest approval surfaces. |
| **Windows users** | No functional change. The Windows launcher is selected via the win32 override exactly as in v1.0.5 — it just lives in `scripts/` now. |
| **Sandboxed / remote users** | `/qec-setup` no longer dead-ends; it falls back to native diagnostics and reports honestly. |

---

## What changed in v1.0.6

### 1. Claude.ai marketplace compliance (fixes a platform-policy rejection)

- **Launchers moved from `bin/` to `scripts/`.** Both `qector-python` (POSIX
  sh) and `qector-python.cmd` (Windows) now live in `scripts/`, with the exec
  bit preserved through packaging (git mode `100755`, archive attr `0o755`).
  Every reference was repointed: `plugin.json`, `.mcp.json`, `hooks/hooks.json`
  (SessionStart + PostToolUse), the Desktop MCPB manifest, the win32
  `platform_overrides` block, the builder whitelists, and the bundle validator.
  Commit `2bd1aa4`.
- **Canonical marketplace manifests.** `marketplace.json` now declares the
  plugin with the relative same-repo source (`"source": "./"`), the form every
  official Anthropic marketplace uses and the only form guaranteed resolvable
  across every sync path that clones the repository. All fields are from the
  documented schema (`homepage`, `repository`, `keywords`, owner `url`).
  Commits `5814242` and `7bb49f7`.
- **`bin/` ban guard (regression lock).** `validate_plugin_bundle.py` now
  hard-fails if a `bin/` entry appears in any of the three release artifacts
  (plugin zip, source zip, Desktop MCPB). Commit `2bd1aa4`.

### 2. Environment-agnostic setup

- **`/qec-setup` works everywhere.** The command now detects whether it is
  running on a real checkout (script present) or in a sandbox/remote/no-clone
  environment, and falls back to native diagnostics (Python version, pip,
  package versions, artifacts directory) instead of failing. It explicitly
  instructs Claude to **never claim the script ran** when it used the
  fallback — honest reporting by design. Commit `c49b34f`.

### 3. Dependency security hardening

- **MCP SDK pinned to `mcp>=1.28.1,<2`.** Bumps the `mcp` runtime from
  `1.26.0` to the patched `1.x` line, fixing three high-severity GitHub
  Security Advisories: GHSA-hvrp-rf83-w775 / CVE-2026-52870, GHSA-jpw9-pfvf-9f58
  / CVE-2026-52869, GHSA-vj7q-gjh5-988w / CVE-2026-59950. The `<2` upper bound
  keeps the build on `1.x`; `2.0.0` removes the WebSocket transport and renames
  core symbols this codebase imports directly. Commits `7b1a6b4`, `176247e`,
  `af11a03`.

---

## Interpreter pinning note (no action unless you set it in v1.0.5)

The `userConfig.python_path` / `user_config.python_path` block was removed
from `plugin.json` in this release. This was the newest and least-standard
manifest field, and the strict claude.ai approval schema does not recognize
it. **The feature is not lost:** interpreter pinning still works end to end —
set the `QECTOR_PYTHON` environment variable to an absolute Python 3.9-3.13
path and every launcher honors it before auto-resolution. If you previously
configured `userConfig.python_path`, migrate by setting `QECTOR_PYTHON`
instead; there is a one-line note in the README.
---

## Supported environments

- **Python: 3.9 through 3.13.** Launchers explicitly reject 3.14+ (the
  `qector-decoder-v3` wheel matrix does not cover it) with guidance, rather
  than crashing at import time.
- **`qector-decoder-v3==1.0.0`**, the pinned decoder runtime.
- **Claude Code:** Windows, macOS, Linux (via the shipped launchers).
- **Claude Desktop:** Windows, macOS (Desktop MCPB, safe profile).
- **Web / iOS / Android / Cowork:** local stdio cannot reach those surfaces
  (Anthropic architecture); a hosted remote connector is on the 1.1.x
  roadmap.

---

## What does NOT change

- **Surface counts.** 28 skills, 11 commands, 5 agents, 4 MCP servers, 8
  stable library tools, 32 research tools, 3 admin tools — identical to v1.0.5.
- **All 16 reference theorems** remain executable-proof-verified in the test
  suite (74 unit tests, 48 subtests across the math, protocol, and production
  readiness gates).
- **The eight-tool safe Desktop profile** is unchanged.
- **Offline-by-default** privacy binary is unchanged (no network calls unless
  explicitly requested).

---

## Known limitations

- **Sandbox / remote diagnostics depth.** The native fallback path in
  `/qec-setup` reports the core audit (interpreter, pip, package versions,
  artifacts dir) but does not run the full math validation the local script
  performs (that needs the `qector-decoder-v3` wheel, which sandboxes may not
  have). It is intentionally reduced scope, clearly labeled, and sessions are
  told to install and validate on a real machine when possible.
- **Marketplace sync still needs a private repo on managed orgs.** Per the
  Claude documents, if you use Claude Desktop's managed-org marketplace
  pipeline (the one that says "Sync automatically"), the repository must be
  private or internal and owned by the same org as the Claude GitHub App. A
  public repo can still be rejected with a generic sync error on that
  pipeline, even though every direct install path works.

---

## Integrity

Artifacts are built deterministically with fixed timestamps, so the build is
byte-for-byte reproducible. SHA-256 hashes are published in `SHA256SUMS`,
sidecar files, and the MCP Registry descriptor, and the registry entry's
`fileSha256` matches the published Desktop MCPB.

| Artifact | SHA-256 |
|:---------|:--------|
| `qector-claude-desktop-1.0.6.mcpb` | `fdab720ab3914b3a7e8da23a6706f99337acfb20c7709ebbcd981cf8c5d10cd6` |
| `qector-claude-plugin-1.0.6.zip` | `ad80d8ae7b67196228b5af1e83585f353c37d4754fdb4f9308568437aa5a332d` |
| `qector-claude-plugin-source-1.0.6.zip` | `5dcf83726c9e55ac5e89236fe81171fe597af3a30bd949cc20853d3218046792` |

**Verification summary:** 832/832 source checks · bundle ALL CLEAR · 15/15
release metadata · 74/74 unit tests (+48 subtests) · `claude plugin validate
. --strict` passes · fresh marketplace add + install exits 0.

---

## Upgrade

**Claude Code:** `/plugin marketplace update qector-tools` then
`/plugin install qector@qector-tools`.

**Claude Desktop:** remove the old v1.0.5 extension, download
`qector-claude-desktop-1.0.6.mcpb` from the release page, install via the
extension UI, restart when prompted.

---

## Traceability

| Commit | Change |
|:-------|:-------|
| `5814242` | Canonical marketplace manifests |
| `09ca506` | Drop unknown license fields (strict sync) |
| `2bd1aa4` | Launchers `bin/` → `scripts/`, `bin/` ban guard |
| `c49b34f` | `/qec-setup` environment-agnostic fallback |
| `7b1a6b4` | Bump `mcp` to `>=1.28.1,<2` (3 GHSA fixes) |
| `176247e` | Propagate `mcp` pin to `runtime_check`/`system_setup`/`bench` |
| `650f5aa` | Rebuild `dist/` + `server.json` from patched HEAD |
| `af8a2ac` | v1.0.6 release commit |

---

## Acknowledgments

Thanks to the claude.ai marketplace review pipeline for surfacing the `bin/`
approval-surface policy, which drove the relocation, and to everyone who
exercised the marketplace and `/qec-setup` paths from real Desktop and
sandboxed environments and reported the gaps. Straightforward, reproducible
feedback like that is what makes the resilience layer worth keeping.

---

_Questions, edge-feature requests, or QEC research collaborations: open an
issue or reach out via the repository. QECTOR is source-available; the
reference manual ships separately via Zenodo DOI._