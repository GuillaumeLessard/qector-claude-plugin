"""Ed25519 release signing for QECTOR archives and manifests.

What is signed
--------------
* ``INTEGRITY.json`` inside every archive → ``INTEGRITY.json.sig`` (the
  signature covers the exact bytes of the manifest file).
* ``dist/SHA256SUMS`` → ``dist/SHA256SUMS.sig``.

Key handling
------------
The private key never enters the repository or an archive. The public key
(32 raw bytes, base64) and its SHA-256 fingerprint are recorded in
``release-manifest.json`` under ``signing`` and published in SECURITY.md
and in the collaboration proposal, so a reviewer can pin the key
out-of-band and verify that the archive they hold was produced by the
key holder. ``cryptography`` (already a hard dependency of the decoder
wheel) provides the primitive; no new dependency is introduced.

Verification policy in ``qector-secure``
----------------------------------------
* ``QECTOR_INTEGRITY_PUBKEY`` (or ``--integrity-pubkey``) pins a public key
  from an out-of-band source. When set, strict mode requires
  ``INTEGRITY.json.sig`` to verify under that key; a signature that merely
  matches the key embedded in the archive is not enough, because an
  attacker who rewrites the code can rewrite the embedded key too.
* Without a pinned key, a signature present in the archive is verified
  against the embedded public key and reported as
  ``signature.source = "release_manifest"`` — a consistency check, not a
  proof of origin. The result states which of the two happened.
"""

from __future__ import annotations

import base64
import hashlib
import json
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

SIGNATURE_SUFFIX = ".sig"
ALGORITHM = "ed25519"


class QECTORSignatureError(RuntimeError):
    """Raised when a signature is missing, malformed or does not verify."""


def generate_private_key(path: Path) -> Ed25519PrivateKey:
    key = Ed25519PrivateKey.generate()
    pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(pem)
    try:
        path.chmod(0o600)
    except OSError:  # pragma: no cover - platform dependent
        pass
    return key


def load_private_key(path: Path) -> Ed25519PrivateKey:
    key = serialization.load_pem_private_key(path.read_bytes(), password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise QECTORSignatureError(f"{path} is not an Ed25519 private key")
    return key


def public_key_b64(key: Ed25519PrivateKey | Ed25519PublicKey) -> str:
    public = key.public_key() if isinstance(key, Ed25519PrivateKey) else key
    raw = public.public_bytes(encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw)
    return base64.b64encode(raw).decode("ascii")


def fingerprint(public_b64: str) -> str:
    """SHA-256 of the raw 32-byte public key, hex; the value to pin out-of-band.

    Raises :class:`QECTORSignatureError` for anything that is not a
    base64-encoded 32-byte key, so a mistyped ``QECTOR_INTEGRITY_PUBKEY``
    is reported as a configuration error instead of a traceback.
    """
    if not isinstance(public_b64, str):
        raise QECTORSignatureError("public key must be a base64 string")
    try:
        raw = base64.b64decode(public_b64, validate=True)
    except Exception as exc:
        raise QECTORSignatureError("public key is not valid base64") from exc
    if len(raw) != 32:
        raise QECTORSignatureError("public key must be 32 raw Ed25519 bytes")
    return hashlib.sha256(raw).hexdigest()


def load_public_key(public_b64: str) -> Ed25519PublicKey:
    try:
        raw = base64.b64decode(public_b64, validate=True)
    except Exception as exc:
        raise QECTORSignatureError("public key is not valid base64") from exc
    if len(raw) != 32:
        raise QECTORSignatureError("public key must be 32 raw Ed25519 bytes")
    return Ed25519PublicKey.from_public_bytes(raw)


def sign_bytes(key: Ed25519PrivateKey, payload: bytes) -> str:
    return base64.b64encode(key.sign(payload)).decode("ascii")


def verify_bytes(public_b64: str, payload: bytes, signature_b64: str) -> bool:
    try:
        load_public_key(public_b64).verify(base64.b64decode(signature_b64, validate=True), payload)
    except (InvalidSignature, ValueError, QECTORSignatureError):
        return False
    return True


def signature_document(key: Ed25519PrivateKey, payload: bytes, *, subject: str) -> dict[str, Any]:
    """Detached signature as JSON so the public key and subject travel with it."""
    public = public_key_b64(key)
    return {
        "algorithm": ALGORITHM,
        "subject": subject,
        "subject_sha256": hashlib.sha256(payload).hexdigest(),
        "public_key": public,
        "fingerprint": fingerprint(public),
        "signature": sign_bytes(key, payload),
    }


def verify_signature_file(subject_path: Path, *, pinned_public_key: str | None = None) -> dict[str, Any]:
    """Verify ``<subject>.sig`` next to *subject_path*.

    Returns a report; never raises for a missing or bad signature so the
    caller can decide whether that is fatal (strict mode with a pinned key)
    or merely reportable.
    """
    sig_path = subject_path.with_name(subject_path.name + SIGNATURE_SUFFIX)
    report: dict[str, Any] = {
        "present": sig_path.is_file(),
        "valid": False,
        "source": "none",
        "fingerprint": None,
        "pinned_fingerprint": None,
        "reason": None,
    }
    if pinned_public_key:
        try:
            report["pinned_fingerprint"] = fingerprint(pinned_public_key)
        except QECTORSignatureError as exc:
            report["reason"] = f"verification key rejected: {exc}"
            return report
    if not sig_path.is_file():
        report["reason"] = f"{sig_path.name} absent"
        return report
    try:
        document = json.loads(sig_path.read_text(encoding="utf-8"))
        public = str(document["public_key"])
        signature = str(document["signature"])
    except (OSError, ValueError, KeyError, TypeError) as exc:
        report["reason"] = f"malformed signature file: {exc.__class__.__name__}"
        return report
    try:
        payload = subject_path.read_bytes()
    except OSError as exc:
        report["reason"] = f"subject unreadable: {exc.__class__.__name__}"
        return report
    report["fingerprint"] = fingerprint(public) if _b64_ok(public) else None
    if pinned_public_key:
        if not _b64_ok(public) or fingerprint(public) != fingerprint(pinned_public_key):
            report["reason"] = "signature public key does not match the pinned/declared key"
            return report
        report["valid"] = verify_bytes(pinned_public_key, payload, signature)
        report["source"] = "pinned"
    else:
        report["valid"] = verify_bytes(public, payload, signature)
        report["source"] = "release_manifest"
    if not report["valid"]:
        report["reason"] = "signature does not verify over the current file bytes"
    return report


def _b64_ok(value: str) -> bool:
    try:
        return len(base64.b64decode(value, validate=True)) == 32
    except Exception:
        return False
