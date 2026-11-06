---
description: Run the guided first-time system setup and diagnostic audit with user approbation safety gate.
argument-hint: "(no arguments; confirmation is asked interactively)"
---

Perform a guided first-time setup and dependency audit of the QECTOR quantum error correction environment.

Safety gate: Never execute installation without explicit user approval.

## Environment detection

First determine which environment you are running in:

- **Local machine with the plugin installed**: the setup script exists at
  `scripts/qector_system_setup.py` inside the plugin root (resolve it via
  `${CLAUDE_PLUGIN_ROOT}` if available, or the local project directory).
- **Sandboxed / remote / cloud environment** (no project checkout, no scripts/
  directory, e.g. claude.ai code execution): the script is NOT available. Fall
  back to the native diagnostic below and never claim you ran the script.

## Step 1 - Diagnostic Audit (Dry-Run)

**If the script is present** (local machine), run:

```
python scripts/qector_system_setup.py --check-only
```

**If the script is absent** (sandboxed/remote), run the equivalent audit with
the Bash tool instead. Do NOT report that the script ran — report what you
actually executed:

```bash
python --version 2>/dev/null || python3 --version
python -m pip --version 2>/dev/null || python3 -m pip --version
python scripts/qector_runtime_check.py          # versions of qector-decoder-v3, mcp, numpy, cryptography and the Python window
python scripts/qector_system_setup.py --check-only
```

Inspect and present to the user:

- Python interpreter path and version (Python >= 3.10, < 3.14: the MCP SDK needs 3.10+, the wheel stops at 3.13).
- Pip availability.
- Installed package versions (`qector-decoder-v3==1.0.1`, `mcp>=1.30,<3`,
  `numpy`, `cryptography`).
- State of the `artifacts/` evidence directory.

Present the diagnostic table clearly. Do not call the MCP `system_setup` tool
unless `qector-admin` is enabled with `QECTOR_ADMIN_ENABLED=1`. Prefer the CLI.

## Step 2 - User Approbation & Execution

- If any dependencies are missing or unverified, ask the user for confirmation:
  "Would you like to install the required dependencies
  (`pip install -r requirements.lock`, or `--offline-wheelhouse <dir>` on an air-gapped host) and configure the workspace?"
- **Local machine**: upon confirmation, run
  `python scripts/qector_system_setup.py --confirm`.
- **Sandboxed/remote**: upon confirmation, install directly:
  `python -m pip install --require-hashes -r requirements.lock` (the exact
  tested closure; quote any ad-hoc specifier such as `"mcp>=1.30,<3"` because
  `>` is a shell redirect), then verify with `scripts/qector_runtime_check.py`.
- Verify the in-process decoding check asserting Theorem 1
  ($H c \equiv s \pmod 2$) if the decoder wheel is installed.
- Report final ready-state status honestly, noting which path was used.
