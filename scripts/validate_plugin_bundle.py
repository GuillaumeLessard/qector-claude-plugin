#!/usr/bin/env python3
"""Validate built QECTOR release bundles in ``dist/``.

This script is the *post-build* companion to ``scripts/validate_source.py``.
It is only meaningful after ``scripts/build_release.py --all`` has produced
release artifacts. When ``dist/`` is absent the script reports the situation
as informational and exits 0, because a source-only checkout is a valid state
of the repository.

Checks:

* The plugin zip for the current plugin.json version exists and is non-empty.
* The plugin zip carries the Desktop extension manifest and the profiled
  Desktop server source.
* A Claude Desktop MCPB bundle is present and contains the runtime
  manifests it advertises.
* Every sidecar ``.sha256`` file matches its artifact.

Exit code is 0 when every check passes, 1 otherwise. ``--warn-only`` keeps the
exit code at 0; useful for local edits where a single known regression is
acceptable.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
import zipfile
from pathlib import Path as _Path

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "mcp"))
import qector_signing  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST = os.path.join(ROOT, "dist")

_passed = 0
_failed = 0
_warnings = 0
_warn_only = False


def check(condition: bool, label: str, warn_only: bool = False) -> None:
    global _passed, _failed, _warnings
    if condition:
        print(f"  PASS - {label}")
        _passed += 1
    elif warn_only or _warn_only:
        print(f"  WARN - {label}")
        _warnings += 1
    else:
        print(f"  FAIL - {label}")
        _failed += 1


def _section(title: str) -> None:
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}")


def _expected_version() -> str | None:
    plugin_json = os.path.join(ROOT, ".claude-plugin", "plugin.json")
    if not os.path.isfile(plugin_json):
        return None
    with open(plugin_json, "r", encoding="utf-8") as handle:
        return json.load(handle).get("version")


def _boot_secure_server(archive_path: str, *, bundled_lib: bool) -> tuple[bool, str]:
    """Extract *archive_path* and start its secure server over real stdio.

    Strict integrity is left at its default (on) so the archive's own
    INTEGRITY.json gates the start exactly as it will on a user's machine.
    A vendored ``server/lib`` is only usable on the platform and CPython
    minor it was built for, so a bundled MCPB is booted only when this
    interpreter matches its manifest; otherwise the check is skipped with a
    note rather than reported as a failure.
    """
    import platform
    import subprocess

    with tempfile.TemporaryDirectory(prefix="qector-boot-") as tmp:
        with zipfile.ZipFile(archive_path) as archive:
            archive.extractall(tmp)
            entries = set(archive.namelist())
        env = {k: v for k, v in os.environ.items() if not k.startswith("QECTOR_")}
        env["QECTOR_SILENT"] = "1"
        env["QECTOR_AIR_GAPPED"] = "1"
        if bundled_lib:
            manifest = json.loads((_Path(tmp) / "manifest.json").read_text(encoding="utf-8"))
            platforms = manifest.get("compatibility", {}).get("platforms", [])
            runtime = manifest.get("compatibility", {}).get("runtimes", {}).get("python", "")
            here = "win32" if sys.platform.startswith("win") else ("darwin" if sys.platform == "darwin" else "linux")
            minor = f"{sys.version_info.major}.{sys.version_info.minor}"
            if here not in platforms or f">={minor}," not in runtime or platform.machine() not in archive_path:
                return True, f"skipped (vendored runtime targets {platforms}/{runtime}, this host is {here}/{minor}/{platform.machine()})"
            env["PYTHONPATH"] = os.path.join(tmp, "server", "lib")
            env["PYTHONNOUSERSITE"] = "1"
        # Pin the key exactly as the shipped configuration does, so the boot
        # exercises origin verification (signature.source == "pinned").
        pubkey = None
        if "manifest.json" in entries:
            manifest = json.loads((_Path(tmp) / "manifest.json").read_text(encoding="utf-8"))
            pubkey = manifest.get("server", {}).get("mcp_config", {}).get("env", {}).get("QECTOR_INTEGRITY_PUBKEY")
        elif ".mcp.json" in entries:
            servers = json.loads((_Path(tmp) / ".mcp.json").read_text(encoding="utf-8")).get("mcpServers", {})
            for server in servers.values():
                pubkey = pubkey or server.get("env", {}).get("QECTOR_INTEGRITY_PUBKEY")
        if pubkey:
            env["QECTOR_INTEGRITY_PUBKEY"] = pubkey
        frames = "\n".join(
            json.dumps(frame)
            for frame in (
                {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "qector-bundle-validator", "version": "1"}}},
                {"jsonrpc": "2.0", "method": "notifications/initialized"},
                {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
                {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "integrity_check", "arguments": {}}},
            )
        ) + "\n"
        # Keep stdin open until every response has arrived: a server that
        # sees EOF may shut down before it drains queued requests, which is
        # correct behaviour but would make the smoke test flaky.
        proc = subprocess.Popen(
            [sys.executable, os.path.join(tmp, "mcp", "mcp_server_secure.py"), "--profile", "safe"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            cwd=tmp,
        )
        responses: dict = {}
        stderr_text = ""
        try:
            assert proc.stdin is not None and proc.stdout is not None
            proc.stdin.write(frames.encode("utf-8"))
            proc.stdin.flush()
            import threading

            timer = threading.Timer(120, proc.kill)
            timer.start()
            try:
                while len(responses) < 3:
                    line = proc.stdout.readline()
                    if not line:
                        break
                    text = line.decode("utf-8", "replace").strip()
                    if text.startswith("{"):
                        message = json.loads(text)
                        if "id" in message:
                            responses[message["id"]] = message
            finally:
                timer.cancel()
            proc.stdin.close()
            try:
                proc.wait(timeout=30)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)
            stderr_text = proc.stderr.read().decode("utf-8", "replace") if proc.stderr else ""
        finally:
            for stream in (proc.stdin, proc.stdout, proc.stderr):
                try:
                    if stream:
                        stream.close()
                except OSError:
                    pass
        if proc.returncode != 0:
            tail = stderr_text.strip().splitlines()[-1:] or ["no stderr"]
            return False, f"exit {proc.returncode}: {tail[0][:200]}"
        tools = responses.get(2, {}).get("result", {}).get("tools", [])
        if len(tools) != 12:
            return False, f"tools/list returned {len(tools)} tools, expected 12"
        content = responses.get(3, {}).get("result", {}).get("content", [{}])
        envelope = json.loads(content[0].get("text", "{}")) if content else {}
        report = envelope.get("result", {})
        if not report.get("passed"):
            return False, f"integrity_check did not pass inside the archive: {envelope.get('error') or report}"
        signature = report.get("signature", {})
        return True, (
            f"booted on {sys.version.split()[0]}, 12 tools, integrity passed, "
            f"signature {signature.get('source')}"
        )


def _sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--warn-only",
        action="store_true",
        help="Do not exit with a non-zero status on failures.",
    )
    args = parser.parse_args()

    global _warn_only
    _warn_only = args.warn_only

    if not os.path.isdir(DIST):
        _section("BUNDLE VALIDATION")
        print("  FAIL - dist/ is absent: nothing was validated. Run scripts/build_release.py --all first.")
        print("  Status:   NOTHING TO VALIDATE")
        return 2

    dist_files = sorted(os.listdir(DIST))
    plugin_zips = [
        name for name in dist_files
        if name.startswith("qector-claude-plugin-") and name.endswith(".zip")
        and not name.endswith(".sha256")
        and "-source-" not in name
    ]
    source_zips = [
        name for name in dist_files
        if name.startswith("qector-claude-plugin-source-") and name.endswith(".zip")
        and not name.endswith(".sha256")
    ]
    desktop_bundles = [name for name in dist_files if name.endswith(".mcpb")]
    sha_sidecars = [name for name in dist_files if name.endswith(".sha256")]

    _section("DIST ARCHIVES VALIDATION")
    check(len(plugin_zips) > 0, "dist/ contains a Claude Code plugin archive")
    check(len(source_zips) > 0, "dist/ contains a source archive", warn_only=True)
    check(len(desktop_bundles) > 0, "dist/ contains a Claude Desktop MCPB bundle")
    check(len(sha_sidecars) > 0, "dist/ contains checksum sidecar(s)")

    expected_version = _expected_version()
    if expected_version:
        expected_plugin = f"qector-claude-plugin-{expected_version}.zip"
        expected_desktop = f"qector-claude-desktop-{expected_version}.mcpb"
        _section(f"VERSIONED RELEASE ARTIFACTS ({expected_version})")
        check(
            expected_plugin in plugin_zips,
            f"dist/ contains plugin archive {expected_plugin}",
        )
        check(
            expected_desktop in desktop_bundles,
            f"dist/ contains Desktop MCPB {expected_desktop}",
        )
        archive_path = os.path.join(DIST, expected_plugin)
        if os.path.isfile(archive_path):
            check(
                os.path.getsize(archive_path) > 1024,
                f"{expected_plugin} is non-trivial (>1KB)",
            )
            with zipfile.ZipFile(archive_path) as archive:
                entries = set(archive.namelist())
            check(
                ".claude-plugin/plugin.json" in entries,
                "plugin archive includes .claude-plugin/plugin.json",
            )
            check(
                "mcp/mcp_server_library.py" in entries,
                "plugin archive includes the library MCP server",
            )
            check(
                "mcp/mcp_server_secure.py" in entries,
                "plugin archive includes the secure MCP server",
            )
            check(
                "INTEGRITY.json" in entries,
                "plugin archive carries INTEGRITY.json",
            )
            check(
                "requirements.lock" in entries,
                "plugin archive carries requirements.lock",
            )
            check(
                "schemas/index.json" in entries,
                "plugin archive carries the exported JSON schemas",
            )
            check(
                "mcp/qector_mcp_contract.py" in entries,
                "plugin archive includes the shared MCP contract",
            )
            check(
                "scripts/qector_session_start.py" in entries,
                "plugin archive includes SessionStart hook script",
            )
            check(
                "scripts/qector_tool_log.py" in entries,
                "plugin archive includes PostToolUse hook script",
            )
            check(
                "SECURITY.md" in entries,
                "plugin archive includes SECURITY.md",
            )
            for forbidden in (
                "plugin.json.deprecated",
                "marketplace.json.deprecated",
                "scratch_probe_library.py",
                "scratch_probe_servers.py",
            ):
                check(
                    not any(entry.endswith(forbidden) for entry in entries),
                    f"plugin archive does not contain {forbidden}",
                )
            # claude.ai-hosted plugins may not ship bin/ executables (they land
            # on PATH without appearing on the admin approval surface).
            check(
                not any(entry.startswith("bin/") for entry in entries),
                f"{expected_plugin} ships no bin/ executables (claude.ai policy)",
            )

    # Source archive must be free of dev-internal material.
    _section("SOURCE ARCHIVE CLEANLINESS")
    for archive_name in source_zips:
        archive_path = os.path.join(DIST, archive_name)
        with zipfile.ZipFile(archive_path) as archive:
            entries = set(archive.namelist())
        for forbidden_prefix in (
            "presentations/",
            "bin/",
            "wheelhouse/",
            "dist/",
        ):
            check(
                not any(entry.startswith(forbidden_prefix) for entry in entries),
                f"{archive_name} does not contain {forbidden_prefix.rstrip('/')}",
            )
        check(
            "tests/test_secure_server.py" in entries,
            f"{archive_name} ships the executable test suite",
        )
        for required in ("skills/qector-core/SKILL.md", "hooks/hooks.json", "mcp/tests/test_mcp_stdio.py", "commands/qec-setup.md", "agents/qec-validator.md"):
            check(required in entries, f"{archive_name} ships {required} (full reviewable tree)")
        check(
            "INTEGRITY.json" in entries,
            f"{archive_name} carries INTEGRITY.json",
        )
        for forbidden_file in (
            "scratch_probe_library.py",
            "scratch_probe_servers.py",
        ):
            check(
                forbidden_file not in entries,
                f"{archive_name} does not contain {forbidden_file}",
            )

    # Signatures: required to be VALID whenever present; absence is a warning
    # (CI builds without the private key) unless the release declares no key.
    _section("RELEASE SIGNATURES")
    release_path = os.path.join(ROOT, "release-manifest.json")
    declared_key = None
    if os.path.isfile(release_path):
        with open(release_path, "r", encoding="utf-8") as handle:
            declared_key = json.load(handle).get("signing", {}).get("public_key")
    sums_sig = os.path.join(DIST, "SHA256SUMS.sig")
    if os.path.isfile(sums_sig):
        report = qector_signing.verify_signature_file(_Path(DIST) / "SHA256SUMS", pinned_public_key=declared_key)
        check(report["valid"], f"SHA256SUMS.sig verifies under the declared key ({report['reason'] or 'ok'})")
    else:
        check(declared_key is None, "SHA256SUMS.sig present (release declares a signing key)", warn_only=True)
    for archive_name in sorted(n for n in dist_files if n.endswith((".zip", ".mcpb"))):
        with zipfile.ZipFile(os.path.join(DIST, archive_name)) as archive, tempfile.TemporaryDirectory() as tmp:
            names = set(archive.namelist())
            if "INTEGRITY.json.sig" not in names:
                check(declared_key is None, f"{archive_name} carries INTEGRITY.json.sig", warn_only=True)
                continue
            archive.extract("INTEGRITY.json", tmp)
            archive.extract("INTEGRITY.json.sig", tmp)

            report = qector_signing.verify_signature_file(_Path(tmp) / "INTEGRITY.json", pinned_public_key=declared_key)
            check(report["valid"], f"{archive_name} INTEGRITY.json.sig verifies under the declared key")

    # Sidecar integrity check.
    _section("CHECKSUM SIDECARS")
    for sidecar in sha_sidecars:
        sidecar_path = os.path.join(DIST, sidecar)
        target_name = sidecar[: -len(".sha256")]
        target_path = os.path.join(DIST, target_name)
        if not os.path.isfile(target_path):
            check(
                False,
                f"sidecar {sidecar} references an existing artifact {target_name}",
            )
            continue
        with open(sidecar_path, "r", encoding="utf-8") as handle:
            line = handle.read().strip()
        recorded = line.split()[0] if line else ""
        actual = _sha256(target_path)
        check(
            recorded == actual,
            f"sha256 matches for {target_name} (recorded {recorded[:12]}..., "
            f"actual {actual[:12]}...)",
        )

    # Standalone skill zips must track the plugin version. A stale upload
    # here shipped retired commands to claude.ai users in the 1.0.2 era.
    if expected_version:
        _section("STANDALONE SKILL ZIP STALENESS")
        skill_zips = [
            name
            for name in dist_files
            if name.endswith(".zip")
            and "skill" in name
            and not name.startswith("qector-claude")
        ]
        for skill_zip in skill_zips:
            archive_path = os.path.join(DIST, skill_zip)
            with zipfile.ZipFile(archive_path) as archive:
                skill_names = [
                    entry for entry in archive.namelist()
                    if entry.endswith("SKILL.md")
                ]
                found_versions = []
                for skill_name in skill_names:
                    text = archive.read(skill_name).decode("utf-8", "replace")
                    match = re.search(r"\bv?(\d+\.\d+\.\d+)\b", text)
                    if match:
                        found_versions.append(match.group(1))
            check(
                bool(found_versions) and all(
                    version == expected_version for version in found_versions
                ),
                f"{skill_zip} declares plugin version {expected_version} "
                f"(found {sorted(set(found_versions))})",
            )

    # Desktop MCPB content check.
    _section("CLAUDE DESKTOP MCPB BUNDLE")
    for bundle in desktop_bundles:
        bundle_path = os.path.join(DIST, bundle)
        with zipfile.ZipFile(bundle_path) as archive:
            entries = set(archive.namelist())
        check(
            "manifest.json" in entries,
            f"{bundle} contains manifest.json",
        )
        check(
            "provenance.json" in entries,
            f"{bundle} contains provenance.json",
        )
        check(
            "icon.png" in entries,
            f"{bundle} contains icon.png at bundle root",
        )
        # Launcher requirements apply to the CURRENT release bundle only;
        # older MCPBs kept in dist/ are historical artifacts.
        if (
            expected_version
            and bundle == f"qector-claude-desktop-{expected_version}.mcpb"
        ):
            for launcher in ("scripts/qector-python", "scripts/qector-python.cmd", "scripts/qector-python.ps1"):
                check(
                    launcher in entries,
                    f"{bundle} bundles the {launcher} launcher",
                )
            # claude.ai-hosted plugins may not ship bin/ executables; guard the
            # current release bundle so the directory can never creep back in.
            check(
                not any(e.startswith("bin/") for e in entries),
                f"{bundle} ships no bin/ executables (claude.ai approval policy)",
            )
        check(
            "mcp/mcp_server_library.py" in entries,
            f"{bundle} contains the library MCP server",
        )
        check(
            "mcp/mcp_server_desktop.py" in entries,
            f"{bundle} contains the Desktop MCP adapter",
        )
        check(
            "mcp/mcp_server_secure.py" in entries,
            f"{bundle} contains the secure MCP server",
        )
        check(
            "INTEGRITY.json" in entries,
            f"{bundle} carries INTEGRITY.json",
        )
        check(
            "mcp/mcp_server_qector_bench.py" not in entries,
            f"{bundle} does not bundle the research server",
        )
        check(
            "mcp/mcp_server_admin.py" not in entries,
            f"{bundle} does not bundle the admin server",
        )
        if "manifest.json" in entries:
            with zipfile.ZipFile(bundle_path) as archive:
                manifest_data = json.loads(archive.read("manifest.json"))
            check(
                manifest_data.get("license", "").lower() == "proprietary",
                f"{bundle} manifest license is Proprietary",
            )
            check(
                manifest_data.get("icon") == "icon.png",
                f"{bundle} manifest icon is icon.png",
            )
            check(
                manifest_data.get("server", {}).get("entry_point") == "mcp/mcp_server_secure.py",
                f"{bundle} manifest entry point is the secure server",
            )
            check(
                manifest_data.get("server", {}).get("mcp_config", {}).get("env", {}).get("QECTOR_AIR_GAPPED") == "1",
                f"{bundle} manifest is air-gapped by default",
            )
            # Verify the bundled INTEGRITY.json against the bundle's own entries.
            if "INTEGRITY.json" in entries:
                with zipfile.ZipFile(bundle_path) as archive:
                    manifest_files = json.loads(archive.read("INTEGRITY.json"))["files"]
                    drift = [
                        name for name, digest in manifest_files.items()
                        if name not in entries or hashlib.sha256(archive.read(name)).hexdigest() != digest
                    ]
                check(
                    not drift,
                    f"{bundle} INTEGRITY.json matches bundle contents ({len(manifest_files)} files)",
                )

    _section("LIVE STDIO BOOT OF EVERY SHIPPED SECURE SERVER")
    for archive_name in sorted(n for n in dist_files if n.endswith((".zip", ".mcpb")) and "source" not in n):
        if expected_version and expected_version not in archive_name:
            continue
        ok, detail = _boot_secure_server(os.path.join(DIST, archive_name), bundled_lib="bundled" in archive_name)
        check(ok, f"{archive_name}: secure server boots strict from the extracted archive ({detail})")

    _section("BUNDLE VALIDATION SUMMARY")
    print(f"  Passed:   {_passed}")
    print(f"  Failed:   {_failed}")
    print(f"  Warnings: {_warnings}")
    status = "ALL CLEAR" if _failed == 0 else "FAILURES DETECTED"
    print(f"  Status:   {status}")
    print(f"{'=' * 70}")
    if _warn_only:
        return 0
    return 0 if _failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
