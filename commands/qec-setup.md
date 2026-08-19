---
description: Run the guided first-time system setup and diagnostic audit with user approbation safety gate.
---

Perform a guided first-time setup and dependency audit of the QECTOR quantum error correction environment.

Safety gate: Never execute installation without explicit user approval.

1. **Step 1 - Diagnostic Audit (Dry-Run)**:
   - Run `python scripts/qector_system_setup.py --check-only` or call MCP `system_setup(confirm=false)`.
   - Inspect:
     - Python interpreter path and version (Python >= 3.9).
     - Pip availability.
     - Installed package versions (`qector-decoder-v3==1.0.0`, `mcp==1.26.0`, `numpy`, `cryptography`).
     - State of the `artifacts/` evidence directory.
   - Present the diagnostic table clearly to the user.

2. **Step 2 - User Approbation & Execution**:
   - If any dependencies are missing or unverified, ask the user for confirmation:
     "Would you like to install the required dependencies (`pip install -r requirements.txt`) and configure the workspace?"
   - Upon confirmation, run `python scripts/qector_system_setup.py --confirm` or call MCP `system_setup(confirm=true)`.
   - Verify the in-process decoding check asserting Theorem 1 ($H c \equiv s \pmod 2$).
   - Report final ready-state status.
