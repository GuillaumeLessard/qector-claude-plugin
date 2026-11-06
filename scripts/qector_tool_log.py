"""
QECTOR hook helper - local tool-usage log (optional, see hooks/hooks.json).

PostToolUse: reads the hook JSON payload from stdin and records which QECTOR MCP
tools were invoked into a local debugging log. Nothing leaves the machine.
Exits 0 always.
"""

import datetime
import json
import os
import sys

def _default_data_dir() -> str:
    """Same per-user data root the MCP servers use for artifacts."""
    import platform

    system = platform.system()
    if system == "Windows":
        base = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Local")
        return os.path.join(base, "QectorClaudePlugin")
    if system == "Darwin":
        return os.path.join(os.path.expanduser("~"), "Library", "Application Support", "QectorClaudePlugin")
    base = os.environ.get("XDG_DATA_HOME") or os.path.join(os.path.expanduser("~"), ".local", "share")
    return os.path.join(base, "qector-claude-plugin")


LOG_DIR = os.environ.get("QECTOR_DATA_DIR") or _default_data_dir()


def main():
    try:
        raw = sys.stdin.read()
        name = "unknown"
        try:
            data = json.loads(raw) if raw else {}
            tool = data.get("tool_name") or data.get("tool") or "unknown"
            if isinstance(tool, dict):
                name = str(tool.get("name", "unknown"))
            else:
                name = str(tool)
        except Exception:
            pass
        if "qector" not in name and "mcp__" not in name:
            return 0
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(
            os.path.join(LOG_DIR, "claude_plugin_usage.log"), "a", encoding="utf-8"
        ) as fh:
            fh.write(f"{datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')} tool={name}\n")
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
