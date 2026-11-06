"""Contract 2.0 regression tests: SDK compatibility layer, schema export
sync, error taxonomy, and the research-tool defects fixed in 2.0.0.
"""

from __future__ import annotations

import json
import math
import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MCP_DIR = ROOT / "mcp"
if str(MCP_DIR) not in sys.path:
    sys.path.insert(0, str(MCP_DIR))
os.environ.setdefault("QECTOR_SILENT", "1")


def _mcp() -> bool:
    # find_spec("mcp") would be fooled by this repository's own mcp/ directory
    # (a namespace package on sys.path); import the SDK for real.
    try:
        import mcp.types  # noqa: F401
    except Exception:
        return False
    return True


def _wheel() -> bool:
    try:
        import qector_decoder_v3  # noqa: F401
    except Exception:
        return False
    return True


@unittest.skipUnless(_mcp(), "mcp SDK not installed")
class _FixtureFamilies:
    """Register deliberately defective, test-only code families.

    qector-decoder-v3 1.0.1 fixed the wheel families that used to exercise
    the server's weak / degenerate / contradicted verdicts (1.0.0's rotated
    surface had distance 2, heavy_hex had unchecked qubits, color_code was
    degenerate). Those verdict paths must stay covered, so these fixtures
    rebuild each defect explicitly. Nothing here is registered outside tests.
    """

    FAMILIES = ("fixture_duplicate_column", "fixture_unchecked_qubit", "fixture_single_check")

    def __init__(self, library) -> None:
        self.library = library

    @staticmethod
    def duplicate_column(d: int):
        import qector_codes

        # Repetition code of length d plus qubit d duplicating qubit 0's column:
        # q0 + qd is undetectable and flips the logical, so the true distance is 2.
        checks = [[i, i + 1] for i in range(d - 1)]
        checks[0] = checks[0] + [d]
        return qector_codes.PluginCode(
            name=f"fixture_duplicate_column_d{d}", description="test fixture", check_to_qubits=checks,
            n_qubits=d + 1, logicals=[[0]], distance=d,
        )

    @staticmethod
    def unchecked_qubit(d: int):
        import qector_codes

        checks = [[i, i + 1] for i in range(d - 1)]
        return qector_codes.PluginCode(
            name=f"fixture_unchecked_qubit_d{d}", description="test fixture", check_to_qubits=checks,
            n_qubits=d + 1, logicals=[[0]], distance=d,
        )

    @staticmethod
    def single_check(d: int):
        import qector_codes

        return qector_codes.PluginCode(
            name=f"fixture_single_check_d{d}", description="test fixture", check_to_qubits=[[0, 1]],
            n_qubits=2, logicals=[[0]], distance=d,
        )

    def __enter__(self):
        import qector_codes

        self._saved = {name: getattr(qector_codes, name, None) for name in self.FAMILIES}
        qector_codes.fixture_duplicate_column = self.duplicate_column
        qector_codes.fixture_unchecked_qubit = self.unchecked_qubit
        qector_codes.fixture_single_check = self.single_check
        import mcp_server_qector_bench as bench

        for name in self.FAMILIES:
            self.library.FAMILY_REGISTRY[name] = {
                "generator": name, "code_factory": name, "kind": "size_code",
                "source": "plugin", "description": "test fixture",
            }
            bench.FAMILY_FACTORY[name] = name  # the research server routes through the library
        self._clear()
        return self

    def __exit__(self, *exc) -> None:
        import qector_codes

        import mcp_server_qector_bench as bench

        for name, value in self._saved.items():
            self.library.FAMILY_REGISTRY.pop(name, None)
            bench.FAMILY_FACTORY.pop(name, None)
            if value is None:
                if hasattr(qector_codes, name):
                    delattr(qector_codes, name)
            else:
                setattr(qector_codes, name, value)
        self._clear()

    def _clear(self) -> None:
        for cache in ("_CODE_CACHE", "_FAMILY_HEALTH_CACHE"):
            getattr(self.library, cache, {}).clear()


