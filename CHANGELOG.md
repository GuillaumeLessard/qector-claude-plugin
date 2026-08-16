# Changelog

## 2026-08-16 - All-skills expansion

- Expanded `skills/` to the full set: 7 QECTOR strict-math skills plus all 16
  official Anthropic skills (docx, xlsx, pptx, pdf, doc-coauthoring,
  canvas-design, frontend-design, web-artifacts-builder, webapp-testing,
  algorithmic-art, theme-factory, slack-gif-creator, internal-comms,
  claude-api, skill-creator, mcp-builder).
- Added `THIRD_PARTY_NOTICES.md` for the official skills' licenses.
- The upload ZIP now ships all 23 skills.

## 2026-08-16 - Repo split and claude.ai upload fix

- Split the standalone CLI tooling out of the hosted plugin: `bin/`, `tests/`,
  `qector_math_ground_truth.py`, `ruff.toml`, and the validation protocol now
  live in the all-in-one `qector-claude-skills` repository.
- Hook helpers moved from `bin/` to `scripts/`; `hooks/hooks.json` now points
  at `${CLAUDE_PLUGIN_ROOT}/scripts/...`. claude.ai-hosted plugins may not
  ship a top-level `bin/` directory (executables are added to PATH on the CLI
  but are not shown on the admin approval surface), so executable entry points
  are declared via hooks, commands, and mcpServers instead.
- All documentation updated to reference `qector-claude-skills` for CLI
  workflows.

## 1.0.0 - 2026-08-15

- Pinned the production library path to the live PyPI wheel `qector-decoder-v3==1.0.0`.
- Pinned the tested MCP runtime to `mcp==1.26.0` and added a low-level stdio adapter.
- Corrected parity-check matrix orientation to `(n_checks, n_qubits)`.
- Added strict binary input validation, graphlike eligibility checks, resource limits,
  fail-closed syndrome verification, and MCP `isError` responses without trace leakage.
- Added hashed raw JSON LER artifacts with Wilson 95% intervals and required metadata.
- Added `qector_math_ground_truth.py` and executable reference-manual proof obligations.
- Made the library server the only default MCP configuration; Workbench is opt-in.
- Aligned public skills, agents, commands, prompts, and documentation with the
  pinned runtime and device-local validation model.
- Removed internal authoring material, machine snapshots, business proposals,
  and proprietary reference documents from the public package.

Performance, GPU, threshold, and universal optimality claims remain workload-scoped;
this plugin does not publish portable speed claims.
