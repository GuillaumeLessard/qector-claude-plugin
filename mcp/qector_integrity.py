"""Runtime integrity manifest for the QECTOR MCP servers.

``INTEGRITY.json`` (repository root, also shipped inside every archive)
lists the SHA-256 of every file the servers execute or read at runtime.
``scripts/generate_integrity_manifest.py`` writes it at build time and the
secure server verifies it at startup:

* ``QECTOR_INTEGRITY_STRICT=1`` (default for the Desktop bundle manifest)
  refuses to start when a listed file is missing or modified;
* otherwise a mismatch is reported through ``integrity_check`` and on
  stderr but the server still starts, so a developer tree keeps working.

Files under ``mcp/``, ``python/``, ``scripts/`` (launchers, hook scripts,
installers, validators) and the manifests are covered. Documentation is deliberately excluded so an edited
README never invalidates a runtime manifest.
"""

from __future__ import annotations

import hashlib
import importlib.metadata
import json
from pathlib import Path
from typing import Any, Iterable

MANIFEST_NAME = "INTEGRITY.json"
MANIFEST_VERSION = "1"
RUNTIME_GLOBS: tuple[str, ...] = (
    "mcp/*.py",
    "python/*.py",
    "scripts/*.py",
    "scripts/*.sh",
    "scripts/*.ps1",
    "scripts/*.cmd",
    "scripts/*.bat",
    "scripts/qector-python",
    ".claude-plugin/plugin.json",
    ".claude-plugin/marketplace.json",
    ".claude-desktop-extension/manifest.json",
    ".mcp.json",
    "hooks/hooks.json",
    "release-manifest.json",
    "requirements.txt",
    "requirements.lock",
)
RUNTIME_DISTRIBUTIONS: tuple[str, ...] = ("qector-decoder-v3", "mcp", "numpy", "jsonschema", "pydantic")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def runtime_files(root: Path) -> list[Path]:
    seen: set[Path] = set()
    for pattern in RUNTIME_GLOBS:
        for path in sorted(root.glob(pattern)):
            if path.is_file() and "__pycache__" not in path.parts:
                seen.add(path)
    return sorted(seen)


def is_runtime_path(relative: str) -> bool:
    """True when *relative* (posix) matches one of RUNTIME_GLOBS.

    ``*`` never crosses a ``/`` here, mirroring ``Path.glob`` in
    :func:`runtime_files`, so archive manifests and tree manifests select
    the same files.
    """
    import re

    for pattern in RUNTIME_GLOBS:
        regex = "^" + re.escape(pattern).replace(r"\*", "[^/]*") + "$"
        if re.match(regex, relative):
            return True
    return False


def _display_path(path: Path, root: Path) -> str:
    """Manifest location for reports: relative to the install root, never the account's home."""
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        home = str(Path.home())
        text = str(path)
        return text.replace(home, "~") if home and home != "/" and home in text else text


def _safe_manifest_entry(relative: Any, expected: Any) -> bool:
    """True when a manifest entry may be verified: a runtime path confined to the root and a hex digest."""
    if not isinstance(relative, str) or not isinstance(expected, str):
        return False
    if relative.startswith(("/", "\\")) or ":" in relative or "\\" in relative:
        return False
    parts = relative.split("/")
    if any(part in ("", ".", "..") for part in parts):
        return False
    if not is_runtime_path(relative):
        return False
    return len(expected) == 64 and all(ch in "0123456789abcdef" for ch in expected)


def build_manifest_from_blobs(blobs: dict[str, bytes], *, version: str) -> dict[str, Any]:
    """Manifest for an archive assembled in memory (path -> bytes)."""
    files = {
        relative: hashlib.sha256(payload).hexdigest()
        for relative, payload in blobs.items()
        if is_runtime_path(relative)
    }
    return {
        "manifest_version": MANIFEST_VERSION,
        "release_version": version,
        "algorithm": "sha256",
        "files": dict(sorted(files.items())),
    }


def build_manifest(root: Path, *, version: str, extra_files: Iterable[Path] = ()) -> dict[str, Any]:
    files: dict[str, str] = {}
    for path in list(runtime_files(root)) + list(extra_files):
        files[path.relative_to(root).as_posix()] = sha256_file(path)
    return {
        "manifest_version": MANIFEST_VERSION,
        "release_version": version,
        "algorithm": "sha256",
        "files": dict(sorted(files.items())),
    }


