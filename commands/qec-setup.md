---
description: Run the guided first-time system setup and diagnostic audit with user approbation safety gate.
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
python -c "import importlib.metadata as m; [print(p, getattr(m,'version',lambda x:'?')(p) if True else '') for p in ['qector-decoder-v3','mcp','numpy','cryptography']]" 2>/dev/null || echo "packages not installed"
ls -la artifacts/ 2>/dev/null || echo "artifacts/ not found"
```

Inspect and present to the user:

- Python interpreter path and version (Python >= 3.9, < 3.14 for the wheel).
- Pip availability.
- Installed package versions (`qector-decoder-v3==1.0.0`, `mcp==1.26.0`,
  `numpy`, `cryptography`).
- State of the `artifacts/` evidence directory.

Present the diagnostic table clearly. Do not call the MCP `system_setup` tool
unless `qector-admin` is enabled with `QECTOR_ADMIN_ENABLED=1`. Prefer the CLI.

## Step 2 - User Approbation & Execution

- If any dependencies are missing or unverified, ask the user for confirmation:
  "Would you like to install the required dependencies
  (`pip install -r requirements.txt`) and configure the workspace?"
- **Local machine**: upon confirmation, run
  `python scripts/qector_system_setup.py --confirm`.
- **Sandboxed/remote**: upon confirmation, install directly:
  `pip install qector-decoder-v3==1.0.0 mcp==1.26.0 numpy cryptography`
  then verify with a quick import test.
- Verify the in-process decoding check asserting Theorem 1
  ($H c \equiv s \pmod 2$) if the decoder wheel is installed.
- Report final ready-state status honestly, noting which path was used.
