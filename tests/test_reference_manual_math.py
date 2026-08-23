"""Executable proof obligations for QECTOR Decoder v3 manual v1.0.0.

Run with:

    python -m unittest discover -s tests -v

The tests are intentionally independent of the PDF text at runtime. Their
inputs and assertions are transcribed from the manual's stated definitions and
worked examples, then checked against the live qector-decoder-v3==1.0.0 wheel.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_PYTHON_DIR = ROOT / "python"
if str(_PYTHON_DIR) not in sys.path:
    sys.path.insert(0, str(_PYTHON_DIR))

import numpy as np  # noqa: E402
import qector_decoder_v3 as qector  # noqa: E402
from qector_decoder_v3 import BlossomDecoder, codes  # noqa: E402
from qector_math_ground_truth import (  # noqa: E402
    all_binary_vectors,
    ambiguity_component_sum,
    bit_identity,
    cluster_parity,
    collision_time,
    dem_collapse_probability,
    dem_weight,
    detector_differences,
    edge_slack,
    f2_mat_vec,
    gf2_solve,
    graphlike,
    peel_tree,
    peeling_work,
    row_space_contains,
    telescope_differences,
    theorem_1_obligation,
    theorem_2_obligation,
    two_stage_css_obligation,
    wilson_ci,
)


ROOT = Path(__file__).resolve().parents[1]
SERVER_PATH = ROOT / "mcp" / "mcp_server_library.py"


def load_library_server():
    """Load the local server without shadowing the installed ``mcp`` package."""
    spec = importlib.util.spec_from_file_location("qector_library_server", SERVER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {SERVER_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def matrix_from_checks(checks: list[list[int]], n_qubits: int) -> np.ndarray:
    matrix = np.zeros((len(checks), n_qubits), dtype=np.uint8)
    for check, qubits in enumerate(checks):
        matrix[check, qubits] = 1
    return matrix


class ManualArithmeticTests(unittest.TestCase):
    def test_appendix_e1_steane_syndrome(self) -> None:
        checks = [[3, 4, 5, 6], [1, 2, 5, 6], [0, 2, 4, 6]]
        matrix = matrix_from_checks(checks, 7)
        error = [0, 0, 0, 0, 0, 1, 0]
        self.assertEqual(f2_mat_vec(matrix, error), (1, 1, 0))
        self.assertEqual(
            theorem_1_obligation(matrix, error, error)["syndrome"], (1, 1, 0)
        )

    def test_appendix_e2_wilson_matches_manual_and_library(self) -> None:
        expected = (0.0054407544447740265, 0.018309468872823392)
        self.assertAlmostEqual(wilson_ci(10, 1000)[0], expected[0], places=15)
        self.assertAlmostEqual(wilson_ci(10, 1000)[1], expected[1], places=15)
        self.assertTrue(0.0 <= wilson_ci(0, 1)[0] <= wilson_ci(0, 1)[1] <= 1.0)
        self.assertTrue(0.0 <= wilson_ci(1, 1)[0] <= wilson_ci(1, 1)[1] <= 1.0)
        from qector_decoder_v3.ler import wilson_ci as library_wilson_ci

        self.assertEqual(library_wilson_ci(10, 1000), expected)

    def test_appendix_e3_dem_collapse_and_weight(self) -> None:
        collapsed = dem_collapse_probability(0.01, 0.02)
        self.assertAlmostEqual(collapsed, 0.0296, places=15)
        self.assertAlmostEqual(dem_weight(collapsed), 3.4899339962998255, places=14)
        self.assertEqual(dem_weight(0.0), float("inf"))
        self.assertEqual(dem_weight(1.0), float("-inf"))

    def test_theorem_15_appendix_e4_two_stage_css_feedforward(self) -> None:
        hx = [[1, 1, 0], [0, 1, 1]]
        hz = [[0, 1, 1], [1, 1, 0]]
        cross = [[0, 1, 0], [1, 0, 0]]
        sx = [1, 0]
        sz = [1, 1]
        cx = [1, 0, 0]
        cz = [0, 0, 1]
        result = two_stage_css_obligation(hx, hz, cross, sx, sz, cx, cz)
        self.assertEqual(result["induced_z"], (0, 1))
        self.assertEqual(result["updated_z"], (1, 0))
        self.assertEqual(result["combined_z"], (1, 1))
        self.assertTrue(result["faithful"])

    def test_dem_weight_is_monotone_on_physical_probability(self) -> None:
        self.assertGreater(dem_weight(0.01), dem_weight(0.02))


class TheoremObligationTests(unittest.TestCase):
    def test_theorem_1_equivalence_exhaustive_on_repetition_matrix(self) -> None:
        matrix = [[1, 1, 0], [0, 1, 1]]
        for error in all_binary_vectors(3):
            for correction in all_binary_vectors(3):
                result = theorem_1_obligation(matrix, error, correction)
                self.assertTrue(result["equivalent"], result)

    def test_theorem_2_stabilizer_and_logical_cosets(self) -> None:
        matrix = [
            [0, 0, 0, 1, 1, 1, 1],
            [0, 1, 1, 0, 0, 1, 1],
            [1, 0, 1, 0, 1, 0, 1],
        ]
        error = [0, 0, 0, 0, 0, 1, 0]
        stabilizer_shift = matrix[0]
        stabilizer_correction = tuple(a ^ b for a, b in zip(error, stabilizer_shift))
        stable = theorem_2_obligation(matrix, error, stabilizer_correction)
        self.assertFalse(stable["logical_failure"])
        logical_shift = (1, 1, 1, 1, 1, 1, 1)
        self.assertTrue(not any(f2_mat_vec(matrix, logical_shift)))
        self.assertFalse(row_space_contains(matrix, logical_shift))
        logical_correction = tuple(a ^ b for a, b in zip(error, logical_shift))
        failed = theorem_2_obligation(matrix, error, logical_correction)
        self.assertTrue(failed["logical_failure"])

    def test_theorem_3_ring_paths_are_both_syndrome_faithful(self) -> None:
        checks = [[0, 1], [1, 2], [2, 3], [3, 4], [4, 0]]
        matrix = matrix_from_checks(checks, 5)
        syndrome = [1, 0, 1, 0, 0]
        short_path = [0, 1, 1, 0, 0]
        long_path = [1, 0, 0, 1, 1]
        self.assertEqual(f2_mat_vec(matrix, short_path), tuple(syndrome))
        self.assertEqual(f2_mat_vec(matrix, long_path), tuple(syndrome))
        self.assertTrue(
            theorem_1_obligation(matrix, short_path, long_path)["residual_in_kernel"]
        )

    def test_theorem_4_path_symmetric_difference_is_a_cycle(self) -> None:
        matrix = matrix_from_checks(
            [[0, 1], [1, 2], [2, 3], [3, 4], [4, 0]],
            5,
        )
        first = [0, 1, 1, 0, 0]
        second = [1, 0, 0, 1, 1]
        cycle = tuple(a ^ b for a, b in zip(first, second))
        self.assertEqual(f2_mat_vec(matrix, cycle), (0, 0, 0, 0, 0))

    def test_theorems_5_and_6_growth_slack_and_collision(self) -> None:
        event = collision_time(0.0, 4.0, 1.0, 1.0, 1.0, 1.0)
        self.assertEqual(event, 1.0)
        self.assertGreater(edge_slack(4.0, 1.0, 1.0), 0.0)
        self.assertEqual(edge_slack(4.0, 2.0, 2.0), 0.0)
        self.assertIsNone(collision_time(0.0, 4.0, 1.0, 1.0, 1.0, -1.0))

    def test_theorem_7_sparse_backend_is_faithful_on_a_live_instance(self) -> None:
        code = codes.rotated_surface_code(3)
        error = np.zeros(code.n_qubits, dtype=np.uint8)
        error[4] = 1
        syndrome = code.syndrome(error)
        correction = qector.SparseBlossomDecoder(
            code.check_to_qubits,
            n_qubits=code.n_qubits,
        ).decode(syndrome)
        self.assertTrue(
            np.array_equal(
                (np.asarray(code.parity_check_matrix()) @ correction.astype(int)) % 2,
                syndrome,
            )
        )

    def test_theorem_8_cluster_parity_is_additive(self) -> None:
        left = [1, 0, 1, 1]
        right = [0, 1, 1]
        self.assertEqual(
            cluster_parity(left) ^ cluster_parity(right),
            cluster_parity((*left, *right)),
        )

    def test_theorem_9_tree_peeling_satisfies_a_repetition_syndrome(self) -> None:
        # Vertex 3 is the root; edge/child index i joins i to parent[i].
        correction, residual = peel_tree([1, 2, 3, None], [1, 0, 0, 1])
        self.assertEqual(correction, (1, 1, 1, 0))
        self.assertEqual(residual, (0, 0, 0, 0))
        matrix = [
            [1, 0, 0, 0],
            [1, 1, 0, 0],
            [0, 1, 1, 0],
            [0, 0, 1, 0],
        ]
        self.assertEqual(f2_mat_vec(matrix, correction), (1, 0, 0, 1))

    def test_theorem_11_osd_residual_solve(self) -> None:
        matrix = [[1, 1, 0], [0, 1, 1]]
        syndrome = [1, 0]
        hard = [0, 1, 0]
        residual = tuple(a ^ b for a, b in zip(syndrome, f2_mat_vec(matrix, hard)))
        basis = [[1, 0], [0, 1]]
        basis_solution = gf2_solve(basis, residual)
        self.assertEqual(basis_solution, (0, 1))
        candidate = [0, 1, 1]
        self.assertEqual(f2_mat_vec(matrix, candidate), tuple(syndrome))

    def test_theorem_10_finite_peeling_work_is_linear_in_tree_edges(self) -> None:
        parent = [1, 2, 3, None]
        self.assertEqual(peeling_work(parent), 3)
        self.assertLessEqual(peeling_work(parent), len(parent))

    def test_theorem_12_disjoint_ambiguity_components_sum_linearly(self) -> None:
        matrix = [[1, 0, 1, 0], [0, 1, 0, 1]]
        values = [1, 1, 1, 1]
        split = ambiguity_component_sum(matrix, ((0, 2), (1, 3)), values)
        whole = f2_mat_vec(matrix, values)
        self.assertEqual(split, whole)

    def test_theorem_13_space_time_difference_telescope(self) -> None:
        rounds = [[0, 0], [1, 0], [0, 0]]
        differences = detector_differences(rounds)
        self.assertEqual(differences, ((0, 0), (1, 0), (1, 0)))
        self.assertEqual(telescope_differences(differences), (0, 0))

    def test_theorem_14_graphlike_structural_guard(self) -> None:
        self.assertTrue(graphlike([[0, 1], [1, 2], [2, 3]]))
        self.assertFalse(graphlike([[0, 1, 2], [0, 3], [0, 4]]))

    def test_theorem_16_bit_identity_is_exact_not_approximate(self) -> None:
        self.assertTrue(bit_identity([0, 1, 1], [0, 1, 1]))
        self.assertFalse(bit_identity([0, 1, 1], [0, 1, 0]))


class LiveQECTORTests(unittest.TestCase):
    def test_mcp_configuration_files_use_only_standard_server_fields(self) -> None:
        # The repo root ``.mcp.json`` is the live Claude Code config and
        # uses literal values (``python`` + ``${CLAUDE_PLUGIN_ROOT}``).
        # The ``mcp/mcp_config.json`` and ``mcp/claude_desktop_config.json``
        # files are install-time templates with documented placeholders
        # (``<PYTHON_EXECUTABLE>`` + ``<PLUGIN_ROOT>``) that
        # ``scripts/configure_claude_desktop.py`` substitutes. Both shapes
        # are valid; the test now asserts the documented convention for
        # each file instead of overwriting the templates.
        config_paths = [
            ROOT / ".mcp.json",
            ROOT / "mcp" / "mcp_config.json",
            ROOT / "mcp" / "claude_desktop_config.json",
        ]
        for path in config_paths:
            document = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(set(document), {"mcpServers"}, str(path))
            server = document["mcpServers"]["qector-library"]
            self.assertEqual(set(server), {"command", "args", "env"}, str(path))
            if path.parent.name == "mcp":
                # Template: installer rewrites the placeholders.
                self.assertEqual(server["command"], "<PYTHON_EXECUTABLE>", str(path))
                self.assertEqual(
                    server["args"],
                    ["<PLUGIN_ROOT>/mcp/mcp_server_library.py"],
                    str(path),
                )
            else:
                # Live Claude Code config: literal values.
                self.assertEqual(server["command"], "python", str(path))
                self.assertEqual(
                    server["args"],
                    ["${CLAUDE_PLUGIN_ROOT}/mcp/mcp_server_library.py"],
                    str(path),
                )
            self.assertEqual(server["env"]["QECTOR_SILENT"], "1", str(path))

    def test_marketplace_manifest_points_to_this_plugin_without_path_traversal(
        self,
    ) -> None:
        manifest = json.loads(
            (ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8")
        )
        plugin = json.loads(
            (ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
        )
        self.assertEqual(manifest["name"], "qector-tools")
        self.assertEqual(len(manifest["plugins"]), 1)
        entry = manifest["plugins"][0]
        self.assertEqual(entry["name"], plugin["name"])
        self.assertEqual(entry["source"], "./")
        self.assertEqual(entry["version"], plugin["version"])
        self.assertNotIn("..", entry["source"])

    def test_stable_public_api_is_present_in_live_1_0_0_wheel(self) -> None:
        self.assertEqual(qector.__version__, "1.0.0")
        stable_symbols = [
            "UnionFindDecoder",
            "FastUnionFindDecoder",
            "BlossomDecoder",
            "SparseBlossomDecoder",
            "NativeAutoDecoder",
            "generate_repetition_code_checks",
            "generate_ring_code_checks",
            "generate_surface_code_checks",
            "set_license_key",
            "get_license_info",
            "record_shots",
            "get_accumulated_shots",
            "DecodeResult",
        ]
        self.assertTrue(all(hasattr(qector, symbol) for symbol in stable_symbols))

    def test_manual_direct_decode_against_live_blossom(self) -> None:
        checks = [[0, 1], [1, 2], [2, 3], [3, 4]]
        syndrome = np.array([0, 1, 0, 0], dtype=np.uint8)
        correction = BlossomDecoder(checks, n_qubits=5).decode(syndrome)
        matrix = matrix_from_checks(checks, 5)
        self.assertEqual(tuple((matrix @ correction.astype(int)) % 2), tuple(syndrome))

    def test_all_live_size_families_are_faithful_for_single_qubit_errors(self) -> None:
        families = {
            "repetition": codes.repetition_code(3),
            "ring": codes.ring_code(5),
            "rotated_surface": codes.rotated_surface_code(3),
            "unrotated_surface": codes.unrotated_surface_code(3),
            "toric": codes.toric_code(3),
            "heavy_hex": codes.heavy_hex_code(3),
            "color_code": codes.color_code(3),
        }
        for name, code in families.items():
            self.assertTrue(code.is_matching_graph(), name)
            matrix = np.asarray(code.parity_check_matrix(), dtype=np.uint8)
            for qubit in range(code.n_qubits):
                error = np.zeros(code.n_qubits, dtype=np.uint8)
                error[qubit] = 1
                syndrome = np.asarray(code.syndrome(error), dtype=np.uint8)
                correction = BlossomDecoder(
                    code.check_to_qubits,
                    n_qubits=code.n_qubits,
                ).decode(syndrome)
                self.assertTrue(
                    np.array_equal((matrix @ correction.astype(int)) % 2, syndrome),
                    f"{name} qubit {qubit}",
                )

    def test_every_stable_decoder_is_faithful_on_repetition_example(self) -> None:
        code = codes.repetition_code(3)
        error = np.array([1, 0, 0], dtype=np.uint8)
        syndrome = code.syndrome(error)
        matrix = np.asarray(code.parity_check_matrix(), dtype=np.uint8)
        decoders = [
            qector.UnionFindDecoder,
            qector.FastUnionFindDecoder,
            qector.BlossomDecoder,
            qector.SparseBlossomDecoder,
            qector.NativeAutoDecoder,
        ]
        for decoder_type in decoders:
            correction = decoder_type(
                code.check_to_qubits, n_qubits=code.n_qubits
            ).decode(syndrome)
            self.assertTrue(
                np.array_equal((matrix @ correction.astype(int)) % 2, syndrome),
                decoder_type.__name__,
            )

    def test_wrapper_is_strict_and_uses_live_v1_0_0(self) -> None:
        server = load_library_server()
        result = server.dispatch_tool("decode_syndrome", {"syndrome": [0, 1, 0, 0]})
        self.assertEqual(result["qector_version"], "1.0.0")
        self.assertTrue(result["syndrome_valid"])
        with self.assertRaises(server.QECTORInputError):
            server.dispatch_tool("decode_syndrome", {"syndrome": [0, 2, 0, 0]})
        with self.assertRaises(server.QECTORInputError):
            server.dispatch_tool(
                "decode_syndrome",
                {"family": "surface_legacy", "size": 3, "syndrome": [0] * 18},
            )
        with self.assertRaises(server.QECTORInputError):
            server.dispatch_tool(
                "build_code_from_matrix",
                {"H_matrix": [[1, 0], [1]]},
            )

    def test_wrapper_reports_missing_logical_observables_honestly(self) -> None:
        server = load_library_server()
        result = server.dispatch_tool(
            "decode_single",
            {"family": "unrotated_surface", "distance": 3, "seed": 42},
        )
        self.assertTrue(result["syndrome_valid"])
        self.assertIsNone(result["logical_failure"])
        self.assertIn("unavailable", result["logical_scoring"])

    def test_wrapper_threshold_artifact_is_raw_and_sha256_verified(self) -> None:
        server = load_library_server()
        with tempfile.TemporaryDirectory() as directory:
            old_value = os.environ.get("QECTOR_ARTIFACT_DIR")
            os.environ["QECTOR_ARTIFACT_DIR"] = directory
            try:
                result = server.dispatch_tool(
                    "threshold_sweep",
                    {
                        "family": "rotated_surface",
                        "distances": [3],
                        "error_rates": [0.05],
                        "trials": 3,
                        "seed": 42,
                        "artifact_path": "manual-validation.json",
                    },
                )
            finally:
                if old_value is None:
                    os.environ.pop("QECTOR_ARTIFACT_DIR", None)
                else:
                    os.environ["QECTOR_ARTIFACT_DIR"] = old_value
            artifact = Path(result["artifact"]["path"])
            payload = artifact.read_bytes()
            self.assertEqual(
                hashlib.sha256(payload).hexdigest(), result["artifact"]["sha256"]
            )
            sidecar = Path(f"{artifact}.sha256")
            self.assertEqual(
                sidecar.read_text(encoding="ascii").split()[0],
                result["artifact"]["sha256"],
            )
            document = json.loads(payload)
            self.assertEqual(
                document["required_metadata"]["noise_model"]["tag"], "code_capacity"
            )
            self.assertEqual(document["harness"]["theorem1_violations"], 0)


class MCPProtocolTests(unittest.TestCase):
    def test_stdio_initialize_and_tools_list(self) -> None:
        server_module = load_library_server()
        self.assertEqual(server_module.SERVER_NAME, "qector-decoder-v3-mcp")
        # SERVER_VERSION is the *plugin* version, not the *decoder wheel*
        # version. The decoder wheel version is pinned in requirements.txt
        # (``qector-decoder-v3==1.0.0``) and verified by the runtime check.
        # The plugin version is independent of the decoder wheel pin.
        # Compare against release-manifest.json so the two stay in sync.
        release_manifest = json.loads(
            (ROOT / "release-manifest.json").read_text(encoding="utf-8")
        )
        self.assertEqual(
            server_module.SERVER_VERSION,
            release_manifest["release"]["version"],
        )

        names = {tool.name for tool in server_module.TOOLS}
        self.assertEqual(
            names,
            {
                "list_code_families",
                "list_decoders",
                "get_license_info",
                "decode_syndrome",
                "decode_single",
                "threshold_sweep",
                "build_code_from_matrix",
                "compat_report",
            },
        )

        res_valid = server_module.dispatch_tool(
            "decode_syndrome",
            {"syndrome": [0, 1, 0, 0], "family": "repetition", "size": 5},
        )
        self.assertIn("correction", res_valid)
        self.assertTrue(res_valid.get("syndrome_valid", False))

        with self.assertRaises(server_module.QECTORInputError):
            server_module.dispatch_tool("decode_syndrome", {"syndrome": [0, 2, 0, 0]})


if __name__ == "__main__":
    unittest.main()