class SdkCompatTests(unittest.TestCase):
    def test_wire_names_are_camel_case_on_any_generation(self) -> None:
        from qector_mcp_compat import (
            SDK_VERSION,
            make_annotations,
            make_call_tool_result,
            make_tool,
            result_wire_dict,
            sdk_supported,
            tool_input_schema,
            tool_output_schema,
            tool_wire_dict,
        )

        tool = make_tool(
            name="x",
            description="d",
            input_schema={"type": "object", "properties": {}},
            output_schema={"type": "object"},
            annotations=make_annotations(read_only=True, destructive=False, idempotent=True, open_world=False),
        )
        wire = tool_wire_dict(tool)
        self.assertEqual(wire["inputSchema"], {"type": "object", "properties": {}})
        self.assertEqual(wire["outputSchema"], {"type": "object"})
        self.assertEqual(wire["annotations"]["readOnlyHint"], True)
        self.assertEqual(tool_input_schema(tool), {"type": "object", "properties": {}})
        self.assertEqual(tool_output_schema(tool), {"type": "object"})
        result = result_wire_dict(make_call_tool_result({"a": 1}, is_error=False))
        self.assertEqual(result["structuredContent"], {"a": 1})
        self.assertEqual(json.loads(result["content"][0]["text"]), {"a": 1})
        self.assertFalse(result["isError"])
        supported, detail = sdk_supported()
        self.assertTrue(supported, detail)
        self.assertIn(SDK_VERSION.split(".")[0], {"1", "2"})

    def test_unsupported_sdk_versions_are_named(self) -> None:
        import qector_mcp_compat as compat

        saved = compat.SDK_VERSION
        try:
            compat.SDK_VERSION = "1.26.0"
            ok, detail = compat.sdk_supported()
            self.assertFalse(ok)
            self.assertIn("CVE-2026-52869", detail)
            compat.SDK_VERSION = "3.0.0"
            self.assertFalse(compat.sdk_supported()[0])
            compat.SDK_VERSION = "2.3.0"
            self.assertTrue(compat.sdk_supported()[0])
        finally:
            compat.SDK_VERSION = saved


@unittest.skipUnless(_mcp(), "mcp SDK not installed")
class ContractTests(unittest.TestCase):
    def test_error_codes_are_closed_set_and_class_based(self) -> None:
        import qector_mcp_contract as c

        self.assertEqual(c.error_code(c.QECTORSchemaError("t", "m", "$")), "INVALID_INPUT")
        self.assertEqual(c.error_code(c.QECTORUnknownToolError("x")), "UNKNOWN_TOOL")
        self.assertEqual(c.error_code(c.QECTORNetworkDisabledError("x")), "NETWORK_DISABLED")
        self.assertEqual(c.error_code(c.QECTORContractViolation("x")), "CONTRACT_VIOLATION")
        self.assertEqual(c.error_code(c.QECTORIntegrityError("x")), "INTEGRITY_FAILED")
        self.assertEqual(c.error_code(c.QECTORResourceLimitError("x")), "RESOURCE_LIMIT")
        self.assertEqual(c.error_code(PermissionError("x")), "PERMISSION_DENIED")
        self.assertEqual(c.error_code(ImportError("x")), "DEPENDENCY_MISSING")
        for code in c.STABLE_ERROR_CODES:
            self.assertIn(code, c.ERROR_SCHEMA["properties"]["code"]["enum"])

    def test_output_schema_specialises_result_and_allows_empty_error_result(self) -> None:
        from jsonschema import Draft202012Validator

        import qector_mcp_contract as c

        schema = c.output_schema_for("wilson_ci", surface="research")
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema)
        error_envelope = c.error_envelope(ValueError("bad"), tool_name="wilson_ci", server_name="s", server_version="2.0.0", stability="provisional")
        self.assertEqual(list(validator.iter_errors(error_envelope)), [])
        good = c.result_envelope({"k": 1, "n": 10, "z": 1.96, "wilson_95": [0.0, 0.4], "reference_manual": "10.5281/zenodo.21941046"}, tool_name="wilson_ci", server_name="s", server_version="2.0.0", stability="provisional")
        self.assertEqual(list(validator.iter_errors(good)), [])
        bad = dict(good)
        bad["result"] = {"k": "one"}
        self.assertTrue(list(validator.iter_errors(bad)))

    def test_rate_limit_is_enforced(self) -> None:
        import qector_mcp_contract as c

        c.reset_call_budget()
        os.environ["QECTOR_MCP_RATE_LIMIT_PER_MINUTE"] = "3"
        try:
            c.reset_call_budget()
            for _ in range(3):
                c.consume_call_budget("list_decoders")
            with self.assertRaises(c.QECTORResourceLimitError):
                c.consume_call_budget("list_decoders")
        finally:
            os.environ.pop("QECTOR_MCP_RATE_LIMIT_PER_MINUTE", None)
            c.reset_call_budget()

    def test_home_directory_is_redacted_from_error_messages(self) -> None:
        import qector_mcp_contract as c

        home = str(Path.home())
        envelope = c.error_envelope(OSError(f"cannot open {home}/secret.json"), tool_name="x", server_name="s", server_version="2.0.0", stability="stable")
        if home != "/":
            self.assertNotIn(home, envelope["error"]["message"])


