#!/usr/bin/env python3
"""Validate release metadata, public-surface boundaries, and evidence pins."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
RELEASE_MANIFEST = ROOT / "release-manifest.json"


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _server_version(path: Path, _depth: int = 0) -> str | None:
    """Return the SERVER_VERSION that a server module reports.

    Resolved statically from source: a module either declares a literal
    string or inherits one (``SERVER_VERSION = library.SERVER_VERSION``).
    Inheritance is followed by reading the referenced sibling module's own
    literal -- no modules are imported, so this gate stays runnable on a
    bare interpreter that does not have the ``mcp`` SDK installed.
    """
    text = path.read_text(encoding="utf-8")
    literal = re.search(
        r'^SERVER_VERSION\s*=\s*["\']([^"\']+)["\']',
        text,
        flags=re.MULTILINE,
    )
    if literal:
        return literal.group(1)
    if _depth >= 3:
        return None
    inherited = re.search(
        r'^SERVER_VERSION\s*=\s*([A-Za-z_][A-Za-z0-9_]*)\.SERVER_VERSION',
        text,
        flags=re.MULTILINE,
    )
    if not inherited:
        return None
    siblings = {
        "library": "mcp_server_library.py",
        "research": "mcp_server_qector_bench.py",
    }
    sibling = siblings.get(inherited.group(1))
    if sibling is None:
        return None
    return _server_version(path.parent / sibling, _depth + 1)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manual", type=Path, help="Optional Reference Manual PDF to hash-check.")
    parser.add_argument("--proof-suite", type=Path, help="Optional proof suite to hash-check.")
    args = parser.parse_args(argv)

    checks: list[tuple[bool, str]] = []
    release = _load_json(RELEASE_MANIFEST)
    version = release["release"]["version"]
    license_name = release["release"]["license"]

    json_paths = {
        ".claude-plugin/plugin.json": ROOT / ".claude-plugin" / "plugin.json",
        ".claude-plugin/marketplace.json": ROOT / ".claude-plugin" / "marketplace.json",
        ".claude-desktop-extension/manifest.json": ROOT / ".claude-desktop-extension" / "manifest.json",
        "server.json": ROOT / "server.json",
    }
    for label, path in json_paths.items():
        document = _load_json(path)
        checks.append((document.get("version") == version, f"{label} version is {version}"))
        # Marketplace manifests drop nonstandard fields for strict validators;
        # their license statement lives in plugin.json instead.
        if "license" in document:
            checks.append(
                (document.get("license") == license_name, f"{label} license is {license_name}")
            )

    for path in (
        ROOT / "mcp" / "mcp_server_library.py",
        ROOT / "mcp" / "mcp_server_qector_bench.py",
        ROOT / "mcp" / "mcp_server_desktop.py",
        ROOT / "mcp" / "mcp_server_admin.py",
    ):
        checks.append((
            _server_version(path) == version,
            f"{path.relative_to(ROOT)} server version is {version}",
        ))

    default_plugin = _load_json(ROOT / ".claude-plugin" / "plugin.json")
    default_servers = set(default_plugin.get("mcpServers", {}))
    checks.append((default_servers == {"qector-library"}, "Claude Code defaults to qector-library only"))

    desktop_manifest = _load_json(ROOT / ".claude-desktop-extension" / "manifest.json")
    desktop_tools = desktop_manifest.get("tools", [])
    checks.append((len(desktop_tools) == 8, "Desktop safe extension declares 8 stable tools"))
    checks.append((desktop_manifest["server"]["mcp_config"]["args"][-1] == "safe", "Desktop extension selects safe profile"))

    privacy = (ROOT / "PRIVACY.md").read_text(encoding="utf-8")
    checks.append(("https://pypi.org/pypi/qector-decoder-v3/json" in privacy, "Privacy notice names opt-in PyPI endpoint"))
    checks.append(("No network request is made by default" in privacy, "Privacy notice scopes offline default"))

    if args.manual:
        expected = release["evidence"]["reference_manual"]["sha256"]
        checks.append((args.manual.is_file(), "Reference Manual path exists"))
        if args.manual.is_file():
            checks.append((_file_sha256(args.manual) == expected, "Reference Manual SHA-256 matches release manifest"))
    if args.proof_suite:
        expected = release["evidence"]["external_proof_suite"]["sha256"]
        checks.append((args.proof_suite.is_file(), "Proof suite path exists"))
        if args.proof_suite.is_file():
            checks.append((_file_sha256(args.proof_suite) == expected, "Proof suite SHA-256 matches release manifest"))

    failures = 0
    for ok, label in checks:
        print(f"{'PASS' if ok else 'FAIL'} - {label}")
        failures += not ok
    print(f"Release metadata validation: {len(checks) - failures} passed, {failures} failed")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
