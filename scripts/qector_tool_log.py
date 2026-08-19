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

LOG_DIR = os.environ.get(
    "QECTOR_DATA_DIR",
    os.path.join(
        os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "QectorClaudePlugin"
    ),
)


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
            fh.write(f"{datetime.datetime.now().isoformat()} tool={name}\n")
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