@unittest.skipUnless(_mcp() and _wheel(), "runtime not installed")
class ResearchFixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        import mcp_server_qector_bench as bench

        cls.bench = bench

    def test_sinter_task_template_no_longer_crashes(self) -> None:
        result = self.bench.dispatch_tool("sinter_task_template", {"family": "rotated_surface", "size": 3})
        self.assertEqual(result["task_template"]["decoder"], "qector_blossom")
        self.assertEqual(result["task_template"]["error_rate"], 0.05)

    def test_dem_collapse_combines_every_member(self) -> None:
        dem = "error(0.01) D0 D1 L0\nerror(0.02) D0 D1\nerror(0.03) D0 D1 L0\n"
        edge = self.bench.tool_dem_collapse_parallel(dem)["collapse"]["graphlike_edges"][0]
        expected = (1 - (1 - 0.02) * (1 - 0.04) * (1 - 0.06)) / 2
        self.assertAlmostEqual(edge["p_combined"], expected, places=15)
        self.assertEqual(edge["n_members"], 3)
        self.assertEqual(edge["winning_observables"], ["0"])
        two = self.bench.tool_dem_collapse_parallel("error(0.01) D0 D1\nerror(0.02) D0 D1\n")["collapse"]["graphlike_edges"][0]
        self.assertAlmostEqual(two["p_combined"], 0.0296, places=15)
        self.assertAlmostEqual(two["weight_log"], math.log(0.9704 / 0.0296), places=12)

    def test_dem_parser_rejects_bad_probabilities_and_handles_stim_forms(self) -> None:
        bad = ["error(1.5) D0 D1\n", "error(-0.1) D0 D1\n", "error() D0 D1\n", "error(0.1 0.2) D0 D1\n", "repeat 2 {\nerror(0.1) D0 D1\n}\n", "error(0.1) D0 X1\n"]
        for text in bad:
            with self.subTest(text=text), self.assertRaises(self.bench.QECTORInputError):
                self.bench.tool_dem_collapse_parallel(text)
        # p in {0, 1}: no finite weight, reported as null with a warning, never inf.
        result = self.bench.tool_dem_collapse_parallel("error(0) D0 D1\nerror(1) D0 D1\n")
        edge = result["collapse"]["graphlike_edges"][0]
        self.assertIsNone(edge["weight_log"])
        self.assertTrue(any("undefined" in w for w in result["warnings"]))
        # Boundary (weight-1) mechanisms collapse too.
        boundary = self.bench.tool_dem_collapse_parallel("error(0.1) D2\nerror(0.2) D2\n")["collapse"]["graphlike_edges"]
        self.assertEqual((boundary[0]["kind"], boundary[0]["n_members"]), ("boundary", 2))
        self.assertAlmostEqual(boundary[0]["p_combined"], 0.1 * 0.8 + 0.2 * 0.9, places=12)
        # Stim's ^ separator yields one mechanism per component; repeated detectors cancel.
        split = self.bench.tool_dem_collapse_parallel("error(0.03) D0 D1 ^ D1 D2\n")["collapse"]
        self.assertEqual([e["detectors"] for e in split["graphlike_edges"]], [["0", "1"], ["1", "2"]])
        cancelled = self.bench.tool_dem_collapse_parallel("error(0.01) D0 D0\n")["collapse"]
        self.assertEqual((cancelled["n_unique_edges"], cancelled["n_detector_free"]), (0, 1))
        # The worked example is recomputed, not a constant.
        check = self.bench.tool_dem_collapse_parallel("error(0.5) D0\n")["manual_worked_example_check"]
        self.assertTrue(check["matches"])
        self.assertAlmostEqual(check["computed_p_combined"], 0.0296, places=15)

    def test_research_wilson_has_no_floor_and_validates_z(self) -> None:
        lo, hi = self.bench.wilson_ci(0, 10**7)
        z = 1.959963985
        n = 10**7
        exact_hi = (z * z / (2 * n) + z * math.sqrt(z * z / (4 * n * n))) / (1 + z * z / n)
        self.assertEqual(lo, 0.0)
        self.assertAlmostEqual(hi, exact_hi, places=15)
        for bad_z in (0, -1, float("nan"), float("inf")):
            with self.subTest(z=bad_z), self.assertRaises(self.bench.QECTORInputError):
                self.bench.wilson_ci(1, 10, bad_z)
        with self.assertRaises(self.bench.QECTORInputError):
            self.bench.wilson_ci(5, 3)

    def test_code_distance_check_contradicts_a_wrong_label(self) -> None:
        import mcp_server_library as library

        with _FixtureFamilies(library):
            weak = self.bench.tool_code_distance_check("fixture_duplicate_column", 5)
        self.assertEqual((weak["verdict"], weak["distance_verified"], weak["nominal_distance"]), ("contradicted", False, 5))
        self.assertEqual(weak["effective_distance"]["min_logical_weight"], 2)
        repetition = self.bench.tool_code_distance_check("repetition", 5)
        self.assertEqual((repetition["verdict"], repetition["distance_verified"]), ("verified", True))

    def test_code_distance_check_verifies_the_1_0_1_wheel_families(self) -> None:
        # qector-decoder-v3 1.0.1 builds every family at its labelled distance
        # (1.0.0: rotated distance 2, unrotated and colour k=0, heavy_hex 2d-1).
        for family, size in (("rotated_surface", 5), ("unrotated_surface", 3), ("heavy_hex", 5), ("toric", 4)):
            with self.subTest(family=family):
                result = self.bench.tool_code_distance_check(family, size)
                self.assertEqual((result["verdict"], result["distance_verified"]), ("verified", True))
                self.assertEqual(result["effective_distance"]["min_logical_weight"], size)

    def test_microbench_times_decode_only_after_warmup(self) -> None:
        result = self.bench.tool_hot_path_microbench("rotated_surface", 5, shots=40, decoder_name="blossom", seed=7)
        self.assertEqual(result["warmup_shots"], self.bench.MICROBENCH_WARMUP_SHOTS)
        self.assertIn("decoder.decode", result["timed_window"])
        stats = result["latency_us"]
        self.assertEqual(stats["n"], 40)
        self.assertGreaterEqual(stats["ci95_mean"][0], 0.0)
        small = self.bench.tool_hot_path_microbench("rotated_surface", 3, shots=5, decoder_name="blossom", seed=7)
        self.assertIsNone(small["latency_us"]["ci95_mean"])

    def test_artifact_metadata_check_checks_a_real_artifact(self) -> None:
        import tempfile

        import mcp_server_library as library

        with tempfile.TemporaryDirectory() as tmp:
            os.environ["QECTOR_ARTIFACT_DIR"] = tmp
            try:
                sweep = library.threshold_sweep("repetition", [3], [0.1], trials=5, seed=1, artifact_path="sweep.json")
                checked = self.bench.tool_artifact_metadata_check("repetition", 3, artifact_path="sweep.json")
                self.assertEqual((checked["mode"], checked["checked"], checked["missing_fields"]), ("checked", True, []))
                self.assertTrue(checked["all_required_fields_present"])
                self.assertTrue(checked["sidecar_matches"])
                self.assertEqual(checked["artifact_sha256"], sweep["artifact"]["sha256"])
                # Tamper: sidecar no longer matches, reported not hidden.
                with open(os.path.join(tmp, "sweep.json"), "a", encoding="utf-8") as handle:
                    handle.write("\n")
                tampered = self.bench.tool_artifact_metadata_check("repetition", 3, artifact_path="sweep.json")
                self.assertFalse(tampered["sidecar_matches"])
                # Containment holds.
                with self.assertRaises(self.bench.QECTORInputError):
                    self.bench.tool_artifact_metadata_check("repetition", 3, artifact_path="../escape.json")
                template = self.bench.tool_artifact_metadata_check("repetition", 3)
                self.assertEqual((template["mode"], template["checked"], template["all_required_fields_present"]), ("template", False, False))
                self.assertNotIn("TBD", json.dumps(template))
            finally:
                os.environ.pop("QECTOR_ARTIFACT_DIR", None)

    def test_workload_hash_accepts_partial_workloads(self) -> None:
        only_syndrome = self.bench.dispatch_tool("workload_hash", {"syndrome": [1, 0]})
        self.assertEqual(only_syndrome["workload_keys"], ["syndrome_bytes"])
        with self.assertRaises(self.bench.QECTORInputError):
            self.bench.dispatch_tool("workload_hash", {})

    def test_faithfulness_check_reports_mismatch_indices(self) -> None:
        H = [[1, 1, 0], [0, 1, 1]]
        ok = self.bench.tool_decode_faithfulness_check(H, [1, 0], [1, 0, 0])
        self.assertTrue(ok["syndrome_valid"])
        self.assertEqual(ok["syndrome_mismatch_indices"], [])
        bad = self.bench.tool_decode_faithfulness_check(H, [1, 1], [1, 0, 0])
        self.assertFalse(bad["syndrome_valid"])
        self.assertEqual(bad["syndrome_mismatch_indices"], [1])
        self.assertEqual(bad["computed_syndrome"], [1, 0])

    def test_license_check_uses_live_wheel_not_a_table(self) -> None:
        result = self.bench.tool_license_active_check()
        self.assertEqual(result["source"], "live_wheel")
        self.assertNotIn("tier_table", result)
        self.assertNotIn("tier_table", json.dumps(result))

    def test_microbench_rejects_matrix_only_decoders(self) -> None:
        with self.assertRaises(self.bench.QECTORInputError):
            self.bench.tool_hot_path_microbench("rotated_surface", 3, shots=2, decoder_name="space_time")

    def test_code_family_info_exposes_health(self) -> None:
        import mcp_server_library as library

        with _FixtureFamilies(library):
            info = self.bench.tool_code_family_info("fixture_single_check", 3)
        self.assertEqual(info["health"]["status"], "degenerate")
        info = self.bench.tool_code_family_info("rotated_surface", 3)
        self.assertEqual(info["health"]["status"], "ok")
        info = self.bench.tool_code_family_info("color_code", 3)
        self.assertEqual(info["health"]["status"], "ok")
        self.assertFalse(info["health"]["graphlike"])


