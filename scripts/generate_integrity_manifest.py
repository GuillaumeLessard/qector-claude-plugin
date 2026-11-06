#!/usr/bin/env python3
"""Write (or verify) ``INTEGRITY.json``: SHA-256 of every runtime file.

Usage:
    python scripts/generate_integrity_manifest.py            # write
    python scripts/generate_integrity_manifest.py --check    # verify, exit 1 on drift

The manifest covers the files the MCP servers execute or read at runtime
(see ``mcp/qector_integrity.py``). ``scripts/build_release.py`` regenerates
it before packaging so every archive carries a manifest that matches its
own contents, and ``mcp_server_secure.py`` verifies it at startup.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "mcp"))

import qector_integrity  # noqa: E402
import qector_signing  # noqa: E402


def _release_version() -> str:
    return json.loads((ROOT / "release-manifest.json").read_text(encoding="utf-8"))["release"]["version"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify instead of writing.")
    parser.add_argument("--root", type=Path, default=ROOT, help="Tree to hash (default: repository root).")
    parser.add_argument("--signing-key", type=Path, default=None, help="Also write INTEGRITY.json.sig with this Ed25519 private key.")
    parser.add_argument("--pubkey", default=None, help="With --check: require a valid signature under this pinned public key.")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    target = root / qector_integrity.MANIFEST_NAME
    if args.check:
        report = qector_integrity.verify(root, strict=True, manifest_path=target, pinned_public_key=args.pubkey)
        print(json.dumps({k: v for k, v in report.items() if k != "runtime_distributions"}, indent=2, sort_keys=True))
        return 0 if report["passed"] else 1
    manifest = qector_integrity.build_manifest(root, version=_release_version())
    payload = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")
    target.write_bytes(payload)
    print(f"wrote {target.relative_to(root)} with {len(manifest['files'])} files")
    sig_path = root / (qector_integrity.MANIFEST_NAME + qector_signing.SIGNATURE_SUFFIX)
    if args.signing_key is not None:
        key = qector_signing.load_private_key(args.signing_key.expanduser().resolve())
        document = qector_signing.signature_document(key, payload, subject=qector_integrity.MANIFEST_NAME)
        sig_path.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"wrote {sig_path.relative_to(root)} (fingerprint {document['fingerprint']})")
    elif sig_path.exists():
        sig_path.unlink()
        print(f"removed stale {sig_path.relative_to(root)} (manifest changed without --signing-key)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
