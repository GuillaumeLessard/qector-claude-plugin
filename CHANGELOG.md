# Changelog

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