@unittest.skipUnless(_mcp() and _wheel(), "runtime not installed")
class VerificationStateTests(unittest.TestCase):
    def test_only_checking_tools_are_verified(self) -> None:
        from qector_mcp_contract import result_envelope

        def env(tool: str, result: dict) -> dict:
            return result_envelope(result, tool_name=tool, server_name="t", server_version="0", stability="stable")

        self.assertEqual(env("build_code_from_matrix", {"rank": 0})["status"], "not_checked")
        self.assertEqual(env("system_setup", {"actions_executed": []})["status"], "not_checked")
        answered = env("decode_faithfulness_check", {"syndrome_valid": False, "syndrome_mismatch_indices": [1]})
        self.assertEqual((answered["status"], answered["verification"]["status"]), ("verified", "verified"))
        self.assertNotIn("error", answered)
        failed = env("integrity_check", {"passed": False, "mismatched": ["x"]})
        self.assertEqual((failed["status"], failed["error"]["code"]), ("error", "INTEGRITY_FAILED"))
        self.assertEqual(failed["result"]["mismatched"], ["x"])

    def test_input_error_classes_map_before_message_heuristics(self) -> None:
        from qector_mcp_contract import error_code

        class QECTORInputError(ValueError):
            pass

        self.assertEqual(error_code(QECTORInputError("k cannot exceed n")), "INVALID_INPUT")
        self.assertEqual(error_code(QECTORInputError("limit reached")), "INVALID_INPUT")


