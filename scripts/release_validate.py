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
        "secure": "mcp_server_secure.py",
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
        if label == "server.json" and not path.is_file():
            # Registry metadata is published by the release workflow and is
            # not part of the archives; its absence in an extracted archive
            # is expected.
            print("SKIP - server.json not present (registry metadata, repository only)")
            continue
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
        ROOT / "mcp" / "mcp_server_secure.py",
    ):
        checks.append((
            _server_version(path) == version,
            f"{path.relative_to(ROOT)} server version is {version}",
        ))

    default_plugin = _load_json(ROOT / ".claude-plugin" / "plugin.json")
    default_servers = set(default_plugin.get("mcpServers", {}))
    checks.append((default_servers == {"qector-secure"}, "Claude Code defaults to qector-secure only"))
    secure_cfg = default_plugin["mcpServers"].get("qector-secure", {})
    checks.append((secure_cfg.get("args", [])[-2:] == ["--profile", "safe"], "Claude Code default profile is safe"))
    checks.append((secure_cfg.get("env", {}).get("QECTOR_AIR_GAPPED") == "1", "Claude Code default is air-gapped"))

    desktop_manifest = _load_json(ROOT / ".claude-desktop-extension" / "manifest.json")
    desktop_tools = desktop_manifest.get("tools", [])
    checks.append((len(desktop_tools) == 12, "Desktop safe extension declares 12 tools (8 stable + 4 control)"))
    checks.append((desktop_manifest["server"]["mcp_config"]["args"][-1] == "safe", "Desktop extension selects safe profile"))
    checks.append((desktop_manifest["server"]["entry_point"] == "mcp/mcp_server_secure.py", "Desktop extension runs the secure server"))
    checks.append((desktop_manifest["server"]["mcp_config"]["env"].get("QECTOR_AIR_GAPPED") == "1", "Desktop extension is air-gapped by default"))
    checks.append((desktop_manifest["compatibility"]["runtimes"]["python"] == ">=3.10,<3.14", "Desktop extension declares the Python 3.10-3.13 window"))
    checks.append(("platform_overrides" not in desktop_manifest and "win32" in desktop_manifest["server"]["mcp_config"].get("platform_overrides", {}), "Desktop manifest keeps platform_overrides inside server.mcp_config (MCPB spec)"))
    mcp_config = desktop_manifest["server"]["mcp_config"]
    checks.append((mcp_config["command"] == "sh" and mcp_config["args"][0].endswith("scripts/qector-python"), "Desktop POSIX command is sh + launcher (no dependency on an executable bit surviving extraction)"))
    win32 = mcp_config["platform_overrides"]["win32"]
    checks.append((win32["command"] == "powershell.exe" and "-File" in win32["args"] and any(a.endswith("qector-python.ps1") for a in win32["args"]), "Desktop win32 command is powershell.exe -File (a real executable; .cmd files cannot be spawned without a shell)"))
    checks.append((win32["args"][-1] == "safe" and win32["env"] == mcp_config["env"], "Desktop win32 override runs the same profile with the same environment"))
    gitattributes = (ROOT / ".gitattributes").read_text(encoding="utf-8") if (ROOT / ".gitattributes").is_file() else ""
    checks.append(("-text" in gitattributes.split("\n")[0:12].__str__() and any(line.split()[:2] == ["*", "-text"] for line in gitattributes.splitlines() if line.strip() and not line.startswith("#")), ".gitattributes disables EOL conversion (Windows checkouts keep the hashed bytes)"))
    lock = (ROOT / "requirements.lock").read_text(encoding="utf-8")
    checks.append(("qector-decoder-v3==1.0.1" in lock, "requirements.lock pins qector-decoder-v3==1.0.1"))
    checks.append((any(line.startswith("mcp==1.3") or line.startswith("mcp==2.") for line in lock.splitlines()), "requirements.lock pins a patched mcp release"))
    checks.append(((ROOT / "schemas" / "index.json").is_file(), "schemas/index.json exported"))

    privacy = (ROOT / "PRIVACY.md").read_text(encoding="utf-8")
    checks.append(("https://pypi.org/pypi/qector-decoder-v3/json" in privacy, "Privacy notice names opt-in PyPI endpoint"))
    checks.append(("No network request is made by default" in privacy, "Privacy notice scopes offline default"))
    security = (ROOT / "SECURITY.md").read_text(encoding="utf-8")
    checks.append(("api.stripe.com" in security, "Security notice discloses the wheel's native network surface"))

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
