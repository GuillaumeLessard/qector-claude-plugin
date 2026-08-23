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
import zipfile

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
        print("  INFO - dist/ is absent; skipping bundle validation.")
        print("  Build artifacts with: python scripts/build_release.py --all")
        return 0

    dist_files = sorted(os.listdir(DIST))
    plugin_zips = [
        name for name in dist_files
        if name.startswith("qector-claude-plugin-") and name.endswith(".zip")
        and not name.endswith(".sha256")
        and "-source-" not in name
        and "-v" not in name
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
            "tests/",
            "mcp/tests/",
            ".github/",
            "presentations/",
            "bin/",
        ):
            check(
                not any(entry.startswith(forbidden_prefix) for entry in entries),
                f"{archive_name} does not contain {forbidden_prefix.rstrip('/')}",
            )
        check(
            "conftest.py" not in entries,
            f"{archive_name} does not contain conftest.py",
        )
        for forbidden_file in (
            "scratch_probe_library.py",
            "scratch_probe_servers.py",
        ):
            check(
                forbidden_file not in entries,
                f"{archive_name} does not contain {forbidden_file}",
            )

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
            for launcher in ("scripts/qector-python", "scripts/qector-python.cmd"):
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
