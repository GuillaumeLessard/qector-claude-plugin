# QECTOR Quantum Error Correction Plugin

This is the QECTOR Claude Plugin, an advanced quantum error correction engineering and research environment.

## 🚀 Build & Test Commands
- **Structure Tests**: `python scripts/test_structure.py`
- **Math/Theorem Proofs**: `python scripts/run_manual_math_validation.py`
- **Rebuild Dist Packages**: `python scripts/pro_pack.py --all`
- **Configure Claude Desktop (Windows/Mac/Linux)**: `python scripts/configure_claude_desktop.py --confirm`

## 🧩 Claude Code Architecture
- **MCP Servers** (`.mcp.json`): Integrates `qector-library` (stable) and `qector-bench` (research) tools.
- **Skills** (`skills/`): 28 domain-specific instruction sets.
- **Commands** (`commands/`): 13 automated slash commands (e.g., `/qec-theorem`, `/qec-threshold-sweep`).
- **Agents** (`agents/`): 5 specialized personas.
- **Hooks** (`hooks/hooks.json`): Automated session start and tool usage logging.
- **Plugin Manifests** (`.claude-plugin/`): Formal definitions for Anthropic Marketplace distribution.

## 📏 Core Engineering Guidelines
1. **Mathematical Strictness**: Every single syndrome decoding must verify $H c \equiv s \pmod 2$. Do not accept approximations.
2. **Zero-Egress Security**: Operations must run 100% locally. Never write code that attempts to offload QEC simulation telemetry to the cloud.
3. **Fail-Closed Design**: Any mismatched matrix dimensions, unrecognized code families, or invalid distance requests must immediately raise a deterministic error rather than silently corrupting the quantum state.
4. **Statistical Rigor**: All LER threshold sweeps must include exact Wilson 95% binomial score intervals. Point estimates without bounds are rejected.

## 🔗 Extension Context
For a detailed mathematical specification, consult the `QECTOR_Reference_Manual_v1.0.0.pdf` (DOI: 10.5281/zenodo.21941046) and the live offline fact sheet.
