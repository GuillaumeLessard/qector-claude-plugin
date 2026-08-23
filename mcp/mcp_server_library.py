"""
QECTOR Decoder v3 library MCP server.

This server is intentionally library-only: it runs against the published
``qector-decoder-v3==1.0.0`` wheel and does not require QECTOR Workbench.
The server exposes eight local tools and keeps the mathematical contract from
the reference manual explicit:

* every returned correction passes ``H c = s (mod 2)`` (Theorem 1);
* logical outcomes are scored with the logical-observable matrix (Theorem 2);
* every LER sweep includes a 95% Wilson interval and a hashed raw artifact.

The only exposed transport is local stdio. Network transports are intentionally
not part of this public package.
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import sys
import tempfile
import time
import urllib.error
import urllib.request
from numbers import Integral, Real
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

_MCP_DIR = Path(__file__).resolve().parent
if str(_MCP_DIR) not in sys.path:
    sys.path.insert(0, str(_MCP_DIR))

from qector_mcp_contract import (  # noqa: E402
    apply_tool_contract,
    call_tool_result,
    consume_call_budget,
    error_envelope,
    result_envelope,
)

# qector prints a startup banner unless this flag is set. Any stdout
# before an MCP frame corrupts the stdio protocol, so the server owns this flag.
os.environ["QECTOR_SILENT"] = "1"

try:
    import numpy as np  # noqa: E402
except Exception as exc:  # pragma: no cover - exercised by deployment smoke tests
    raise RuntimeError("numpy is required by the QECTOR library MCP server") from exc

try:
    import qector_decoder_v3  # noqa: E402
    from qector_decoder_v3 import (  # noqa: E402
        BlossomDecoder,
        FastUnionFindDecoder,
        NativeAutoDecoder,
        SparseBlossomDecoder,
        UnionFindDecoder,
        codes,
        generate_repetition_code_checks,
        generate_ring_code_checks,
        generate_surface_code_checks,
    )
except Exception as exc:  # pragma: no cover - exercised by deployment smoke tests
    raise RuntimeError(
        "qector-decoder-v3 is required and could not be imported; "
        "install requirements.txt first"
    ) from exc


REF_DOI = "10.5281/zenodo.21941046"
# Reviewed API window for this server: the floor is the version this file's
# behavior was validated against; the ceiling is the first minor version NOT
# yet reviewed (a minor bump may add or change surface area; per this
# project's own semantic-versioning convention a patch bump like 1.0.0 ->
# 1.0.3 does not). A version outside this window degrades to a loud startup
# warning (see _check_qector_version_window below) rather than the previous
# hard RuntimeError, which made every patch release of qector-decoder-v3 a
# breaking change for this connector even when nothing in the 8-tool surface
# this server calls had changed.
MIN_REVIEWED_QECTOR_VERSION = "1.0.0"
MAX_REVIEWED_QECTOR_VERSION_EXCLUSIVE = "1.1.0"
SERVER_NAME = "qector-decoder-v3-mcp"
SERVER_VERSION = "1.0.5"
Z95 = 1.959963985

# These are safety limits for an MCP process. The license tier remains the
# authority for QECTOR distance limits; these bounds only prevent accidental
# unbounded requests from blocking a local agent session.
MAX_DISTANCE = int(os.environ.get("QECTOR_MCP_MAX_DISTANCE", "63"))
MAX_CHECKS = int(os.environ.get("QECTOR_MCP_MAX_CHECKS", "10000"))
MAX_QUBITS = int(os.environ.get("QECTOR_MCP_MAX_QUBITS", "100000"))
MAX_MATRIX_CELLS = int(os.environ.get("QECTOR_MCP_MAX_MATRIX_CELLS", "1000000"))
MAX_TRIALS = int(os.environ.get("QECTOR_MCP_MAX_TRIALS", "10000"))
MAX_SWEEP_POINTS = int(os.environ.get("QECTOR_MCP_MAX_SWEEP_POINTS", "64"))
PYPI_FRESHNESS_TIMEOUT_S = float(os.environ.get("QECTOR_MCP_PYPI_TIMEOUT_S", "3.0"))

if (
    min(
        MAX_DISTANCE,
        MAX_CHECKS,
        MAX_QUBITS,
        MAX_MATRIX_CELLS,
        MAX_TRIALS,
        MAX_SWEEP_POINTS,
    )
    <= 0
):
    raise RuntimeError("QECTOR MCP resource limits must be positive integers")


def _installed_version(distribution: str) -> str:
    try:
        return importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


def _parse_version_tuple(version: str) -> tuple[int, ...] | None:
    """Parse a dotted numeric version prefix ('1.0.3', '1.0.3rc1' -> (1,0,3)).

    Returns None for anything that doesn't start with at least one dotted
    integer component (e.g. 'unknown'), so callers can treat an unparsable
    version as "can't verify" rather than crashing on it.
    """
    parts: list[int] = []
    for chunk in version.split("."):
        digits = ""
        for ch in chunk:
            if ch.isdigit():
                digits += ch
            else:
                break
        if not digits:
            break
        parts.append(int(digits))
    return tuple(parts) if parts else None


def _check_qector_version_window(
    installed: str, floor: str, ceiling_exclusive: str
) -> tuple[bool, str]:
    """Check *installed* against [floor, ceiling_exclusive).

    Returns (in_window, detail). ``in_window`` is True both when the version
    is inside the reviewed range and when any of the three versions fails to
    parse (an unparsable version is a "cannot verify", not a "cannot use" --
    the previous behavior of hard-crashing on any mismatch, parsable or not,
    is exactly the defect this replaces). ``detail`` is a human-readable
    string suitable for a startup warning or a compat_report field.
    """
    installed_t = _parse_version_tuple(installed)
    floor_t = _parse_version_tuple(floor)
    ceiling_t = _parse_version_tuple(ceiling_exclusive)
    if installed_t is None or floor_t is None or ceiling_t is None:
        return True, f"could not parse version(s) for comparison: installed={installed!r}"
    if floor_t <= installed_t < ceiling_t:
        return True, f"{installed} is within the reviewed [{floor}, {ceiling_exclusive}) window"
    return False, (
        f"{installed} is outside the reviewed [{floor}, {ceiling_exclusive}) window "
        f"for this MCP server (server v{SERVER_VERSION})"
    )


QECTOR_VERSION = getattr(qector_decoder_v3, "__version__", "unknown")
_QECTOR_VERSION_IN_WINDOW, _QECTOR_VERSION_DETAIL = _check_qector_version_window(
    QECTOR_VERSION, MIN_REVIEWED_QECTOR_VERSION, MAX_REVIEWED_QECTOR_VERSION_EXCLUSIVE
)
if not _QECTOR_VERSION_IN_WINDOW:
    # Degrade to a stderr warning rather than the previous hard RuntimeError.
    # The 8 tools this server exposes are a stable, narrow surface (decode,
    # list families/decoders, license info, threshold sweep, build-from-
    # matrix, compat report); a qector-decoder-v3 patch release the server
    # hasn't explicitly re-reviewed yet is far more likely to be unaffected
    # on this surface than to silently corrupt a decode -- and every tool
    # result is still fail-closed verified against H c = s (mod 2) (Theorem
    # 1) regardless of which reviewed wheel produced it, so a version outside
    # the window cannot itself produce an unverified result. Set
    # QECTOR_MCP_STRICT_VERSION=1 to restore the previous hard-fail behavior
    # for deployments that want it.
    if os.environ.get("QECTOR_MCP_STRICT_VERSION", "").strip() in {"1", "true", "yes", "on"}:
        raise RuntimeError(f"Unsupported qector-decoder-v3 version: {_QECTOR_VERSION_DETAIL}")
    # Deliberately NOT gated on QECTOR_SILENT: that flag suppresses the
    # qector_decoder_v3 licensing banner (set unconditionally by the Claude
    # Desktop manifest env for every launch), which would make a genuine
    # compatibility warning invisible in exactly the deployment where seeing
    # it matters most. QECTOR_MCP_QUIET is this server's own, narrower flag
    # for operators who have explicitly reviewed and accepted the version
    # skew and want the one-line notice gone.
    if os.environ.get("QECTOR_MCP_QUIET", "").strip() not in {"1", "true", "yes", "on"}:
        try:
            import sys as _sys_for_warning

            _sys_for_warning.stderr.write(
                f"[qector-decoder-v3-mcp] warning: {_QECTOR_VERSION_DETAIL}. "
                "Tool results remain fail-closed verified; set "
                "QECTOR_MCP_STRICT_VERSION=1 to refuse to start instead, or "
                "QECTOR_MCP_QUIET=1 to silence this notice.\n"
            )
            _sys_for_warning.stderr.flush()
        except (OSError, ValueError, UnicodeEncodeError):
            pass


class QECTORInputError(ValueError):
    """Raised for malformed or resource-exceeding tool input."""


class QECTORFaithfulnessError(RuntimeError):
    """Raised when a backend violates the universal syndrome contract."""


class QECTORArtifactError(RuntimeError):
    """Raised when an evidence artifact cannot be written safely."""


FAMILY_REGISTRY: dict[str, dict[str, Any]] = {
    "repetition": {
        "generator": "generate_repetition_code_checks",
        "code_factory": "repetition_code",
        "kind": "size_code",
        "description": "Open repetition code; size is the distance/qubit count.",
    },
    "ring": {
        "generator": "generate_ring_code_checks",
        "code_factory": "ring_code",
        "kind": "size_code",
        "description": "Periodic ring code; size is the ring length.",
    },
    "surface_legacy": {
        "generator": "generate_surface_code_checks",
        "code_factory": None,
        "kind": "checks_only",
        "description": "Legacy toric-style weight-4 check generator; not graphlike.",
    },
    "rotated_surface": {
        "generator": "rotated_surface_code",
        "code_factory": "rotated_surface_code",
        "kind": "size_code",
        "description": "Graphlike rotated surface code.",
    },
    "unrotated_surface": {
        "generator": "unrotated_surface_code",
        "code_factory": "unrotated_surface_code",
        "kind": "size_code",
        "description": "Graphlike unrotated surface code.",
    },
    "toric": {
        "generator": "toric_code",
        "code_factory": "toric_code",
        "kind": "size_code",
        "description": "Graphlike toric code.",
    },
    "heavy_hex": {
        "generator": "heavy_hex_code",
        "code_factory": "heavy_hex_code",
        "kind": "size_code",
        "description": "Graphlike heavy-hex code.",
    },
    "color_code": {
        "generator": "color_code",
        "code_factory": "color_code",
        "kind": "size_code",
        "description": "Color-code family exposed by the wheel.",
    },
    "hypergraph_product": {
        "generator": "hypergraph_product",
        "code_factory": "hypergraph_product",
        "kind": "matrix_pair",
        "description": "Hypergraph-product constructor; requires two matrices.",
    },
}

DECODERS: dict[str, type] = {
    "union_find": UnionFindDecoder,
    "fast_union_find": FastUnionFindDecoder,
    "blossom": BlossomDecoder,
    "sparse_blossom": SparseBlossomDecoder,
    "native_auto": NativeAutoDecoder,
}

TOOL_NAMES = (
    "list_code_families",
    "list_decoders",
    "get_license_info",
    "decode_syndrome",
    "decode_single",
    "threshold_sweep",
    "build_code_from_matrix",
    "compat_report",
)


def _require_integral(
    value: Any, name: str, *, minimum: int = 0, maximum: int | None = None
) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise QECTORInputError(f"{name} must be an integer")
    result = int(value)
    if result < minimum:
        raise QECTORInputError(f"{name} must be >= {minimum}")
    if maximum is not None and result > maximum:
        raise QECTORInputError(f"{name} must be <= {maximum}")
    return result


def _require_probability(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise QECTORInputError(f"{name} must be a finite number in [0, 1]")
    result = float(value)
    if not math.isfinite(result) or not 0.0 <= result <= 1.0:
        raise QECTORInputError(f"{name} must be a finite number in [0, 1]")
    return result


def _binary_vector(
    value: Any, name: str, *, expected_length: int | None = None
) -> np.ndarray:
    try:
        array = np.asarray(value)
    except Exception as exc:
        raise QECTORInputError(
            f"{name} must be a one-dimensional binary array"
        ) from exc
    if array.ndim != 1:
        raise QECTORInputError(f"{name} must be one-dimensional")
    if array.size > MAX_QUBITS:
        raise QECTORInputError(f"{name} exceeds the {MAX_QUBITS}-element limit")
    if expected_length is not None and array.size != expected_length:
        raise QECTORInputError(
            f"{name} must contain {expected_length} elements; received {array.size}"
        )
    if array.dtype.kind in "fc" and not np.isfinite(array).all():
        raise QECTORInputError(f"{name} must contain only finite values")
    if not np.all((array == 0) | (array == 1)):
        raise QECTORInputError(f"{name} must contain only 0 and 1")
    return array.astype(np.uint8, copy=False)


def _validated_checks(
    c2q: Any, n_qubits: int | None = None
) -> tuple[list[list[int]], int]:
    if not isinstance(c2q, Sequence) or isinstance(c2q, (str, bytes)):
        raise QECTORInputError("check_to_qubits must be a sequence of sequences")
    if len(c2q) == 0:
        raise QECTORInputError("check_to_qubits must contain at least one check")
    if len(c2q) > MAX_CHECKS:
        raise QECTORInputError(f"check_to_qubits exceeds the {MAX_CHECKS}-check limit")

    normalized: list[list[int]] = []
    largest_qubit = -1
    for check_index, qubits in enumerate(c2q):
        if not isinstance(qubits, Sequence) or isinstance(qubits, (str, bytes)):
            raise QECTORInputError(f"check {check_index} must be a sequence")
        row: list[int] = []
        for qubit in qubits:
            q = _require_integral(qubit, f"check {check_index} qubit", minimum=0)
            if q in row:
                raise QECTORInputError(
                    f"check {check_index} contains duplicate qubit {q}"
                )
            row.append(q)
            largest_qubit = max(largest_qubit, q)
        normalized.append(row)

    inferred = largest_qubit + 1
    if inferred <= 0:
        raise QECTORInputError("checks must reference at least one qubit")
    if n_qubits is None:
        resolved = inferred
    else:
        resolved = _require_integral(
            n_qubits, "n_qubits", minimum=inferred, maximum=MAX_QUBITS
        )
    if resolved > MAX_QUBITS:
        raise QECTORInputError(f"n_qubits exceeds the {MAX_QUBITS}-qubit limit")
    if len(normalized) * resolved > MAX_MATRIX_CELLS:
        raise QECTORInputError(
            f"parity-check matrix exceeds the {MAX_MATRIX_CELLS}-cell limit"
        )
    return normalized, resolved


def matrix_from_checks(c2q: Any, n_qubits: int | None = None) -> np.ndarray:
    """Construct H with shape (n_checks, n_qubits), as defined by the manual."""
    checks, resolved_n_qubits = _validated_checks(c2q, n_qubits)
    matrix = np.zeros((len(checks), resolved_n_qubits), dtype=np.uint8)
    for check_index, qubits in enumerate(checks):
        matrix[check_index, qubits] = 1
    return matrix


def _gf2_rank(matrix: np.ndarray) -> int:
    work = np.asarray(matrix, dtype=np.uint8).copy() % 2
    rows, columns = work.shape
    rank = 0
    for column in range(columns):
        pivot = next((row for row in range(rank, rows) if work[row, column]), None)
        if pivot is None:
            continue
        if pivot != rank:
            work[[rank, pivot]] = work[[pivot, rank]]
        for row in range(rows):
            if row != rank and work[row, column]:
                work[row] ^= work[rank]
        rank += 1
        if rank == rows:
            break
    return rank


def _unpack_generated_checks(
    raw: Any, family: str
) -> tuple[list[list[int]], int | None]:
    """Accept both the documented list form and the v1.0 tuple form."""
    inferred: int | None = None
    checks = raw
    if (
        isinstance(raw, tuple)
        and len(raw) == 2
        and (raw[1] is None or isinstance(raw[1], Integral))
    ):
        checks, inferred = raw
        if inferred is not None:
            inferred = _require_integral(
                inferred, f"{family} inferred n_qubits", minimum=1
            )
    normalized, resolved = _validated_checks(checks, inferred)
    return normalized, resolved


def _checks_for_family(family: str, size: int) -> tuple[list[list[int]], int]:
    spec = FAMILY_REGISTRY.get(family)
    if spec is None:
        raise QECTORInputError(
            f"Unknown family {family!r}; choose one of {sorted(FAMILY_REGISTRY)}"
        )
    size = _require_integral(size, "size", minimum=1, maximum=MAX_DISTANCE)
    if spec["kind"] != "checks_only" and spec["kind"] != "size_code":
        raise QECTORInputError(
            f"family {family!r} requires matrices; use build_code_from_matrix"
        )
    if spec["kind"] == "size_code":
        code = _code_for_family(family, size)
        return _validated_checks(code.check_to_qubits, code.n_qubits)
    generator = {
        "generate_repetition_code_checks": generate_repetition_code_checks,
        "generate_ring_code_checks": generate_ring_code_checks,
        "generate_surface_code_checks": generate_surface_code_checks,
    }.get(spec["generator"])
    if generator is None:
        raise QECTORInputError(f"Generator for {family!r} is not available")
    checks, inferred = _unpack_generated_checks(generator(size), family)
    return checks, inferred


def _code_for_family(family: str, size: int) -> Any:
    spec = FAMILY_REGISTRY.get(family)
    if spec is None:
        raise QECTORInputError(
            f"Unknown family {family!r}; choose one of {sorted(FAMILY_REGISTRY)}"
        )
    size = _require_integral(size, "distance", minimum=1, maximum=MAX_DISTANCE)
    factory_name = spec.get("code_factory")
    if spec["kind"] == "checks_only":
        raise QECTORInputError(
            f"family {family!r} is an explicit-check generator; use decode_syndrome"
        )
    if spec["kind"] == "matrix_pair":
        raise QECTORInputError(
            f"family {family!r} requires two parity-check matrices; use build_code_from_matrix"
        )
    factory = getattr(codes, factory_name, None)
    if not callable(factory):
        raise QECTORInputError(
            f"Code factory {factory_name!r} is unavailable in qector 1.0.0"
        )
    code = factory(size)
    if isinstance(code, tuple):
        raise QECTORInputError(
            f"Code factory {factory_name!r} returned multiple sectors; explicit matrices are required"
        )
    return code


def _code_matrix(code: Any) -> np.ndarray:
    matrix = code.parity_check_matrix()
    if matrix is None:
        matrix = matrix_from_checks(code.check_to_qubits, code.n_qubits)
    matrix = np.asarray(matrix, dtype=np.uint8)
    if matrix.ndim != 2 or matrix.shape != (code.n_checks, code.n_qubits):
        raise QECTORInputError(
            "Code parity_check_matrix() did not return an (n_checks, n_qubits) matrix"
        )
    if not np.all((matrix == 0) | (matrix == 1)):
        raise QECTORInputError("Code parity_check_matrix() returned non-binary values")
    return matrix


def _is_graphlike_checks(checks: Sequence[Sequence[int]]) -> bool:
    degrees: dict[int, int] = {}
    for check in checks:
        for qubit in check:
            degrees[qubit] = degrees.get(qubit, 0) + 1
    return max(degrees.values(), default=0) <= 2


def _logical_matrix(code: Any) -> np.ndarray | None:
    logicals = code.logicals_matrix()
    if logicals is None:
        return None
    logicals = np.asarray(logicals, dtype=np.uint8)
    if logicals.ndim != 2 or logicals.shape[1] != code.n_qubits:
        raise QECTORInputError("Code logicals_matrix() has an invalid shape")
    if not np.all((logicals == 0) | (logicals == 1)):
        raise QECTORInputError("Code logicals_matrix() returned non-binary values")
    return logicals


def _verify_faithfulness(
    matrix: np.ndarray, correction: Any, syndrome: np.ndarray
) -> np.ndarray:
    normalized = _binary_vector(
        correction,
        "correction",
        expected_length=matrix.shape[1],
    )
    calculated = (matrix.astype(np.int64) @ normalized.astype(np.int64)) % 2
    if not np.array_equal(calculated.astype(np.uint8), syndrome):
        raise QECTORFaithfulnessError(
            "decoder returned a correction that fails H c = s (mod 2)"
        )
    return normalized


def _env_block() -> dict[str, Any]:
    memory_bytes: int | None = None
    try:
        import psutil

        memory_bytes = int(psutil.virtual_memory().total)
    except Exception:
        pass
    return {
        "os": platform.system(),
        "platform": platform.platform(),
        "cpu": platform.processor() or "unknown",
        "ram_bytes": memory_bytes,
        "python": platform.python_version(),
        "numpy": np.__version__,
        "qector_decoder_v3": QECTOR_VERSION,
        "mcp_sdk": _installed_version("mcp"),
        "git_commit": os.environ.get("QECTOR_GIT_COMMIT", "not available"),
    }


def wilson_ci(k: int, n: int, z: float = Z95) -> tuple[float, float]:
    """Return the 95% Wilson score interval from manual chapter 15.2."""
    k = _require_integral(k, "logical_errors", minimum=0)
    n = _require_integral(n, "trials", minimum=1, maximum=MAX_TRIALS)
    if k > n:
        raise QECTORInputError("logical_errors cannot exceed trials")
    p = k / n
    denominator = 1.0 + z * z / n
    center = (p + z * z / (2.0 * n)) / denominator
    margin = z * math.sqrt(p * (1.0 - p) / n + z * z / (4.0 * n * n)) / denominator
    return max(0.0, center - margin), min(1.0, center + margin)


def list_code_families() -> dict[str, Any]:
    families: dict[str, Any] = {}
    for name, spec in sorted(FAMILY_REGISTRY.items()):
        if spec["kind"] == "checks_only":
            available = callable(
                {
                    "generate_repetition_code_checks": generate_repetition_code_checks,
                    "generate_ring_code_checks": generate_ring_code_checks,
                    "generate_surface_code_checks": generate_surface_code_checks,
                }.get(spec["generator"])
            )
        else:
            available = callable(getattr(codes, spec["code_factory"], None))
        families[name] = {
            "generator": spec["generator"],
            "code_factory": spec["code_factory"],
            "available": available,
            "description": spec["description"],
            "single_decode": spec["kind"] == "size_code",
        }
    return {
        "families": families,
        "reference_manual": REF_DOI,
        "qector_version": QECTOR_VERSION,
    }


def list_decoders() -> dict[str, Any]:
    return {
        "decoders": {
            name: {"class": decoder.__name__, "status": "stable"}
            for name, decoder in DECODERS.items()
        },
        "reference_manual": REF_DOI,
    }


def get_license_info() -> dict[str, Any]:
    info = qector_decoder_v3.get_license_info()
    # The wheel returns the license as a small dict of private fields; this
    # MCP tool normalizes that into the documented public schema so agents
    # do not have to guess at field names. Every field below has a fixed
    # type; missing keys become ``None`` rather than being silently dropped.
    key_status = str(info.get("key_status", "unknown"))
    is_expired = bool(info.get("is_expired", False))
    if is_expired:
        commercial_status = "expired"
    elif key_status in {"no_key", "community"}:
        commercial_status = "community"
    elif key_status in {"evaluation", "trial"}:
        commercial_status = "evaluation"
    elif key_status in {"paid", "active", "valid"}:
        commercial_status = "commercial"
    else:
        commercial_status = "unknown"
    return {
        "license": {
            "tier": str(info.get("tier", "unknown")),
            "distance_limit": int(info["max_distance"]) if "max_distance" in info else None,
            "gpu_allowed": bool(info.get("gpu_enabled", False)),
            "gnn_allowed": bool(info.get("gnn_enabled", False)),
            "commercial_status": commercial_status,
            "enforcement_mode": (
                "enforced" if bool(info.get("enforce_mode", False)) else "permissive"
            ),
            "license_evidence": {
                "key_status": key_status,
                "is_expired": is_expired,
                "subject": info.get("sub"),
                "customer_id": info.get("customer_id"),
                "issued_at": info.get("iat"),
                "expires_at": info.get("exp"),
            },
            "raw": dict(info),
        },
        "qector_version": QECTOR_VERSION,
        "reference_manual": REF_DOI,
    }


def decode_syndrome(
    family: str = "repetition",
    size: int = 5,
    syndrome: Sequence[int] | None = None,
    decoder_name: str = "blossom",
    n_qubits: int | None = None,
) -> dict[str, Any]:
    if syndrome is None:
        raise QECTORInputError("syndrome is required")
    if decoder_name not in DECODERS:
        raise QECTORInputError(
            f"Unknown decoder {decoder_name!r}; choose one of {sorted(DECODERS)}"
        )
    checks, inferred_n_qubits = _checks_for_family(family, size)
    resolved_n_qubits = inferred_n_qubits if n_qubits is None else n_qubits
    checks, resolved_n_qubits = _validated_checks(checks, resolved_n_qubits)
    if decoder_name in {"blossom", "sparse_blossom", "union_find", "fast_union_find"}:
        if not _is_graphlike_checks(checks):
            raise QECTORInputError(
                f"decoder {decoder_name!r} requires a graphlike check structure; "
                f"family {family!r} is non-graphlike"
            )
    matrix = matrix_from_checks(checks, resolved_n_qubits)
    normalized_syndrome = _binary_vector(
        syndrome,
        "syndrome",
        expected_length=matrix.shape[0],
    )
    decoder = DECODERS[decoder_name](checks, n_qubits=resolved_n_qubits)
    started = time.perf_counter()
    correction = _verify_faithfulness(
        matrix,
        decoder.decode(normalized_syndrome),
        normalized_syndrome,
    )
    latency_us = (time.perf_counter() - started) * 1e6
    return {
        "family": family,
        "size": int(size),
        "decoder": decoder_name,
        "backend_used": decoder.__class__.__name__,
        "qector_version": QECTOR_VERSION,
        "n_checks": int(matrix.shape[0]),
        "n_qubits": int(matrix.shape[1]),
        "syndrome": normalized_syndrome.astype(int).tolist(),
        "correction": correction.astype(int).tolist(),
        "hamming_weight": int(correction.sum()),
        "syndrome_valid": True,
        "latency_us": round(latency_us, 3),
    }


def decode_single(
    family: str = "rotated_surface",
    distance: int = 5,
    decoder_name: str = "blossom",
    error_rate: float = 0.05,
    seed: int = 42,
) -> dict[str, Any]:
    if decoder_name not in DECODERS:
        raise QECTORInputError(
            f"Unknown decoder {decoder_name!r}; choose one of {sorted(DECODERS)}"
        )
    distance = _require_integral(distance, "distance", minimum=1, maximum=MAX_DISTANCE)
    error_rate = _require_probability(error_rate, "error_rate")
    seed = _require_integral(seed, "seed", minimum=0)
    code = _code_for_family(family, distance)
    matrix = _code_matrix(code)
    logicals = _logical_matrix(code)
    if decoder_name in {"blossom", "sparse_blossom", "union_find", "fast_union_find"}:
        if hasattr(code, "is_matching_graph") and not code.is_matching_graph():
            raise QECTORInputError(
                f"decoder {decoder_name!r} requires a graphlike code; {family!r} is not graphlike"
            )
    rng = np.random.default_rng(seed)
    error = _binary_vector(
        code.random_error(error_rate, rng=rng),
        "error",
        expected_length=code.n_qubits,
    )
    syndrome = _binary_vector(
        code.syndrome(error),
        "syndrome",
        expected_length=code.n_checks,
    )
    decoder = DECODERS[decoder_name](code.check_to_qubits, n_qubits=code.n_qubits)
    started = time.perf_counter()
    correction = _verify_faithfulness(
        matrix,
        decoder.decode(syndrome),
        syndrome,
    )
    latency_us = (time.perf_counter() - started) * 1e6
    residual = correction ^ error
    if logicals is None:
        logical_failure: bool | None = None
        logical_scoring = "unavailable: logicals_matrix() returned None"
    else:
        logical_failure = bool(
            ((logicals.astype(np.int64) @ residual.astype(np.int64)) % 2).any()
        )
        logical_scoring = "logical-observable matrix (Theorem 2)"
    return {
        "family": family,
        "distance": int(distance),
        "decoder": decoder_name,
        "backend_used": decoder.__class__.__name__,
        "qector_version": QECTOR_VERSION,
        "error_rate": error_rate,
        "seed": seed,
        "n_qubits": int(code.n_qubits),
        "n_checks": int(code.n_checks),
        "error": error.astype(int).tolist(),
        "syndrome": syndrome.astype(int).tolist(),
        "correction": correction.astype(int).tolist(),
        "error_weight": int(error.sum()),
        "correction_weight": int(correction.sum()),
        "syndrome_valid": True,
        "logical_failure": logical_failure,
        "logical_scoring": logical_scoring,
        "latency_us": round(latency_us, 3),
    }


def _validate_sweep_inputs(
    family: str,
    distances: Sequence[int],
    error_rates: Sequence[float],
    trials: int,
    seed: int,
    decoder_name: str,
) -> tuple[list[int], list[float], int, int]:
    spec = FAMILY_REGISTRY.get(family)
    if spec is None or spec["kind"] != "size_code":
        raise QECTORInputError(
            f"threshold_sweep requires a size-based code family; choose from "
            f"{[name for name, item in FAMILY_REGISTRY.items() if item['kind'] == 'size_code']}"
        )
    if decoder_name not in DECODERS:
        raise QECTORInputError(
            f"Unknown decoder {decoder_name!r}; choose one of {sorted(DECODERS)}"
        )
    if (
        not isinstance(distances, Sequence)
        or isinstance(distances, (str, bytes))
        or not distances
    ):
        raise QECTORInputError("distances must be a non-empty array")
    if (
        not isinstance(error_rates, Sequence)
        or isinstance(error_rates, (str, bytes))
        or not error_rates
    ):
        raise QECTORInputError("error_rates must be a non-empty array")
    normalized_distances = [
        _require_integral(distance, "distance", minimum=1, maximum=MAX_DISTANCE)
        for distance in distances
    ]
    normalized_rates = [
        _require_probability(rate, "error_rate") for rate in error_rates
    ]
    if len(normalized_distances) * len(normalized_rates) > MAX_SWEEP_POINTS:
        raise QECTORInputError(
            f"sweep contains more than {MAX_SWEEP_POINTS} distance/rate points"
        )
    normalized_trials = _require_integral(
        trials, "trials", minimum=1, maximum=MAX_TRIALS
    )
    normalized_seed = _require_integral(seed, "seed", minimum=0)
    return normalized_distances, normalized_rates, normalized_trials, normalized_seed


def _artifact_root() -> Path:
    configured = os.environ.get("QECTOR_ARTIFACT_DIR")
    if configured:
        return Path(configured).expanduser().resolve()
    return (Path(__file__).resolve().parent.parent / "artifacts").resolve()


def _artifact_path(requested: str | None) -> Path:
    root = _artifact_root().resolve()
    if requested:
        candidate = Path(requested).expanduser()
        if not candidate.is_absolute():
            candidate = root / candidate
        candidate = candidate.resolve()
        if candidate.suffix.lower() != ".json":
            candidate = candidate / "threshold_sweep.json"
    else:
        candidate = root / f"qector_threshold_{time.time_ns()}.json"
    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise QECTORArtifactError(
            "artifact_path must remain inside QECTOR_ARTIFACT_DIR"
        ) from exc
    candidate.parent.mkdir(parents=True, exist_ok=True)
    return candidate


def _write_artifact(
    document: Mapping[str, Any], requested: str | None
) -> tuple[str, str]:
    path = _artifact_path(requested)
    if isinstance(document.get("required_metadata"), dict):
        artifact_metadata = document["required_metadata"].get("artifact")
        if isinstance(artifact_metadata, dict):
            artifact_metadata["path"] = str(path)
            artifact_metadata["sha256_sidecar"] = f"{path}.sha256"
            artifact_metadata.pop("sha256", None)
    payload = json.dumps(document, sort_keys=True, indent=2).encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    temporary_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_path = handle.name
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    except Exception as exc:
        if temporary_path:
            try:
                os.unlink(temporary_path)
            except OSError:
                pass
        raise QECTORArtifactError(f"could not write artifact {path}") from exc
    sidecar = Path(f"{path}.sha256")
    sidecar_temporary: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="ascii",
            dir=sidecar.parent,
            prefix=f".{sidecar.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            sidecar_temporary = handle.name
            handle.write(f"{digest}  {path.name}\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(sidecar_temporary, sidecar)
    except Exception as exc:
        if sidecar_temporary:
            try:
                os.unlink(sidecar_temporary)
            except OSError:
                pass
        raise QECTORArtifactError(
            f"could not write artifact sidecar {sidecar}"
        ) from exc
    return str(path), digest


def threshold_sweep(
    family: str = "rotated_surface",
    distances: Sequence[int] = (3, 5, 7),
    error_rates: Sequence[float] = (0.01, 0.05, 0.1),
    trials: int = 100,
    seed: int = 42,
    decoder_name: str = "blossom",
    artifact_path: str | None = None,
) -> dict[str, Any]:
    distances, error_rates, trials, seed = _validate_sweep_inputs(
        family, distances, error_rates, trials, seed, decoder_name
    )
    rows: list[dict[str, Any]] = []
    code_sizes: list[dict[str, int]] = []
    theorem1_violations = 0
    for distance in distances:
        code = _code_for_family(family, distance)
        matrix = _code_matrix(code)
        logicals = _logical_matrix(code)
        if logicals is None:
            raise QECTORInputError(
                f"{family!r} does not expose logical observables; LER cannot be scored"
            )
        if decoder_name in {
            "blossom",
            "sparse_blossom",
            "union_find",
            "fast_union_find",
        }:
            if hasattr(code, "is_matching_graph") and not code.is_matching_graph():
                raise QECTORInputError(
                    f"decoder {decoder_name!r} requires a graphlike code; {family!r} is not graphlike"
                )
        code_sizes.append(
            {
                "distance": int(distance),
                "n_checks": int(code.n_checks),
                "n_qubits": int(code.n_qubits),
            }
        )
        decoder = DECODERS[decoder_name](code.check_to_qubits, n_qubits=code.n_qubits)
        for error_rate in error_rates:
            logical_errors = 0
            for trial in range(trials):
                rng = np.random.default_rng(seed + trial)
                error = _binary_vector(
                    code.random_error(error_rate, rng=rng),
                    "error",
                    expected_length=code.n_qubits,
                )
                syndrome = _binary_vector(
                    code.syndrome(error),
                    "syndrome",
                    expected_length=code.n_checks,
                )
                correction = _verify_faithfulness(
                    matrix,
                    decoder.decode(syndrome),
                    syndrome,
                )
                residual = correction ^ error
                if bool(
                    ((logicals.astype(np.int64) @ residual.astype(np.int64)) % 2).any()
                ):
                    logical_errors += 1
            lo, hi = wilson_ci(logical_errors, trials)
            rows.append(
                {
                    "distance": int(distance),
                    "n_checks": int(code.n_checks),
                    "n_qubits": int(code.n_qubits),
                    "error_rate": float(error_rate),
                    "logical_error_rate": logical_errors / trials,
                    "wilson_95": [lo, hi],
                    "logical_errors": int(logical_errors),
                    "trials": int(trials),
                }
            )

    document: dict[str, Any] = {
        "schema_version": "1.0",
        "reference_manual": REF_DOI,
        "recipe": {
            "family": family,
            "distances": distances,
            "error_rates": error_rates,
            "decoder": decoder_name,
            "decoder_class": DECODERS[decoder_name].__name__,
            "mode": "single-shot CPU decode; code-capacity sampling",
            "trials": trials,
            "seed": seed,
            "seed_scheme": "seed = base + trial_index",
        },
        "required_metadata": {
            "code_family": family,
            "distance_size": code_sizes,
            "noise_model": {
                "tag": "code_capacity",
                "error_rates": error_rates,
                "source": "qector Code.random_error",
            },
            "dem_settings": {
                "decompose_errors": None,
                "graphlike_collapse": None,
                "applicable": False,
            },
            "decoder": {
                "class": DECODERS[decoder_name].__name__,
                "name": decoder_name,
                "weighted": False,
                "batch": False,
                "gpu": False,
            },
            "sample_count": {"trials_per_point": trials, "seed": seed},
            "metric": "logical_error_rate (logical coset scoring, Theorem 2)",
            "environment": _env_block(),
            "artifact": {
                "format": "raw JSON",
                "sha256": "returned with the tool result; hash covers this file",
            },
        },
        "harness": {
            "theorem1_violations": theorem1_violations,
            "faithfulness_policy": "fail closed before logical scoring",
        },
        "results": rows,
        "methodology": "Wilson 95% CI, z=1.959963985; code_capacity only.",
        "caveat": (
            "Screening estimate for the requested trial count; not a converged threshold. "
            "Do not compare code_capacity values with circuit_level values."
        ),
    }
    path, digest = _write_artifact(document, artifact_path)
    return {
        "family": family,
        "decoder": decoder_name,
        "qector_version": QECTOR_VERSION,
        "results": rows,
        "harness": document["harness"],
        "artifact": {
            "path": path,
            "sha256": digest,
            "metadata": document["required_metadata"],
        },
        "methodology": document["methodology"],
        "caveat": document["caveat"],
    }


def build_code_from_matrix(
    H_matrix: Sequence[Sequence[int]],
    family: str = "custom",
    distance: int = 3,
) -> dict[str, Any]:
    if (
        not isinstance(H_matrix, Sequence)
        or isinstance(H_matrix, (str, bytes))
        or not H_matrix
    ):
        raise QECTORInputError("H_matrix must be a non-empty rectangular matrix")
    rows = len(H_matrix)
    if rows > MAX_CHECKS or not isinstance(H_matrix[0], Sequence):
        raise QECTORInputError("H_matrix must be a non-empty rectangular matrix")
    columns = len(H_matrix[0])
    if columns <= 0:
        raise QECTORInputError("H_matrix must contain at least one qubit column")
    if rows * columns > MAX_MATRIX_CELLS:
        raise QECTORInputError(f"H_matrix exceeds the {MAX_MATRIX_CELLS}-cell limit")
    if any(not isinstance(row, Sequence) or len(row) != columns for row in H_matrix):
        raise QECTORInputError("H_matrix must be rectangular")
    matrix = np.asarray(H_matrix)
    if not np.all((matrix == 0) | (matrix == 1)):
        raise QECTORInputError("H_matrix must contain only 0 and 1")
    distance = _require_integral(distance, "distance", minimum=1, maximum=MAX_DISTANCE)
    code = codes.from_parity_check_matrix(
        matrix.astype(np.uint8), name=str(family), distance=distance
    )
    result_matrix = _code_matrix(code)
    logicals = _logical_matrix(code)
    return {
        "family": str(family),
        "distance": distance,
        "matrix_shape": [int(result_matrix.shape[0]), int(result_matrix.shape[1])],
        "rank": _gf2_rank(result_matrix),
        "n_checks": int(code.n_checks),
        "n_qubits": int(code.n_qubits),
        "logical_observables": None if logicals is None else int(logicals.shape[0]),
        "graphlike": bool(code.is_matching_graph())
        if hasattr(code, "is_matching_graph")
        else None,
        "code_built": True,
        "qector_version": QECTOR_VERSION,
        "reference_manual": REF_DOI,
    }


_PYPI_FRESHNESS_CACHE: dict[str, Any] | None = None


def _check_pypi_freshness() -> dict[str, Any]:
    """Opt-in, one-time-per-process PyPI freshness check.

    Never raises and never runs unless explicitly requested via
    ``compat_report(check_pypi=True)``. Any network failure (offline,
    DNS blocked, rate-limited, timeout) degrades to a ``"unavailable"``
    status rather than propagating, so the offline-by-default contract
    of ``compat_report`` is preserved on its default path. The result
    is cached for the lifetime of the server process so repeated calls
    within a session do not re-hit the network.
    """
    global _PYPI_FRESHNESS_CACHE
    if _PYPI_FRESHNESS_CACHE is not None:
        return _PYPI_FRESHNESS_CACHE
    result: dict[str, Any]
    try:
        request = urllib.request.Request(
            "https://pypi.org/pypi/qector-decoder-v3/json",
            headers={"User-Agent": f"{SERVER_NAME}/{SERVER_VERSION}"},
        )
        with urllib.request.urlopen(
            request, timeout=PYPI_FRESHNESS_TIMEOUT_S
        ) as response:
            payload = json.loads(response.read().decode("utf-8"))
        latest_version = payload.get("info", {}).get("version")
        if not isinstance(latest_version, str) or not latest_version:
            raise ValueError("PyPI response did not contain a version string")
        result = {
            "status": "ok",
            "latest_version": latest_version,
            "installed_version": QECTOR_VERSION,
            "up_to_date": latest_version == QECTOR_VERSION,
            "source": "https://pypi.org/pypi/qector-decoder-v3/json",
        }
    except Exception as exc:
        result = {
            "status": "unavailable",
            "reason": f"{exc.__class__.__name__}: {exc}",
            "installed_version": QECTOR_VERSION,
        }
    _PYPI_FRESHNESS_CACHE = result
    return result


def compat_report(check_pypi: bool = False) -> dict[str, Any]:
    try:
        import importlib.util

        numpy_available = importlib.util.find_spec("numpy") is not None
        mcp_available = importlib.util.find_spec("mcp") is not None
    except Exception:
        numpy_available = True
        mcp_available = False
    report: dict[str, Any] = {
        "runtime_ok": _QECTOR_VERSION_IN_WINDOW and numpy_available,
        "qector_decoder_v3": {
            "installed": True,
            "version": QECTOR_VERSION,
            "reviewed_window": [
                MIN_REVIEWED_QECTOR_VERSION,
                MAX_REVIEWED_QECTOR_VERSION_EXCLUSIVE,
            ],
            "in_reviewed_window": _QECTOR_VERSION_IN_WINDOW,
            "version_detail": _QECTOR_VERSION_DETAIL,
        },
        "numpy": {"installed": numpy_available, "version": np.__version__},
        "mcp_sdk": {"installed": mcp_available, "version": _installed_version("mcp")},
        "pymatching_compat": {
            "available": callable(getattr(qector_decoder_v3, "pymatching_compat", None))
            or importlib.util.find_spec("qector_decoder_v3.pymatching_compat")
            is not None
        },
        "reference_manual": REF_DOI,
        "provisional_surfaces": {
            "library_stdio_mcp": "supported local stdio wrapper in this package",
            "upstream_network_surfaces": "REST/gRPC/metrics/SSE require separate deployment review",
            "batch_gpu": "CUDA hardware and license are separate gates; no GPU claim is made here",
            "opencl": "OpenCL requires the documented source-build path",
        },
    }
    if check_pypi:
        report["pypi_freshness"] = _check_pypi_freshness()
    else:
        report["pypi_freshness"] = {
            "status": "not_checked",
            "reason": "pass check_pypi=true to query PyPI; default path stays fully offline",
        }
    return report


TOOL_FUNCTIONS: dict[str, Callable[..., Any]] = {
    "list_code_families": list_code_families,
    "list_decoders": list_decoders,
    "get_license_info": get_license_info,
    "decode_syndrome": decode_syndrome,
    "decode_single": decode_single,
    "threshold_sweep": threshold_sweep,
    "build_code_from_matrix": build_code_from_matrix,
    "compat_report": compat_report,
}

TOOL_DEFAULTS: dict[str, dict[str, Any]] = {
    "list_code_families": {},
    "list_decoders": {},
    "get_license_info": {},
    "decode_syndrome": {
        "family": "repetition",
        "size": 5,
        "decoder_name": "blossom",
        "n_qubits": None,
    },
    "decode_single": {
        "family": "rotated_surface",
        "distance": 5,
        "decoder_name": "blossom",
        "error_rate": 0.05,
        "seed": 42,
    },
    "threshold_sweep": {
        "family": "rotated_surface",
        "distances": [3, 5, 7],
        "error_rates": [0.01, 0.05, 0.1],
        "trials": 100,
        "seed": 42,
        "decoder_name": "blossom",
        "artifact_path": None,
    },
    "build_code_from_matrix": {"family": "custom", "distance": 3},
    "compat_report": {"check_pypi": False},
}


def _merged_arguments(name: str, arguments: Mapping[str, Any] | None) -> dict[str, Any]:
    if name not in TOOL_FUNCTIONS:
        raise QECTORInputError(
            f"Unknown tool {name!r}; choose one of {list(TOOL_NAMES)}"
        )
    merged = dict(TOOL_DEFAULTS[name])
    if arguments:
        merged.update(dict(arguments))
    return merged


def dispatch_tool(
    name: str, arguments: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    """Synchronous dispatch used by both MCP adapters and tests."""
    function = TOOL_FUNCTIONS.get(name)
    if function is None:
        raise QECTORInputError(
            f"Unknown tool {name!r}; choose one of {list(TOOL_NAMES)}"
        )
    consume_call_budget(name)
    return function(**_merged_arguments(name, arguments))


def _error_payload(exc: Exception) -> dict[str, Any]:
    return {
        "error": {
            "type": exc.__class__.__name__,
            "message": str(exc),
            "verified": False,
        }
    }


try:
    from mcp.types import (
    CallToolResult,
    ServerCapabilities,
    Tool,
        ToolsCapability,
    )
except Exception as exc:  # pragma: no cover - deployment error path
    raise RuntimeError(
        "The MCP Python SDK is required; install requirements.txt"
    ) from exc


def _tool_schema() -> list[Tool]:
    return [
        Tool(
            name="list_code_families",
            description="List code families and live qector 1.0.0 availability.",
            inputSchema={
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        ),
        Tool(
            name="list_decoders",
            description="List the five stable decoder classes exposed by the wheel.",
            inputSchema={
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        ),
        Tool(
            name="get_license_info",
            description="Read the live offline QECTOR license tier and feature gates.",
            inputSchema={
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        ),
        Tool(
            name="decode_syndrome",
            description="Decode a binary syndrome and fail unless H c = s (mod 2).",
            inputSchema={
                "type": "object",
                "properties": {
                    "family": {
                        "type": "string",
                        "enum": [
                            name
                            for name, spec in FAMILY_REGISTRY.items()
                            if spec["kind"] in {"checks_only", "size_code"}
                        ],
                        "default": "repetition",
                    },
                    "size": {"type": "integer", "minimum": 1, "default": 5},
                    "syndrome": {
                        "type": "array",
                        "items": {"type": "integer", "enum": [0, 1]},
                    },
                    "decoder_name": {
                        "type": "string",
                        "enum": sorted(DECODERS),
                        "default": "blossom",
                    },
                    "n_qubits": {
                        "type": ["integer", "null"],
                        "minimum": 1,
                        "default": None,
                    },
                },
                "required": ["syndrome"],
                "additionalProperties": False,
            },
        ),
        Tool(
            name="decode_single",
            description="Run one seeded code-capacity decode with Theorems 1 and 2 checks.",
            inputSchema={
                "type": "object",
                "properties": {
                    "family": {
                        "type": "string",
                        "enum": [
                            name
                            for name, spec in FAMILY_REGISTRY.items()
                            if spec["kind"] == "size_code"
                        ],
                        "default": "rotated_surface",
                    },
                    "distance": {"type": "integer", "minimum": 1, "default": 5},
                    "decoder_name": {
                        "type": "string",
                        "enum": sorted(DECODERS),
                        "default": "blossom",
                    },
                    "error_rate": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                        "default": 0.05,
                    },
                    "seed": {"type": "integer", "minimum": 0, "default": 42},
                },
                "additionalProperties": False,
            },
        ),
        Tool(
            name="threshold_sweep",
            description="Run a code-capacity LER sweep with Wilson 95% intervals and a hashed JSON artifact.",
            inputSchema={
                "type": "object",
                "properties": {
                    "family": {
                        "type": "string",
                        "enum": [
                            name
                            for name, spec in FAMILY_REGISTRY.items()
                            if spec["kind"] == "size_code"
                        ],
                        "default": "rotated_surface",
                    },
                    "distances": {
                        "type": "array",
                        "items": {"type": "integer", "minimum": 1},
                        "default": [3, 5, 7],
                    },
                    "error_rates": {
                        "type": "array",
                        "items": {"type": "number", "minimum": 0, "maximum": 1},
                        "default": [0.01, 0.05, 0.1],
                    },
                    "trials": {"type": "integer", "minimum": 1, "default": 100},
                    "seed": {"type": "integer", "minimum": 0, "default": 42},
                    "decoder_name": {
                        "type": "string",
                        "enum": sorted(DECODERS),
                        "default": "blossom",
                    },
                    "artifact_path": {"type": ["string", "null"], "default": None},
                },
                "additionalProperties": False,
            },
        ),
        Tool(
            name="build_code_from_matrix",
            description="Validate and build a binary (n_checks, n_qubits) parity-check matrix.",
            inputSchema={
                "type": "object",
                "properties": {
                    "H_matrix": {
                        "type": "array",
                        "items": {
                            "type": "array",
                            "items": {"type": "integer", "enum": [0, 1]},
                        },
                    },
                    "family": {"type": "string", "default": "custom"},
                    "distance": {"type": "integer", "minimum": 1, "default": 3},
                },
                "required": ["H_matrix"],
                "additionalProperties": False,
            },
        ),
        Tool(
            name="compat_report",
            description=(
                "Report live package compatibility and Provisional-surface "
                "boundaries. Set check_pypi=true to query PyPI for a newer "
                "qector-decoder-v3 release (single outbound HTTPS call, "
                "cached for the process lifetime); default stays fully offline."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "check_pypi": {
                        "type": "boolean",
                        "default": False,
                        "description": (
                            "Opt in to a one-time PyPI freshness check for this "
                            "server process. Never automatic."
                        ),
                    },
                },
                "additionalProperties": False,
            },
        ),
    ]


TOOLS = apply_tool_contract(_tool_schema())


async def _dispatch_mcp_call(
    name: str, arguments: Mapping[str, Any] | None
) -> CallToolResult:
    try:
        result = dispatch_tool(name, arguments)
        return call_tool_result(
            result_envelope(
                result,
                tool_name=name,
                server_name=SERVER_NAME,
                server_version=SERVER_VERSION,
                stability="stable",
            )
        )
    except Exception as exc:
        return call_tool_result(
            error_envelope(
                exc,
                tool_name=name,
                server_name=SERVER_NAME,
                server_version=SERVER_VERSION,
                stability="stable",
            ),
            is_error=True,
        )


try:
    from mcp.server import Server as _LowLevelServer
except Exception:  # pragma: no cover - deployment error path
    _LowLevelServer = None


def _build_low_level_server() -> Any:
    if _LowLevelServer is None:
        raise RuntimeError(
            "No supported low-level MCP server implementation is installed"
        )
    server = _LowLevelServer(
        SERVER_NAME,
        version=SERVER_VERSION,
        instructions=(
            "Local QECTOR decoder tools. Corrections are fail-closed against "
            "H c = s (mod 2); LER is logical-coset scored."
        ),
    )

    @server.list_tools()
    async def _list_tools() -> list[Tool]:
        return TOOLS

    @server.call_tool()
    async def _call_tool(
        name: str, arguments: dict[str, Any]
    ) -> CallToolResult:
        return await _dispatch_mcp_call(name, arguments)

    return server


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="QECTOR Decoder v3 library-only MCP server"
    )
    parser.add_argument("--transport", choices=("stdio",), default="stdio")
    parser.parse_args(argv)
    server = _build_low_level_server()
    from mcp.server.models import InitializationOptions

    initialization_options = InitializationOptions(
        server_name=SERVER_NAME,
        server_version=SERVER_VERSION,
        capabilities=ServerCapabilities(tools=ToolsCapability(listChanged=False)),
    )

    async def run_server() -> None:
        from mcp.server.stdio import stdio_server

        async with stdio_server() as (read, write):
            await server.run(read, write, initialization_options)

    asyncio.run(run_server())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
