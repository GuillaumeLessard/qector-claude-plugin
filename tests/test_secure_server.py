"""Behavioural tests for ``mcp/mcp_server_secure.py`` (qector-secure).

Covers the 2.0.0 control plane in-process (no subprocess): configuration,
tool assembly for both profiles, input and output schema validation, the
unknown-tool and request-size paths, the air-gap guard, the hash-chained
audit log, the integrity manifest gate and the schema catalog. The live
stdio conformance matrix lives in ``test_mcp_conformance.py``.
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MCP_DIR = ROOT / "mcp"
if str(MCP_DIR) not in sys.path:
    sys.path.insert(0, str(MCP_DIR))
os.environ.setdefault("QECTOR_SILENT", "1")


def _runtime_available() -> bool:
    return importlib.util.find_spec("mcp") is not None and importlib.util.find_spec("qector_decoder_v3") is not None


@unittest.skipUnless(_runtime_available(), "qector-decoder-v3 + mcp SDK not installed")
class SecureServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        import mcp_server_secure as secure
        import qector_airgap
        from qector_mcp_compat import result_wire_dict
        from qector_mcp_contract import reset_call_budget

        cls.secure = secure
        cls.airgap = qector_airgap
        cls.wire = staticmethod(result_wire_dict)
        cls.tmp = Path(tempfile.mkdtemp(prefix="qector-secure-test-"))
        os.environ["QECTOR_ARTIFACT_DIR"] = str(cls.tmp / "artifacts")
        os.environ.pop("QECTOR_AIR_GAPPED", None)
        reset_call_budget()
        cls.report = secure.configure(profile="research", audit_dir=str(cls.tmp / "audit"), strict_integrity=False)

    @classmethod
    def tearDownClass(cls) -> None:
        shutil.rmtree(cls.tmp, ignore_errors=True)
        os.environ.pop("QECTOR_ARTIFACT_DIR", None)
        os.environ.pop("QECTOR_AUDIT_DIR", None)

    def call(self, name: str, arguments: dict) -> tuple[bool, dict]:
        wire = self.wire(asyncio.run(self.secure._dispatch_mcp_call(name, arguments)))
        self.assertIn("structuredContent", wire)
        self.assertEqual(json.loads(wire["content"][0]["text"]), wire["structuredContent"])
        return bool(wire.get("isError", False)), wire["structuredContent"]

    # -- assembly ---------------------------------------------------------

    def test_startup_report_and_tool_inventory(self) -> None:
        self.assertEqual(self.report["server"], "qector-secure-mcp")
        self.assertTrue(self.report["air_gapped"])
        self.assertTrue(self.report["audit_enabled"])
        names = self.report["tools"]
        self.assertEqual(names, sorted(names))
        self.assertEqual(len(names), 41)
        for control in ("airgap_status", "integrity_check", "schema_catalog", "audit_log_status"):
            self.assertIn(control, names)
        self.assertIn("research_compat_report", names)
        self.assertIn("compat_report", names)
        safe_tools, stability, research = self.secure.assemble_tools("safe")
        self.assertEqual(len(safe_tools), 12)
        self.assertIsNone(research)
        self.assertEqual({stability[t.name] for t in safe_tools}, {"stable", "control"})

    def test_every_tool_has_input_and_output_schema(self) -> None:
        from jsonschema import Draft202012Validator
        from qector_mcp_compat import tool_annotations_dict, tool_input_schema, tool_output_schema

        for tool in self.secure.STATE.tools:
            with self.subTest(tool=tool.name):
                input_schema = tool_input_schema(tool)
                output_schema = tool_output_schema(tool)
                self.assertIsNotNone(output_schema)
                Draft202012Validator.check_schema(input_schema)
                Draft202012Validator.check_schema(output_schema)
                self.assertEqual(input_schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
                self.assertFalse(input_schema.get("additionalProperties", True))
                self.assertIn("readOnlyHint", tool_annotations_dict(tool))

    # -- validation -------------------------------------------------------

    def test_valid_decode_is_verified_and_audited(self) -> None:
        is_error, envelope = self.call("decode_syndrome", {"syndrome": [1, 0, 0, 1]})
        self.assertFalse(is_error)
        self.assertEqual(envelope["status"], "verified")
        self.assertEqual(envelope["contract_version"], "2.0")
        self.assertIn("theorem_1_syndrome_faithfulness", envelope["verification"]["checks"])
        self.assertIn("audit", envelope)
        self.assertRegex(envelope["audit"]["record_sha256"], r"^[0-9a-f]{64}$")

    def test_additional_property_is_invalid_input(self) -> None:
        is_error, envelope = self.call("decode_syndrome", {"syndrome": [1, 0, 0, 1], "bogus": 1})
        self.assertTrue(is_error)
        self.assertEqual(envelope["error"]["code"], "INVALID_INPUT")
        self.assertEqual(envelope["error"]["path"], "$")
        self.assertEqual(envelope["result"], {})

    def test_wrong_type_reports_json_path(self) -> None:
        is_error, envelope = self.call("decode_syndrome", {"syndrome": [1, 0, "x", 1]})
        self.assertTrue(is_error)
        self.assertEqual(envelope["error"]["code"], "INVALID_INPUT")
        self.assertEqual(envelope["error"]["path"], "$.syndrome[2]")

    def test_unknown_tool_is_stable_error(self) -> None:
        is_error, envelope = self.call("not_a_tool", {})
        self.assertTrue(is_error)
        self.assertEqual(envelope["error"]["code"], "UNKNOWN_TOOL")
        self.assertEqual(envelope["tool"], "unknown_tool")

    def test_oversized_request_is_refused_before_decoding(self) -> None:
        old = self.secure.STATE.max_request_bytes
        self.secure.STATE.max_request_bytes = 64
        try:
            is_error, envelope = self.call("decode_syndrome", {"syndrome": [0] * 200})
        finally:
            self.secure.STATE.max_request_bytes = old
        self.assertTrue(is_error)
        self.assertEqual(envelope["error"]["code"], "INVALID_INPUT")
        self.assertIn("limit", envelope["error"]["message"])

    def test_huge_array_fails_fast(self) -> None:
        import time

        started = time.perf_counter()
        is_error, envelope = self.call("decode_syndrome", {"syndrome": [1] * 100_000})
        self.assertTrue(is_error)
        self.assertEqual(envelope["error"]["code"], "INVALID_INPUT")
        # Lazy first-error validation: 100k items must not be enumerated. The
        # bound is generous so instrumented runs (tracemalloc, coverage) and
        # slow CI runners do not turn a performance property into flakiness.
        self.assertLess(time.perf_counter() - started, 20.0)
        self.assertLess(len(envelope["error"]["message"]), 600)

    def test_output_contract_violation_is_reported_not_forwarded(self) -> None:
        library = self.secure.library
        original = library.TOOL_FUNCTIONS["list_decoders"]
        library.TOOL_FUNCTIONS["list_decoders"] = lambda: {"decoders": "not-an-object", "reference_manual": library.REF_DOI}
        try:
            is_error, envelope = self.call("list_decoders", {})
        finally:
            library.TOOL_FUNCTIONS["list_decoders"] = original
        self.assertTrue(is_error)
        self.assertEqual(envelope["error"]["code"], "CONTRACT_VIOLATION")
        self.assertEqual(envelope["result"], {})

    def test_research_alias_dispatches_research_compat_report(self) -> None:
        is_error, envelope = self.call("research_compat_report", {})
        self.assertFalse(is_error)
        self.assertEqual(envelope["tool"], "research_compat_report")
        self.assertEqual(envelope["result"]["server"]["name"], "qector-research-mcp")
        self.assertEqual(envelope["scope"]["stability"], "provisional")

    # -- air-gap ----------------------------------------------------------

    def test_airgap_status_is_honest_about_native_surface(self) -> None:
        is_error, envelope = self.call("airgap_status", {})
        self.assertFalse(is_error)
        result = envelope["result"]
        self.assertTrue(result["air_gapped"])
        self.assertTrue(result["guards"]["python_socket"])
        self.assertTrue(result["guards"]["python_subprocess"])
        self.assertEqual(result["guards"]["pypi_freshness"], "disabled")
        surface = result["backend_network_surface"]
        self.assertFalse(surface["called_by_plugin"])
        self.assertFalse(surface["python_level_guard_blocks_native_core"])
        self.assertIn("https://api.stripe.com/v1/billing/meter_events", surface["embedded_endpoints"])
        self.assertIn("flush_usage", surface["network_capable_symbols"])

    def test_pypi_check_is_refused_without_network(self) -> None:
        for tool in ("compat_report", "research_compat_report", "env_block", "get_runtime_provenance"):
            with self.subTest(tool=tool):
                is_error, envelope = self.call(tool, {"check_pypi": True})
                self.assertFalse(is_error)
                self.assertEqual(envelope["result"]["pypi_freshness"]["status"], "disabled")
                self.assertEqual(envelope["scope"]["network"], "disabled_air_gapped")

    def test_socket_guard_blocks_egress_but_allows_loopback(self) -> None:
        from qector_mcp_contract import QECTORNetworkDisabledError

        with self.assertRaises(QECTORNetworkDisabledError):
            socket.create_connection(("pypi.org", 443), timeout=1)
        with self.assertRaises(QECTORNetworkDisabledError):
            socket.getaddrinfo("pypi.org", 443)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock, self.assertRaises(QECTORNetworkDisabledError):
            sock.connect(("93.184.216.34", 80))
        # Loopback must keep working: the event loop and stdio plumbing rely on it.
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        client = socket.create_connection(listener.getsockname(), timeout=1)
        client.close()
        listener.close()
        a, b = socket.socketpair()
        a.close()
        b.close()

    def test_subprocess_and_urllib_guards(self) -> None:
        import urllib.request

        from qector_mcp_contract import QECTORNetworkDisabledError

        with self.assertRaises(PermissionError):
            subprocess.Popen([sys.executable, "-c", "pass"])
        with self.assertRaises(QECTORNetworkDisabledError):
            urllib.request.urlopen("https://pypi.org/pypi/qector-decoder-v3/json", timeout=1)

    def test_billing_variables_are_scrubbed(self) -> None:
        for name in self.airgap.SCRUBBED_ENV_VARS:
            self.assertNotIn(name, os.environ)

    # -- audit ------------------------------------------------------------

    def test_audit_chain_is_valid_and_detects_tampering(self) -> None:
        from qector_audit import verify_chain

        for _ in range(3):
            self.call("list_decoders", {})
        is_error, envelope = self.call("audit_log_status", {})
        self.assertFalse(is_error)
        status = envelope["result"]
        self.assertTrue(status["enabled"])
        self.assertTrue(status["chain_valid"])
        self.assertGreaterEqual(status["records"], 4)
        path = Path(status["path"])
        lines = path.read_text(encoding="utf-8").splitlines()
        first = json.loads(lines[0])
        self.assertNotIn("arguments", first)
        self.assertRegex(first["arguments_sha256"], r"^[0-9a-f]{64}$")
        # Tamper with record 2 in a copy and verify the chain breaks there.
        tampered = self.tmp / "tampered.jsonl"
        record = json.loads(lines[1])
        record["tool"] = "something_else"
        lines[1] = json.dumps(record, sort_keys=True, separators=(",", ":"))
        tampered.write_text("\n".join(lines) + "\n", encoding="utf-8")
        valid, count, _head, first_bad = verify_chain(tampered)
        self.assertFalse(valid)
        self.assertEqual(first_bad, 2)
        self.assertEqual(count, 1)

    def test_audit_truncation_and_hmac(self) -> None:
        from qector_audit import AuditLog, QECTORAuditError, verify_chain

        for _ in range(2):
            self.call("list_decoders", {})
        status = self.call("audit_log_status", {})[1]["result"]
        path = Path(status["path"])
        lines = path.read_text(encoding="utf-8").splitlines()
        # Truncate the tail: the file still chains, but the running server
        # knows it wrote more records than the file now holds.
        path.write_text("\n".join(lines[:-2]) + "\n", encoding="utf-8")
        try:
            status = self.call("audit_log_status", {})[1]["result"]
            self.assertFalse(status["chain_valid"])
            self.assertFalse(status["matches_server_head"])
        finally:
            # audit_log_status itself appended a record after the truncation;
            # restore a consistent file for the remaining tests.
            path.write_text("\n".join(lines) + "\n" + path.read_text(encoding="utf-8").splitlines()[-1] + "\n", encoding="utf-8")
        # Keyed log: a forged record with recomputed keyless digests is rejected.
        key = b"k" * 32
        keyed_path = self.tmp / "keyed.jsonl"
        keyed = AuditLog(keyed_path, server="t", server_version="2.0.0", key=key)
        keyed.append(tool="x", arguments={}, envelope={"status": "ok"}, elapsed_ms=1.0)
        self.assertTrue(verify_chain(keyed_path, key=key)[0])
        self.assertFalse(verify_chain(keyed_path)[0])
        with self.assertRaises(QECTORAuditError):
            AuditLog(keyed_path, server="t", server_version="2.0.0", key=b"j" * 32)

    def test_rejected_input_does_not_consume_budget(self) -> None:
        from qector_mcp_contract import call_budget_snapshot

        before = call_budget_snapshot().get("threshold_sweep", 0)
        is_error, envelope = self.call(
            "threshold_sweep",
            {"distances": [3], "error_rates": [0.05], "trials": 2, "artifact_path": "/definitely/outside/x.json"},
        )
        self.assertTrue(is_error)
        self.assertEqual(envelope["error"]["code"], "IO_ERROR")
        self.assertEqual(call_budget_snapshot().get("threshold_sweep", 0), before)

    def test_os_launchers_are_guarded_and_wildcard_bind_refused(self) -> None:
        import os as _os

        from qector_mcp_contract import QECTORNetworkDisabledError

        with self.assertRaises(PermissionError):
            _os.system("true")
        with self.assertRaises(PermissionError):
            _os.popen("true")
        self.assertFalse(self.airgap._is_loopback_host("127.attacker.example"))
        self.assertFalse(self.airgap._is_loopback_host("0.0.0.0"))
        # "" and None are INADDR_ANY for bind/connect; only getaddrinfo may use them.
        self.assertFalse(self.airgap._is_loopback_host(""))
        self.assertFalse(self.airgap._is_loopback_host(None))
        self.assertTrue(self.airgap._is_loopback_host(None, allow_unspecified=True))
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as wildcard, self.assertRaises(QECTORNetworkDisabledError):
            wildcard.bind(("", 0))
        self.assertTrue(self.airgap._is_loopback_host("127.0.0.1"))
        self.assertTrue(self.airgap._is_loopback_host("::1"))
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            with self.assertRaises(QECTORNetworkDisabledError):
                sock.bind(("0.0.0.0", 0))
        finally:
            sock.close()
        self.assertIn("not a sandbox", self.call("airgap_status", {})[1]["result"]["guard_scope"])
        self.assertIs(socket.SocketType, socket.socket)
        with socket.SocketType(socket.AF_INET, socket.SOCK_STREAM) as sock, self.assertRaises(QECTORNetworkDisabledError):
            sock.connect(("8.8.8.8", 53))

    def test_unexpanded_desktop_placeholders_are_ignored(self) -> None:
        from qector_audit import audit_log_from_env

        saved = os.environ.get("QECTOR_AUDIT_DIR")
        os.environ["QECTOR_AUDIT_DIR"] = "${user_config.audit_dir}"
        try:
            self.assertFalse(audit_log_from_env(server="t", server_version="2.0.0").enabled)
            os.environ["QECTOR_ARTIFACT_DIR"] = "${user_config.nope}"
            root = self.secure.library._artifact_root()
            self.assertNotIn("${", str(root))
            self.assertEqual(root, self.secure.STATE.research._artifact_root())
        finally:
            os.environ["QECTOR_AUDIT_DIR"] = saved or ""
            os.environ["QECTOR_ARTIFACT_DIR"] = str(self.tmp / "artifacts")
        self.assertFalse(Path("${user_config.audit_dir}").exists())

    # -- integrity / catalog ---------------------------------------------

    def test_integrity_manifest_roundtrip_and_strict_gate(self) -> None:
        import qector_integrity
        from qector_mcp_contract import QECTORIntegrityError

        tree = self.tmp / "tree"
        if tree.exists():
            shutil.rmtree(tree)
        (tree / "mcp").mkdir(parents=True)
        (tree / "mcp" / "a.py").write_text("print(1)\n", encoding="utf-8")
        (tree / "requirements.txt").write_text("numpy\n", encoding="utf-8")
        manifest = qector_integrity.build_manifest(tree, version="2.0.0")
        self.assertEqual(set(manifest["files"]), {"mcp/a.py", "requirements.txt"})
        (tree / qector_integrity.MANIFEST_NAME).write_text(json.dumps(manifest), encoding="utf-8")
        report = qector_integrity.verify(tree, strict=True)
        self.assertTrue(report["passed"])
        (tree / "mcp" / "a.py").write_text("print(2)\n", encoding="utf-8")
        (tree / "mcp" / "b.py").write_text("", encoding="utf-8")
        report = qector_integrity.verify(tree, strict=True)
        self.assertFalse(report["passed"])
        self.assertEqual(report["mismatched"], ["mcp/a.py"])
        self.assertEqual(report["unlisted_runtime_files"], ["mcp/b.py"])
        # Missing manifest is never a pass.
        report = qector_integrity.verify(tree / "mcp", strict=False)
        self.assertFalse(report["passed"])
        self.assertFalse(report["manifest_present"])
        # The secure server refuses to start strictly against a mismatching manifest.
        with self.assertRaises(QECTORIntegrityError):
            self.secure.configure(profile="safe", strict_integrity=True, integrity_manifest=str(tree / qector_integrity.MANIFEST_NAME))
        # Restore the research configuration for the remaining tests.
        self.secure.configure(profile="research", audit_dir=str(self.tmp / "audit"), strict_integrity=False)

    def test_non_finite_result_is_a_contract_violation(self) -> None:
        original = self.secure.dispatch_tool
        self.secure.dispatch_tool = lambda name, args: {"rate": float("nan")} if name == "airgap_status" else original(name, args)
        try:
            is_error, envelope = self.call("airgap_status", {})
        finally:
            self.secure.dispatch_tool = original
        self.assertTrue(is_error)
        self.assertEqual(envelope["error"]["code"], "CONTRACT_VIOLATION")
        self.assertIn("non-finite", envelope["error"]["message"])

    def test_audit_write_failure_fails_closed(self) -> None:
        from qector_audit import AuditLog

        class Unwritable(AuditLog):
            def append(self, **kwargs):  # noqa: D401 - test double
                raise OSError(28, "No space left on device")

        original = self.secure.STATE.audit
        self.secure.STATE.audit = Unwritable(None, server="t", server_version="0")
        try:
            is_error, envelope = self.call("airgap_status", {})
        finally:
            self.secure.STATE.audit = original
        self.assertTrue(is_error)
        self.assertEqual(envelope["error"]["code"], "IO_ERROR")
        self.assertNotIn("audit", envelope)
        self.assertEqual(envelope["result"], {})

    def test_integrity_report_never_carries_the_home_directory(self) -> None:
        _is_error, envelope = self.call("integrity_check", {})
        home = str(Path.home())
        self.assertNotIn(home, json.dumps(envelope))
        self.assertNotIn(home, json.dumps(self.report))

    def test_schema_catalog_digests_are_stable(self) -> None:
        first = self.call("schema_catalog", {})[1]["result"]
        second = self.call("schema_catalog", {})[1]["result"]
        self.assertEqual(first["catalog_sha256"], second["catalog_sha256"])
        self.assertEqual(set(first["tools"]), set(self.report["tools"]))
        self.assertEqual(first["dialect"], "https://json-schema.org/draft/2020-12/schema")
        for name, entry in first["tools"].items():
            self.assertIn(entry["stability"], {"stable", "provisional", "control"}, name)

    def test_integrity_check_tool_reports_verification_honestly(self) -> None:
        is_error, envelope = self.call("integrity_check", {})
        result = envelope["result"]
        if result["passed"]:
            self.assertFalse(is_error)
            self.assertEqual(envelope["status"], "verified")
        else:
            self.assertTrue(is_error)
            self.assertEqual(envelope["error"]["code"], "INTEGRITY_FAILED")
            self.assertEqual(envelope["result"]["passed"], False)  # diagnostic payload is kept on a failed check


if __name__ == "__main__":
    unittest.main()
