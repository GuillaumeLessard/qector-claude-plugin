# Security

## Identification

| Field | Value |
|:------|:------|
| Plugin name | `qector` |
| Display name | QECTOR Quantum Error Correction |
| Version | 1.0.6 |
| License | Proprietary — see [LICENSE.md](LICENSE.md) |
| Author | Guillaume Lessard <admin@qector.store> |
| Repository | https://github.com/GuillaumeLessard/qector-claude-plugin |
| Reference manual | DOI `10.5281/zenodo.21941046` (v1.0.0) |
| Privacy policy | https://qector.store/privacy |
| Provenance | see [PROVENANCE.md](PROVENANCE.md) and `dist/provenance.json` |
| Provenance (per-call) | every MCP response carries `server_name`, `server_version`, and a stable `status` code from the closed set in [MCP_API.md](MCP_API.md) |

## Trust Boundaries

The plugin is shipped as four named MCP servers and one shared contract. The
total surface is **40 tools** in three trust zones; the default install
exposes only the 8 stable tools.

| Server | Trust zone | Tools | Default | Risk tier |
|:-------|:-----------|:------|:--------|:----------|
| `qector-library` | stable | 8 | ✅ | Tier 1 — every result is verified against `H c = s (mod 2)` before being returned |
| `qector-research` | research | 29 | opt-in (`--with-research`) | Tier 2 — read / compute / measure; writes only inside `QECTOR_ARTIFACT_DIR` |
| `qector-admin` | admin | 3 | opt-in (`--with-admin` + `QECTOR_ADMIN_ENABLED=1`) | Tier 3 — requires `confirm=true` on every mutating call |
| `qector-desktop-mcp` | safe (Desktop) | 8 | ✅ (Desktop) | Tier 1 — same 8 stable tools, re-exported by the Desktop adapter |

## Tool Risk Classification

This is the authoritative classification used by the bundled validator and
the public MCP catalog. Static scanners (PolicyLayer, MCP Registry,
CodeQL-based reviews) should map each tool to one of the four classes
below; the plugin never performs an operation outside its declared class.

| Class | Tools | What they actually do |
|:------|:------|:----------------------|
| `read` | 29 — `list_code_families`, `list_decoders`, `get_license_info`, `compat_report`, plus 25 research tools (`get_capability_matrix`, `get_evidence_policy`, `get_runtime_provenance`, `wilson_ci`, `wilson_table`, `logical_coset_score`, `dem_inspect`, `dem_collapse_parallel`, `code_family_info`, `code_logicals_inspect`, `code_distance_check`, `pymatching_compat_check`, `sinter_decoder_list`, `qiskit_plugin_check`, `hardware_probe`, `license_active_check`, `env_block`, `decode_faithfulness_check`, `stim_circuit_probe`, `sinter_task_template`, `workload_hash`, `theorem_lookup`, `glossary_lookup`, `reproduction_command_lookup`, `artifact_metadata_check`) | Pure read / compute. No filesystem write, no subprocess, no network. |
| `compute` (Execute) | 3 — `decode_syndrome`, `decode_single`, `threshold_sweep` | Scoped QEC math on caller-supplied binary inputs. `decode_*` runs a single algorithm; `threshold_sweep` runs a Wilson-CI LER grid. No subprocess, no dynamic import, no eval, no file write beyond the JSON artifact inside `QECTOR_ARTIFACT_DIR`. |
| `build` (Execute) | 1 — `build_code_from_matrix` | Validates caller-supplied dimensions and code family, then constructs an in-memory parity-check matrix. No subprocess, no eval, no network, no file write. |
| `write` (local) | 4 — `code_export_matrices` (writes only the file path the caller just built), `artifacts_sha256` (writes only inside `QECTOR_ARTIFACT_DIR`), `configure_claude_desktop` (writes only the Desktop config, requires `confirm=true`), `system_setup` (writes only inside the virtualenv or `QECTOR_ARTIFACT_DIR`, requires `confirm=true`) | Local-only writes to a fixed path set. None reach the network. None are reachable from the default 8-tool surface. |
| `launch` (privileged) | 1 — `workbench_probe` | Requires `QECTOR_WORKBENCH_DIR` (an absolute path the user pre-approves), an expected SHA-256 digest, and `confirm=true`. The launched binary is checked against the expected digest before execution. Off by default; opt-in per call. |

### What this plugin does NOT do

- It does not transmit syndromes, parity matrices, circuits, tool
  arguments, or artifacts anywhere by default.
- It does not call `eval` or `exec` on caller input. The repository has
  zero hits for either pattern.
- It does not use `__import__` or `importlib.import_module` on caller
  input. The repository has zero hits for either pattern.
- It does not open arbitrary sockets. Network access is limited to the
  explicit, opt-in `compat_report(check_pypi=true)` and
  `env_block(check_pypi=true)` PyPI check, documented in [PRIVACY.md](PRIVACY.md).
- The default 8-tool stable surface does not launch subprocesses, does
  not write to disk, and does not make network calls.

## Privileged Operations

