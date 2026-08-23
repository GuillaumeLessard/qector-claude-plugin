#!/usr/bin/env python3
"""Build distinct source, Claude Code, and Claude Desktop release artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
RELEASE_MANIFEST_PATH = ROOT / "release-manifest.json"
# The MCP Registry server descriptor. The build patches this file in
# place whenever a Desktop MCPB is produced, so local publishes and the
# CI publish workflow stay in sync with the on-disk artifact hash.
SERVER_JSON_PATH = ROOT / "server.json"

IGNORED_PARTS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".venv",
    "venv",
    "node_modules",
    "artifacts",
    "dist",
}
IGNORED_SUFFIXES = {".pyc", ".pyo", ".log", ".tmp", ".bak"}
PLUGIN_ROOTS = {
    ".claude-plugin",
    "bin",
    "commands",
    "agents",
    "skills",
    "prompts",
    "mega_prompts",
    "hooks",
    "mcp",
    "python",
    "scripts",
    "docs",
    "governance",
    "cheat_sheets",
    "examples",
}
# The source archive is the canonical public QECTOR source release.
# Unlike the plugin archive, it must NOT ship development-only material
# (test suite, CI workflows, internal onboarding decks, scratch probes)
# that lives in the working tree. The whitelist below mirrors how
# PLUGIN_ROOTS / PLUGIN_FILES work for the Claude Code plugin archive
# and is the single source of truth for what the source zip may
# contain. Dev-internal directories (tests/, .github/, presentations/,
# conftest.py, scratch_probe_*.py) are excluded by omission, and
# SOURCE_EXCLUDE_PREFIXES adds explicit "everything below this path is
# internal" carve-outs even when the root is otherwise whitelisted.
SOURCE_ROOTS = {
    ".claude-plugin",
    ".claude-desktop-extension",
    "bin",
    "mcp",
    "python",
    "scripts",
    "docs",
    "governance",
    "cheat_sheets",
    "examples",
    "brand",
}
SOURCE_EXCLUDE_PREFIXES = (
    "mcp/tests/",
)
SOURCE_FILES = {
    "AGENTS.md",
    "ARCHITECTURE.md",
    "CHANGELOG.md",
    "CLAUDE.md",
    "CLAUDE_DESKTOP.md",
    "DESKTOP_EXTENSION.md",
    "DISCLAIMER.md",
    "FIRST_BOOT.md",
    "LICENSE.md",
    "MCP_API.md",
    "PRIVACY.md",
    "PROVENANCE.md",
    "README.md",
    "RELEASE_VALIDATION.md",
    "SECURITY.md",
    "TOOL_STABILITY.md",
    "release-manifest.json",
    "server.json",
    "requirements.txt",
    "ruff.toml",
    ".mcp.json",
}
PLUGIN_FILES = {
    ".mcp.json",
    "README.md",
    "CHANGELOG.md",
    "CLAUDE.md",
    "CLAUDE_DESKTOP.md",
    "AGENTS.md",
    "LICENSE.md",
    "PRIVACY.md",
    "DISCLAIMER.md",
    "requirements.txt",
    "release-manifest.json",
    "TOOL_STABILITY.md",
    "SECURITY.md",
    "MCP_API.md",
    "ARCHITECTURE.md",
    "FIRST_BOOT.md",
    "DESKTOP_EXTENSION.md",
    "PROVENANCE.md",
    "RELEASE_VALIDATION.md",
}

# Root-level files that are NEVER part of any packaged bundle. The
# build_release builder is the only release path that picks files by
# explicit name, so this set is the authoritative allowlist for the
# archive root. Anything not listed here must live under PLUGIN_ROOTS.
# Root-level scratch probes (one-off diagnostics left by interactive
# sessions) are also excluded by the SCRATCH_PREFIX below.
EXCLUDED_ROOT_FILES = frozenset(
    {
        "scratch_probe_library.py",
        "scratch_probe_servers.py",
    }
)
SCRATCH_PREFIX = "scratch_"
DESKTOP_FILES = {
    ".claude-desktop-extension/manifest.json",
    ".claude-desktop-extension/icon.png",
    ".claude-desktop-extension/README.md",
    "bin/qector-python",
    "bin/qector-python.cmd",
    "mcp/mcp_server_desktop.py",
    "mcp/mcp_server_library.py",
    "mcp/qector_mcp_contract.py",
    "requirements.txt",
    "LICENSE.md",
    "PRIVACY.md",
    "SECURITY.md",
    "release-manifest.json",
    "DESKTOP_EXTENSION.md",
    "MCP_API.md",
}
# MCPB layout: Claude Desktop reads icon.png and README.md from the bundle
# root, while the source tree keeps those files under
# .claude-desktop-extension/. None means "omit; written separately".
DESKTOP_ARCHIVE_RENAMES = {
    ".claude-desktop-extension/manifest.json": None,
    ".claude-desktop-extension/icon.png": "icon.png",
    ".claude-desktop-extension/README.md": "README.md",
}


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_included(path: Path) -> bool:
    rel = path.relative_to(ROOT)
    return not any(part in IGNORED_PARTS for part in rel.parts) and path.suffix not in IGNORED_SUFFIXES


def _all_source_files() -> Iterable[Path]:
    for path in sorted(ROOT.rglob("*")):
        if path.is_file() and _is_included(path):
            yield path


def _plugin_files() -> Iterable[Path]:
    for path in _all_source_files():
        rel = path.relative_to(ROOT)
        if rel.name in EXCLUDED_ROOT_FILES and len(rel.parts) == 1:
            continue
        if rel.name.startswith(SCRATCH_PREFIX) and len(rel.parts) == 1:
            continue
        if rel.name in PLUGIN_FILES and len(rel.parts) == 1:
            yield path
        elif rel.parts[0] in PLUGIN_ROOTS:
            yield path


def _source_files() -> Iterable[Path]:
    """Public-source whitelist. Excludes tests/, .github/, presentations/,
    scratch probes, conftest, and any other dev-internal material that
    may exist in the working tree but is not part of the released
    QECTOR source distribution."""
    for path in _all_source_files():
        rel = path.relative_to(ROOT)
        if rel.name in EXCLUDED_ROOT_FILES and len(rel.parts) == 1:
            continue
        if rel.name.startswith(SCRATCH_PREFIX) and len(rel.parts) == 1:
            continue
        if any(rel.as_posix().startswith(prefix) for prefix in SOURCE_EXCLUDE_PREFIXES):
            continue
        if rel.name in SOURCE_FILES and len(rel.parts) == 1:
            yield path
        elif rel.parts[0] in SOURCE_ROOTS:
            yield path


# Fixed DOS timestamp so SHA-256 sidecars are rebuild-stable. ZipInfo
# otherwise stamps writestr() entries with the current local time, which
# made the Desktop MCPB hash change on every build.
ZIP_TIMESTAMP = (2026, 8, 23, 0, 0, 0)


def _zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(filename=name, date_time=ZIP_TIMESTAMP)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    # Deterministic permissions: launchers must survive extraction as 0755 so
    # Claude Code / Claude Desktop can exec them directly after install.
    if name.startswith("bin/"):
        info.external_attr = 0o755 << 16
    else:
        info.external_attr = 0o644 << 16
    return info


def _write_zip_bytes(archive: zipfile.ZipFile, name: str, payload: bytes) -> None:
    archive.writestr(_zip_info(name), payload)


def _write_zip(output: Path, files: Iterable[Path], extra: dict[str, bytes] | None = None) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            _write_zip_bytes(
                archive, path.relative_to(ROOT).as_posix(), path.read_bytes()
            )
        for name, contents in (extra or {}).items():
            payload = contents if isinstance(contents, bytes) else contents.encode("utf-8")
            _write_zip_bytes(archive, name, payload)


def _write_sha256_sidecar(path: Path) -> str:
    digest = _sha256(path)
    path.with_suffix(path.suffix + ".sha256").write_text(
        f"{digest}  {path.name}\n", encoding="ascii"
    )
    return digest


def _git_commit() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
        return result.stdout.strip()
    except Exception:
        return "unavailable"


def _validate_versions(release: dict[str, Any]) -> None:
    version = release["release"]["version"]
    for path in (
        ROOT / ".claude-plugin" / "plugin.json",
        ROOT / ".claude-plugin" / "marketplace.json",
        ROOT / ".claude-desktop-extension" / "manifest.json",
    ):
        if _load_json(path).get("version") != version:
            raise RuntimeError(f"{path.relative_to(ROOT)} does not match release version {version}")


def _runtime_python_relative(runtime_root: Path) -> Path:
    candidates = (Path("Scripts/python.exe"), Path("bin/python"))
    for relative in candidates:
        if (runtime_root / relative).is_file():
            return relative
    raise RuntimeError(
        "runtime root must be a virtual environment containing Scripts/python.exe or bin/python"
    )


def _desktop_manifest(runtime_root: Path | None) -> tuple[dict[str, Any], dict[str, Any]]:
    manifest = _load_json(ROOT / ".claude-desktop-extension" / "manifest.json")
    provenance: dict[str, Any] = {
        "release": _load_json(RELEASE_MANIFEST_PATH),
        "git_commit": _git_commit(),
        "runtime_bundled": runtime_root is not None,
    }
    if runtime_root is not None:
        relative = _runtime_python_relative(runtime_root)
        manifest["server"]["mcp_config"]["command"] = (
            "${__dirname}/runtime/" + relative.as_posix()
        )
        # Bundled-runtime builds own the interpreter on every platform, so the
        # launcher-shim platform overrides must not fight the runtime path.
        manifest.pop("platform_overrides", None)
        provenance["runtime_root_name"] = runtime_root.name
    return manifest, provenance


def _desktop_entries(runtime_root: Path | None) -> list[Path]:
    entries = [ROOT / relative for relative in sorted(DESKTOP_FILES)]
    if runtime_root is not None:
        for path in sorted(runtime_root.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts:
                entries.append(path)
    return entries


def _write_desktop_bundle(output: Path, runtime_root: Path | None) -> None:
    manifest, provenance = _desktop_manifest(runtime_root)
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in _desktop_entries(runtime_root):
            if runtime_root is not None and path.is_relative_to(runtime_root):
                name = "runtime/" + path.relative_to(runtime_root).as_posix()
            else:
                name = path.relative_to(ROOT).as_posix()
            if name in DESKTOP_ARCHIVE_RENAMES:
                renamed = DESKTOP_ARCHIVE_RENAMES[name]
                if renamed is None:
                    continue
                name = renamed
            _write_zip_bytes(archive, name, path.read_bytes())
        _write_zip_bytes(
            archive,
            "manifest.json",
            (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8"),
        )
        _write_zip_bytes(
            archive,
            "provenance.json",
            (json.dumps(provenance, indent=2, sort_keys=True) + "\n").encode("utf-8"),
        )


def _write_sbom(output: Path, release: dict[str, Any], artifacts: dict[str, str]) -> None:
    runtime = release["runtime"]
    document = {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": f"{release['release']['name']}-{release['release']['version']}",
        "documentNamespace": release["release"]["repository"],
        "packages": [
            {
                "SPDXID": "SPDXRef-QECTORPlugin",
                "name": release["release"]["name"],
                "versionInfo": release["release"]["version"],
                "licenseConcluded": release["release"]["license"],
            },
            {
                "SPDXID": "SPDXRef-QECTORDecoder",
                "name": "qector-decoder-v3",
                "versionInfo": runtime["qector_decoder_v3"],
                "licenseConcluded": "NOASSERTION",
            },
            {
                "SPDXID": "SPDXRef-MCP",
                "name": "mcp",
                "versionInfo": runtime["mcp"],
                "licenseConcluded": "NOASSERTION",
            },
        ],
        "annotations": [
            {"annotationType": "OTHER", "comment": f"{name} sha256={digest}"}
            for name, digest in sorted(artifacts.items())
        ],
    }
    output.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _patch_server_json(release: dict[str, Any], desktop_artifact: str, desktop_sha256: str) -> None:
    """Rewrite the MCP Registry server descriptor with the just-built MCPB.

    The descriptor carries four fields that depend on the freshly built
    Desktop MCPB: the top-level ``version``, the package ``version``, the
    ``fileSha256`` of the MCPB, and the ``identifier`` download URL. Every
    other field is preserved verbatim so future schema additions in
    ``server.json`` survive a rebuild. The download URL is composed from
    ``release-manifest.json`` so the repository location stays in one
    place. The local file is left untouched when it is missing, which
    keeps this helper safe to call from builds that do not publish to
    the MCP Registry.
    """
    if not SERVER_JSON_PATH.is_file():
        print(f"skip server.json patch: {SERVER_JSON_PATH.relative_to(ROOT)} not found")
        return
    version = release["release"]["version"]
    repository = release["release"]["repository"]
    identifier = (
        f"{repository.rstrip('/')}/releases/download/v{version}/{desktop_artifact}"
    )
    document = _load_json(SERVER_JSON_PATH)
    document["version"] = version
    package = document.get("packages", [{}])[0]
    package["version"] = version
    package["fileSha256"] = desktop_sha256
    package["identifier"] = identifier
    document["packages"] = document.get("packages", [])
    document["packages"][0] = package
    SERVER_JSON_PATH.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"patched {SERVER_JSON_PATH.relative_to(ROOT)} sha256={desktop_sha256}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", action="store_true", help="Build source archive.")
    parser.add_argument("--plugin", action="store_true", help="Build Claude Code plugin archive.")
    parser.add_argument("--desktop", action="store_true", help="Build Claude Desktop MCPB bundle.")
    parser.add_argument("--all", action="store_true", help="Build every release artifact.")
    parser.add_argument(
        "--runtime-root",
        type=Path,
        help="Optional virtual-environment root to bundle in the MCPB artifact.",
    )
    parser.add_argument(
        "--no-server-json",
        action="store_true",
        help=(
            "Skip rewriting the MCP Registry server.json after a Desktop "
            "MCPB build. The default is to keep server.json in sync with "
            "the on-disk artifact so local publishes match the registry "
            "descriptor."
        ),
    )
    args = parser.parse_args(argv)
    if not any((args.source, args.plugin, args.desktop, args.all)):
        parser.error("specify --source, --plugin, --desktop, or --all")
    if args.runtime_root and not args.desktop and not args.all:
        parser.error("--runtime-root requires --desktop or --all")

    release = _load_json(RELEASE_MANIFEST_PATH)
    _validate_versions(release)
    version = release["release"]["version"]
    build_source = args.source or args.all
    build_plugin = args.plugin or args.all
    build_desktop = args.desktop or args.all
    runtime_root = args.runtime_root.resolve() if args.runtime_root else None
    artifacts: dict[str, str] = {}

    if build_source:
        output = DIST / f"qector-claude-plugin-source-{version}.zip"
        _write_zip(output, _source_files())
        artifacts[output.name] = _write_sha256_sidecar(output)
    if build_plugin:
        output = DIST / f"qector-claude-plugin-{version}.zip"
        _write_zip(output, _plugin_files())
        artifacts[output.name] = _write_sha256_sidecar(output)
    if build_desktop:
        output = DIST / f"qector-claude-desktop-{version}.mcpb"
        _write_desktop_bundle(output, runtime_root)
        artifacts[output.name] = _write_sha256_sidecar(output)
        if not args.no_server_json:
            _patch_server_json(release, output.name, artifacts[output.name])

    DIST.mkdir(parents=True, exist_ok=True)
    (DIST / "release-manifest.json").write_text(
        json.dumps(release, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (DIST / "provenance.json").write_text(
        json.dumps(
            {"release": release, "git_commit": _git_commit(), "artifacts": artifacts},
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    _write_sbom(DIST / f"qector-claude-plugin-{version}.sbom.json", release, artifacts)
    (DIST / "SHA256SUMS").write_text(
        "".join(f"{digest}  {name}\n" for name, digest in sorted(artifacts.items())),
        encoding="ascii",
    )
    for name, digest in sorted(artifacts.items()):
        print(f"built {name} sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
