# QECTOR Claude Plugin

Local quantum-error-correction engineering for Claude Code, built for
`qector-decoder-v3` by Guillaume Lessard / iD01t Productions.

The primary product surface is the app-free library MCP server shipped in
`mcp/mcp_server_library.py`. It runs locally against the published
`qector-decoder-v3==1.0.0` wheel and does not require QECTOR Workbench.

## What Ships

- Strict-math QEC skills grounded in the QECTOR reference-manual contract.
- Focused researcher, developer, validator, sysadmin, and hardware agents.
- Reproducible commands for runtime inspection, math obligations, and local LER sweeps.
- A local stdio MCP server with explicit schemas and fail-closed error handling.
- Public F2 ground-truth helpers and device-local validation tests.
- Claude Code marketplace metadata in `.claude-plugin/marketplace.json`.

## Runtime

Supported runtime: Python 3.9 or newer, `qector-decoder-v3==1.0.0`,
`mcp==1.26.0`. Install the pinned dependencies with the same interpreter that
will launch the MCP server:

```text
python -m pip install -r requirements.txt
python bin/qector_runtime_check.py
```

The runtime is supported in system Python and in a virtual environment:

```text
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python bin/qector_runtime_check.py
```

The runtime check is device-local and produces no bundled evidence.

## Standalone MCP Server

Launch the library server directly:

```text
python mcp/mcp_server_library.py
```

The server exposes exactly these eight tools:

1. `list_code_families`
2. `list_decoders`
3. `get_license_info`
4. `decode_syndrome`
5. `decode_single`
6. `threshold_sweep`
7. `build_code_from_matrix`
8. `compat_report`

The transport is local stdio only. The server validates binary inputs, enforces
resource bounds, checks every correction against `H c = s (mod 2)`, and returns
MCP tool errors without exposing tracebacks.

## Claude Code

The root `.mcp.json` uses `${CLAUDE_PLUGIN_ROOT}` and is ready for plugin-local
execution. Validate and launch the plugin with:

```text
claude plugin validate "<PLUGIN_ROOT>" --strict
claude --plugin-dir "<PLUGIN_ROOT>"
```

The plugin contains `.claude-plugin/marketplace.json` with marketplace name
`qector-tools`. From the parent directory, test the local marketplace with:

```text
claude plugin marketplace add ./<PLUGIN_ROOT>
claude plugin install qector@qector-tools
```

For the public repository, use:

```text
claude plugin marketplace add GuillaumeLessard/qector-claude-plugin
claude plugin install qector@qector-tools
```

## Other MCP Clients

For Claude Desktop or a generic MCP client, copy the appropriate template:

- `mcp/claude_desktop_config.json`
- `mcp/mcp_config.json`

Replace `<PLUGIN_ROOT>` with the package's absolute path before launch. Then
perform `initialize` and `tools/list` before using any tool.

## Mathematical Contract

- All binary algebra is over F2.
- Corrections must satisfy `H c = s (mod 2)` before logical scoring.
- Logical outcomes use the logical coset, not raw correction equality.
- LER reports include Wilson 95% intervals and a noise-model tag.
- `code_capacity` and `circuit_level` results are not comparable.
- Performance, hardware, GPU, threshold, and license state are device-local.
- Fresh artifacts belong outside the plugin and use an external `.sha256` sidecar.

The public mathematical source is `qector_math_ground_truth.py`. Run the local
validation procedures with:

```text
python bin/run_manual_math_validation.py
python -m unittest discover -s tests -v
```

For a fresh local sweep, write artifacts outside this repository:

```text
python bin/run_threshold_sweep.py --family rotated_surface --distances 3 5 --error-rates 0.05 --trials 100 --seed 42 --out ..\qector-artifacts\device_sweep.json
```

## Optional Features

Stim/DEM workflows are not required by the library MCP server. Install the
published optional extra only when needed:

```text
python -m pip install "qector-decoder-v3[stim]==1.0.0"
```

QECTOR Workbench is a separate optional application. Its tool names, schemas,
hardware, and license state must be negotiated on the target device; no
Workbench tool is part of the standalone library contract.

## Security And Legal

The default server is local stdio. Do not send circuits, syndromes, matrices,
credentials, or generated artifacts to external services. Review
`governance/security_playbook.md` before deployment.

This plugin is provided **AS IS** and without warranty to the maximum extent
permitted by applicable law. See `DISCLAIMER.md`. The upstream
`qector-decoder-v3` package and all third-party dependencies retain their own
licenses and terms.

## Repository Layout

- `.claude-plugin/`: plugin and marketplace manifests.
- `skills/`: QECTOR domain skills.
- `agents/`: custom QEC agents.
- `commands/`: local slash-command workflows.
- `bin/`: runtime, validation, and artifact helpers.
- `mcp/`: standalone server and client templates.
- `docs/`: public user and math-validation documentation.
- `tests/`: executable device-local obligations.

Author: Guillaume Lessard / iD01t Productions, ORCID `0009-0000-3465-3753`.
