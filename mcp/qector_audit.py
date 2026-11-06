"""Hash-chained, append-only JSONL audit log for QECTOR MCP tool calls.

Each record binds the previous record's SHA-256, the tool name, a SHA-256
of the canonical arguments (never the arguments themselves, so syndromes
and matrices never leave the result channel), the envelope status / error
code, the result envelope's SHA-256 and the elapsed time. Tampering with,
removing or reordering any line breaks the chain, which ``verify_chain``
reports with the first invalid sequence number.

The log lives only where ``QECTOR_AUDIT_DIR`` points. When the variable is
unset, auditing is disabled and the server reports ``enabled: false``;
nothing is written anywhere by default.

Threat boundary, stated plainly: a keyless hash chain detects edits,
deletions and reordering **inside** the chain, and the running server also
detects truncation of the tail (it compares the file against the head it
wrote). It cannot, by itself, prove that a same-user attacker did not
rewrite the whole file and recompute every digest after the server
stopped. Two mitigations are available:

* ``QECTOR_AUDIT_HMAC_KEY_FILE`` — a file holding at least 32 bytes of
  secret. Record digests become HMAC-SHA256 under that key, so a rewrite
  requires the key (keep it off the audited host or in a hardware store).
* Anchoring — ship ``head_sha256`` from ``audit_log_status`` to a WORM
  store or notebook at the end of each session; any later rewrite changes
  the head.

Argument digests are SHA-256 of canonical JSON. Low-entropy arguments
(``{"distance": 3}``) are therefore dictionary-reversible; the digest
exists to bind the record to the call, not to hide the call's content.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import threading
import time
from pathlib import Path
from typing import Any, Mapping

from qector_mcp_contract import canonical_json

GENESIS = "0" * 64
RECORD_SCHEMA: dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://qector.store/schemas/mcp/2.0.0/audit-record.schema.json",
    "title": "QECTORAuditRecord",
    "type": "object",
    "required": [
        "sequence",
        "timestamp_ns",
        "server",
        "server_version",
        "tool",
        "arguments_sha256",
        "status",
        "error_code",
        "envelope_sha256",
        "elapsed_ms",
        "previous_sha256",
        "record_sha256",
    ],
    "properties": {
        "sequence": {"type": "integer", "minimum": 1},
        "timestamp_ns": {"type": "integer", "minimum": 0},
        "server": {"type": "string"},
        "server_version": {"type": "string"},
        "tool": {"type": "string"},
        "arguments_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
        "status": {"type": "string"},
        "error_code": {"type": ["string", "null"]},
        "envelope_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
        "elapsed_ms": {"type": "number", "minimum": 0},
        "previous_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
        "record_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
    },
    "additionalProperties": False,
}


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class QECTORAuditError(RuntimeError):
    """Raised when an existing audit log fails chain verification or the key is unusable."""


def _record_digest(record: Mapping[str, Any], key: bytes | None = None) -> str:
    body = {key_: value for key_, value in record.items() if key_ != "record_sha256"}
    payload = canonical_json(body).encode("utf-8")
    if key:
        return hmac.new(key, payload, hashlib.sha256).hexdigest()
    return hashlib.sha256(payload).hexdigest()


def load_hmac_key() -> bytes | None:
    """Return the optional HMAC key from ``QECTOR_AUDIT_HMAC_KEY_FILE``."""
    configured = os.environ.get("QECTOR_AUDIT_HMAC_KEY_FILE", "").strip()
    if not configured or configured.startswith("${"):
        return None
    path = Path(configured).expanduser()
    try:
        key = path.read_bytes().strip()
    except OSError as exc:
        raise QECTORAuditError(f"cannot read QECTOR_AUDIT_HMAC_KEY_FILE {path}: {exc}") from exc
    if len(key) < 32:
        raise QECTORAuditError("QECTOR_AUDIT_HMAC_KEY_FILE must hold at least 32 bytes of key material")
    return key


class AuditLog:
    """Append-only chained log. Thread-safe; one instance per server process."""

    def __init__(self, path: Path | None, *, server: str, server_version: str, key: bytes | None = None) -> None:
        self.path = path
        self.server = server
        self.server_version = server_version
        self._key = key
        self._lock = threading.Lock()
        self._sequence = 0
        self._head = GENESIS
        if path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
            if path.exists():
                valid, sequence, head, _first_bad = verify_chain(path, key=key)
                if not valid:
                    raise QECTORAuditError(
                        f"audit log {path} fails chain verification; refusing to append to a corrupt log"
                    )
                self._sequence, self._head = sequence, head
            else:
                path.touch()
                try:
                    os.chmod(path, 0o600)
                except OSError:  # pragma: no cover - platform dependent
                    pass

    @property
    def enabled(self) -> bool:
        return self.path is not None

    def append(
        self,
        *,
        tool: str,
        arguments: Mapping[str, Any] | None,
        envelope: Mapping[str, Any],
        elapsed_ms: float,
    ) -> dict[str, Any] | None:
        if self.path is None:
            return None
        with self._lock:
            self._sequence += 1
            record: dict[str, Any] = {
                "sequence": self._sequence,
                "timestamp_ns": time.time_ns(),
                "server": self.server,
                "server_version": self.server_version,
                "tool": tool,
                "arguments_sha256": sha256_text(canonical_json(dict(arguments or {}))),
                "status": str(envelope.get("status")),
                "error_code": (envelope.get("error") or {}).get("code") if isinstance(envelope.get("error"), dict) else None,
                "envelope_sha256": sha256_text(canonical_json(dict(envelope))),
                "elapsed_ms": round(float(elapsed_ms), 3),
                "previous_sha256": self._head,
            }
            record["record_sha256"] = _record_digest(record, self._key)
            with self.path.open("a", encoding="utf-8", newline="\n") as handle:
                handle.write(canonical_json(record) + "\n")
                handle.flush()
                os.fsync(handle.fileno())
            self._head = record["record_sha256"]
            return {"sequence": record["sequence"], "record_sha256": record["record_sha256"]}

    def status(self) -> dict[str, Any]:
        if self.path is None:
            return {
                "enabled": False,
                "path": None,
                "records": 0,
                "head_sha256": None,
                "chain_valid": None,
                "first_invalid_sequence": None,
                "keyed": False,
                "matches_server_head": None,
                "record_schema": RECORD_SCHEMA,
            }
        valid, sequence, head, first_bad = verify_chain(self.path, key=self._key)
        with self._lock:
            expected_sequence, expected_head = self._sequence, self._head
        # The running server knows how many records it wrote and the head it
        # produced; a truncated or rewritten file disagrees with that memory
        # even when the surviving prefix still chains correctly.
        matches = valid and sequence == expected_sequence and head == expected_head
        return {
            "enabled": True,
            "path": str(self.path),
            "records": sequence,
            "head_sha256": head if sequence else None,
            "chain_valid": valid and matches,
            "first_invalid_sequence": first_bad if not valid else (sequence + 1 if not matches else None),
            "keyed": self._key is not None,
            "matches_server_head": matches,
            "record_schema": RECORD_SCHEMA,
        }


def verify_chain(path: Path, key: bytes | None = None) -> tuple[bool, int, str, int | None]:
    """Return (valid, record_count, head_sha256, first_invalid_sequence).

    Verifies internal consistency only; see the module docstring for what
    a keyless chain cannot prove (tail truncation after the server exits,
    whole-file rewrite by the same user).
    """
    head = GENESIS
    count = 0
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                return False, count, head, line_number
            if not isinstance(record, dict):
                return False, count, head, line_number
            expected_sequence = count + 1
            if record.get("sequence") != expected_sequence:
                return False, count, head, expected_sequence
            if record.get("previous_sha256") != head:
                return False, count, head, expected_sequence
            if record.get("record_sha256") != _record_digest(record, key):
                return False, count, head, expected_sequence
            head = str(record["record_sha256"])
            count += 1
    return True, count, head, None


def audit_log_from_env(*, server: str, server_version: str) -> AuditLog:
    configured = os.environ.get("QECTOR_AUDIT_DIR", "").strip()
    if not configured or configured.startswith("${"):
        # Empty, or an unexpanded Desktop placeholder such as
        # "${user_config.audit_dir}" for an unset optional setting: auditing off.
        return AuditLog(None, server=server, server_version=server_version)
    root = Path(configured).expanduser().resolve()
    return AuditLog(root / f"{server}.audit.jsonl", server=server, server_version=server_version, key=load_hmac_key())
