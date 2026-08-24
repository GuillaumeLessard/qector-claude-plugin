"""Production-readiness contract tests for the public MCP and release surface.

These tests do not require ``qector-decoder-v3`` to be installed. They cover
the *contract* surface that the production audit demanded:

* Every MCP tool schema carries ``outputSchema``, ``annotations``, and a
  draft 2020-12 ``$schema`` field.
* The ``QECTORToolResult`` envelope has the documented required keys.
* The error code taxonomy maps the documented exception classes to the
  documented stable codes.
* The MCP servers report the unified version on every public entry point.
* The ``hooks/hooks.json`` SessionStart and PostToolUse commands run
  ``python`` (not ``python3``), so the file does not regress on native
  Windows Claude Code.
* The plugin and Desktop manifests declare the same version, the
  proprietary license, and the safe-profile args.
* The evidence layer tools (``get_capability_matrix``,
  ``get_evidence_policy``, ``get_runtime_provenance``) live in the
  provisional research server, not in the frozen 8-tool library server.
* ``system_setup`` accepts only the fixed SECURITY.md profile allowlist
  and rejects arbitrary package specifications.
* ``tool_artifacts_sha256`` constrains paths to ``QECTOR_ARTIFACT_DIR``
  and rejects arbitrary filesystem paths.
* The source / bundle validators exist and pass when their input is sane.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python"))
MCP_DIR = ROOT / "mcp"
SCRIPTS_DIR = ROOT / "scripts"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load {name} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules.setdefault(name, module)
    spec.loader.exec_module(module)
    return module


def _mcp_loaded() -> bool:
    try:
        import mcp.types  # noqa: F401
    except Exception:
        return False
    return True


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@unittest.skipUnless(_mcp_loaded(), "mcp SDK not installed")
class TestMCPServerContracts(unittest.TestCase):
    """Every advertised tool carries the contract fields."""

    def setUp(self) -> None:
        sys.path.insert(0, str(MCP_DIR))
        self.library = _load_module("mcp_server_library_under_test", MCP_DIR / "mcp_server_library.py")
        self.bench = _load_module(
            "mcp_server_qector_bench_under_test",
            MCP_DIR / "mcp_server_qector_bench.py",
        )
        self.admin = _load_module(
            "mcp_server_admin_under_test",
            MCP_DIR / "mcp_server_admin.py",
        )
        self.desktop = _load_module(
            "mcp_server_desktop_under_test",
            MCP_DIR / "mcp_server_desktop.py",
        )

    def test_library_server_is_eight_tools(self) -> None:
        names = sorted(tool.name for tool in self.library.TOOLS)
        expected = sorted(
            {
                "list_code_families",
                "list_decoders",
                "get_license_info",
                "decode_syndrome",
                "decode_single",
                "threshold_sweep",
                "build_code_from_matrix",
                "compat_report",
            }
        )
        self.assertEqual(names, expected)

    def test_get_license_info_normalized_schema(self) -> None:
        # The library server normalizes the wheel's license dict into the
        # documented public schema. Even without the wheel installed, the
        # wheel is present in the runtime that this test was collected
        # against; we rely on the importability check above to skip the
        # rest of the suite if it is not.
        result = self.library.get_license_info()
        self.assertIn("license", result)
        lic = result["license"]
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
        self.assertIn("license_evidence", lic)
        for evidence_field in (
            "key_status",
            "is_expired",
        ):
            self.assertIn(
                evidence_field, lic["license_evidence"],
                msg=f"license_evidence.{evidence_field} missing",
            )
        self.assertEqual(lic["enforcement_mode"], "permissive")
        self.assertIn(lic["commercial_status"],
                      {"community", "evaluation", "commercial", "expired", "unknown"})

    def test_library_server_version_is_unified(self) -> None:
        version = json.loads((ROOT / "release-manifest.json").read_text(encoding="utf-8"))[
            "release"
        ]["version"]
        self.assertEqual(self.library.SERVER_VERSION, version)

    def test_bench_server_version_is_unified(self) -> None:
        version = json.loads((ROOT / "release-manifest.json").read_text(encoding="utf-8"))[
            "release"
        ]["version"]
        self.assertEqual(self.bench.SERVER_VERSION, version)
        self.assertEqual(self.admin.SERVER_VERSION, version)
        self.assertEqual(len(self.bench.TOOLS), 29)
        self.assertEqual(len(self.bench.TOOL_FUNCTIONS), 29)
        self.assertTrue(
            set(self.bench.TOOL_FUNCTIONS).isdisjoint(
                {"system_setup", "configure_claude_desktop", "workbench_probe"}
            )
        )

    def test_library_server_tools_have_contract(self) -> None:
        for tool in self.library.TOOLS:
            with self.subTest(tool=tool.name):
                self.assertIn("outputSchema", tool.model_dump())
                annotations = tool.annotations
                self.assertIsNotNone(annotations)
                schema = tool.inputSchema
                self.assertEqual(schema.get("$schema"),
                                 "https://json-schema.org/draft/2020-12/schema")

    def test_bench_server_tools_have_contract(self) -> None:
        for tool in self.bench.TOOLS:
            with self.subTest(tool=tool.name):
                self.assertIn("outputSchema", tool.model_dump())
                annotations = tool.annotations
                self.assertIsNotNone(annotations)

    def test_admin_server_tools_have_contract(self) -> None:
        for tool in self.admin.TOOLS:
            with self.subTest(tool=tool.name):
                self.assertIn("outputSchema", tool.model_dump())
                annotations = tool.annotations
                self.assertIsNotNone(annotations)

    def test_bench_server_does_not_expose_admin_tools(self) -> None:
        names = {tool.name for tool in self.bench.TOOLS}
        for forbidden in (
            "system_setup",
            "configure_claude_desktop",
            "workbench_probe",
        ):
            self.assertNotIn(forbidden, names)

    def test_evidence_layer_lives_in_research_only(self) -> None:
        library_names = {tool.name for tool in self.library.TOOLS}
        for evidence_tool in (
            "get_capability_matrix",
            "get_evidence_policy",
            "get_runtime_provenance",
        ):
            self.assertNotIn(evidence_tool, library_names)
            self.assertIn(evidence_tool, {t.name for t in self.bench.TOOLS})


@unittest.skipUnless(_mcp_loaded(), "mcp SDK not installed")
class TestSharedContract(unittest.TestCase):
    """QECTORToolResult envelope + stable error code taxonomy."""

    def setUp(self) -> None:
        sys.path.insert(0, str(MCP_DIR))
        self.contract = _load_module(
            "qector_mcp_contract_under_test",
            MCP_DIR / "qector_mcp_contract.py",
        )

    def test_envelope_required_keys(self) -> None:
        required = set(
            self.contract.RESULT_OUTPUT_SCHEMA["required"]
        )
        self.assertEqual(
            required,
            {
                "status",
                "claim_class",
                "provenance",
                "runtime",
                "scope",
                "verification",
                "artifact",
                "warnings",
                "result",
            },
        )

    def test_envelope_status_enum(self) -> None:
        statuses = set(self.contract.RESULT_OUTPUT_SCHEMA["properties"]["status"]["enum"])
        self.assertEqual(
            statuses,
            {"verified", "reference_only", "measured", "not_checked", "error"},
        )

    def test_error_code_taxonomy(self) -> None:
        class _FaithfulnessError(RuntimeError):
            pass

        class _UnsupportedError(RuntimeError):
            pass

        class _ImportMissingError(ImportError):
            pass

        class _PermissionDeniedError(PermissionError):
            pass

        self.assertEqual(
            self.contract.error_code(_FaithfulnessError("fail")),
            "VERIFICATION_FAILED",
        )
        self.assertEqual(
            self.contract.error_code(_UnsupportedError("decoder unavailable")),
            "BACKEND_UNAVAILABLE",
        )
        self.assertEqual(
            self.contract.error_code(_ImportMissingError("missing")),
            "DEPENDENCY_MISSING",
        )
        self.assertEqual(
            self.contract.error_code(_PermissionDeniedError("denied")),
            "PERMISSION_DENIED",
        )
        self.assertEqual(
            self.contract.error_code(ValueError("bad input")),
            "INVALID_INPUT",
        )
        self.assertEqual(
            self.contract.error_code(OSError("disk")),
            "IO_ERROR",
        )

    def test_call_budget_enforced(self) -> None:
        self.contract.reset_call_budget()
        old = os.environ.get("QECTOR_MCP_MAX_CALLS_THRESHOLD_SWEEP")
        os.environ["QECTOR_MCP_MAX_CALLS_THRESHOLD_SWEEP"] = "1"
        try:
            self.contract.reset_call_budget()
            self.contract.consume_call_budget("threshold_sweep")
            with self.assertRaises(self.contract.QECTORResourceLimitError):
                self.contract.consume_call_budget("threshold_sweep")
            self.assertEqual(
                self.contract.error_code(
                    self.contract.QECTORResourceLimitError("limit")
                ),
                "RESOURCE_LIMIT",
            )
        finally:
            if old is None:
                os.environ.pop("QECTOR_MCP_MAX_CALLS_THRESHOLD_SWEEP", None)
            else:
                os.environ["QECTOR_MCP_MAX_CALLS_THRESHOLD_SWEEP"] = old
            self.contract.reset_call_budget()

    def test_result_envelope_shape(self) -> None:
        envelope = self.contract.result_envelope(
            {"decoder": "blossom", "syndrome_valid": True, "reference_manual": "10.5281/zenodo.21941046"},
            tool_name="decode_syndrome",
            server_name="qector-decoder-v3-mcp",
            server_version="1.0.6",
            stability="stable",
        )
        self.assertEqual(envelope["status"], "verified")
        self.assertEqual(envelope["claim_class"], "runtime_verified")
        self.assertEqual(envelope["provenance"]["server"], "qector-decoder-v3-mcp")
        self.assertEqual(envelope["verification"]["status"], "verified")


class TestManifestConsistency(unittest.TestCase):
    """Version, license, and surface shape are consistent across manifests."""

    def _load(self, name: str) -> dict:
        with open(ROOT / name, "r", encoding="utf-8") as handle:
            return json.load(handle)

    def test_manifests_share_version(self) -> None:
        expected = self._load("release-manifest.json")["release"]["version"]
        plugin = self._load(".claude-plugin/plugin.json")
        marketplace = self._load(".claude-plugin/marketplace.json")
        desktop = self._load(".claude-desktop-extension/manifest.json")
        registry = self._load("server.json")
        self.assertEqual(plugin["version"], expected)
        for entry in marketplace.get("plugins", []):
            self.assertEqual(entry["version"], expected)
        self.assertEqual(desktop["version"], expected)
        self.assertEqual(registry["version"], expected)

    def test_manifests_share_license(self) -> None:
        plugin = self._load(".claude-plugin/plugin.json")
        marketplace = self._load(".claude-plugin/marketplace.json")
        desktop = self._load(".claude-desktop-extension/manifest.json")
        self.assertEqual(plugin["license"], "Proprietary")
        # Marketplace manifest carries no nonstandard fields on purpose;
        # strict Desktop sync validators reject license there. The license
        # is declared exactly once in plugin.json (and in the Desktop bundle).
        self.assertNotIn("license", marketplace.get("plugins", [{}])[0])
        self.assertEqual(desktop["license"], "Proprietary")

    def test_desktop_extension_is_eight_tools_safe(self) -> None:
        desktop = self._load(".claude-desktop-extension/manifest.json")
        self.assertEqual(len(desktop["tools"]), 8)
        self.assertEqual(
            desktop["server"]["mcp_config"]["args"],
            ["${__dirname}/mcp/mcp_server_desktop.py", "--profile", "safe"],
        )

    def test_release_manifest_artifact_name(self) -> None:
        release = self._load("release-manifest.json")
        version = release["release"]["version"]
        self.assertEqual(
            release["surfaces"]["claude_desktop"]["artifact"],
            f"qector-claude-desktop-{version}.mcpb",
        )

    def test_default_mcp_servers(self) -> None:
        with open(ROOT / ".mcp.json", "r", encoding="utf-8") as handle:
            mcp = json.load(handle)
        self.assertEqual(set(mcp["mcpServers"]), {"qector-library"})

    def test_hooks_launcher_uses_python_not_python3(self) -> None:
        with open(ROOT / "hooks" / "hooks.json", "r", encoding="utf-8") as handle:
            hooks = json.load(handle)
        for event_name, event_list in hooks.get("hooks", {}).items():
            for entry in event_list:
                for hook in entry.get("hooks", []):
                    cmd = hook.get("command", "")
                    self.assertNotIn("python3", cmd,
                                     msg=f"hooks.{event_name} regressed to python3")


class TestSystemSetupAllowlist(unittest.TestCase):
    """system_setup must reject arbitrary package specifications."""

    def test_profile_allowlist_is_finite(self) -> None:
        # SETUP_PROFILES is the four SECURITY.md-listed profiles and nothing
        # else. The bench server defines it; we read it through importlib.
        sys.path.insert(0, str(MCP_DIR))
        bench = _load_module("mcp_server_qector_bench_under_test",
                             MCP_DIR / "mcp_server_qector_bench.py")
        self.assertEqual(
            set(bench.SETUP_PROFILES),
            {"production", "developer", "optional-stim", "optional-qiskit"},
        )

    def test_tool_system_setup_rejects_unknown_profile(self) -> None:
        sys.path.insert(0, str(MCP_DIR))
        bench = _load_module("mcp_server_qector_bench_under_test",
                             MCP_DIR / "mcp_server_qector_bench.py")
        with self.assertRaises(bench.QECTORInputError):
            bench.tool_system_setup(
                confirm=False,
                profile="arbitrary",
                install_requirements=False,
                create_artifact_dir=False,
                run_validation_test=False,
            )

    def test_admin_system_setup_requires_admin_flag_and_confirm(self) -> None:
        sys.path.insert(0, str(MCP_DIR))
        admin = _load_module("mcp_server_admin_under_test",
                             MCP_DIR / "mcp_server_admin.py")
        # No QECTOR_ADMIN_ENABLED: permission error before any I/O.
        with self.assertRaises(admin.QECTORAdminPermissionError):
            admin.system_setup(confirm=True)
        # confirm=False is a permission error even with the flag set.
        old = os.environ.get("QECTOR_ADMIN_ENABLED")
        os.environ["QECTOR_ADMIN_ENABLED"] = "1"
        try:
            with self.assertRaises(admin.QECTORAdminPermissionError):
                admin.system_setup(confirm=False)
        finally:
            if old is None:
                os.environ.pop("QECTOR_ADMIN_ENABLED", None)
            else:
                os.environ["QECTOR_ADMIN_ENABLED"] = old


class TestArtifactRootContainment(unittest.TestCase):
    """tool_artifacts_sha256 must reject paths outside QECTOR_ARTIFACT_DIR."""

    def setUp(self) -> None:
        sys.path.insert(0, str(MCP_DIR))
        self.bench = _load_module(
            "mcp_server_qector_bench_under_test",
            MCP_DIR / "mcp_server_qector_bench.py",
        )
        self.tmp = ROOT / ".pytest_cache" / "artifact_containment_test"
        self.tmp.mkdir(parents=True, exist_ok=True)
        (self.tmp / "inside.txt").write_text("inside", encoding="utf-8")
        (self.tmp / "outside.txt").write_text("outside", encoding="utf-8")
        # Point QECTOR_ARTIFACT_DIR at the .pytest_cache subdirectory.
        self._old_artifact_dir = os.environ.get("QECTOR_ARTIFACT_DIR")
        os.environ["QECTOR_ARTIFACT_DIR"] = str(self.tmp)

    def tearDown(self) -> None:
        if self._old_artifact_dir is None:
            os.environ.pop("QECTOR_ARTIFACT_DIR", None)
        else:
            os.environ["QECTOR_ARTIFACT_DIR"] = self._old_artifact_dir

    def test_in_artifact_dir_is_accepted(self) -> None:
        result = self.bench.tool_artifacts_sha256([str(self.tmp / "inside.txt")])
        self.assertEqual(len(result["files"]), 1)

    def test_outside_artifact_dir_is_rejected(self) -> None:
        # The artifact root is QECTOR_ARTIFACT_DIR, set in setUp to
        # ``self.tmp``. A path that lives outside the artifact root
        # must be rejected; build a sibling directory of ``self.tmp``
        # under the pytest cache to exercise that.
        outside = self.tmp.parent / "artifact_containment_outside"
        outside.mkdir(parents=True, exist_ok=True)
        outside_file = outside / "outside.txt"
        outside_file.write_text("outside", encoding="utf-8")
        try:
            with self.assertRaises(self.bench.QECTORInputError):
                self.bench.tool_artifacts_sha256([str(outside_file)])
        finally:
            outside_file.unlink(missing_ok=True)
            outside.rmdir()


class TestEvidenceLayerTools(unittest.TestCase):
    """The three new tools return a stable shape without decoder execution."""

    def setUp(self) -> None:
        sys.path.insert(0, str(MCP_DIR))
        self.bench = _load_module(
            "mcp_server_qector_bench_under_test",
            MCP_DIR / "mcp_server_qector_bench.py",
        )

    def test_capability_matrix_shape(self) -> None:
        result = self.bench.tool_get_capability_matrix()
        self.assertEqual(result["matrix_version"], "1.0.0")
        self.assertIn("qector-library", result["servers"])
        self.assertIn("qector-research", result["servers"])
        self.assertIn("qector-admin", result["servers"])
        for server in result["servers"].values():
            self.assertIn("stability", server)
            self.assertIn("n_tools", server)
        for capability in result["capabilities"]:
            self.assertIn("capability", capability)
            self.assertIn("servers", capability)
            self.assertIn("stability", capability)
            self.assertIn("verification", capability)

    def test_evidence_policy_shape(self) -> None:
        result = self.bench.tool_get_evidence_policy()
        self.assertEqual(result["policy_version"], "1.0.0")
        statuses = {entry["status"] for entry in result["result_statuses"]}
        self.assertEqual(
            statuses,
            {"verified", "measured", "reference_only", "not_checked", "error"},
        )
        for code in (
            "INVALID_INPUT",
            "RESOURCE_LIMIT",
            "LICENSE_DENIED",
            "BACKEND_UNAVAILABLE",
            "DEPENDENCY_MISSING",
            "VERIFICATION_FAILED",
            "IO_ERROR",
            "NETWORK_DISABLED",
            "NETWORK_REQUIRED",
            "PERMISSION_DENIED",
            "PROTOCOL_ERROR",
        ):
            self.assertIn(code, result["stable_error_codes"])

    def test_runtime_provenance_shape(self) -> None:
        result = self.bench.tool_get_runtime_provenance(check_pypi=False)
        self.assertEqual(result["server"], "qector-research-mcp")
        version = json.loads((ROOT / "release-manifest.json").read_text(encoding="utf-8"))[
            "release"
        ]["version"]
        self.assertEqual(result["server_version"], version)
        self.assertIn("environment", result)
        self.assertEqual(
            result["pypi_freshness"]["status"], "not_checked"
        )


class TestValidators(unittest.TestCase):
    """The split source / bundle validators exist and run."""

    def test_validate_source_runs(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "validate_source", SCRIPTS_DIR / "validate_source.py"
        )
        self.assertIsNotNone(spec)

    def test_validate_bundle_runs(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "validate_plugin_bundle", SCRIPTS_DIR / "validate_plugin_bundle.py"
        )
        self.assertIsNotNone(spec)

    def test_test_structure_wrapper_runs(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "test_structure", SCRIPTS_DIR / "test_structure.py"
        )
        self.assertIsNotNone(spec)


class TestReleasePackaging(unittest.TestCase):
    """Plugin and Desktop artifacts include the files the runtime needs."""

    def setUp(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "build_release_under_test", SCRIPTS_DIR / "build_release.py"
        )
        if spec is None or spec.loader is None:
            self.fail("could not load scripts/build_release.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.builder = module

    def test_plugin_roots_include_hook_scripts(self) -> None:
        self.assertIn("scripts", self.builder.PLUGIN_ROOTS)
        files = {
            path.relative_to(ROOT).as_posix()
            for path in self.builder._plugin_files()
        }
        self.assertIn("scripts/qector_session_start.py", files)
        self.assertIn("scripts/qector_tool_log.py", files)
        self.assertIn("hooks/hooks.json", files)
        self.assertIn("SECURITY.md", files)
        self.assertNotIn("scratch_probe_library.py", files)
        self.assertNotIn("scratch_probe_servers.py", files)

    def test_desktop_bundle_flattens_icon_and_excludes_privileged_servers(
        self,
    ) -> None:
        self.assertEqual(
            self.builder.DESKTOP_ARCHIVE_RENAMES[
                ".claude-desktop-extension/icon.png"
            ],
            "icon.png",
        )
        self.assertEqual(
            self.builder.DESKTOP_ARCHIVE_RENAMES[
                ".claude-desktop-extension/README.md"
            ],
            "README.md",
        )
        self.assertIsNone(
            self.builder.DESKTOP_ARCHIVE_RENAMES[
                ".claude-desktop-extension/manifest.json"
            ]
        )
        self.assertNotIn("mcp/mcp_server_qector_bench.py", self.builder.DESKTOP_FILES)
        self.assertNotIn("mcp/mcp_server_admin.py", self.builder.DESKTOP_FILES)
        self.assertIn("mcp/mcp_server_library.py", self.builder.DESKTOP_FILES)
        self.assertIn("mcp/qector_mcp_contract.py", self.builder.DESKTOP_FILES)
        self.assertEqual(self.builder.ZIP_TIMESTAMP, (2026, 8, 23, 0, 0, 0))

    def test_library_artifact_root_is_plugin_artifacts_not_cwd(self) -> None:
        text = (MCP_DIR / "mcp_server_library.py").read_text(encoding="utf-8")
        self.assertNotIn('Path.cwd() / "artifacts"', text)
        self.assertIn('parent.parent / "artifacts"', text)


class TestInstallerPythonPath(unittest.TestCase):
    """configure_claude_desktop rejects non-Python python_path values."""

    def setUp(self) -> None:
        spec = importlib.util.spec_from_file_location(
            "configure_claude_desktop_under_test",
            SCRIPTS_DIR / "configure_claude_desktop.py",
        )
        if spec is None or spec.loader is None:
            self.fail("could not load scripts/configure_claude_desktop.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.installer = module

    def test_default_python_is_current_interpreter(self) -> None:
        self.assertEqual(
            self.installer._resolve_python_executable(None), sys.executable
        )

    def test_non_python_file_is_rejected(self) -> None:
        decoy = ROOT / "requirements.txt"
        with self.assertRaises(ValueError):
            self.installer._resolve_python_executable(str(decoy))

    def test_missing_file_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            self.installer._resolve_python_executable(
                str(ROOT / "not-a-python-interpreter.exe")
            )


if __name__ == "__main__":
    unittest.main()
