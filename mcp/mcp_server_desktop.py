"""Claude Desktop entry point for QECTOR (2.0.0).

Since 2.0.0 the Desktop bundle runs the secure server. This module is kept
so configurations written for 1.x (``mcp_server_desktop.py --profile safe``)
keep working unchanged: it parses the same flags and hands over to
``mcp_server_secure.main`` with the same profile. The advertised server
name stays ``qector-desktop-mcp`` so Desktop users see a familiar identity;
every other behaviour (air-gap guard, schema validation, integrity check,
audit log) is the secure server's.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Sequence

_MCP_DIR = Path(__file__).resolve().parent
if str(_MCP_DIR) not in sys.path:
    sys.path.insert(0, str(_MCP_DIR))

import mcp_server_secure as secure  # noqa: E402

SERVER_NAME = "qector-desktop-mcp"
SERVER_VERSION = secure.SERVER_VERSION
PROFILES = secure.PROFILES

dispatch_tool = secure.dispatch_tool


def tools() -> list:
    """Safe-profile tool list (imports the decoder modules on first use)."""
    return secure.assemble_tools("safe")[0]


def main(argv: Sequence[str] | None = None) -> int:
    secure.SERVER_NAME = SERVER_NAME
    return secure.main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