@unittest.skipUnless(_mcp() and _wheel(), "runtime not installed")
class AdminBudgetTests(unittest.TestCase):
    def test_refused_admin_calls_do_not_consume_budget(self) -> None:
        import mcp_server_admin as admin
        from qector_mcp_contract import reset_call_budget

        reset_call_budget()
        os.environ.pop("QECTOR_ADMIN_ENABLED", None)
        for _ in range(5):
            with self.assertRaises(admin.QECTORAdminPermissionError):
                admin.dispatch_tool("workbench_probe", {"confirm": True, "executable": "/nonexistent/qector-workbench", "expected_sha256": "0" * 64})
        os.environ["QECTOR_ADMIN_ENABLED"] = "1"
        try:
            for _ in range(5):
                with self.assertRaises(admin.QECTORAdminPermissionError):
                    admin.dispatch_tool("workbench_probe", {"confirm": False, "executable": "/nonexistent/qector-workbench", "expected_sha256": "0" * 64})
        finally:
            os.environ.pop("QECTOR_ADMIN_ENABLED", None)
            reset_call_budget()


@unittest.skipUnless(_mcp() and _wheel(), "runtime not installed")
class LibraryFixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        import mcp_server_library as library

        cls.library = library

    def test_degenerate_family_is_refused_and_listed(self) -> None:
        with _FixtureFamilies(self.library):
            families = self.library.list_code_families()["families"]
            self.assertEqual(families["fixture_single_check"]["health"]["status"], "degenerate")
            self.assertFalse(families["fixture_single_check"]["single_decode"])
            # Duplicate parity-check columns: an undetectable weight-2 logical
            # error exists, so the family is reported weak with the witness,
            # never "ok" (this was the 1.0.0 wheel's rotated_surface_code).
            weak = families["fixture_duplicate_column"]["health"]
            self.assertEqual(weak["status"], "weak")
            self.assertEqual(weak["effective_distance"]["min_logical_weight"], 2)
            self.assertTrue(weak["effective_distance"]["exact"])
            self.assertTrue(any("effective distance is 2" in note for note in weak["notes"]))
            with self.assertRaises(self.library.QECTORInputError):
                self.library.decode_single("fixture_single_check", 3)
        families = self.library.list_code_families()["families"]
        # qector-decoder-v3 1.0.1: every wheel family is at its labelled distance.
        for name in ("rotated_surface", "unrotated_surface", "heavy_hex", "toric", "repetition", "color_code"):
            with self.subTest(family=name):
                health = families[name]["health"]
                self.assertEqual(health["status"], "ok")
                self.assertEqual(health["effective_distance"]["min_logical_weight"], 3)
        # The 6.6.6 colour code is a real code now but not graphlike: listed,
        # never offered to the matching decoders.
        self.assertFalse(families["color_code"]["single_decode"])
        self.assertTrue(any("not graphlike" in note for note in families["color_code"]["health"]["notes"]))
        with self.assertRaises(self.library.QECTORInputError):
            self.library.decode_single("color_code", 3)

    def test_effective_distance_probe_is_independent_of_nominal_distance(self) -> None:
        import numpy as np

        # Repetition code d=5: exact distance 5.
        code = self.library._code_for_family("repetition", 5)
        report = self.library.effective_distance(self.library._code_matrix(code), self.library._logical_matrix(code), nominal=5)
        self.assertEqual((report["min_logical_weight"], report["exact"]), (5, True))
        # A hand-built H with a duplicate column that the logical distinguishes: distance 2.
        H = np.array([[1, 1, 0, 0], [0, 1, 1, 1]], dtype=np.uint8)
        L = np.array([[0, 0, 1, 0]], dtype=np.uint8)
        H[:, 3] = H[:, 2]
        report = self.library.effective_distance(H, L, nominal=3)
        self.assertEqual((report["min_logical_weight"], report["exact"], report["witness"]), (2, True, [2, 3]))
        # Duplicate columns that the logical does NOT distinguish are harmless.
        L2 = np.array([[0, 0, 1, 1]], dtype=np.uint8)
        report = self.library.effective_distance(H, L2, nominal=3)
        self.assertNotEqual(report["min_logical_weight"], 2)
        # Zero column carrying a logical: distance 1.
        H0 = np.array([[1, 1, 0], [0, 1, 0]], dtype=np.uint8)
        report = self.library.effective_distance(H0, np.array([[0, 0, 1]], dtype=np.uint8), nominal=3)
        self.assertEqual((report["min_logical_weight"], report["witness"]), (1, [2]))
        # Budget exhaustion yields a lower bound, never a fabricated exact value
        # (graph method disabled so the enumeration path is what runs).
        code = self.library._code_for_family("heavy_hex", 7)
        saved = self.library.MAX_GRAPH_DISTANCE_WORK
        self.library.MAX_GRAPH_DISTANCE_WORK = 0
        try:
            report = self.library.effective_distance(self.library._code_matrix(code), self.library._logical_matrix(code), nominal=7, search_budget=2000)
        finally:
            self.library.MAX_GRAPH_DISTANCE_WORK = saved
        self.assertFalse(report["exact"])
        self.assertIsNone(report["min_logical_weight"])
        self.assertGreaterEqual(report["lower_bound"], 2)
        # No logicals: cannot score.
        self.assertIsNone(self.library.effective_distance(H0, None, nominal=3)["lower_bound"])

    def test_graphlike_exact_distance_agrees_with_brute_force(self) -> None:
        """The shortest-odd-cycle method must equal exhaustive enumeration wherever both run."""
        import numpy as np

        lib = self.library
        cases = [("toric", 3), ("repetition", 5), ("ring", 6), ("heavy_hex", 3), ("rotated_surface", 3), ("rotated_surface_corrected", 3), ("rotated_surface_corrected", 5)]
        saved = lib.MAX_GRAPH_DISTANCE_WORK
        for family, size in cases:
            with self.subTest(family=family, size=size):
                code = lib._code_for_family(family, size)
                H, L = lib._code_matrix(code), lib._logical_matrix(code)
                lib.MAX_GRAPH_DISTANCE_WORK = saved
                graph = lib.effective_distance(H, L, nominal=size)
                lib.MAX_GRAPH_DISTANCE_WORK = 0  # force enumeration, searched up to the full qubit count
                brute = lib.effective_distance(H, L, nominal=H.shape[1], search_budget=2_000_000)
                lib.MAX_GRAPH_DISTANCE_WORK = saved
                self.assertTrue(graph["exact"])
                self.assertEqual(graph["min_logical_weight"], brute["min_logical_weight"])
                # the witness is a real undetectable logical error of that weight
                e = np.zeros(H.shape[1], dtype=np.int64)
                e[graph["witness"]] = 1
                self.assertFalse(((H.astype(np.int64) @ e) % 2).any())
                self.assertTrue(((L.astype(np.int64) @ e) % 2).any())
                self.assertEqual(len(graph["witness"]), graph["min_logical_weight"])

    def test_plugin_rotated_surface_has_the_distance_it_claims(self) -> None:
        import qector_codes

        for d in (3, 5, 7, 9, 11):
            with self.subTest(d=d):
                code = qector_codes.rotated_surface_corrected(d)
                self.assertTrue(code.is_matching_graph())
                self.assertEqual((code.n_qubits, code.n_checks, code.num_logical_qubits), (d * d, (d * d - 1) // 2, 1))
                report = self.library.effective_distance(code.parity_check_matrix(), code.logicals_matrix(), nominal=d)
                self.assertEqual((report["min_logical_weight"], report["exact"]), (d, True))
        # Since qector-decoder-v3 1.0.1 the wheel's own families measure at
        # their labels too (1.0.0: rotated 2, heavy_hex 2d-1); measured, never assumed.
        wheel = self.library.family_health("rotated_surface", 7)["effective_distance"]
        self.assertEqual((wheel["min_logical_weight"], wheel["exact"]), (7, True))
        hex7 = self.library.family_health("heavy_hex", 7)["effective_distance"]
        self.assertEqual((hex7["min_logical_weight"], hex7["exact"]), (7, True))
        families = self.library.list_code_families()["families"]
        self.assertEqual(families["rotated_surface_corrected"]["source"], "plugin")
        self.assertEqual(families["rotated_surface_corrected"]["health"]["status"], "ok")
        self.assertTrue(families["rotated_surface_corrected"]["single_decode"])
        # A construction that fails its own self-check is refused, not served.
        original = qector_codes.rotated_surface_checks
        qector_codes.rotated_surface_checks = lambda d: ([[1, 2]], [[0]], 3)  # qubit 0 unchecked and logical: distance 1 under a d=3 label
        try:
            with self.assertRaises(RuntimeError):
                qector_codes.rotated_surface_corrected(3)
        finally:
            qector_codes.rotated_surface_checks = original

    def test_sweep_rows_carry_effective_distance_and_wall_clock(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            os.environ["QECTOR_ARTIFACT_DIR"] = tmp
            try:
                result = self.library.threshold_sweep("rotated_surface", [3, 5], [0.05], trials=20, seed=3)
                with _FixtureFamilies(self.library):
                    weak = self.library.threshold_sweep("fixture_duplicate_column", [3, 5], [0.05], trials=20, seed=3)
            finally:
                os.environ.pop("QECTOR_ARTIFACT_DIR", None)
        for row in result["results"]:
            self.assertEqual(row["effective_distance"]["min_logical_weight"], row["distance"])
        for row in weak["results"]:
            self.assertEqual(row["effective_distance"]["min_logical_weight"], 2)
        self.assertTrue(any("effective distance is 2" in w for w in weak["warnings"]))
        self.assertIn("wall_clock_seconds", result["harness"])
        self.assertNotIn("theorem1_violations", result["harness"])

    def test_sweep_wall_clock_budget_is_enforced(self) -> None:
        from qector_mcp_contract import QECTORResourceLimitError

        saved = self.library.MAX_SWEEP_SECONDS
        self.library.MAX_SWEEP_SECONDS = 0.0
        try:
            with self.assertRaises(QECTORResourceLimitError):
                self.library.threshold_sweep("repetition", [3], [0.1], trials=5, seed=1)
        finally:
            self.library.MAX_SWEEP_SECONDS = saved

    def test_toric_size_is_capped_by_construction_cost(self) -> None:
        from qector_mcp_contract import QECTORResourceLimitError

        with self.assertRaises(QECTORResourceLimitError):
            self.library._code_for_family("toric", self.library.FAMILY_MAX_SIZE["toric"] + 1)

    def test_unreachable_syndrome_is_invalid_input_not_decoder_blame(self) -> None:
        with self.assertRaises(self.library.QECTORInputError) as ctx:
            self.library.decode_syndrome("ring", 3, [1, 0, 0])
        self.assertIn("not in the image of H", str(ctx.exception))
        # A reachable syndrome still decodes.
        self.assertTrue(self.library.decode_syndrome("ring", 3, [1, 1, 0])["syndrome_valid"])

    def test_code_objects_are_cached_per_process(self) -> None:
        first = self.library._code_for_family("repetition", 9)
        self.assertIs(first, self.library._code_for_family("repetition", 9))

    def test_weak_family_decodes_with_warning(self) -> None:
        with _FixtureFamilies(self.library):
            result = self.library.decode_single("fixture_unchecked_qubit", 3, seed=1)
        self.assertTrue(result["syndrome_valid"])
        self.assertTrue(any("participate in no check" in w for w in result["warnings"]))

    def test_artifact_root_is_outside_install_dir(self) -> None:
        saved = os.environ.pop("QECTOR_ARTIFACT_DIR", None)
        try:
            root = self.library._artifact_root()
            self.assertNotEqual(root, (ROOT / "artifacts").resolve())
            self.assertTrue(str(root).endswith("artifacts"))
        finally:
            if saved is not None:
                os.environ["QECTOR_ARTIFACT_DIR"] = saved

    def test_compat_report_reports_windows_and_policy(self) -> None:
        report = self.library.compat_report()
        self.assertIn("network_policy", report)
        self.assertEqual(report["python"]["supported_window"], ">=3.10,<3.14")
        self.assertIn("supported", report["mcp_sdk"])


@unittest.skipUnless(_mcp() and _wheel(), "runtime not installed")
class SchemaExportTests(unittest.TestCase):
    def setUp(self) -> None:
        # These tests spawn helper scripts; lift the in-process subprocess
        # guard if an earlier test module installed it, so module order
        # cannot make them fail.
        import qector_airgap

        if qector_airgap.status()["guards"].get("python_subprocess"):
            qector_airgap._uninstall_for_tests()

    def test_committed_schemas_match_live_servers(self) -> None:
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "export_schemas.py"), "--check"],
            capture_output=True,
            text=True,
            env={**os.environ, "QECTOR_SILENT": "1"},
            timeout=180,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_lockfile_is_hashed_and_sbom_has_checksums(self) -> None:
        lock = (ROOT / "requirements.lock").read_text(encoding="utf-8")
        pins = [line for line in lock.splitlines() if "==" in line and not line.startswith("#")]
        self.assertGreaterEqual(len(pins), 25)
        self.assertEqual(lock.count("--hash=sha256:"), lock.count("--hash="))
        for pin in pins:
            self.assertTrue(pin.rstrip().endswith("\\"), f"{pin} carries no hash continuation")

    def test_integrity_manifest_matches_tree(self) -> None:
        if not (ROOT / "INTEGRITY.json").is_file():
            self.skipTest("INTEGRITY.json not generated in this checkout")
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "generate_integrity_manifest.py"), "--check"],
            capture_output=True,
            text=True,
            timeout=120,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)


if __name__ == "__main__":
    unittest.main()
