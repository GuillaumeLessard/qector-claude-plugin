# First Boot

1. Install a supported Python runtime (3.9-3.13) and dependencies:

   ```bash
   python -m pip install -r requirements.txt
   python scripts/qector_runtime_check.py
   ```

2. Choose one surface:

   - Claude Code: install the marketplace plugin; it enables `qector-library`.
   - Claude Desktop: install the generated safe `.mcpb` extension.
   - Research/admin: explicitly add the example server configuration only after
     reviewing `TOOL_STABILITY.md` and `SECURITY.md`.

3. Verify a stable tool is available:

   ```text
   list_decoders
   ```

4. Do not call setup, configuration, or Workbench tools unless you have
   enabled `qector-admin` and reviewed the planned local changes.
