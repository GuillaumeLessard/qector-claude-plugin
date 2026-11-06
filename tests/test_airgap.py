"""Static and dynamic air-gap guarantees.

* No server module references a network-capable symbol of the decoder
  wheel (``flush_usage``, ``rest_api``, ``run_grpc_server`` ...). The list
  is the one ``airgap_status`` publishes, so the tool's ``called_by_plugin:
  false`` claim is checked, not asserted.
* No server module imports an HTTP client at module scope; the only
  ``urllib`` use is inside the opt-in PyPI check and is guarded by
  ``qector_airgap.require_network``.
* ``qector_airgap`` installs and uninstalls cleanly and counts blocked
  attempts.
"""

from __future__ import annotations

import os
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MCP_DIR = ROOT / "mcp"
if str(MCP_DIR) not in sys.path:
    sys.path.insert(0, str(MCP_DIR))
os.environ.setdefault("QECTOR_SILENT", "1")


def _mcp() -> bool:
    """The guard module imports the contract, which needs the real SDK."""
    try:
        import mcp.types  # noqa: F401
    except Exception:
        return False
    return True


SERVER_SOURCES = [
    MCP_DIR / "mcp_server_library.py",
    MCP_DIR / "mcp_server_qector_bench.py",
    MCP_DIR / "mcp_server_admin.py",
    MCP_DIR / "mcp_server_desktop.py",
    MCP_DIR / "mcp_server_secure.py",
    MCP_DIR / "qector_mcp_contract.py",
    MCP_DIR / "qector_mcp_compat.py",
    MCP_DIR / "qector_schemas.py",
    MCP_DIR / "qector_audit.py",
    MCP_DIR / "qector_integrity.py",
]


@unittest.skipUnless(_mcp(), "mcp SDK not installed")
class StaticAirgapTests(unittest.TestCase):
    def test_servers_never_reference_wheel_network_symbols(self) -> None:
        import qector_airgap

        for path in SERVER_SOURCES:
            text = path.read_text(encoding="utf-8")
            for symbol in qector_airgap.WHEEL_NETWORK_SYMBOLS:
                if symbol in {"workbench", "Workbench"}:
                    # The admin probe launches a *user-approved* Workbench
                    # binary by path; it never imports the wheel's module.
                    pattern = rf"qector_decoder_v3\.{symbol}\b|from qector_decoder_v3 import .*\b{symbol}\b"
                else:
                    pattern = rf"\b{re.escape(symbol)}\b"
                with self.subTest(file=path.name, symbol=symbol):
                    self.assertIsNone(re.search(pattern, text), f"{path.name} references {symbol}")

    def test_no_module_scope_http_clients(self) -> None:
        for path in SERVER_SOURCES:
            text = path.read_text(encoding="utf-8")
            with self.subTest(file=path.name):
                self.assertNotRegex(text, r"^import (requests|httpx|aiohttp)\b", "HTTP client imported")
                self.assertNotRegex(text, r"^import urllib\.request", "urllib must be imported lazily inside the guarded check")
                self.assertNotIn("eval(", text)
                self.assertNotIn("exec(", text)

    def test_network_calls_are_guarded(self) -> None:
        for name in ("mcp_server_library.py", "mcp_server_qector_bench.py"):
            text = (MCP_DIR / name).read_text(encoding="utf-8")
            start = text.index("def _check_pypi_freshness")
            body = text[start : text.index("urllib.request.urlopen", start)]
            self.assertIn("qector_airgap.require_network", body, name)

    def test_subprocess_is_confined_to_admin_implementations(self) -> None:
        allowed = {"mcp_server_qector_bench.py", "mcp_server_admin.py"}
        for path in SERVER_SOURCES:
            if path.name in allowed:
                continue
            text = path.read_text(encoding="utf-8")
            with self.subTest(file=path.name):
                self.assertNotRegex(text, r"^\s*import subprocess|^\s*from subprocess", "subprocess outside admin paths")
                self.assertNotRegex(text, r"\bos\.(system|popen|spawn|posix_spawn|exec[lv])")

    def test_only_stdio_transport_is_exposed(self) -> None:
        for path in SERVER_SOURCES:
            text = path.read_text(encoding="utf-8")
            with self.subTest(file=path.name):
                self.assertNotIn("streamable_http", text)
                self.assertNotIn("sse_server", text)
                self.assertNotIn("uvicorn", text)
                if "add_argument(\"--transport\"" in text:
                    self.assertIn('choices=("stdio",)', text)


@unittest.skipUnless(_mcp(), "mcp SDK not installed")
class GuardLifecycleTests(unittest.TestCase):
    def test_install_uninstall_and_counters(self) -> None:
        import socket

        import qector_airgap
        from qector_mcp_contract import QECTORNetworkDisabledError

        qector_airgap._uninstall_for_tests()
        try:
            status = qector_airgap.install(force=True, source="cli")
            self.assertTrue(status["air_gapped"])
            self.assertEqual(status["mode_source"], "cli")
            with self.assertRaises(QECTORNetworkDisabledError):
                socket.getaddrinfo("example.com", 443)
            self.assertGreaterEqual(qector_airgap.status()["blocked_attempts"], 1)
            # install() is idempotent.
            again = qector_airgap.install()
            self.assertTrue(again["guards"]["python_socket"])
            # The wheel's own native-core refusal (qector-decoder-v3 >= 1.0.1).
            import os

            self.assertTrue(again["guards"]["wheel_offline_flag"])
            self.assertEqual(os.environ.get("QECTOR_OFFLINE"), "1")
        finally:
            qector_airgap._uninstall_for_tests()
        self.assertFalse(qector_airgap.status()["guards"]["python_socket"])
        self.assertFalse(qector_airgap.status()["guards"]["wheel_offline_flag"])

    def test_allow_network_mode_reports_opt_in(self) -> None:
        import qector_airgap

        qector_airgap._uninstall_for_tests()
        try:
            status = qector_airgap.install(force=False, source="cli")
            self.assertFalse(status["air_gapped"])
            self.assertFalse(status["guards"]["wheel_offline_flag"])
            self.assertEqual(status["guards"]["pypi_freshness"], "opt_in")
            self.assertFalse(status["guards"]["python_socket"])
            self.assertTrue(status["guards"]["env_scrub"])
        finally:
            qector_airgap._uninstall_for_tests()

    def test_default_is_air_gapped(self) -> None:
        import qector_airgap

        saved = os.environ.pop("QECTOR_AIR_GAPPED", None)
        try:
            self.assertEqual(qector_airgap.air_gapped_requested(), (True, "default"))
            os.environ["QECTOR_AIR_GAPPED"] = "0"
            self.assertEqual(qector_airgap.air_gapped_requested(), (False, "environment"))
        finally:
            if saved is None:
                os.environ.pop("QECTOR_AIR_GAPPED", None)
            else:
                os.environ["QECTOR_AIR_GAPPED"] = saved


if __name__ == "__main__":
    unittest.main()