def installed_distributions() -> dict[str, str | None]:
    out: dict[str, str | None] = {}
    for name in RUNTIME_DISTRIBUTIONS:
        try:
            out[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            out[name] = None
    return out


def _embedded_public_key(root: Path) -> str | None:
    try:
        release = json.loads((root / "release-manifest.json").read_text(encoding="utf-8"))
        key = release.get("signing", {}).get("public_key")
        return str(key) if key else None
    except (OSError, ValueError, AttributeError):
        return None


def verify(
    root: Path,
    *,
    strict: bool,
    manifest_path: Path | None = None,
    pinned_public_key: str | None = None,
) -> dict[str, Any]:
    """Verify the manifest, its files and (when present or required) its signature.

    ``passed`` is True only when every listed file matches, no runtime file is
    unlisted, and — if a key is pinned — the signature verifies under that key.
    An unpinned signature is verified against the key embedded in
    ``release-manifest.json`` and reported as a consistency check.
    """
    from qector_signing import verify_signature_file

    manifest_file = manifest_path or (root / MANIFEST_NAME)
    report: dict[str, Any] = {
        "manifest_path": _display_path(manifest_file, root),
        "manifest_present": manifest_file.is_file(),
        "manifest_version": None,
        "strict": bool(strict),
        "files_checked": 0,
        "files_ok": 0,
        "mismatched": [],
        "missing": [],
        "unlisted_runtime_files": [],
        "passed": False,
        "signature": {"present": False, "valid": False, "source": "none", "fingerprint": None, "pinned_fingerprint": None, "reason": "not checked"},
        "runtime_distributions": installed_distributions(),
    }
    if not manifest_file.is_file():
        # No manifest means nothing was verified; ``passed`` is False even in
        # non-strict mode so the integrity_check tool never reports a
        # verification it did not perform. configure() decides whether a
        # missing manifest is fatal.
        report["unlisted_runtime_files"] = [path.relative_to(root).as_posix() for path in runtime_files(root)]
        return report
    try:
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        if not isinstance(manifest, dict) or not isinstance(manifest.get("files"), dict):
            raise ValueError("manifest or its 'files' member is not an object")
        listed = dict(manifest["files"])
        report["manifest_version"] = str(manifest.get("manifest_version"))
    except (OSError, ValueError, AttributeError):
        report["mismatched"] = [MANIFEST_NAME]
        return report
    for relative, expected in sorted(listed.items(), key=lambda item: str(item[0])):
        report["files_checked"] += 1
        # A manifest is attacker-writable in the unsigned case, so a listed
        # path is checked before it is opened: it must be a relative,
        # traversal-free runtime path and carry a hex SHA-256. Anything else
        # is a mismatch, never a file access outside *root*.
        if not _safe_manifest_entry(relative, expected):
            report["mismatched"].append(str(relative))
            continue
        path = root / relative
        if not path.is_file():
            report["missing"].append(relative)
            continue
        if sha256_file(path) != expected:
            report["mismatched"].append(relative)
            continue
        report["files_ok"] += 1
    present = {path.relative_to(root).as_posix() for path in runtime_files(root)}
    report["unlisted_runtime_files"] = sorted(present - set(listed))
    files_ok = not report["mismatched"] and not report["missing"] and not report["unlisted_runtime_files"]
    embedded = _embedded_public_key(root)
    if pinned_public_key is not None:
        # Origin proof demanded by the operator: the signature must exist and
        # verify under the pinned key.
        signature = verify_signature_file(manifest_file, pinned_public_key=pinned_public_key)
        signature_ok = bool(signature["valid"])
    elif embedded is not None and (manifest_file.with_name(manifest_file.name + ".sig")).is_file():
        # Not pinned: the signature must verify under the key the release
        # itself declares in release-manifest.json, never under whatever key
        # the signature document happens to carry. A re-keyed signature
        # therefore fails unless the attacker also rewrites the declared key
        # (which changes the published fingerprint).
        signature = verify_signature_file(manifest_file, pinned_public_key=embedded)
        signature["source"] = "release_manifest" if signature["valid"] else signature["source"]
        signature["pinned_fingerprint"] = None
        signature_ok = bool(signature["valid"])
    else:
        signature = verify_signature_file(manifest_file, pinned_public_key=None)
        # Unsigned tree (development checkout or CI build without the key):
        # files alone decide; the report says why no origin proof exists.
        signature["valid"] = False
        signature["source"] = "none"
        signature["reason"] = (
            "release declares a signing key but INTEGRITY.json.sig is absent (unsigned build)"
            if embedded
            else "release is unsigned"
        )
        signature_ok = True
    report["signature"] = signature
    report["passed"] = files_ok and signature_ok
    return report
