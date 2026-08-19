---
description: Zero-friction Claude Desktop connector for Windows and macOS with non-destructive backup
---

# `/qec-desktop-connector` - Claude Desktop MCP Configuration

Connect both QECTOR MCP servers (`qector-library` with 8 tools and `qector-bench` with 29 tools)
directly into Claude Desktop.

## Workflow

1. **Pre-flight Audit & Dry Run**:
   Inspect your current Claude Desktop configuration without modifying any files:
   ```bash
   python scripts/configure_claude_desktop.py --check-only
   ```
   Or via MCP:
   ```json
   {
     "name": "configure_claude_desktop",
     "arguments": {
       "confirm": false
     }
   }
   ```

2. **Execute Configuration with User Approbation**:
   Creates a timestamped backup (`claude_desktop_config.json.bak.<timestamp>`), safely merges
   both servers, normalizes paths to avoid Windows backslash crashes, and sets `QECTOR_SILENT=1`:
   ```bash
   python scripts/configure_claude_desktop.py --confirm
   ```
   Or via MCP:
   ```json
   {
     "name": "configure_claude_desktop",
     "arguments": {
       "confirm": true
     }
   }
   ```

3. **Restart Claude Desktop**:
   Fully restart Claude Desktop to load all 37 MCP tools (8 library + 29 bench).

4. **Verify Live Connection**:
   Check that both servers appear in Claude Desktop's hammer icon with all expected tools.
