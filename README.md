# QECTOR for Claude Code

QECTOR is Guillaume Lessard's Claude Code plugin for local quantum-error-
correction engineering. It provides custom skills, persona agents, slash
commands, local hooks, and a library-first MCP server.

## Production Runtime

The supported library runtime is the live PyPI release. Python 3.9 or newer is
required, and the same commands work in system Python or a virtual environment.

```text
python -m pip install -r requirements.txt
python bin/qector_runtime_check.py
```

For an isolated Windows environment:

```text
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python bin/qector_runtime_check.py
```

`requirements.txt` pins `qector-decoder-v3==1.0.0` and `mcp==1.26.0`. The
library server is app-free and runs against the Rust/PyO3 wheel directly.

```text
python mcp/mcp_server_library.py
python bin/qector_runtime_check.py
```

The same commands work with system Python or a virtual environment. The active
interpreter is the only selection that changes; no desktop application is
involved.

The default MCP transport is stdio. It exposes exactly eight tools:

`list_code_families`, `list_decoders`, `get_license_info`, `decode_syndrome`,
`decode_single`, `threshold_sweep`, `build_code_from_matrix`, and
`compat_report`.

## Claude Configuration

- Claude Code: use the root `.mcp.json`; it resolves the server through
  `${CLAUDE_PLUGIN_ROOT}` and does not require Workbench. Validate and launch
  the plugin with `claude plugin validate "<PLUGIN_ROOT>" --strict` and
  `claude --plugin-dir "<PLUGIN_ROOT>"`.
- Claude Desktop or another MCP client: copy `mcp/claude_desktop_config.json`
  and replace `<PLUGIN_ROOT>` with the package's absolute path before launch.
- Optional Workbench: use `mcp/workbench_config.example.json` only after the
  executable path is confirmed and `bin/probe_workbench_mcp.py --executable
  <target-workbench-executable>` succeeds. The
  Workbench is not required by any library workflow.

## Marketplace Distribution

This repository includes `.claude-plugin/marketplace.json` with marketplace
name `qector-tools` and plugin source `./`.

```text
claude plugin validate "<PLUGIN_ROOT>" --strict
claude plugin marketplace add GuillaumeLessard/qector-claude-plugin
claude plugin install qector@qector-tools
```

For local development, use `claude plugin marketplace add ./<PLUGIN_ROOT>`
from the parent directory, then install `qector@qector-tools`. The marketplace
and plugin names are stable identifiers; bump the manifest version on releases.

Always perform `initialize` followed by `tools/list` before relying on a tool
name. The bundled server exposes stdio only; network transports are not part of
this package. Local `.stim`, `.npy`, syndrome, and parity-check data must not be
sent to external services.

## Mathematical Contract

The normative source is the QECTOR Decoder v3 reference manual v1.0.0 at DOI
`10.5281/zenodo.21941046`; the source document is not redistributed here. The
plugin enforces its core boundaries:

- every returned correction is checked against `H c = s (mod 2)` (Theorem 1);
- logical scoring uses the logical coset, never raw correction equality (Theorem 2);
- every LER row has a Wilson 95% interval;
- `code_capacity` and `circuit_level` results are never compared;
- evidence artifacts carry metadata and an external SHA-256 sidecar;
- hardware, performance, and Provisional API claims remain scoped to evidence.

The public executable math ground truth is `qector_math_ground_truth.py`, with
device-local checks in `tests/test_reference_manual_math.py`. No test output or
hardware result is bundled; run the gate fresh on each target device.

```text
python bin/run_manual_math_validation.py
```

Threshold artifacts use the same contract:

```text
python bin/run_threshold_sweep.py --family rotated_surface --distances 3 5 --error-rates 0.05 --trials 100 --seed 42 --out ..\qector-artifacts\device_sweep.json
```

Low-trial results are screening estimates, not converged thresholds.

## Plugin Contents

- `.claude-plugin/plugin.json`: Claude plugin manifest.
- `skills/`: math foundations, core facts, researcher, developer, educator,
  sysadmin, and hardware-engineer skills.
- `agents/`: five focused QEC persona agents.
- `commands/`: facts, validation, and sweep workflows.
- `bin/`: local validation, threshold, Workbench probe, session, and usage-log helpers.
- `mcp/`: library server and client configuration.
- `governance/`: zero-egress, provenance, and claim-boundary rules.
- `docs/MATH_VALIDATION.md`: theorem-to-test map.
- `.claude-plugin/marketplace.json`: public marketplace catalog entry.

## Author And License

Author: Guillaume Lessard / iD01t Productions, ORCID `0009-0000-3465-3753`.
The decoder wheel carries its own package license. This plugin does not modify
or replace those upstream terms.

See `DISCLAIMER.md` before use. The plugin is provided **AS IS**, without
warranty or guarantee, to the maximum extent permitted by law.
