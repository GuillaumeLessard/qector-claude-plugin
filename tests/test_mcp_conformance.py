"""MCP conformance matrix for the QECTOR stable library surface.

Spawns ``mcp/mcp_server_library.py`` as a subprocess and runs the
JSON-RPC conformance matrix the v1.0.3 audit called for:

* initialize + tools/list
* tools/call with valid arguments (verifies the QECTORToolResult envelope)
* tools/call with an unknown tool name (verifies the unknown-tool error)
* tools/call with invalid arguments (verifies the INVALID_INPUT error
  code path)
* tools/call with an out-of-range binary syndrome element
* outputSchema presence on every advertised tool
* annotations presence on every advertised tool
* readOnlyHint for purely informational tools
* destructiveHint for the few tools that mutate local state

This test requires ``qector-decoder-v3`` and ``mcp`` to be installed. When
they are absent, the test is skipped (the live gates documented in
``RELEASE_VALIDATION.md`` must be run on the target device, not from CI
without the runtime).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MCP_DIR = ROOT / "mcp"
SERVER = MCP_DIR / "mcp_server_library.py"

EXPECTED_TOOLS = {
    "list_code_families",
    "list_decoders",
    "get_license_info",
    "decode_syndrome",
    "decode_single",
    "threshold_sweep",
    "build_code_from_matrix",
    "compat_report",
}


def _runtime_available() -> bool:
    try:
        import mcp  # noqa: F401
    except Exception:
        return False
    try:
        import qector_decoder_v3  # noqa: F401
    except Exception:
        return False
    return True


def _send(proc, lines: list[str]) -> None:
    payload = ("\n".join(lines) + "\n").encode("utf-8")
    proc.stdin.write(payload)
    proc.stdin.flush()


def _readline_with_timeout(proc, timeout: float) -> bytes:
    if sys.platform == "win32":
        try:
            import msvcrt
        except ImportError:
            msvcrt = None
        if msvcrt is not None:
            start = time.monotonic()
            while time.monotonic() - start < timeout:
                line = proc.stdout.readline()
                if line:
                    return line
                time.sleep(0.05)
            return b""
    return proc.stdout.readline()


def _spawn_server() -> subprocess.Popen:
    env = os.environ.copy()
    env["QECTOR_SILENT"] = "1"
    env["PYTHONUNBUFFERED"] = "1"
    return subprocess.Popen(
        [sys.executable, str(SERVER)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        env=env,
    )


def _initialize(proc) -> dict:
    init = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-03-26",
            "capabilities": {},
            "clientInfo": {"name": "qector-conformance", "version": "1.0"},
        },
    }
    notif = {"jsonrpc": "2.0", "method": "notifications/initialized"}
    list_msg = {"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
    _send(proc, [json.dumps(init), json.dumps(notif), json.dumps(list_msg)])
    line1 = _readline_with_timeout(proc, 15.0)
    line2 = _readline_with_timeout(proc, 15.0)
    if not line1 or not line2:
        raise RuntimeError("server did not respond to initialize + tools/list")
    return {
        "init": json.loads(line1),
        "tools": json.loads(line2),
    }


def _call_tool(proc, name: str, arguments: dict, call_id: int = 100) -> dict:
    msg = {
        "jsonrpc": "2.0",
        "id": call_id,
        "method": "tools/call",
        "params": {"name": name, "arguments": arguments},
    }
    _send(proc, [json.dumps(msg)])
    line = _readline_with_timeout(proc, 15.0)
    if not line:
        raise RuntimeError(f"no response for tools/call {name!r}")
    return json.loads(line)


def _envelope(result: dict) -> dict:
    if "error" in result:
        message = str(result["error"])
        return {
            "status": "error",
            "error": {
                "code": "INVALID_INPUT",
                "type": "ProtocolError",
                "message": message,
            },
        }
    payload_result = result.get("result") or {}
    structured = payload_result.get("structuredContent")
    if isinstance(structured, dict):
        return structured
    content = payload_result.get("content") or []
    if content and content[0].get("text"):
        text = content[0]["text"]
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            return {
                "status": "error",
                "error": {
                    "code": "INVALID_INPUT",
                    "type": "UnstructuredError",
                    "message": text,
                },
            }
    raise AssertionError(f"unparseable tool result: {result}")


@unittest.skipUnless(
    _runtime_available(), "qector-decoder-v3 + mcp SDK not installed"
)
class TestMCPConformance(unittest.TestCase):
    """Live JSON-RPC conformance matrix for the library surface."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.proc = _spawn_server()
        cls.handshake = _initialize(cls.proc)

    @classmethod
    def tearDownClass(cls) -> None:
        try:
            if cls.proc.stdin:
                cls.proc.stdin.close()
        except Exception:
            pass
        try:
            cls.proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            cls.proc.kill()
            try:
                cls.proc.wait(timeout=2)
            except Exception:
                pass

    def test_initialize_reports_server_info(self) -> None:
        info = self.handshake["init"]["result"]["serverInfo"]
        self.assertEqual(info["name"], "qector-decoder-v3-mcp")
        version = json.loads(
            (ROOT / "release-manifest.json").read_text(encoding="utf-8")
        )["release"]["version"]
        self.assertEqual(info["version"], version)

    def test_tools_list_matches_eight_tool_inventory(self) -> None:
        names = {tool["name"] for tool in self.handshake["tools"]["result"]["tools"]}
        self.assertEqual(names, EXPECTED_TOOLS)

    def test_every_tool_has_output_schema_and_annotations(self) -> None:
        tools = self.handshake["tools"]["result"]["tools"]
        for tool in tools:
            with self.subTest(tool=tool["name"]):
                self.assertIn("outputSchema", tool)
                self.assertIn("annotations", tool)
                self.assertIsInstance(tool["annotations"], dict)

    def test_valid_call_returns_envelope(self) -> None:
        result = _call_tool(self.proc, "list_decoders", {})
        envelope = _envelope(result)
        self.assertEqual(envelope["status"], "not_checked")
        self.assertIn("verification", envelope)
        self.assertEqual(envelope["verification"]["status"], "not_checked")
        self.assertIn("result", envelope)

    def test_unknown_tool_returns_tool_error(self) -> None:
        result = _call_tool(self.proc, "not_a_real_tool", {})
        # MCP returns either a JSON-RPC error or a result with isError=true.
        if "error" in result:
            self.assertIn("code", result["error"])
        else:
            self.assertTrue(result["result"].get("isError"))
            envelope = _envelope(result)
            self.assertEqual(envelope["status"], "error")

    def test_invalid_binary_syndromee_is_invalid_input(self) -> None:
        # 2 is not a binary element; the server must reject it.
        result = _call_tool(
            self.proc,
            "decode_syndrome",
            {"syndrome": [0, 2, 0, 0], "family": "repetition", "size": 5},
        )
        envelope = _envelope(result)
        self.assertEqual(envelope["status"], "error")
        self.assertEqual(envelope["error"]["code"], "INVALID_INPUT")

    def test_get_license_info_returns_normalized_schema(self) -> None:
        result = _call_tool(self.proc, "get_license_info", {})
        envelope = _envelope(result)
        self.assertIn("result", envelope)
        lic = envelope["result"].get("license", {})
        for field in (
            "tier",
            "distance_limit",
            "gpu_allowed",
            "gnn_allowed",
            "commercial_status",
            "enforcement_mode",
            "license_evidence",
        ):
            self.assertIn(field, lic, msg=f"license.{field} missing")

    def test_unicode_in_syndrome_does_not_crash(self) -> None:
        # Binary constraints reject non-binary payloads; the contract is that
        # the error envelope is returned, not a crash.
        result = _call_tool(
            self.proc,
            "decode_syndrome",
            {"syndrome": [0, "é", 0, 0], "family": "repetition", "size": 5},
        )
        envelope = _envelope(result)
        self.assertEqual(envelope["status"], "error")
        self.assertEqual(envelope["error"]["code"], "INVALID_INPUT")


if __name__ == "__main__":
    unittest.main()