`system_setup` accepts fixed profiles only: `production`, `developer`,
`optional-stim`, and `optional-qiskit`. It does not accept arbitrary package
specifications. `workbench_probe` requires an executable within
`QECTOR_WORKBENCH_DIR`, an expected SHA-256 digest, and explicit confirmation.

## Privileged Operations

`system_setup` accepts fixed profiles only: `production`, `developer`,
`optional-stim`, and `optional-qiskit`. It does not accept arbitrary package
specifications. `workbench_probe` requires an executable within
`QECTOR_WORKBENCH_DIR`, an expected SHA-256 digest, and explicit confirmation.

## Built-in Call Budgets

Agents have no external rate limiter, so the MCP process enforces its own
ceilings. These tools charge a per-process counter and fail closed with
`RESOURCE_LIMIT` when the budget is exhausted:

| Tool | Default max calls / process | Why it is limited |
| --- | ---: | --- |
| `threshold_sweep` | 8 | Writes hashed artifacts and can run a large LER grid |
| `decode_single` | 64 | Seeded decode loop; unbounded agent retries |
| `decode_syndrome` | 256 | Per-call decode compute |
| `build_code_from_matrix` | 32 | Allocates and validates an arbitrary parity-check matrix |
| `hot_path_microbench` | 4 | Machine-scoped measurement, not a portable claim |
| `system_setup` | 2 | Can install packages and write local directories |
| `configure_claude_desktop` | 2 | Rewrites Claude Desktop configuration |
| `workbench_probe` | 2 | Launches a local executable |

Override a single ceiling with `QECTOR_MCP_MAX_CALLS_<TOOL_NAME>` (uppercase).
Set the value to `-1` to disable that tool's budget. Input-size ceilings
(`QECTOR_MCP_MAX_DISTANCE`, `QECTOR_MCP_MAX_TRIALS`,
`QECTOR_MCP_MAX_SWEEP_POINTS`, `QECTOR_MCP_MAX_MATRIX_CELLS`) still apply on
every call.

## Network Boundary

Default operation is local-only. The only network-capable tool arguments are
the explicit PyPI freshness checks documented in `PRIVACY.md`. Do not enable
them in air-gapped deployments.

## Reporting

Report vulnerabilities privately to <admin@qector.store>. Do not include
licenses, credentials, private matrices, or customer artifacts in reports.

## Static Scanner Notes

External catalog scanners (PolicyLayer, MCP Registry, CodeQL, etc.)
classify the 40-tool surface as **3 Execute + 4 Write + 33 Read** when
they walk the `qector-library`, `qector-research`, and `qector-admin`
servers together. The mapping is:

- "Execute" is **not** code execution. The three Execute tools perform
  scoped quantum error-correction math on caller-supplied binary inputs.
  They do not call `eval`, `exec`, `__import__`, `importlib`, or
  `subprocess`. They never read or write outside `QECTOR_ARTIFACT_DIR`.
- "Write" is **not** arbitrary file system access. The four Write tools
  write only to caller-named or pre-approved paths. Three of them
  require `confirm=true` on every call. None of them is in the default
  8-tool surface that ships to Claude Desktop.
- The recommended policy for a strict allow-list is:
  - **Read tools** → `allow`
  - `build_code_from_matrix` (Execute) → `require_approval`
  - `code_export_matrices` (Write) → `rate_limit`
  - `configure_claude_desktop`, `system_setup`, `workbench_probe` (privileged) → `require_approval + confirm=true` and the admin server must be enabled by environment flag

The MCP processes enforce their own per-tool call budgets (see
"Built-in Call Budgets" above) and fail closed with `RESOURCE_LIMIT`
when the budget is exhausted, so a runaway agent cannot loop the
Write or Execute tools.

## Runtime Dependabot Advisories (status)

The `1.0.6` release ships with `mcp>=1.28.1,<2`, which is patched
against three CVEs GitHub's Dependabot previously flagged against the
earlier `mcp==1.26.0` pin. Each was in a code path the QECTOR plugin
does not exercise, and the runtime wheel (`qector-decoder-v3==1.0.0`)
does not require `mcp` at all, so exposure was **not applicable** to
this release even before the bump. The pin was raised anyway as
defense-in-depth so the dependency itself carries no open advisory:

| CVE | Title | Why it does not apply to QECTOR |
|:----|:------|:--------------------------------|
| CVE-2026-59950 | MCP Python SDK: WebSocket server transport does not support Host/Origin validation | QECTOR ships no WebSocket server. The four MCP servers all use `stdio` transport. |
| CVE-2026-52869 | MCP Python SDK: HTTP transports serve session requests without verifying the authenticated principal | QECTOR ships no HTTP MCP transport. The four MCP servers all use `stdio` transport; the only outbound HTTP is the explicit opt-in PyPI freshness check, which is a plain `urllib` GET with a fixed URL. |
| CVE-2026-52870 | MCP Python SDK: Experimental task handlers allow any client to access and cancel other clients' tasks | QECTOR does not register any experimental task handlers. The `qector_mcp_contract.py` envelope does not expose a task-cancel surface. |

All three alerts are resolved as of `mcp>=1.28.1,<2`. If a future
release adds an HTTP or WebSocket transport, the corresponding
advisory will be re-evaluated independently of this pin.
