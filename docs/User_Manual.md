# QECTOR Claude Plugin User Manual

This public plugin provides local Claude skills, agents, commands, and an
app-free MCP server for the QECTOR decoder library. The mathematical authority
is the QECTOR Decoder v3 reference manual at DOI `10.5281/zenodo.21941046`;
the manual itself is not distributed in this repository.

## Install

Use Python 3.9 or newer. The app-free library server supports both the system
interpreter and an isolated virtual environment.

```text
python -m pip install -r requirements.txt
```

Windows virtual environment:

```text
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

The production runtime pins `qector-decoder-v3==1.0.0` and `mcp==1.26.0`.
The library MCP server is part of this plugin and works without QECTOR
Workbench in system Python or in a virtual environment.

Stim/DEM workflows are optional and are not installed by the default runtime.
Install the published extra only when needed:

```text
python -m pip install "qector-decoder-v3[stim]==1.0.0"
```

## MCP Surfaces

The default library server requires no desktop application:

```text
python mcp/mcp_server_library.py
```

It exposes the eight local tools `list_code_families`, `list_decoders`,
`get_license_info`, `decode_syndrome`, `decode_single`, `threshold_sweep`,
`build_code_from_matrix`, and `compat_report`.

For Claude Code, use the root `.mcp.json` and validate/launch with
`claude plugin validate "<PLUGIN_ROOT>" --strict` and
`claude --plugin-dir "<PLUGIN_ROOT>"`. For Claude Desktop, start with
[`CLAUDE_DESKTOP.md`](../CLAUDE_DESKTOP.md) and use the detailed guide at
[`mcp/CLAUDE_DESKTOP.md`](../mcp/CLAUDE_DESKTOP.md). It uses the same local
stdio server and never requires a machine-specific path in the package. For
another MCP client, use `mcp/mcp_config.json`, replace its `<PLUGIN_ROOT>`
token, and run `initialize` followed by `tools/list` before any tool call. The
optional Workbench configuration is a separate example and must be probed on
the target device before use.

The repository also includes `.claude-plugin/marketplace.json`. From the
parent directory, a local marketplace test is:

```text
claude plugin marketplace add ./<PLUGIN_ROOT>
claude plugin install qector@qector-tools
```

For the public GitHub source, use
`claude plugin marketplace add GuillaumeLessard/qector-claude-plugin`.

### Prebuilt archives

A single-skill ZIP for the claude.ai custom-skill uploader and a full plugin
ZIP for `claude --plugin-dir` are shipped under `dist/` with `.sha256`
sidecars in the companion
[`qector-claude-plugin`](https://github.com/GuillaumeLessard/qector-claude-plugin)
repository. See "Packaging and Distribution" in that repository's `README.md`.

## Strict Mathematics

- Arithmetic is over F2.
- Every correction is checked against `H c = s (mod 2)` before it is returned.
- Logical scoring uses the logical coset, never raw correction equality.
- LER uses a Wilson 95% interval and a `code_capacity` or `circuit_level` tag.
- Results from different noise-model tags are not comparable.
- Performance, GPU, and hardware claims are device-local and require fresh artifacts.

The F2 obligations are validated device-local against the reference manual
(DOI `10.5281/zenodo.21941046`); the validation tooling is internal and not
distributed. Keep generated artifacts outside the distributed plugin. A
low-trial sweep is a screening estimate, not a converged threshold.

## Public Contents

- `skills/`: 24 skills - 8 QECTOR domain skills (math, core facts, research,
  development, education, operations, hardware, headless run) plus 16 official
  Anthropic skills (documents, spreadsheets, presentations, PDF, design, web,
  and development tooling; see `THIRD_PARTY_NOTICES.md`).
- `agents/`: focused QEC subagents.
- `commands/`: reproducible local workflows.
- `mcp/`: library server, hosted connector kit, and portable configuration examples.
- `scripts/`: hook helpers referenced by `hooks/hooks.json`.
- `LICENSE.md`: proprietary QECTOR plugin license.
- `PRIVACY.md`: local and hosted privacy notice.

No private transcripts, machine snapshots, internal authoring files, business
proposals, or proprietary reference documents are included.
