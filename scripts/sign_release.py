#!/usr/bin/env python3
"""Manage the QECTOR Ed25519 release-signing key and verify signed releases.

    # one-time: create the private key (keep it OFF the repository and OFF lab hosts)
    python scripts/sign_release.py --generate-key ~/.qector/release-signing.pem

    # record its public key + fingerprint in release-manifest.json (commit this)
    python scripts/sign_release.py --register-key ~/.qector/release-signing.pem

    # build signed archives
    python scripts/build_release.py --all --signing-key ~/.qector/release-signing.pem

    # reviewer / lab: verify SHA256SUMS.sig and every archive's INTEGRITY.json.sig
    python scripts/sign_release.py --verify dist --pubkey <base64 key from SECURITY.md>
    python scripts/sign_release.py --verify dist            # uses release-manifest.json (consistency only)

Verification is independent of git and of the server: it reads the files
in ``dist/`` (or any directory holding the archives) and the signature
documents next to them, and exits 1 on the first failure.
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "mcp"))

import qector_signing  # noqa: E402

RELEASE_MANIFEST = ROOT / "release-manifest.json"


def _generate(path: Path) -> int:
    if path.exists():
        print(f"refusing to overwrite existing key {path}")
        return 1
    key = qector_signing.generate_private_key(path)
    public = qector_signing.public_key_b64(key)
    print(f"private key written to {path} (mode 0600; never commit or copy to lab hosts)")
    print(f"public key (base64): {public}")
    print(f"fingerprint (sha256): {qector_signing.fingerprint(public)}")
    return 0


def _register(path: Path) -> int:
    key = qector_signing.load_private_key(path)
    public = qector_signing.public_key_b64(key)
    release = json.loads(RELEASE_MANIFEST.read_text(encoding="utf-8"))
    release["signing"] = {
        "algorithm": qector_signing.ALGORITHM,
        "public_key": public,
        "fingerprint": qector_signing.fingerprint(public),
        "signed_files": ["INTEGRITY.json (inside every archive)", "dist/SHA256SUMS"],
        "verify": "python scripts/sign_release.py --verify dist --pubkey <public_key>",
    }
    RELEASE_MANIFEST.write_text(json.dumps(release, indent=2) + "\n", encoding="utf-8")
    print(f"release-manifest.json now declares signing key fingerprint {release['signing']['fingerprint']}")
    return 0


def _verify_dir(directory: Path, pubkey: str | None) -> int:
    if pubkey is None:
        try:
            pubkey_embedded = json.loads(RELEASE_MANIFEST.read_text(encoding="utf-8"))["signing"]["public_key"]
        except (OSError, KeyError, ValueError):
            pubkey_embedded = None
        print("no --pubkey given: verifying against the key embedded in release-manifest.json (consistency, not origin)")
    else:
        pubkey_embedded = None
    failures = 0
    sums = directory / "SHA256SUMS"
    if sums.is_file():
        report = qector_signing.verify_signature_file(sums, pinned_public_key=pubkey or pubkey_embedded)
        print(f"{'OK  ' if report['valid'] else 'FAIL'} SHA256SUMS.sig ({report['source']}, fingerprint {report['fingerprint']}) {report['reason'] or ''}")
        failures += not report["valid"]
    else:
        print("WARN SHA256SUMS absent")
    for archive in sorted(list(directory.glob("*.zip")) + list(directory.glob("*.mcpb"))):
        with zipfile.ZipFile(archive) as zf, tempfile.TemporaryDirectory() as tmp:
            names = set(zf.namelist())
            if "INTEGRITY.json" not in names:
                print(f"FAIL {archive.name}: INTEGRITY.json missing")
                failures += 1
                continue
            zf.extract("INTEGRITY.json", tmp)
            if "INTEGRITY.json.sig" in names:
                zf.extract("INTEGRITY.json.sig", tmp)
            report = qector_signing.verify_signature_file(Path(tmp) / "INTEGRITY.json", pinned_public_key=pubkey or pubkey_embedded)
            print(f"{'OK  ' if report['valid'] else 'FAIL'} {archive.name}: INTEGRITY.json.sig ({report['source']}) {report['reason'] or ''}")
            failures += not report["valid"]
    print("signature verification:", "PASS" if not failures else f"{failures} failure(s)")
    return 0 if not failures else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--generate-key", type=Path, metavar="PEM")
    group.add_argument("--register-key", type=Path, metavar="PEM")
    group.add_argument("--verify", type=Path, metavar="DIR")
    parser.add_argument("--pubkey", default=None, help="Base64 Ed25519 public key obtained out-of-band (SECURITY.md).")
    args = parser.parse_args(argv)
    if args.generate_key:
        return _generate(args.generate_key.expanduser())
    if args.register_key:
        return _register(args.register_key.expanduser())
    return _verify_dir(args.verify.resolve(), args.pubkey)


if __name__ == "__main__":
    raise SystemExit(main())
