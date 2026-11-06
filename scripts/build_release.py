#!/usr/bin/env python3
"""Build the source, Claude Code plugin and Claude Desktop release artifacts.

Every archive is assembled in memory first so that:

* a per-archive ``INTEGRITY.json`` (SHA-256 of every runtime file *in that
  archive*) can be written next to the files it covers, and the secure
  server can verify it at startup from any of the three layouts;
* zip entries get a fixed timestamp and fixed permissions, so a rebuild of
  the same tree is byte-identical and the published SHA-256 values never
  drift from the artifacts (the 1.0.6 release shipped three different
  "1.0.6" trees under one version number; this builder makes that
  impossible by construction);
* ``server.json`` is patched with the real Desktop bundle digest.

``--bundle-lib WHEELHOUSE`` vendors the pinned runtime into ``server/lib``
of the Desktop bundle (what the MCPB ``python`` server type expects) using
``pip install --no-index --target``; the result is platform specific and
is named accordingly. Without it the bundle is the portable
bring-your-own-interpreter layout and the manifest's ``user_config``
Python path applies.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "mcp"))
import qector_integrity  # noqa: E402
import qector_signing  # noqa: E402

DIST = ROOT / "dist"
RELEASE_MANIFEST_PATH = ROOT / "release-manifest.json"
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
    "wheelhouse",
}
IGNORED_SUFFIXES = {".pyc", ".pyo", ".log", ".tmp", ".bak"}
PLUGIN_ROOTS = {
    ".claude-plugin",
    "commands",
    "agents",
    "skills",
    "prompts",
    "mega_prompts",
    "hooks",
    "mcp",
    "python",
    "scripts",
    "schemas",
    "docs",
    "governance",
    "cheat_sheets",
    "examples",
}
# The source archive is the complete reviewable tree: everything the plugin
# archive ships plus the Desktop extension sources, brand assets, tests and
# CI definitions. Every verification recipe in the documentation runs from
# it unchanged.
SOURCE_ROOTS = PLUGIN_ROOTS | {".claude-desktop-extension", "brand", "tests", ".github"}
SOURCE_EXCLUDE_PREFIXES: tuple[str, ...] = ()
ROOT_DOCS = {
    "AGENTS.md",
    "AIRGAP.md",
    "ANTHROPIC_COLLABORATION_PROPOSAL.md",
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
    "RELEASE_NOTES_v2.0.0.md",
    "RELEASE_NOTES_v2.0.1.md",
    "RELEASE_VALIDATION.md",
    "REVIEWER_GUIDE.md",
    "SECURITY.md",
    "THREAT_MODEL.md",
    "TOOL_STABILITY.md",
}
ROOT_RUNTIME = {"release-manifest.json", "requirements.txt", "requirements.lock", ".mcp.json", ".gitattributes"}
# Written into every archive so a rebuild from an extracted archive (no .git)
# still records the commit it came from and reproduces the MCPB byte for byte.
COMMIT_FILE = "RELEASE_COMMIT"
PROVENANCE_FILE = "provenance.json"
# server.json is MCP Registry metadata derived from the built MCPB digest; it
# is published by the release workflow and deliberately kept out of the
# archives so a build from a committed tree is a fixed point (no file in the
# archive depends on the archive's own hash).
SOURCE_FILES = ROOT_DOCS | ROOT_RUNTIME | {"ruff.toml", "conftest.py"}
# CLAUDE.md is repository context for people working on this tree; Claude
# Code does not load it from an installed plugin (the plugin validator
# warns), and the same guidance ships as skills, so it stays out of the
# plugin archive and in the source archive.
PLUGIN_FILES = (ROOT_DOCS | ROOT_RUNTIME) - {"CLAUDE.md"}
EXCLUDED_ROOT_FILES = frozenset({"scratch_probe_library.py", "scratch_probe_servers.py", "INTEGRITY.json", "INTEGRITY.json.sig", "RELEASE_COMMIT"})
SCRATCH_PREFIX = "scratch_"
DESKTOP_FILES = {
    ".claude-desktop-extension/manifest.json",
    ".claude-desktop-extension/icon.png",
    ".claude-desktop-extension/README.md",
    "scripts/qector-python",
    "scripts/qector-python.cmd",
    "scripts/qector-python.ps1",
    "scripts/generate_integrity_manifest.py",
    "scripts/qector_runtime_check.py",
    "mcp/mcp_server_desktop.py",
    "mcp/mcp_server_secure.py",
    "mcp/mcp_server_library.py",
    "mcp/qector_mcp_contract.py",
    "mcp/qector_mcp_compat.py",
    "mcp/qector_schemas.py",
    "mcp/qector_airgap.py",
    "mcp/qector_audit.py",
    "mcp/qector_integrity.py",
    "mcp/qector_signing.py",
    "mcp/qector_codes.py",
    "requirements.txt",
    "requirements.lock",
    "LICENSE.md",
    "PRIVACY.md",
    "SECURITY.md",
    "AIRGAP.md",
    "release-manifest.json",
    "DESKTOP_EXTENSION.md",
    "MCP_API.md",
}
DESKTOP_ARCHIVE_RENAMES = {
    ".claude-desktop-extension/manifest.json": None,
    ".claude-desktop-extension/icon.png": "icon.png",
    ".claude-desktop-extension/README.md": "README.md",
}
EXECUTABLE_ENTRIES = {"scripts/qector-python", "scripts/qector-python.cmd", "scripts/install_offline.sh"}
# Fixed DOS timestamp so SHA-256 sidecars are rebuild-stable.
ZIP_TIMESTAMP = (2026, 11, 2, 0, 0, 0)


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


def _root_filtered(path: Path) -> bool:
    rel = path.relative_to(ROOT)
    if len(rel.parts) == 1 and (rel.name in EXCLUDED_ROOT_FILES or rel.name.startswith(SCRATCH_PREFIX)):
        return True
    return False


def _plugin_files() -> Iterable[Path]:
    for path in _all_source_files():
        if _root_filtered(path):
            continue
        rel = path.relative_to(ROOT)
        if rel.name in PLUGIN_FILES and len(rel.parts) == 1:
            yield path
        elif rel.parts[0] in PLUGIN_ROOTS:
            yield path


def _source_files() -> Iterable[Path]:
    for path in _all_source_files():
        if _root_filtered(path):
            continue
        rel = path.relative_to(ROOT)
        if any(rel.as_posix().startswith(prefix) for prefix in SOURCE_EXCLUDE_PREFIXES):
            continue
        if rel.name in SOURCE_FILES and len(rel.parts) == 1:
            yield path
        elif rel.parts[0] in SOURCE_ROOTS:
            yield path


def _zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(filename=name, date_time=ZIP_TIMESTAMP)
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = (0o755 if name in EXECUTABLE_ENTRIES else 0o644) << 16
    return info


def _write_archive(output: Path, blobs: dict[str, bytes]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(blobs):
            archive.writestr(_zip_info(name), blobs[name])


_SIGNING_KEY: Any = None


def _with_integrity(blobs: dict[str, bytes], version: str, prefix: str = "") -> dict[str, bytes]:
    """Add RELEASE_COMMIT, INTEGRITY.json and (when a key is loaded) INTEGRITY.json.sig."""
    blobs = dict(blobs)
    blobs[prefix + COMMIT_FILE] = (_git_commit() + "\n").encode("ascii")
    stripped = {name[len(prefix):]: payload for name, payload in blobs.items() if name.startswith(prefix)}
    manifest = qector_integrity.build_manifest_from_blobs(stripped, version=version)
    manifest_bytes = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")
    blobs[prefix + qector_integrity.MANIFEST_NAME] = manifest_bytes
    if _SIGNING_KEY is not None:
        document = qector_signing.signature_document(_SIGNING_KEY, manifest_bytes, subject=qector_integrity.MANIFEST_NAME)
        blobs[prefix + qector_integrity.MANIFEST_NAME + qector_signing.SIGNATURE_SUFFIX] = (
            json.dumps(document, indent=2, sort_keys=True) + "\n"
        ).encode("utf-8")
    return blobs


def _check_signing_key_matches_release(release: dict[str, Any]) -> None:
    declared = release.get("signing", {}).get("public_key")
    actual = qector_signing.public_key_b64(_SIGNING_KEY)
    if declared != actual:
        raise RuntimeError(
            "signing key does not match release-manifest.json signing.public_key "
            f"(declared fingerprint {qector_signing.fingerprint(declared) if declared else 'none'}, "
            f"key fingerprint {qector_signing.fingerprint(actual)}); run scripts/sign_release.py --register-key first"
        )


def _pin_public_key(blobs: dict[str, bytes]) -> dict[str, bytes]:
    """When signing, make the shipped server configs pin the signing key.

    ``QECTOR_INTEGRITY_PUBKEY`` in ``plugin.json`` / ``.mcp.json`` / the
    Desktop manifest turns the startup gate from "consistent with the
    embedded key" into "signed by this key" for every install of the
    archive. It is not origin proof on its own (the archive carries the
    key) but it refuses unsigned or re-keyed trees out of the box; pinning
    the published fingerprint out-of-band remains the lab's job.
    """
    if _SIGNING_KEY is None:
        return blobs
    public = qector_signing.public_key_b64(_SIGNING_KEY)
    blobs = dict(blobs)
    for name in (".claude-plugin/plugin.json", ".mcp.json"):
        if name in blobs:
            document = json.loads(blobs[name].decode("utf-8"))
            for server in document.get("mcpServers", {}).values():
                server.setdefault("env", {})["QECTOR_INTEGRITY_PUBKEY"] = public
            blobs[name] = (json.dumps(document, indent=2) + "\n").encode("utf-8")
    return blobs


def _tree_blobs(files: Iterable[Path]) -> dict[str, bytes]:
    return _pin_public_key({path.relative_to(ROOT).as_posix(): path.read_bytes() for path in files})


def _write_sha256_sidecar(path: Path) -> str:
    digest = _sha256(path)
    path.with_suffix(path.suffix + ".sha256").write_text(f"{digest}  {path.name}\n", encoding="ascii")
    return digest


def _git_commit() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, timeout=10, check=True
        )
        commit = result.stdout.strip()
        if commit:
            return commit
    except Exception:
        pass
    recorded = ROOT / COMMIT_FILE
    if recorded.is_file():
        return recorded.read_text(encoding="ascii").strip() or "unavailable"
    return "unavailable"


def _git_dirty() -> bool:
    if not (ROOT / ".git").exists():
        return False  # extracted archive: provenance comes from RELEASE_COMMIT
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=no"],
            cwd=ROOT, capture_output=True, text=True, timeout=10, check=True,
        )
    except Exception:
        return False
    return any(line and not line.endswith("INTEGRITY.json") for line in result.stdout.splitlines())


def _validate_versions(release: dict[str, Any]) -> None:
    version = release["release"]["version"]
    for path in (
        ROOT / ".claude-plugin" / "plugin.json",
        ROOT / ".claude-plugin" / "marketplace.json",
        ROOT / ".claude-desktop-extension" / "manifest.json",
    ):
        if _load_json(path).get("version") != version:
            raise RuntimeError(f"{path.relative_to(ROOT)} does not match release version {version}")


def _vendor_runtime(wheelhouse: Path) -> dict[str, bytes]:
    """pip install --no-index --target into a temp dir; return server/lib blobs."""
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "lib"
        cmd = [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--no-index",
            "--find-links",
            str(wheelhouse),
            "--target",
            str(target),
            "--disable-pip-version-check",
            "-r",
            str(ROOT / "requirements.lock"),
        ]
        subprocess.run(cmd, check=True)
        blobs: dict[str, bytes] = {}
        for path in sorted(target.rglob("*")):
            relative = path.relative_to(target)
            # Console-script shims (bin/) are not importable code and are not
            # needed by PYTHONPATH loading; leave them out of the bundle.
            if path.is_file() and "__pycache__" not in path.parts and relative.parts[0] != "bin":
                blobs["server/lib/" + relative.as_posix()] = path.read_bytes()
        return blobs


def _desktop_manifest(*, bundled: bool) -> dict[str, Any]:
    manifest = _load_json(ROOT / ".claude-desktop-extension" / "manifest.json")
    if bundled:
        mcp_config = manifest["server"]["mcp_config"]
        mcp_config.setdefault("env", {})["PYTHONPATH"] = "${__dirname}/server/lib"
        # A vendored server/lib holds compiled wheels for exactly one platform
        # and one CPython minor; the manifest must say so rather than inherit
        # the portable bundle's three-platform claim.
        if sys.platform == "win32":
            win32 = mcp_config.get("platform_overrides", {}).get("win32")
            if win32 is not None:
                win32.setdefault("env", {})["PYTHONPATH"] = "${__dirname}\\server\\lib"
            manifest["compatibility"]["platforms"] = ["win32"]
        else:
            mcp_config.pop("platform_overrides", None)
            manifest["compatibility"]["platforms"] = ["darwin" if sys.platform == "darwin" else "linux"]
        minor = f"{sys.version_info.major}.{sys.version_info.minor}"
        manifest["compatibility"]["runtimes"]["python"] = f">={minor},<{sys.version_info.major}.{sys.version_info.minor + 1}"
        manifest["description"] += f" (runtime vendored for {sys.platform} {platform.machine()}, CPython {minor})"
    return manifest


def _local_import_closure(entry_points: Iterable[str]) -> set[str]:
    """Every ``mcp/<module>.py`` reachable by static import from *entry_points*.

    Walks ``import x`` / ``from x import y`` statements (module level and
    inside functions, since several modules import lazily) and resolves the
    names that exist as sibling files under ``mcp/``. An import that sits
    directly inside a ``try`` whose handler catches ``ImportError`` is
    optional by construction (the research server in the safe-profile
    MCPB) and is not part of the required closure.
    """
    import ast

    mcp_dir = ROOT / "mcp"
    local = {path.stem for path in mcp_dir.glob("*.py")}
    seen: set[str] = set()
    todo = [Path(entry).stem for entry in entry_points]

    def _optional_nodes(tree: ast.AST) -> set[int]:
        optional: set[int] = set()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Try):
                continue
            catches_import_error = any(
                handler.type is None
                or (isinstance(handler.type, ast.Name) and handler.type.id in ("ImportError", "ModuleNotFoundError", "Exception"))
                or (isinstance(handler.type, ast.Tuple) and any(isinstance(e, ast.Name) and e.id in ("ImportError", "ModuleNotFoundError", "Exception") for e in handler.type.elts))
                for handler in node.handlers
            )
            if catches_import_error:
                optional.update(id(child) for child in node.body)
        return optional

    while todo:
        module = todo.pop()
        if module in seen or module not in local:
            continue
        seen.add(module)
        tree = ast.parse((mcp_dir / f"{module}.py").read_text(encoding="utf-8"))
        optional = _optional_nodes(tree)
        for node in ast.walk(tree):
            if id(node) in optional:
                continue
            if isinstance(node, ast.Import):
                todo.extend(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                todo.append(node.module.split(".")[0])
    return {f"mcp/{name}.py" for name in seen}


def _check_desktop_closure() -> None:
    """Refuse to build a Desktop bundle whose server would fail to import."""
    required = _local_import_closure(
        name for name in DESKTOP_FILES if name.startswith("mcp/mcp_server_")
    )
    missing = sorted(required - DESKTOP_FILES)
    if missing:
        raise SystemExit(
            "DESKTOP_FILES is missing modules the bundled servers import: "
            + ", ".join(missing)
            + " (add them to DESKTOP_FILES in scripts/build_release.py)"
        )


def _desktop_blobs(version: str, wheelhouse: Path | None) -> dict[str, bytes]:
    _check_desktop_closure()
    blobs: dict[str, bytes] = {}
    for relative in sorted(DESKTOP_FILES):
        name = DESKTOP_ARCHIVE_RENAMES.get(relative, relative)
        if name is None:
            continue
        blobs[name] = (ROOT / relative).read_bytes()
    bundled = wheelhouse is not None
    manifest = _desktop_manifest(bundled=bundled)
    if _SIGNING_KEY is not None:
        public = qector_signing.public_key_b64(_SIGNING_KEY)
        manifest["server"]["mcp_config"].setdefault("env", {})["QECTOR_INTEGRITY_PUBKEY"] = public
        win32 = manifest["server"]["mcp_config"].get("platform_overrides", {}).get("win32")
        if win32 is not None:
            win32.setdefault("env", {})["QECTOR_INTEGRITY_PUBKEY"] = public
    blobs["manifest.json"] = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")
    blobs = _with_integrity(blobs, version)
    if bundled:
        blobs.update(_vendor_runtime(wheelhouse))
    provenance = {
        "release": _load_json(RELEASE_MANIFEST_PATH),
        "git_commit": _git_commit(),
        "git_tree_dirty": _git_dirty(),
        "runtime_bundled": bundled,
        "bundle_platform": platform.platform() if bundled else None,
        "bundle_python": platform.python_version() if bundled else None,
    }
    blobs["provenance.json"] = (json.dumps(provenance, indent=2, sort_keys=True) + "\n").encode("utf-8")
    return blobs


def _parse_lock(text: str) -> list[tuple[str, list[str]]]:
    """Parse ``name==version [--hash=sha256:...]...`` entries (backslash continuations allowed)."""
    entries: list[tuple[str, list[str]]] = []
    logical = ""
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        logical += " " + line.rstrip("\\")
        if line.endswith("\\"):
            continue
        tokens = logical.split()
        logical = ""
        requirement = tokens[0]
        if "==" not in requirement:
            continue
        hashes = [tok.split("sha256:", 1)[1] for tok in tokens[1:] if tok.startswith("--hash=sha256:")]
        entries.append((requirement, hashes))
    return entries


def _write_sbom(output: Path, release: dict[str, Any], artifacts: dict[str, str]) -> None:
    packages = [
        {
            "SPDXID": "SPDXRef-QECTORPlugin",
            "name": release["release"]["name"],
            "versionInfo": release["release"]["version"],
            "licenseConcluded": release["release"]["license"],
            "downloadLocation": release["release"]["repository"],
        }
    ]
    lock = (ROOT / "requirements.lock").read_text(encoding="utf-8")
    for requirement, hashes in _parse_lock(lock):
        name, version = requirement.split("==", 1)
        packages.append(
            {
                "SPDXID": "SPDXRef-" + "".join(ch if ch.isalnum() else "-" for ch in name),
                "name": name,
                "versionInfo": version,
                "licenseConcluded": "NOASSERTION",
                "downloadLocation": f"https://pypi.org/project/{name}/{version}/",
                "checksums": [{"algorithm": "SHA256", "checksumValue": digest} for digest in hashes],
                "externalRefs": [
                    {
                        "referenceCategory": "PACKAGE-MANAGER",
                        "referenceType": "purl",
                        "referenceLocator": f"pkg:pypi/{name.lower()}@{version}",
                    }
                ],
            }
        )
    document = {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": f"{release['release']['name']}-{release['release']['version']}",
        "documentNamespace": f"{release['release']['repository']}/sbom/{release['release']['version']}",
        "creationInfo": {"creators": ["Tool: scripts/build_release.py"], "created": "2026-11-02T00:00:00Z"},
        "packages": packages,
        "relationships": [
            {"spdxElementId": "SPDXRef-DOCUMENT", "relationshipType": "DESCRIBES", "relatedSpdxElement": "SPDXRef-QECTORPlugin"}
        ]
        + [
            {"spdxElementId": "SPDXRef-QECTORPlugin", "relationshipType": "DEPENDS_ON", "relatedSpdxElement": pkg["SPDXID"]}
            for pkg in packages[1:]
        ],
        "annotations": [
            {"annotationType": "OTHER", "annotationDate": "2026-11-02T00:00:00Z", "annotator": "Tool: scripts/build_release.py", "comment": f"{name} sha256={digest}"}
            for name, digest in sorted(artifacts.items())
        ],
    }
    output.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _patch_server_json(release: dict[str, Any], desktop_artifact: str, desktop_sha256: str) -> None:
    if not SERVER_JSON_PATH.is_file():
        print("skip server.json patch: server.json not found")
        return
    version = release["release"]["version"]
    repository = release["release"]["repository"]
    document = _load_json(SERVER_JSON_PATH)
    document["version"] = version
    package = document.get("packages", [{}])[0]
    package["version"] = version
    package["fileSha256"] = desktop_sha256
    package["identifier"] = f"{repository.rstrip('/')}/releases/download/v{version}/{desktop_artifact}"
    document["packages"] = [package] + document.get("packages", [])[1:]
    SERVER_JSON_PATH.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"patched server.json sha256={desktop_sha256}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--source", action="store_true", help="Build the public source archive.")
    parser.add_argument("--plugin", action="store_true", help="Build the Claude Code plugin archive.")
    parser.add_argument("--desktop", action="store_true", help="Build the Claude Desktop MCPB bundle.")
    parser.add_argument("--all", action="store_true", help="Build every release artifact.")
    parser.add_argument(
        "--bundle-lib",
        type=Path,
        default=None,
        help="Wheelhouse directory; vendor the pinned runtime into server/lib of the Desktop bundle (platform specific).",
    )
    parser.add_argument("--patch-server-json", action="store_true", help="Rewrite server.json with the Desktop MCPB digest (release workflow only).")
    parser.add_argument("--no-server-json", action="store_true", help="Accepted for compatibility; patching is off by default.")
    parser.add_argument("--allow-dirty", action="store_true", help="Build from an uncommitted tree (provenance then names the last commit, not the tree).")
    parser.add_argument(
        "--signing-key",
        type=Path,
        default=None,
        help="Ed25519 private key (PEM) to sign INTEGRITY.json in every archive and dist/SHA256SUMS. Must match release-manifest.json signing.public_key.",
    )
    args = parser.parse_args(argv)
    if not any((args.source, args.plugin, args.desktop, args.all)):
        parser.error("specify --source, --plugin, --desktop, or --all")

    release = _load_json(RELEASE_MANIFEST_PATH)
    _validate_versions(release)
    version = release["release"]["version"]
    global _SIGNING_KEY
    if args.signing_key is not None:
        _SIGNING_KEY = qector_signing.load_private_key(args.signing_key.resolve())
        _check_signing_key_matches_release(release)
    elif release.get("signing", {}).get("public_key"):
        print("WARNING: release-manifest.json declares a signing key but --signing-key was not given; archives will be unsigned and strict verification against a pinned key will fail")
    if _git_dirty() and not args.allow_dirty:
        parser.error(
            "working tree has uncommitted changes; provenance.json would attest the wrong commit. "
            "Commit first or pass --allow-dirty for a local test build."
        )
    # Refresh the working-tree manifest so a source checkout validates too.
    (ROOT / qector_integrity.MANIFEST_NAME).write_text(
        json.dumps(qector_integrity.build_manifest(ROOT, version=version), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    artifacts: dict[str, str] = {}
    DIST.mkdir(parents=True, exist_ok=True)

    # Desktop first so a --patch-server-json release run has the MCPB digest
    # before anything else is written (server.json itself stays out of the
    # archives).
    if args.desktop or args.all:
        wheelhouse = args.bundle_lib.resolve() if args.bundle_lib else None
        # The portable bundle is always built; with --bundle-lib the vendored,
        # platform-specific bundle is built as well in the same invocation so
        # one provenance record covers both.
        variants: list[Path | None] = [None] + ([wheelhouse] if wheelhouse is not None else [])
        for variant in variants:
            suffix = ""
            if variant is not None:
                tag = f"{sys.platform}-{platform.machine()}-py{sys.version_info.major}{sys.version_info.minor}".lower()
                suffix = f"-bundled-{tag}"
            output = DIST / f"qector-claude-desktop-{version}{suffix}.mcpb"
            _write_archive(output, _desktop_blobs(version, variant))
            artifacts[output.name] = _write_sha256_sidecar(output)
            if args.patch_server_json and variant is None:
                _patch_server_json(release, output.name, artifacts[output.name])
    if args.source or args.all:
        output = DIST / f"qector-claude-plugin-source-{version}.zip"
        _write_archive(output, _with_integrity(_tree_blobs(_source_files()), version))
        artifacts[output.name] = _write_sha256_sidecar(output)
    if args.plugin or args.all:
        output = DIST / f"qector-claude-plugin-{version}.zip"
        _write_archive(output, _with_integrity(_tree_blobs(_plugin_files()), version))
        artifacts[output.name] = _write_sha256_sidecar(output)

    (DIST / "release-manifest.json").write_text(json.dumps(release, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    # Provenance, SBOM and SHA256SUMS accumulate across invocations (a
    # --desktop --bundle-lib run after --all must not drop the three core
    # artifacts from the attestation), restricted to artifacts still on disk.
    sums_path = DIST / "SHA256SUMS"
    existing: dict[str, str] = {}
    if sums_path.is_file():
        for line in sums_path.read_text(encoding="ascii").splitlines():
            if line.strip():
                digest, name = line.split(None, 1)
                if (DIST / name.strip()).is_file():
                    existing[name.strip()] = digest
    existing.update(artifacts)
    all_artifacts = dict(sorted(existing.items()))
    (DIST / PROVENANCE_FILE).write_text(
        json.dumps({"release": release, "git_commit": _git_commit(), "git_tree_dirty": _git_dirty(), "artifacts": all_artifacts}, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    _write_sbom(DIST / f"qector-claude-plugin-{version}.sbom.json", release, all_artifacts)
    sums_path.write_text("".join(f"{digest}  {name}\n" for name, digest in all_artifacts.items()), encoding="ascii")
    if _SIGNING_KEY is not None:
        document = qector_signing.signature_document(_SIGNING_KEY, sums_path.read_bytes(), subject="SHA256SUMS")
        (DIST / ("SHA256SUMS" + qector_signing.SIGNATURE_SUFFIX)).write_text(
            json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        print(f"signed SHA256SUMS with key fingerprint {document['fingerprint']}")
    for name, digest in sorted(artifacts.items()):
        print(f"built {name} sha256={digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
