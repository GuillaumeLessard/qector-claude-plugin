# First Boot

1. Install a supported Python runtime (3.10-3.13) and the pinned dependencies:

   ```bash
   python -m pip install -r requirements.lock
   QECTOR_SILENT=1 python scripts/qector_runtime_check.py
   ```

   Air-gapped machine: follow AIRGAP.md (`scripts/install_offline.sh`).

2. Choose one surface:

   - Claude Code: install the marketplace plugin; it enables `qector-secure`
     (12 tools, air-gapped, strict integrity: a missing or drifted `INTEGRITY.json` refuses to start).
   - Claude Desktop: install the `.mcpb` extension; same server.
   - Research/admin: add the example server configuration only after
     reviewing `TOOL_STABILITY.md` and `SECURITY.md`.

3. Verify the posture from the client:

   ```text
   airgap_status      -> air_gapped: true
   integrity_check    -> passed: true
   list_decoders      -> five stable decoders
   ```

4. Do not call setup, configuration, or Workbench tools unless you have
   enabled `qector-admin` and reviewed the planned local changes.
