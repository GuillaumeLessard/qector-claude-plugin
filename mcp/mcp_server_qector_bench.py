"""
QECTOR Decoder v3 research MCP server.

Companion to ``mcp_server_library.py`` (the 8-tool frozen library surface). Every
tool here is **Provisional** under the v1.0.0 API freeze note; the library's
8 tools remain the stable contract and the research server is an add-on for
research, methodology, and operator workflows that the 8-tool surface does
not cover.

The server implements the JSON-RPC 2.0 stdio transport with the
``mcp.server.Server`` low-level adapter pinned in this project (manual 26.2,
chapter 24.3 frame cap). It is local only; it makes no network calls by
default. The sole exception is an opt-in freshness check
(``env_block(check_pypi=True)``) that queries PyPI once per process and is
never triggered automatically.

The bench server exposes the following tool groups, each grounded in the
v1.0.0 reference manual (DOI 10.5281/zenodo.21941046):

* **Methodology** (``wilson_ci``, ``wilson_table``, ``logical_coset_score``):
  math utilities the library server does not expose; Wilson 95% CI, batch
  scoring on the logical coset (Theorem 2), and a Wilson table generator.

* **DEM / circuit** (``dem_inspect``, ``dem_collapse_parallel``): minimal
  Stim detector-error-model parsing and collapse-rule application, matching
  manual 14. The optional direct-wheel ``dem`` module is *not* required; if
  present, the tools defer to it after live introspection.

* **Codes** (``code_family_info``, ``code_export_matrices``,
  ``code_logicals_inspect``, ``code_distance_check``): structural inspection
  of every code family registered in the wheel (manual 4 / 16).

* **Compatibility** (``pymatching_compat_check``,
  ``sinter_decoder_list``, ``qiskit_plugin_check``): drop-in shim smoke
  tests, sinter entry-point listing, and the Qiskit plugin availability
  probe (manual 17.1-17.3).

* **Hardware / license** (``hardware_probe``, ``license_active_check``,
  ``env_block``): live probes; no hard-coded tier, no assumed device.

* **Workload integrity** (``workload_hash``, ``stim_circuit_probe``,
  ``sinter_task_template``): pure-Python helpers for reproducibility
  (manual 19, 22) that do not require any optional dependency.

* **Reference manual & reproduction** (``theorem_lookup``, ``glossary_lookup``,
  ``reproduction_command_lookup``): offline lookup of theorem statements (1-16),
  symbol / glossary entries, and Appendix D reproduction workflows from the v1.0.0
  reference manual; no decode, no network, no I/O.

Administrative setup, Desktop configuration, and Workbench executable probing
are deliberately implemented by the separately enabled ``qector-admin`` server.

* **Reproducibility** (``artifacts_sha256``, ``artifact_metadata_check``,
  ``decode_faithfulness_check``): chapter 22.3 / 22.5 helpers, plus an
  external H c = s verifier (Theorem 1 gate).

* **Micro-bench** (``hot_path_microbench``): a single-machine hot-path
  latency sample. Outputs a per-shot distribution only; never portable
  claims (manual 22.5).

All decode calls re-verify ``H c = s (mod 2)``; all LER outputs carry a 95%
Wilson interval; no measurement is published without the chapter 22.3
required-metadata block.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.metadata
import importlib.util
import json
import math
import os
import platform
import statistics
import subprocess
import sys
import time
from numbers import Integral, Real
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

_MCP_DIR = Path(__file__).resolve().parent
if str(_MCP_DIR) not in sys.path:
    sys.path.insert(0, str(_MCP_DIR))

from qector_mcp_compat import (  # noqa: E402
    build_server,
    make_tool,
    run_stdio,
    sdk_supported,
)
from qector_mcp_contract import (  # noqa: E402
    QECTORUnknownToolError,
    apply_tool_contract,
    call_tool_result,
    consume_call_budget,
    error_envelope,
    refund_call_budget,
    result_envelope,
    validate_arguments,
    validate_envelope,
)
import qector_airgap  # noqa: E402

os.environ.setdefault("QECTOR_SILENT", "1")

try:
    import numpy as np  # noqa: E402
except Exception as exc:  # pragma: no cover
    raise RuntimeError("numpy is required by the QECTOR bench MCP server") from exc

try:
    import qector_decoder_v3  # noqa: E402
except Exception:
    qector_decoder_v3 = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# Constants and contract surface
# ---------------------------------------------------------------------------

REF_DOI = "10.5281/zenodo.21941046"
EXPECTED_QECTOR_VERSION = "1.0.1"
SERVER_NAME = "qector-research-mcp"
SERVER_VERSION = "2.0.1"
WORKBENCH_PROTOCOL_VERSION = "2025-06-18"
Z95 = 1.959963985

# Safety caps. The library server's caps are authoritative for the frozen
# surface; the bench server has its own.
MAX_MATRIX_CELLS = int(os.environ.get("QECTOR_MCP_BENCH_MAX_MATRIX_CELLS", "2000000"))
MAX_TRIALS = int(os.environ.get("QECTOR_MCP_BENCH_MAX_TRIALS", "200000"))
MAX_DEM_BYTES = int(os.environ.get("QECTOR_MCP_BENCH_MAX_DEM_BYTES", "2000000"))
MAX_WILSON_ROWS = int(os.environ.get("QECTOR_MCP_BENCH_MAX_WILSON_ROWS", "10000"))
MAX_BENCH_SHOTS = int(os.environ.get("QECTOR_MCP_BENCH_MAX_BENCH_SHOTS", "5000"))
# Shots decoded (and verified) before timing starts, so the first-call cost
# of the native decoder never enters the latency sample.
MICROBENCH_WARMUP_SHOTS = int(os.environ.get("QECTOR_MCP_BENCH_WARMUP_SHOTS", "8"))
# Below this many timed shots a normal-approximation CI on the mean is not
# meaningful; the tool reports null instead of a possibly negative interval.
MICROBENCH_MIN_SHOTS_FOR_CI = 30
MAX_DISTANCE = int(os.environ.get("QECTOR_MCP_BENCH_MAX_DISTANCE", "63"))
PYPI_FRESHNESS_TIMEOUT_S = float(
    os.environ.get("QECTOR_MCP_BENCH_PYPI_TIMEOUT_S", "3.0")
)
MAX_WILSON_K = 10_000_000
MAX_BATCH = 4096
MAX_CHECKS = 20000
MAX_QUBITS = 200000

QECTOR_VERSION = (
    getattr(qector_decoder_v3, "__version__", "unknown")
    if qector_decoder_v3 is not None
    else "missing"
)

SETUP_PROFILES: dict[str, tuple[str, ...]] = {
    "production": (
        "numpy>=1.26,<2.3",
        "qector-decoder-v3==1.0.1",
        "mcp>=1.30,<3",
        "cryptography>=48.0.1,<50",
    ),
    "developer": (
        "numpy>=1.26,<2.3",
        "qector-decoder-v3==1.0.1",
        "mcp>=1.30,<3",
        "cryptography>=48.0.1,<50",
        "pytest",
        "ruff",
    ),
    "optional-stim": ("stim",),
    "optional-qiskit": ("qiskit",),
}
ADMIN_TOOL_NAMES = frozenset(
    {"system_setup", "configure_claude_desktop", "workbench_probe"}
)
# Decoders whose constructor is ``cls(check_to_qubits, n_qubits=...)`` and
# which the micro-benchmark can therefore drive without a DEM or matrix.
MICROBENCH_DECODERS = frozenset(
    {"union_find", "fast_union_find", "blossom", "sparse_blossom", "native_auto", "hybrid_cascade", "hybrid", "bposd"}
)


class QECTORInputError(ValueError):
    """Raised for malformed or resource-exceeding tool input."""


class QECTORFaithfulnessError(RuntimeError):
    """Raised when a backend violates the universal syndrome contract."""


class QECTORArtifactError(RuntimeError):
    """Raised when an evidence artifact cannot be written safely."""


class QECTORUnsupportedError(RuntimeError):
    """Raised when the request requires an optional surface that is absent."""


# ---------------------------------------------------------------------------
# Validation helpers (mirror the library server, but standalone)
# ---------------------------------------------------------------------------


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


def _validated_matrix(H_matrix: Any) -> np.ndarray:
    if not isinstance(H_matrix, Sequence) or isinstance(H_matrix, (str, bytes)):
        raise QECTORInputError("H_matrix must be a rectangular 2D array")
    if not H_matrix or not isinstance(H_matrix[0], Sequence):
        raise QECTORInputError("H_matrix must be a non-empty rectangular 2D array")
    rows = len(H_matrix)
    if rows > MAX_CHECKS:
        raise QECTORInputError(f"H_matrix exceeds the {MAX_CHECKS}-row limit")
    columns = len(H_matrix[0])
    if columns <= 0:
        raise QECTORInputError("H_matrix must contain at least one qubit column")
    if rows * columns > MAX_MATRIX_CELLS:
        raise QECTORInputError(f"H_matrix exceeds the {MAX_MATRIX_CELLS}-cell limit")
    for r, row in enumerate(H_matrix):
        if not isinstance(row, Sequence) or len(row) != columns:
            raise QECTORInputError(f"H_matrix row {r} has inconsistent length")
    matrix = np.asarray(H_matrix)
    if not np.all((matrix == 0) | (matrix == 1)):
        raise QECTORInputError("H_matrix must contain only 0 and 1")
    return matrix.astype(np.uint8)


def _validated_priors(priors: Any, expected_length: int) -> np.ndarray:
    if not isinstance(priors, Sequence) or isinstance(priors, (str, bytes)):
        raise QECTORInputError("priors must be a sequence")
    if len(priors) != expected_length:
        raise QECTORInputError(
            f"priors must contain {expected_length} elements; received {len(priors)}"
        )
    out = np.empty(expected_length, dtype=np.float64)
    for i, p in enumerate(priors):
        if isinstance(p, bool) or not isinstance(p, Real):
            raise QECTORInputError(f"priors[{i}] must be a finite number in [0, 1]")
        v = float(p)
        if not math.isfinite(v) or not 0.0 <= v <= 1.0:
            raise QECTORInputError(f"priors[{i}] must be a finite number in [0, 1]")
        out[i] = v
    return out


# ---------------------------------------------------------------------------
# Code / decoder registries (Provisional / device-local)
# ---------------------------------------------------------------------------

FAMILY_KIND = {
    "repetition": "size_code",
    "ring": "size_code",
    "rotated_surface": "size_code",
    "unrotated_surface": "size_code",
    "toric": "size_code",
    "heavy_hex": "size_code",
    "color_code": "size_code",
    "hypergraph_product": "matrix_pair",
    "custom": "from_matrix",
}

FAMILY_FACTORY = {
    "repetition": "repetition_code",
    "ring": "ring_code",
    "rotated_surface": "rotated_surface_code",
    "unrotated_surface": "unrotated_surface_code",
    "toric": "toric_code",
    "heavy_hex": "heavy_hex_code",
    "color_code": "color_code",
    # Built by the plugin (mcp/qector_codes.py), not the wheel; routed through
    # mcp_server_library._code_for_family like every other family.
    "rotated_surface_corrected": "rotated_surface_corrected",
}

DECODER_CLASS_HINTS = {
    "union_find": "UnionFindDecoder",
    "fast_union_find": "FastUnionFindDecoder",
    "blossom": "BlossomDecoder",
    "sparse_blossom": "SparseBlossomDecoder",
    "native_auto": "NativeAutoDecoder",
    "bposd": "BPOSDDecoder",
    "two_stage": "TwoStageDecoder",
    "ambiguity_cluster": "AmbiguityClusterDecoder",
    "space_time": "SpaceTimeDecoder",
    "streaming": "StreamingDecoder",
    "sliding_window": "SlidingWindowDecoder",
    "cuda_batch": "CUDABatchDecoder",
    "opencl_batch": "OpenCLBatchDecoder",
    "cuda_bposd": "CUDABpOsdDecoder",
    "lookup_table": "LookupTableDecoder",
    "auto": "AutoDecoder",
    "hybrid_cascade": "HybridCascadeDecoder",
    "hybrid": "HybridDecoder",
}


def _get_qector():
    if qector_decoder_v3 is None:
        raise QECTORUnsupportedError(
            "qector-decoder-v3 is not installed; install requirements.txt first"
        )
    return qector_decoder_v3


def _get_codes_module():
    q = _get_qector()
    codes = getattr(q, "codes", None)
    if codes is None:
        raise QECTORUnsupportedError("qector_decoder_v3.codes is not present")
    return codes


def _code_for_family(family: str, size: int):
    if family not in FAMILY_FACTORY:
        raise QECTORInputError(
            f"Unknown family {family!r}; choose one of {sorted(FAMILY_FACTORY)} or 'custom'"
        )
    size = _require_integral(size, "size", minimum=2, maximum=63)
    library = _get_library()
    try:
        return library._code_for_family(family, size)
    except library.QECTORInputError as exc:
        raise QECTORInputError(str(exc)) from exc


def _get_library():
    """The frozen library server: shared code cache, size caps and the distance probe."""
    import mcp_server_library

    return mcp_server_library


def _code_from_matrix(H_matrix: Any, name: str = "custom", distance: int | None = None):
    matrix = _validated_matrix(H_matrix)
    distance = (
        _require_integral(distance, "distance", minimum=1, maximum=63)
        if distance is not None
        else 1
    )
    return _get_codes_module().from_parity_check_matrix(
        matrix, name=name, distance=distance
    )


def _logical_matrix(code) -> np.ndarray | None:
    lm = code.logicals_matrix()
    if lm is None:
        return None
    lm = np.asarray(lm, dtype=np.uint8)
    if lm.ndim != 2 or lm.shape[1] != code.n_qubits:
        raise QECTORInputError("Code logicals_matrix() has an invalid shape")
    if not np.all((lm == 0) | (lm == 1)):
        raise QECTORInputError("Code logicals_matrix() returned non-binary values")
    return lm


def _code_matrix(code) -> np.ndarray:
    matrix = code.parity_check_matrix()
    if matrix is None:
        # Fallback: build it from check_to_qubits (the library's stable path).
        c2q = code.check_to_qubits
        matrix = np.zeros((len(c2q), code.n_qubits), dtype=np.uint8)
        for i, qubits in enumerate(c2q):
            for q in qubits:
                matrix[i, int(q)] ^= 1
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
        for q in check:
            degrees[q] = degrees.get(q, 0) + 1
    return max(degrees.values(), default=0) <= 2


def _verify_faithfulness(
    matrix: np.ndarray, correction: Any, syndrome: np.ndarray
) -> np.ndarray:
    normalized = _binary_vector(
        correction, "correction", expected_length=matrix.shape[1]
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


def _installed_version(distribution: str) -> str:
    try:
        return importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        return "unknown"


_PYPI_FRESHNESS_CACHE: dict[str, Any] | None = None


def _check_pypi_freshness() -> dict[str, Any]:
    """Opt-in, one-time-per-process PyPI freshness check.

    Mirrors the library server's ``_check_pypi_freshness``. Never raises
    and never runs unless explicitly requested via
    ``env_block(check_pypi=True)``. Any network failure degrades to a
    ``"unavailable"`` status rather than propagating, preserving the
    air-gapped-by-default contract of this server. Cached for the
    lifetime of the server process.
    """
    global _PYPI_FRESHNESS_CACHE
    qector_airgap.require_network("check_pypi=true")
    if _PYPI_FRESHNESS_CACHE is not None:
        return _PYPI_FRESHNESS_CACHE
    result: dict[str, Any]
    try:
        import urllib.request

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


def _pypi_block(check_pypi: bool) -> dict[str, Any]:
    if not check_pypi:
        return {
            "status": "not_checked",
            "reason": "pass check_pypi=true (and QECTOR_AIR_GAPPED=0) to query PyPI; default path stays fully offline",
        }
    if qector_airgap.is_air_gapped():
        return {
            "status": "disabled",
            "reason": "air-gapped mode (QECTOR_AIR_GAPPED=1, default) refuses the PyPI freshness check",
            "installed_version": QECTOR_VERSION,
        }
    return _check_pypi_freshness()


# ---------------------------------------------------------------------------
# Math utilities
# ---------------------------------------------------------------------------


def wilson_ci(k: int, n: int, z: float = Z95) -> tuple[float, float]:
    """Wilson 95% score interval (manual 15.2)."""
    k = _require_integral(k, "k", minimum=0, maximum=MAX_WILSON_K)
    n = _require_integral(n, "n", minimum=1, maximum=MAX_WILSON_K)
    if k > n:
        raise QECTORInputError("k must be at most n")
    if not isinstance(z, Real) or isinstance(z, bool) or not math.isfinite(float(z)) or float(z) <= 0:
        raise QECTORInputError("z must be a finite positive number (1.959963985 for 95%)")
    z = float(z)
    p = k / n
    denom = 1.0 + z * z / n
    centre = (p + z * z / (2.0 * n)) / denom
    # The radicand z^2/(4n^2) + p(1-p)/n is strictly positive for every n >= 1,
    # so no floor is needed; a floor would inflate the margin for large n.
    margin = z * math.sqrt(p * (1.0 - p) / n + z * z / (4.0 * n * n)) / denom
    return max(0.0, centre - margin), min(1.0, centre + margin)


def logical_coset_score(
    predicted_logicals: np.ndarray,
    sampled_logicals: np.ndarray,
) -> dict[str, Any]:
    """Score logical failures on the logical coset (Theorem 2, manual 3.2).

    Both arrays are ``(n_trials, n_observables)``: one row per decoded shot,
    one column per logical observable (the layout Stim/sinter produce). A
    trial fails when any observable's predicted flip differs from the
    sampled flip, i.e. when the residual anticommutes with a logical.
    """
    if predicted_logicals.shape != sampled_logicals.shape:
        raise QECTORInputError("predicted and sampled logicals must share shape")
    if predicted_logicals.ndim != 2:
        raise QECTORInputError("logicals must be 2D")
    if predicted_logicals.shape[0] == 0 or predicted_logicals.shape[1] == 0:
        raise QECTORInputError("logicals must have at least one trial row and one observable column")
    diff = predicted_logicals.astype(np.int64) ^ sampled_logicals.astype(np.int64)
    per_row = (diff.any(axis=1)).astype(int)
    failures = int(per_row.sum())
    total = int(per_row.size)
    return {
        "failures": failures,
        "trials": total,
        "logical_failure_rate": failures / total if total else 0.0,
        "wilson_95": list(wilson_ci(failures, total)) if total else [0.0, 0.0],
        "scoring": "logical coset (Theorem 2)",
    }


# ---------------------------------------------------------------------------
# DEM parsing + collapse (manual 14)
# ---------------------------------------------------------------------------


def _parse_dem_text(text: str) -> dict[str, Any]:
    """Parse a flattened Stim-style detector error model.

    Accepted instructions (Stim conventions):
        error(p) D0 D2 L0            one mechanism
        error(p) D0 D1 ^ D1 D2       Stim's ``^`` decomposition: each
                                     component becomes its own mechanism with
                                     the same probability (how Stim hands a
                                     decomposed error to a matching decoder)
        detector(x, y) D0
        logical_observable L0
        shift_detectors(...)         accepted and ignored (indices are taken
                                     as written)
    Rules: every ``error`` needs exactly one probability in [0, 1]; a detector
    repeated inside one component cancels (XOR), as in Stim; ``repeat`` blocks
    are refused because expanding them needs the detector-shift semantics of
    the full ``stim`` package (flatten the model with ``DetectorErrorModel.flattened()``
    first). Anything else is an error, never silently skipped.
    """
    text = text.strip()
    if not text:
        raise QECTORInputError("DEM text is empty")
    if len(text.encode("utf-8")) > MAX_DEM_BYTES:
        raise QECTORInputError(f"DEM text exceeds the {MAX_DEM_BYTES}-byte limit")

    mechanisms: list[dict[str, Any]] = []
    detectors: list[dict[str, Any]] = []
    observables: list[dict[str, Any]] = []
    raw_lines = 0
    instruction_counts: dict[str, int] = {}

    for lineno, line in enumerate(text.splitlines(), start=1):
        stripped = line.split("#", 1)[0].strip()
        if not stripped:
            continue
        raw_lines += 1
        tokens = stripped.split(None, 1)
        head = tokens[0]
        body = tokens[1] if len(tokens) > 1 else ""
        # Stim joins the keyword to '(' with no space for error/detector;
        # accept both spellings.
        for keyword in ("error", "detector", "shift_detectors"):
            if head.startswith(keyword + "("):
                body = head + (" " + body if body else "")
                head = keyword
                break
        instruction_counts[head] = instruction_counts.get(head, 0) + 1
        if head == "error":
            paren = body.find("(")
            close = body.find(")")
            if paren == -1 or close == -1 or close < paren:
                raise QECTORInputError(f"DEM line {lineno}: 'error' requires a parenthesized probability")
            prob_tokens = body[paren + 1 : close].split()
            if len(prob_tokens) != 1:
                raise QECTORInputError(f"DEM line {lineno}: 'error' takes exactly one probability, got {len(prob_tokens)}")
            try:
                probability = float(prob_tokens[0])
            except ValueError as exc:
                raise QECTORInputError(f"DEM line {lineno}: probability {prob_tokens[0]!r} is not a number") from exc
            if not math.isfinite(probability) or probability < 0.0 or probability > 1.0:
                raise QECTORInputError(f"DEM line {lineno}: probability {probability!r} is outside [0, 1]")
            components = [component.split() for component in body[close + 1 :].split("^")]
            for component_index, tags in enumerate(components):
                dets: list[str] = []
                obs: list[str] = []
                for tag in tags:
                    if tag.startswith("D") and tag[1:].isdigit():
                        if tag[1:] in dets:
                            dets.remove(tag[1:])  # repeated detector cancels (XOR)
                        else:
                            dets.append(tag[1:])
                    elif tag.startswith("L") and tag[1:].isdigit():
                        if tag[1:] in obs:
                            obs.remove(tag[1:])
                        else:
                            obs.append(tag[1:])
                    else:
                        raise QECTORInputError(f"DEM line {lineno}: unknown target {tag!r} (expected D<n> or L<n>)")
                mechanisms.append(
                    {
                        "line": lineno,
                        "probabilities": [probability],
                        "detectors": sorted(dets, key=int),
                        "observables": sorted(obs, key=int),
                        "weight": len(dets),
                        "component": component_index,
                        "n_components": len(components),
                    }
                )
        elif head == "detector":
            coords: list[float] = []
            paren = body.find("(")
            close = body.find(")")
            if paren != -1 and close > paren:
                for token in body[paren + 1 : close].split(","):
                    token = token.strip()
                    if token:
                        try:
                            coords.append(float(token))
                        except ValueError as exc:
                            raise QECTORInputError(f"DEM line {lineno}: coordinate {token!r} is not a number") from exc
            detectors.append({"line": lineno, "coords": coords})
        elif head == "logical_observable":
            observables.append({"line": lineno, "symbol": body.strip()})
        elif head == "shift_detectors":
            pass
        elif head == "repeat":
            raise QECTORInputError(
                f"DEM line {lineno}: 'repeat' blocks are not supported by this parser; "
                "flatten the model first (stim.DetectorErrorModel.flattened())"
            )
        else:
            raise QECTORInputError(f"DEM line {lineno}: unknown instruction {head!r}")

    return {
        "raw_lines": raw_lines,
        "instructions": instruction_counts,
        "mechanisms": mechanisms,
        "detectors": detectors,
        "observables": observables,
    }


def dem_collapse_parallel(
    parsed: dict[str, Any], *, observable_rule: str = "most_likely"
) -> dict[str, Any]:
    """Apply the manual 14.1 collapse rule: parallel mechanisms on the same
    detector set merge to one edge. Independent-XOR rule for n members:
    ``p = (1 - prod(1 - 2 p_i)) / 2`` (two members: ``p1(1-p2) + p2(1-p1)``);
    weight = ``log((1-p)/p)``; observable set = that of the most likely
    member (or union / first). Boundary edges (one detector) collapse the
    same way, keyed by their single detector. Hyperedges (three or more
    detectors) are reported, not collapsed. A combined probability of 0 or
    1 has no finite weight; ``weight_log`` is then null and a warning says so.
    """
    if observable_rule not in {"most_likely", "union", "first"}:
        raise QECTORInputError("observable_rule must be one of: most_likely, union, first")
    mechanisms = parsed.get("mechanisms", [])
    edges: dict[tuple[str, ...], list[dict[str, Any]]] = {}
    warnings: list[str] = []
    for mech in mechanisms:
        if mech["weight"] not in (1, 2):
            continue
        key = tuple(sorted(mech["detectors"], key=int))
        edges.setdefault(key, []).append(mech)
    collapsed: list[dict[str, Any]] = []
    for key, group in sorted(edges.items(), key=lambda item: tuple(int(d) for d in item[0])):
        member_probabilities = [m["probabilities"][0] for m in group]
        product = 1.0
        for p_i in member_probabilities:
            product *= 1.0 - 2.0 * p_i
        p_combined = (1.0 - product) / 2.0
        p_combined = min(1.0, max(0.0, p_combined))
        if len(group) == 1:
            winning_observables = group[0]["observables"]
        elif observable_rule == "most_likely":
            winning_observables = max(group, key=lambda m: m["probabilities"][0])["observables"]
        elif observable_rule == "first":
            winning_observables = group[0]["observables"]
        else:
            seen: list[str] = []
            for m in group:
                for o in m["observables"]:
                    if o not in seen:
                        seen.append(o)
            winning_observables = seen
        if 0.0 < p_combined < 1.0:
            weight: float | None = math.log((1.0 - p_combined) / p_combined)
        else:
            weight = None
            warnings.append(
                f"edge {list(key)} has combined probability {p_combined:g}; log((1-p)/p) is undefined, weight_log is null"
            )
        collapsed.append(
            {
                "detectors": list(key),
                "kind": "boundary" if len(key) == 1 else "edge",
                "p_combined": p_combined,
                "weight_log": weight,
                "n_members": len(group),
                "members": [{"p": m["probabilities"][0], "observables": m["observables"]} for m in group],
                "winning_observables": winning_observables,
                "observable_rule": observable_rule,
                "combination_rule": "independent_xor: p = (1 - prod(1 - 2 p_i)) / 2",
            }
        )
    hyperedges = [m for m in mechanisms if m["weight"] > 2]
    detector_free = [m for m in mechanisms if m["weight"] == 0]
    if detector_free:
        warnings.append(
            f"{len(detector_free)} mechanism(s) touch no detector (observable-only or cancelled); they form no edge"
        )
    return {
        "graphlike_edges": collapsed,
        "hyperedges": hyperedges,
        "n_graphlike_members": sum(len(g) for g in edges.values()),
        "n_unique_edges": len(collapsed),
        "n_detector_free": len(detector_free),
        **({"warnings": warnings} if warnings else {}),
    }


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------


def tool_wilson_ci(k: int, n: int, z: float = Z95) -> dict[str, Any]:
    lo, hi = wilson_ci(k, n, z)
    return {
        "k": int(k),
        "n": int(n),
        "z": float(z),
        "wilson_95": [lo, hi],
        "reference_manual": REF_DOI,
    }


def tool_wilson_table(n: int, k_list: Sequence[int], z: float = Z95) -> dict[str, Any]:
    n = _require_integral(n, "n", minimum=1, maximum=MAX_WILSON_K)
    if not isinstance(k_list, Sequence) or isinstance(k_list, (str, bytes)):
        raise QECTORInputError("k_list must be a sequence of integers")
    if len(k_list) > MAX_WILSON_ROWS:
        raise QECTORInputError(f"k_list exceeds the {MAX_WILSON_ROWS}-row limit")
    rows = []
    for k in k_list:
        lo, hi = wilson_ci(int(k), n, z)
        rows.append({"k": int(k), "n": n, "wilson_95": [lo, hi]})
    return {
        "n": n,
        "z": float(z),
        "rows": rows,
        "reference_manual": REF_DOI,
    }


def tool_logical_coset_score(
    predicted_logicals: Sequence[Sequence[int]],
    sampled_logicals: Sequence[Sequence[int]],
) -> dict[str, Any]:
    p = np.asarray(predicted_logicals, dtype=np.uint8)
    s = np.asarray(sampled_logicals, dtype=np.uint8)
    if p.ndim != 2 or s.ndim != 2:
        raise QECTORInputError("logicals must be 2D")
    if not np.all((p == 0) | (p == 1)) or not np.all((s == 0) | (s == 1)):
        raise QECTORInputError("logicals must contain only 0 and 1")
    return logical_coset_score(p, s)


def tool_dem_inspect(dem_text: str) -> dict[str, Any]:
    parsed = _parse_dem_text(dem_text)
    weights = [m["weight"] for m in parsed["mechanisms"]]
    weight_hist: dict[int, int] = {}
    for w in weights:
        weight_hist[w] = weight_hist.get(w, 0) + 1
    is_graphlike = all(w <= 2 for w in weights) if weights else True
    parsed_summary = {
        "n_mechanisms": len(parsed["mechanisms"]),
        "n_detectors": len(parsed["detectors"]),
        "n_observables": len(parsed["observables"]),
        "weight_histogram": dict(sorted(weight_hist.items())),
        "is_graphlike": is_graphlike,
        "routing": "matching decoders"
        if is_graphlike
        else "BP-OSD (hyperedges present)",
        "instructions": parsed["instructions"],
    }
    return {
        "summary": parsed_summary,
        "reference_manual": REF_DOI,
    }


def tool_dem_collapse_parallel(
    dem_text: str, observable_rule: str = "most_likely"
) -> dict[str, Any]:
    parsed = _parse_dem_text(dem_text)
    result = dem_collapse_parallel(parsed, observable_rule=observable_rule)
    collapse_warnings = result.pop("warnings", [])
    # The manual's worked example (p1=0.01, p2=0.02 -> 0.0296) is recomputed
    # with the same code path on every call, so a regression in the rule
    # shows up here as a mismatch rather than as a constant.
    example = dem_collapse_parallel(_parse_dem_text("error(0.01) D0 D1\nerror(0.02) D0 D1\n"))["graphlike_edges"][0]
    return {
        "dem_text_bytes": len(dem_text.encode("utf-8")),
        "collapse": result,
        "manual_worked_example_check": {
            "p1": 0.01,
            "p2": 0.02,
            "expected_p_combined": 0.0296,
            "computed_p_combined": example["p_combined"],
            "expected_weight_log": math.log(0.9704 / 0.0296),
            "computed_weight_log": example["weight_log"],
            "matches": abs(example["p_combined"] - 0.0296) < 1e-12,
        },
        "reference_manual": REF_DOI,
        **({"warnings": collapse_warnings} if collapse_warnings else {}),
    }


def tool_code_family_info(family: str, size: int) -> dict[str, Any]:
    code = _code_for_family(family, size)
    matrix = _code_matrix(code)
    logicals = _logical_matrix(code)
    is_graphlike = (
        bool(code.is_matching_graph())
        if hasattr(code, "is_matching_graph")
        else _is_graphlike_checks(code.check_to_qubits)
    )
    max_deg = (
        int(code.max_qubit_degree())
        if hasattr(code, "max_qubit_degree")
        else max(
            (
                sum(1 for c in code.check_to_qubits if q in c)
                for q in range(code.n_qubits)
            ),
            default=0,
        )
    )
    return {
        "family": family,
        "size": int(size),
        "n_qubits": int(code.n_qubits),
        "n_checks": int(code.n_checks),
        "distance": code.distance,
        "max_qubit_degree": max_deg,
        "is_matching_graph": is_graphlike,
        "n_logicals": 0 if logicals is None else int(logicals.shape[0]),
        "logicals_present": logicals is not None,
        "matrix_shape": list(matrix.shape),
        "routing": (
            "graphlike matching decoders" if is_graphlike else "BP-OSD (non-graphlike)"
        ),
        "health": _family_health(matrix, logicals, is_graphlike, int(size)),
        "qector_version": QECTOR_VERSION,
        "reference_manual": REF_DOI,
    }


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


def _family_health(matrix: np.ndarray, logicals: np.ndarray | None, graphlike: bool, size: int) -> dict[str, Any]:
    """Classify a live construction (mirrors the library server's probe)."""
    rank = _gf2_rank(matrix)
    unchecked = [int(i) for i in np.where(~matrix.any(axis=0))[0]]
    notes: list[str] = []
    if matrix.shape[0] < 2 or rank == 0:
        status = "degenerate"
        notes.append("fewer than two checks or zero rank; decoding claims are refused for this family/size")
    elif unchecked:
        status = "weak"
        notes.append(f"qubits {unchecked} participate in no check; effective distance is 1")
        if logicals is None:
            notes.append("no logical observables exposed; Theorem 2 scoring is undefined")
    elif logicals is None:
        status = "unscored"
        notes.append("no logical observables exposed; Theorem 2 scoring is undefined")
    else:
        status = "ok"
    return {
        "status": status,
        "probe_size": int(size),
        "n_checks": int(matrix.shape[0]),
        "n_qubits": int(matrix.shape[1]),
        "rank": int(rank),
        "logicals_present": logicals is not None,
        "graphlike": bool(graphlike),
        "unchecked_qubits": unchecked,
        "notes": notes,
    }


def tool_code_export_matrices(
    family: str,
    size: int,
    H_matrix: Sequence[Sequence[int]] | None = None,
    include_logicals: bool = True,
) -> dict[str, Any]:
    if H_matrix is not None:
        code = _code_from_matrix(H_matrix, name=family, distance=size)
    else:
        code = _code_for_family(family, size)
    matrix = _code_matrix(code)
    logicals = _logical_matrix(code) if include_logicals else None
    return {
        "family": family,
        "size": int(size),
        "n_qubits": int(code.n_qubits),
        "n_checks": int(code.n_checks),
        "check_to_qubits": code.check_to_qubits,
        "parity_check_matrix": matrix.astype(int).tolist(),
        "logicals_matrix": None if logicals is None else logicals.astype(int).tolist(),
        "qector_version": QECTOR_VERSION,
        "reference_manual": REF_DOI,
    }


def tool_code_logicals_inspect(family: str, size: int) -> dict[str, Any]:
    code = _code_for_family(family, size)
    logicals = _logical_matrix(code)
    if logicals is None:
        return {
            "family": family,
            "size": int(size),
            "n_logicals": 0,
            "logicals_present": False,
            "scoring_note": (
                "logicals_matrix() is None; Theorem 2 logical-coset scoring is "
                "unavailable. The code may still be decoded (Theorem 1 holds), "
                "but logical-error rate cannot be defined without an explicit "
                "observable basis (manual chapter 15.1)."
            ),
            "reference_manual": REF_DOI,
        }
    return {
        "family": family,
        "size": int(size),
        "n_logicals": int(logicals.shape[0]),
        "logicals_present": True,
        "logicals": logicals.astype(int).tolist(),
        "n_qubits": int(code.n_qubits),
        "reference_manual": REF_DOI,
    }


def tool_code_distance_check(family: str, size: int) -> dict[str, Any]:
    """Check the wheel's nominal distance instead of echoing it.

    ``nominal_distance`` is what the wheel labels the code; ``effective_distance``
    is what a bounded search over error supports finds (see
    ``mcp_server_library.effective_distance``). ``distance_verified`` is True
    only when the search is exact and agrees with the nominal value.
    """
    code = _code_for_family(family, size)
    matrix = _code_matrix(code)
    logicals = _logical_matrix(code)
    probe = _get_library().effective_distance(matrix, logicals, nominal=int(size))
    nominal = code.distance
    if probe["exact"]:
        verdict = "verified" if probe["min_logical_weight"] == nominal else "contradicted"
    elif probe["lower_bound"] is None:
        verdict = "unscorable"
    else:
        verdict = "bounded"
    warnings: list[str] = []
    if verdict == "contradicted":
        warnings.append(
            f"wheel labels {family}({size}) distance {nominal} but an undetectable logical error of weight "
            f"{probe['min_logical_weight']} exists on qubits {probe['witness']}; do not use the nominal distance in claims"
        )
    elif verdict == "bounded":
        warnings.append(
            f"search budget exhausted at weight {probe['searched_weight']}; distance >= {probe['lower_bound']} is all that is established"
        )
    elif verdict == "unscorable":
        warnings.append("no logical observables; the distance cannot be checked for this family")
    return {
        "family": family,
        "size": int(size),
        "n_qubits": int(code.n_qubits),
        "n_checks": int(code.n_checks),
        "nominal_distance": nominal,
        "effective_distance": probe,
        "distance_verified": verdict == "verified",
        "verdict": verdict,
        "matrix_shape": list(matrix.shape),
        "check_to_qubits": code.check_to_qubits,
        "qector_version": QECTOR_VERSION,
        "reference_manual": REF_DOI,
        **({"warnings": warnings} if warnings else {}),
    }


def tool_pymatching_compat_check(family: str, size: int) -> dict[str, Any]:
    """Verify a QECTOR result against a pymatching.Matching-style pipeline.

    Constructs a random syndrome from a QECTOR code, decodes it with QECTOR
    ``BlossomDecoder``, and (when pymatching is installed) decodes the same
    syndrome with a ``pymatching.Matching`` instance built from the same
    parity-check matrix; reports the bit-by-bit agreement of the
    corrections. This is a smoke test for the manual 17.1 drop-in shim; it
    is not a performance or accuracy claim.
    """
    code = _code_for_family(family, size)
    matrix = _code_matrix(code)
    if hasattr(code, "is_matching_graph") and not code.is_matching_graph():
        return {
            "family": family,
            "size": int(size),
            "comparable": False,
            "reason": "code is non-graphlike; pymatching.Matching is not applicable",
            "reference_manual": REF_DOI,
        }
    rng = np.random.default_rng(0)
    error = code.random_error(0.05, rng=rng)
    syndrome = code.syndrome(error)
    q = _get_qector()
    correction = q.BlossomDecoder(code.check_to_qubits, n_qubits=code.n_qubits).decode(
        syndrome
    )
    _verify_faithfulness(matrix, correction, syndrome)
    out: dict[str, Any] = {
        "family": family,
        "size": int(size),
        "n_qubits": int(code.n_qubits),
        "n_checks": int(code.n_checks),
        "qector_correction_weight": int(np.asarray(correction).sum()),
        "qector_syndrome_valid": True,
        "pymatching_compared": False,
    }
    if importlib.util.find_spec("pymatching") is not None:
        try:
            import pymatching  # type: ignore

            pm = pymatching.Matching(matrix)
            pm_correction = pm.decode(syndrome)
            pm_correction = np.asarray(pm_correction, dtype=np.uint8)
            q_correction = np.asarray(correction, dtype=np.uint8)
            out["pymatching_compared"] = True
            out["pymatching_correction_weight"] = int(pm_correction.sum())
            out["pymatching_syndrome_valid"] = bool(
                np.array_equal(
                    (matrix.astype(np.int64) @ pm_correction.astype(np.int64)) % 2,
                    syndrome,
                )
            )
            out["bitwise_equal"] = bool(np.array_equal(q_correction, pm_correction))
            out["agreement_note"] = (
                "Both decoders produce syndrome-valid corrections (Theorem 1). "
                "Bitwise equality is the coset-representative equality QECTOR "
                "and pymatching may not share (degeneracy, Theorem 1 corollary)."
            )
        except Exception as exc:
            out["pymatching_error"] = f"{type(exc).__name__}: {exc}"
    else:
        out["pymatching_skipped"] = "pymatching not installed; install if needed"
    out["reference_manual"] = REF_DOI
    return out


def tool_sinter_decoder_list() -> dict[str, Any]:
    """List the sinter entry points exposed by the wheel (manual 17.2)."""
    if qector_decoder_v3 is None:
        raise QECTORUnsupportedError("qector-decoder-v3 is not installed")
    # The wheel exposes the factory in ``qector_decoder_v3.sinter_compat``
    # (not at top level); it needs the optional ``sinter`` package at call
    # time. Report the three distinguishable states honestly.
    fn = getattr(qector_decoder_v3, "qector_sinter_decoders", None)
    module_path = "qector_decoder_v3"
    if fn is None:
        try:
            sinter_compat = importlib.import_module("qector_decoder_v3.sinter_compat")
        except Exception:
            sinter_compat = None
        fn = getattr(sinter_compat, "qector_sinter_decoders", None) if sinter_compat is not None else None
        module_path = "qector_decoder_v3.sinter_compat"
    if fn is None or not callable(fn):
        return {
            "sinter_decoders": [],
            "sinter_exposed": False,
            "factory": None,
            "sinter_installed": importlib.util.find_spec("sinter") is not None,
            "note": "qector_sinter_decoders() is not present on this build",
            "reference_manual": REF_DOI,
        }
    sinter_installed = importlib.util.find_spec("sinter") is not None
    if not sinter_installed:
        return {
            "sinter_decoders": [],
            "sinter_exposed": False,
            "factory": f"{module_path}.qector_sinter_decoders",
            "sinter_installed": False,
            "note": (
                "the factory exists but the optional 'sinter' package is not installed, so no shim can be "
                "registered; installing it is a network action outside the air-gapped default"
            ),
            "reference_manual": REF_DOI,
        }
    try:
        decoders = fn()
        return {
            "sinter_exposed": True,
            "factory": f"{module_path}.qector_sinter_decoders",
            "sinter_installed": True,
            "sinter_decoders": [{"name": name, "type": type(value).__name__} for name, value in decoders.items()],
            "reference_manual": REF_DOI,
        }
    except Exception as exc:
        return {
            "sinter_exposed": False,
            "factory": f"{module_path}.qector_sinter_decoders",
            "sinter_installed": True,
            "sinter_decoders": [],
            "error": f"{type(exc).__name__}: {exc}",
            "reference_manual": REF_DOI,
        }


def tool_qiskit_plugin_check() -> dict[str, Any]:
    """Probe the optional Qiskit plugin (manual 17.3)."""
    available = importlib.util.find_spec("qiskit") is not None
    out: dict[str, Any] = {
        "qiskit_installed": available,
        "raw_dict_mode": True,
        "reference_manual": REF_DOI,
    }
    if not available:
        out["note"] = (
            "qiskit is not installed. The qiskit_plugin module ships and "
            "operates in raw-dict mode without Qiskit (manual 17.3)."
        )
        return out
    try:
        from qector_decoder_v3 import qiskit_plugin  # type: ignore

        out["qiskit_plugin_imported"] = True
        out["decode_syndrome_counts_signature"] = str(
            getattr(qiskit_plugin, "decode_syndrome_counts", None)
        )
    except Exception as exc:
        out["qiskit_plugin_imported"] = False
        out["error"] = f"{type(exc).__name__}: {exc}"
    return out


def tool_hardware_probe() -> dict[str, Any]:
    """Probe CUDA / OpenCL / license availability live (no assumptions)."""
    out: dict[str, Any] = {"reference_manual": REF_DOI}
    q = _get_qector()
    try:
        cuda_avail = bool(q.cuda_is_available())
    except Exception:
        cuda_avail = False
    out["cuda_available"] = cuda_avail
    try:
        from qector_decoder_v3 import CUDABatchDecoder  # type: ignore

        out["cuda_batch_decoder"] = {
            "class": "CUDABatchDecoder",
            "is_available": bool(
                getattr(CUDABatchDecoder, "is_available", lambda: False)()
            ),
        }
    except Exception as exc:
        out["cuda_batch_decoder"] = {"error": f"{type(exc).__name__}: {exc}"}
    try:
        opencl_avail = bool(q.opencl_is_available())
    except Exception:
        opencl_avail = False
    out["opencl_available"] = opencl_avail
    try:
        info = q.get_license_info()
        out["license"] = info
    except Exception as exc:
        out["license"] = {"error": f"{type(exc).__name__}: {exc}"}
    out["environment"] = _env_block()
    return out


def tool_license_active_check() -> dict[str, Any]:
    """Read the live offline license tier and feature gates (manual 18)."""
    q = _get_qector()
    try:
        info = q.get_license_info()
    except Exception as exc:
        # No tier is assumed when the wheel cannot answer: report the error
        # and leave max_distance unknown instead of inventing "Community".
        return {
            "license_active": False,
            "error": f"{type(exc).__name__}: {exc}",
            "tier": "unknown",
            "max_distance": None,
            "source": "error",
            "reference_manual": REF_DOI,
        }
    info = dict(info) if isinstance(info, dict) else {"raw": str(info)}
    max_distance = info.get("max_distance")
    return {
        "license_active": not bool(info.get("is_expired", False)),
        "tier": str(info.get("tier", "unknown")),
        "max_distance": int(max_distance) if isinstance(max_distance, (int, float)) and not isinstance(max_distance, bool) else None,
        "gpu_enabled": bool(info["gpu_enabled"]) if "gpu_enabled" in info else None,
        "gnn_enabled": bool(info["gnn_enabled"]) if "gnn_enabled" in info else None,
        "source": "live_wheel",
        "info": info,
        "environment": _env_block(),
        "reference_manual": REF_DOI,
    }


def tool_env_block(check_pypi: bool = False) -> dict[str, Any]:
    out: dict[str, Any] = {
        "environment": _env_block(),
        "qector_decoder_v3_present": qector_decoder_v3 is not None,
        "qector_decoder_v3_version": QECTOR_VERSION,
        "reference_manual": REF_DOI,
    }
    out["pypi_freshness"] = _pypi_block(check_pypi)
    return out


def tool_compat_report(check_pypi: bool = False) -> dict[str, Any]:
    """Bench-server compatibility report; companion to the library
    server's ``compat_report``.

    Reports live package compatibility for this server's own runtime
    (numpy, mcp SDK, qector-decoder-v3, the pymatching compat shim) plus
    where this server sits in the Provisional-surface boundary map. Set
    ``check_pypi=True`` to also query PyPI for a newer qector-decoder-v3
    release; the default path stays fully offline, matching the library
    server's contract.
    """
    numpy_available = importlib.util.find_spec("numpy") is not None
    mcp_available = importlib.util.find_spec("mcp") is not None
    qector_installed = qector_decoder_v3 is not None
    pymatching_compat_available = False
    if qector_installed:
        pymatching_compat_available = (
            callable(getattr(qector_decoder_v3, "pymatching_compat", None))
            or importlib.util.find_spec("qector_decoder_v3.pymatching_compat")
            is not None
        )
    sdk_ok, sdk_detail = sdk_supported()
    report: dict[str, Any] = {
        "runtime_ok": (
            qector_installed
            and QECTOR_VERSION == EXPECTED_QECTOR_VERSION
            and numpy_available
            and mcp_available
            and sdk_ok
        ),
        "server": {
            "name": SERVER_NAME,
            "version": SERVER_VERSION,
            "kind": "research (Provisional companion to the 8-tool library server)",
        },
        "qector_decoder_v3": {
            "installed": qector_installed,
            "version": QECTOR_VERSION,
            "expected": EXPECTED_QECTOR_VERSION,
        },
        "numpy": {"installed": numpy_available, "version": np.__version__},
        "mcp_sdk": {"installed": mcp_available, "version": _installed_version("mcp"), "supported": sdk_ok, "detail": sdk_detail},
        "pymatching_compat": {"available": pymatching_compat_available},
        "reference_manual": REF_DOI,
        "network_policy": qector_airgap.network_policy(),
        "provisional_surfaces": {
            "library_stdio_mcp": "supported local stdio wrapper (library server, 8 frozen tools)",
            "research_stdio_mcp": "this server; 29 provisional research tools",
            "claude_code_plugin": "supported via .claude-plugin/plugin.json and .mcp.json",
            "claude_desktop_extension": "supported as a local Desktop extension / MCPB bundle",
            "claude_web_mobile": "not bundled; requires a hosted remote MCP connector and separate security review",
            "upstream_network_surfaces": "REST/gRPC/metrics/SSE require separate deployment review",
            "batch_gpu": "CUDA hardware and license are separate gates; no GPU claim is made here",
            "opencl": "OpenCL requires the documented source-build path",
        },
    }
    report["pypi_freshness"] = _pypi_block(check_pypi)
    return report


def _subprocess_workbench_probe(
    executable: str, timeout: float, list_tools: bool, limit: int | None
) -> dict[str, Any]:
    """Local stdio probe of an optional QECTOR Workbench executable.

    Mirrors ``scripts/probe_workbench_mcp.py``. No transcript is bundled;
    the output is the live JSON-RPC response from the target machine.
    The Workbench is **optional** under the v1.0.0 design. The research
    server's 29 tools cover every Workbench-free need
    (hardware_probe, license_active_check, code_family_info, etc.).
    """
    import subprocess

    if not isinstance(executable, str) or not executable.strip():
        raise QECTORInputError("executable must be a non-empty path string")
    if not Path(executable).is_file():
        raise QECTORInputError(f"Workbench executable not found: {executable}")
    timeout = float(timeout)
    if timeout <= 0 or timeout > 300:
        raise QECTORInputError("timeout must be in (0, 300] seconds")
    env = os.environ.copy()
    env["QECTOR_SILENT"] = "1"
    try:
        proc = subprocess.Popen(
            [executable, "--mcp"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env=env,
        )
    except OSError as exc:
        raise QECTORInputError(f"Failed to start executable: {exc}") from exc

    def _send(lines):
        payload = ("\n".join(lines) + "\n").encode("utf-8")
        proc.stdin.write(payload)
        proc.stdin.flush()

    init_msg = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": WORKBENCH_PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "qector-workbench-probe", "version": "1.0"},
        },
    }
    notif_msg = {"jsonrpc": "2.0", "method": "notifications/initialized"}
    list_msg = {"jsonrpc": "2.0", "id": 3, "method": "tools/list"}
    status_msg = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {"name": "mcp_status", "arguments": {}},
    }

    responses: list[dict] = []
    try:
        _send([json.dumps(init_msg), json.dumps(notif_msg)])
        if list_tools:
            _send([json.dumps(list_msg)])
            expected = 2
        else:
            _send([json.dumps(status_msg), json.dumps(list_msg)])
            expected = 3
        for _ in range(expected):
            line = proc.stdout.readline()
            if not line:
                break
            try:
                responses.append(json.loads(line))
            except json.JSONDecodeError:
                responses.append(
                    {"_raw": line.decode("utf-8", errors="replace").rstrip()}
                )
        if list_tools and responses:
            tools = (
                responses[-1].get("result", {}).get("tools", [])
                if isinstance(responses[-1], dict)
                else []
            )
            names = [t.get("name") for t in tools if isinstance(t, dict)]
            if limit is not None:
                names = names[: int(limit)]
            return {
                "executable": executable,
                "negotiated_protocol_version": responses[0]
                .get("result", {})
                .get("protocolVersion"),
                "tools_total": len(tools),
                "tool_names": names,
                "responses": responses,
                "note": (
                    "Optional Workbench device-local probe. The research server's "
                    "29 tools cover every Workbench-free need; the "
                    "Workbench is not required for any QECTOR workflow."
                ),
                "reference_manual": REF_DOI,
            }
        return {
            "executable": executable,
            "negotiated_protocol_version": responses[0]
            .get("result", {})
            .get("protocolVersion")
            if responses
            else None,
            "responses": responses,
            "note": (
                "Optional Workbench device-local probe. The research server's "
                "29 tools cover every Workbench-free need."
            ),
            "reference_manual": REF_DOI,
        }
    finally:
        try:
            if proc.stdin:
                proc.stdin.close()
        except Exception:
            pass
        try:
            proc.wait(timeout=timeout)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
            try:
                proc.wait()
            except Exception:
                pass


def tool_workbench_probe(
    executable: str,
    timeout: float = 60.0,
    list_tools: bool = True,
    limit: int | None = None,
) -> dict[str, Any]:
    """Local stdio probe of an optional QECTOR Workbench executable.

    The Workbench is optional under the v1.0.0 design (manual 17.5).
    The research server's 29 tools cover every Workbench-free need.
    """
    return _subprocess_workbench_probe(executable, timeout, list_tools, limit)


def default_data_dir() -> Path:
    """Per-user writable data directory (identical to the library server's)."""
    system = platform.system()
    if system == "Windows":
        base = os.environ.get("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / "QectorClaudePlugin"
    if system == "Darwin":
        return Path.home() / "Library" / "Application Support" / "QectorClaudePlugin"
    base = os.environ.get("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
    return Path(base) / "qector-claude-plugin"


def _artifact_root() -> Path:
    configured = os.environ.get("QECTOR_ARTIFACT_DIR")
    if configured and not configured.startswith("${"):
        return Path(configured).expanduser().resolve()
    return (default_data_dir() / "artifacts").resolve()


def _approved_artifact_path(raw_path: str) -> Path:
    artifact_root = _artifact_root()
    candidate = Path(raw_path).expanduser()
    if not candidate.is_absolute():
        # Relative names are artifact names, never cwd-relative paths: the
        # server's working directory is not meaningful under Claude Desktop.
        candidate = artifact_root / candidate
    candidate = candidate.resolve()
    try:
        candidate.relative_to(artifact_root)
    except ValueError as exc:
        raise QECTORInputError(
            "paths must remain inside QECTOR_ARTIFACT_DIR"
        ) from exc
    return candidate


def tool_artifacts_sha256(paths: Sequence[str]) -> dict[str, Any]:
    if not isinstance(paths, Sequence) or isinstance(paths, (str, bytes)):
        raise QECTORInputError("paths must be a sequence of strings")
    if len(paths) > 100:
        raise QECTORInputError("paths exceeds the 100-entry limit")
    out = []
    for raw in paths:
        if not isinstance(raw, str) or not raw.strip():
            raise QECTORInputError("each path must be a non-empty string")
        path = _approved_artifact_path(raw)
        if not path.is_file():
            raise QECTORInputError(f"not a file: {path}")
        digest = hashlib.sha256()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                digest.update(chunk)
        out.append(
            {
                "path": str(path),
                "size_bytes": path.stat().st_size,
                "sha256": digest.hexdigest(),
            }
        )
    return {
        "files": out,
        "n_files": len(out),
        "artifact_root": str(_artifact_root()),
        "reference_manual": REF_DOI,
    }


def tool_artifact_metadata_check(
    family: str,
    size: int,
    decoder_name: str = "blossom",
    trials: int = 100,
    error_rates: Sequence[float] = (0.01, 0.05, 0.1),
    seed: int = 42,
    artifact_path: str | None = None,
) -> dict[str, Any]:
    """Check an artifact's chapter 22.3 metadata, or emit the template.

    With ``artifact_path`` (a ``.json`` inside the artifact root, as written
    by ``threshold_sweep``), the file is loaded, its ``required_metadata``
    block is checked field by field, and the ``.sha256`` sidecar is
    recomputed and compared. Without it, the tool returns the template a
    conforming artifact must carry and says so (``mode: "template"``,
    ``checked: false``); nothing is verified in that mode.
    """
    if family not in FAMILY_FACTORY:
        raise QECTORInputError(f"Unknown family {family!r}")
    if decoder_name not in DECODER_CLASS_HINTS:
        raise QECTORInputError(f"Unknown decoder {decoder_name!r}")
    trials = _require_integral(trials, "trials", minimum=1, maximum=MAX_TRIALS)
    seed = _require_integral(seed, "seed", minimum=0)
    code = _code_for_family(family, size)
    matrix = _code_matrix(code)
    required_fields = [
        "code_family",
        "distance_size",
        "noise_model",
        "dem_settings",
        "decoder",
        "sample_count",
        "metric",
        "environment",
        "artifact",
    ]
    template = {
        "code_family": family,
        "distance_size": [{"distance": int(size), "n_checks": int(code.n_checks), "n_qubits": int(code.n_qubits)}],
        "noise_model": {"tag": "code_capacity", "error_rates": list(error_rates), "source": "qector Code.random_error"},
        "dem_settings": {"decompose_errors": None, "graphlike_collapse": None, "applicable": False},
        "decoder": {"class": DECODER_CLASS_HINTS[decoder_name], "name": decoder_name, "weighted": False, "batch": False, "gpu": False},
        "sample_count": {"trials_per_point": trials, "seed": seed},
        "metric": "logical_error_rate (logical coset scoring, Theorem 2)",
        "environment": _env_block(),
        "artifact": {"format": "raw JSON", "path": "<written by threshold_sweep>", "sha256_sidecar": "<path>.sha256"},
    }
    base = {
        "family": family,
        "size": int(size),
        "decoder": decoder_name,
        "required_fields": required_fields,
        "matrix_shape": list(matrix.shape),
        "reference_manual": REF_DOI,
    }
    if artifact_path is None:
        return {
            **base,
            "mode": "template",
            "checked": False,
            "required_metadata": template,
            "missing_fields": [],
            "all_required_fields_present": False,
            "artifact_sha256": None,
            "sidecar_matches": None,
            "warnings": ["no artifact_path given: this is the metadata template, nothing was checked"],
        }
    library = _get_library()
    try:
        path = library._artifact_path(artifact_path)
    except library.QECTORArtifactError as exc:
        raise QECTORInputError(str(exc)) from exc
    if not path.is_file():
        raise QECTORInputError(f"artifact {path.name} does not exist inside the artifact root")
    payload = path.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    try:
        document = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise QECTORInputError(f"artifact {path.name} is not valid JSON: {exc.__class__.__name__}") from exc
    metadata = document.get("required_metadata") if isinstance(document, dict) else None
    if not isinstance(metadata, dict):
        metadata = {}
    missing = [field for field in required_fields if field not in metadata]
    sidecar = Path(f"{path}.sha256")
    sidecar_matches: bool | None = None
    warnings: list[str] = []
    if sidecar.is_file():
        recorded = sidecar.read_text(encoding="ascii", errors="replace").split()[:1]
        sidecar_matches = bool(recorded) and recorded[0] == digest
        if not sidecar_matches:
            warnings.append("the .sha256 sidecar does not match the artifact bytes; the file changed after it was written")
    else:
        warnings.append("no .sha256 sidecar next to the artifact")
    if missing:
        warnings.append(f"required_metadata lacks {missing}")
    return {
        **base,
        "mode": "checked",
        "checked": True,
        "required_metadata": metadata if not missing else template,
        "missing_fields": missing,
        "all_required_fields_present": not missing,
        "artifact_sha256": digest,
        "sidecar_matches": sidecar_matches,
        **({"warnings": warnings} if warnings else {}),
    }


def tool_decode_faithfulness_check(
    H_matrix: Sequence[Sequence[int]],
    syndrome: Sequence[int],
    correction: Sequence[int],
) -> dict[str, Any]:
    """Re-verify the H c = s (mod 2) gate (Theorem 1) externally.

    Useful when an agent wants to confirm that a correction returned by a
    third-party decoder, an older wheel build, or a non-MCP integration
    satisfies the universal contract. The check is the same one the library
    server runs after every decode.
    """
    H = _validated_matrix(H_matrix)
    s = _binary_vector(syndrome, "syndrome", expected_length=H.shape[0])
    c = _binary_vector(correction, "correction", expected_length=H.shape[1])
    calculated = ((H.astype(np.int64) @ c.astype(np.int64)) % 2).astype(np.uint8)
    valid = bool(np.array_equal(calculated, s))
    mismatch = [int(i) for i in np.where(calculated != s)[0]]
    return {
        "syndrome_valid": valid,
        "n_checks": int(H.shape[0]),
        "n_qubits": int(H.shape[1]),
        "correction_weight": int(c.sum()),
        "syndrome_weight": int(s.sum()),
        "computed_syndrome": calculated.astype(int).tolist(),
        "syndrome_mismatch_indices": mismatch,
        "theorem": "Theorem 1 (manual chapter 3)",
        "reference_manual": REF_DOI,
    }


def tool_hot_path_microbench(
    family: str,
    size: int,
    shots: int = 64,
    decoder_name: str = "blossom",
    seed: int = 42,
) -> dict[str, Any]:
    """Run a small hot-path micro-benchmark.

    Per manual 22.5, the output is a per-shot latency distribution; it is
    never a portable performance claim.
    """
    if shots <= 0 or shots > MAX_BENCH_SHOTS:
        raise QECTORInputError(f"shots must be in (0, {MAX_BENCH_SHOTS}]")
    code = _code_for_family(family, size)
    matrix = _code_matrix(code)
    q = _get_qector()
    if decoder_name not in DECODER_CLASS_HINTS:
        raise QECTORInputError(f"Unknown decoder {decoder_name!r}")
    decoder_cls = getattr(q, DECODER_CLASS_HINTS[decoder_name], None)
    if decoder_cls is None:
        raise QECTORUnsupportedError(
            f"decoder class {DECODER_CLASS_HINTS[decoder_name]!r} is not present in this build"
        )
    if decoder_name not in MICROBENCH_DECODERS:
        raise QECTORInputError(
            f"hot_path_microbench supports the check-list constructor decoders {sorted(MICROBENCH_DECODERS)}; "
            f"{decoder_name!r} needs a matrix/DEM constructor and is not benchmarked here"
        )
    if decoder_name in {"union_find", "fast_union_find", "blossom", "sparse_blossom"} and hasattr(code, "is_matching_graph") and not code.is_matching_graph():
        raise QECTORInputError(f"decoder {decoder_name!r} requires a graphlike code; {family!r} is not graphlike")
    decoder = decoder_cls(code.check_to_qubits, n_qubits=code.n_qubits)
    rng = np.random.default_rng(seed)
    latencies_us: list[float] = []
    syndrome_invalid = 0
    # Warm-up: the first calls into the native decoder pay one-off costs
    # (allocation, graph construction) that are not hot-path latency. They
    # are decoded and verified but not timed.
    for _ in range(MICROBENCH_WARMUP_SHOTS):
        s = code.syndrome(code.random_error(0.05, rng=rng))
        try:
            _verify_faithfulness(matrix, decoder.decode(s), s)
        except QECTORFaithfulnessError:
            pass
    for _ in range(int(shots)):
        err = code.random_error(0.05, rng=rng)
        s = code.syndrome(err)
        # The timed window is decoder.decode() alone. The Theorem 1 check
        # runs afterwards, outside the window, and still fails closed.
        started = time.perf_counter()
        correction = decoder.decode(s)
        elapsed_us = (time.perf_counter() - started) * 1e6
        try:
            _verify_faithfulness(matrix, correction, s)
        except QECTORFaithfulnessError:
            syndrome_invalid += 1
            continue
        latencies_us.append(elapsed_us)
    if not latencies_us:
        workload_hash_input = (
            f"{family}|d={int(size)}|decoder={decoder_name}|"
            f"error_rate=0.05|seed={int(seed)}"
        )
        workload_hash = hashlib.sha256(
            workload_hash_input.encode("utf-8")
        ).hexdigest()
        env = _env_block()
        return {
            "family": family,
            "size": int(size),
            "decoder": decoder_name,
            "shots_requested": int(shots),
            "shots_completed": 0,
            "syndrome_invalid": syndrome_invalid,
            "warning": "no successful decodes; refusing to publish statistics",
            "measurement_scope": {
                "machine": platform.node() or "unknown",
                "os": env.get("os"),
                "platform": env.get("platform"),
                "python": env.get("python"),
                "cpu": env.get("cpu"),
                "ram_bytes": env.get("ram_bytes"),
                "backend": "qector-decoder-v3",
                "backend_version": QECTOR_VERSION,
                "decoder_class": DECODER_CLASS_HINTS.get(
                    decoder_name, decoder_name
                ),
                "code_family": family,
                "code_size": int(size),
                "noise_model": {
                    "tag": "code_capacity",
                    "error_rate": 0.05,
                    "source": "qector Code.random_error",
                },
                "shots_requested": int(shots),
                "shots_completed": 0,
                "seed": int(seed),
                "workload_hash": workload_hash,
                "scope": "single_machine",
                "claim_class": "machine_scoped_measurement",
            },
            "environment": env,
            "qector_version": QECTOR_VERSION,
            "reference_manual": REF_DOI,
        }
    bench_warnings: list[str] = []
    if syndrome_invalid:
        bench_warnings.append(
            f"{syndrome_invalid} of {int(shots)} shots violated H c = s (mod 2); the latency sample excludes them"
        )
    sorted_lat = sorted(latencies_us)
    n = len(sorted_lat)

    def _pct(p: float) -> float:
        if n == 0:
            return 0.0
        k = max(0, min(n - 1, int(round(p * (n - 1)))))
        return sorted_lat[k]

    mean = statistics.fmean(latencies_us)
    sd = statistics.pstdev(latencies_us) if n > 1 else 0.0
    se = sd / math.sqrt(n) if n > 1 else 0.0
    workload_hash_input = (
        f"{family}|d={int(size)}|decoder={decoder_name}|"
        f"error_rate=0.05|seed={int(seed)}"
    )
    workload_hash = hashlib.sha256(
        workload_hash_input.encode("utf-8")
    ).hexdigest()
    env = _env_block()
    measurement_scope: dict[str, Any] = {
        "machine": platform.node() or "unknown",
        "os": env.get("os"),
        "platform": env.get("platform"),
        "python": env.get("python"),
        "cpu": env.get("cpu"),
        "ram_bytes": env.get("ram_bytes"),
        "backend": "qector-decoder-v3",
        "backend_version": QECTOR_VERSION,
        "decoder_class": DECODER_CLASS_HINTS.get(decoder_name, decoder_name),
        "code_family": family,
        "code_size": int(size),
        "noise_model": {
            "tag": "code_capacity",
            "error_rate": 0.05,
            "source": "qector Code.random_error",
        },
        "shots_requested": int(shots),
        "shots_completed": n,
        "seed": int(seed),
        "workload_hash": workload_hash,
        "scope": "single_machine",
        "claim_class": "machine_scoped_measurement",
    }
    return {
        "family": family,
        "size": int(size),
        "decoder": decoder_name,
        "shots_requested": int(shots),
        "shots_completed": n,
        "syndrome_invalid": syndrome_invalid,
        "latency_us": {
            "n": n,
            "mean": mean,
            "stddev": sd,
            "min": min(latencies_us),
            "max": max(latencies_us),
            "p50": _pct(0.50),
            "p90": _pct(0.90),
            "p95": _pct(0.95),
            "p99": _pct(0.99),
            "ci95_mean": (
                [max(0.0, mean - 1.959963985 * se), mean + 1.959963985 * se]
                if n >= MICROBENCH_MIN_SHOTS_FOR_CI
                else None
            ),
        },
        "timed_window": "decoder.decode(syndrome) only; the H c = s verification runs outside the window",
        "warmup_shots": MICROBENCH_WARMUP_SHOTS,
        "scope_note": (
            "Per-machine, per-workload, per-build hot-path latency sample of decoder.decode() after "
            f"{MICROBENCH_WARMUP_SHOTS} untimed warm-up shots. Not a portable performance claim (manual 22.5); "
            f"ci95_mean is null below {MICROBENCH_MIN_SHOTS_FOR_CI} timed shots."
        ),
        "measurement_scope": measurement_scope,
        "environment": env,
        "qector_version": QECTOR_VERSION,
        "reference_manual": REF_DOI,
        **({"warnings": bench_warnings} if bench_warnings else {}),
    }


# ---------------------------------------------------------------------------
# Workload integrity (pure-Python; no qector_decoder_v3 required)
# ---------------------------------------------------------------------------


def _normalize_stim_circuit(circuit_text: str) -> dict[str, Any]:
    """Parse a small Stim circuit text. Returns a structured summary.

    The parser is permissive: it accepts the small subset of Stim that
    the reference manual uses in examples and the worked exercises
    (qubit declarations, single-qubit gates, two-qubit gates, measurement,
    noise channels, detectors, observables, repeat blocks). It does
    not require the Stim package.

    For the full Stim instruction set, install ``stim`` and use the
    optional direct-wheel path.
    """
    circuit_text = circuit_text.strip()
    if not circuit_text:
        raise QECTORInputError("circuit_text is empty")
    if len(circuit_text.encode("utf-8")) > MAX_DEM_BYTES:
        raise QECTORInputError(f"circuit_text exceeds the {MAX_DEM_BYTES}-byte limit")

    # First pass: detect QUBIT_COORDS-style declarations to find n_qubits.
    n_qubits = 0
    rounds: list[dict[str, Any]] = []
    instructions: dict[str, int] = {}
    tick_count = 0
    for lineno, line in enumerate(circuit_text.splitlines(), start=1):
        stripped = line.split("#", 1)[0].strip()
        if not stripped:
            continue
        head, *rest = stripped.split(None, 1)
        body = rest[0] if rest else ""
        # Stim allows `name(args)` to run into the instruction.
        if (
            head.startswith(("H", "X", "Y", "Z", "S", "S_DAG", "T", "T_DAG"))
            and "(" in head
        ):
            instr = head[: head.index("(")]
            body = head[head.index("(") :] + (" " + body if body else "")
            head = instr
        instructions[head] = instructions.get(head, 0) + 1
        if head == "QUBIT_COORDS":
            coords = body.replace("(", "").replace(")", "").split(",")
            try:
                idx = int(coords[0].strip())
            except (ValueError, IndexError) as exc:
                raise QECTORInputError(
                    f"circuit line {lineno}: QUBIT_COORDS missing integer index"
                ) from exc
            n_qubits = max(n_qubits, idx + 1)
        if head == "TICK":
            tick_count += 1
            rounds.append({"tick": tick_count, "line": lineno})
    # If no QUBIT_COORDS, count unique qubit indices across 1q / 2q gates.
    if n_qubits == 0:
        for line in circuit_text.splitlines():
            stripped = line.split("#", 1)[0].strip()
            if not stripped:
                continue
            head, *rest = stripped.split(None, 1)
            body = rest[0] if rest else ""
            tokens = body.replace("(", " ").replace(")", " ").replace(",", " ").split()
            try:
                for t in tokens:
                    idx = int(t)
                    n_qubits = max(n_qubits, idx + 1)
            except ValueError:
                pass
    return {
        "n_qubits": n_qubits,
        "n_ticks": tick_count,
        "instruction_counts": dict(sorted(instructions.items())),
        "rounds_detected": len(rounds),
    }


def tool_stim_circuit_probe(circuit_text: str) -> dict[str, Any]:
    """Parse a small Stim circuit text; return its structure.

    Workbench-free: this tool does not require the Stim package or
    the Workbench app. It accepts the small subset of Stim that the
    reference manual uses in worked examples; for the full Stim
    instruction set, install ``stim`` and use the optional
    direct-wheel path.
    """
    summary = _normalize_stim_circuit(circuit_text)
    return {
        "summary": summary,
        "byte_size": len(circuit_text.encode("utf-8")),
        "note": (
            "Permissive parser for the small Stim subset used in the "
            "reference manual. For full Stim support, install the "
            "``stim`` package and use the optional direct-wheel path."
        ),
        "reference_manual": REF_DOI,
    }


# ---------------------------------------------------------------------------
# Sinter task template
# ---------------------------------------------------------------------------


def tool_sinter_task_template(
    family: str,
    size: int = 5,
    decoder_name: str = "blossom",
    error_rate: float = 0.05,
    shots: int = 1000,
    seed: int = 42,
) -> dict[str, Any]:
    """Generate a sinter task template (manual 17.2).

    Returns a JSON-friendly task description the user can pass to
    ``sinter.collect`` (or any sinter-compatible harness). Does not
    execute the task; the user runs the task separately.
    """
    if family not in FAMILY_FACTORY:
        raise QECTORInputError(
            f"Unknown family {family!r}; choose one of {sorted(FAMILY_FACTORY)}"
        )
    if decoder_name not in DECODER_CLASS_HINTS:
        raise QECTORInputError(
            f"Unknown decoder {decoder_name!r}; choose one of {sorted(DECODER_CLASS_HINTS)}"
        )
    size = _require_integral(size, "size", minimum=2, maximum=MAX_DISTANCE)
    error_rate = _require_probability(error_rate, "error_rate")
    shots = _require_integral(shots, "shots", minimum=1, maximum=MAX_TRIALS)
    seed = _require_integral(seed, "seed", minimum=0)

    code = _code_for_family(family, size)
    matrix = _code_matrix(code)
    logicals = _logical_matrix(code)
    if logicals is None:
        return {
            "family": family,
            "size": int(size),
            "decoder": decoder_name,
            "warning": (
                f"{family!r} does not expose logicals_matrix(); "
                "sinter task can still be generated but the LER will "
                "be undefined (Theorem 2 unavailable)."
            ),
            "task_template": {
                "decoder": f"qector_{decoder_name}",
                "code_family": family,
                "distance": int(size),
                "error_rate": float(error_rate),
                "shots": int(shots),
                "seed": int(seed),
                "decoder_class": DECODER_CLASS_HINTS[decoder_name],
            },
            "matrix_shape": list(matrix.shape),
            "qector_version": QECTOR_VERSION,
            "reference_manual": REF_DOI,
        }
    return {
        "family": family,
        "size": int(size),
        "decoder": decoder_name,
        "task_template": {
            "decoder": f"qector_{decoder_name}",
            "code_family": family,
            "distance": int(size),
            "error_rate": float(error_rate),
            "shots": int(shots),
            "seed": int(seed),
            "decoder_class": DECODER_CLASS_HINTS[decoder_name],
            "n_logicals": int(logicals.shape[0]),
        },
        "matrix_shape": list(matrix.shape),
        "qector_version": QECTOR_VERSION,
        "reference_manual": REF_DOI,
    }


# ---------------------------------------------------------------------------
# Workload hash (manual 22.3 artifact sidecar)
# ---------------------------------------------------------------------------


def tool_workload_hash(
    H_matrix: Sequence[Sequence[int]] | None = None,
    syndrome: Sequence[int] | None = None,
    correction: Sequence[int] | None = None,
) -> dict[str, Any]:
    """Compute a stable SHA-256 over a (H, syndrome, correction) workload.

    Used as the artifact fingerprint for a single decode workload,
    per manual 22.3 (the chapter 22.3 metadata sidecar). The hash
    is content-addressed and stable across runs.
    """
    payload: dict[str, Any] = {}
    # An empty array means "not supplied" (JSON clients cannot always send
    # null), so a syndrome-only or correction-only fingerprint is possible.
    if H_matrix is not None and len(H_matrix) > 0:
        H = _validated_matrix(H_matrix)
        payload["H_shape"] = list(H.shape)
        payload["H_bytes"] = H.tobytes().hex()
    if syndrome is not None and len(syndrome) > 0:
        if not isinstance(syndrome, Sequence) or isinstance(syndrome, (str, bytes)):
            raise QECTORInputError("syndrome must be a sequence of 0/1")
        s = np.asarray(syndrome, dtype=np.uint8)
        if not np.all((s == 0) | (s == 1)):
            raise QECTORInputError("syndrome must contain only 0/1")
        payload["syndrome_bytes"] = s.tobytes().hex()
    if correction is not None and len(correction) > 0:
        if not isinstance(correction, Sequence) or isinstance(correction, (str, bytes)):
            raise QECTORInputError("correction must be a sequence of 0/1")
        c = np.asarray(correction, dtype=np.uint8)
        if not np.all((c == 0) | (c == 1)):
            raise QECTORInputError("correction must contain only 0/1")
        payload["correction_bytes"] = c.tobytes().hex()
    if not payload:
        raise QECTORInputError(
            "at least one non-empty H_matrix, syndrome or correction is required"
        )
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return {
        "sha256": digest,
        "algorithm": "sha256",
        "canonical_json": canonical,
        "workload_keys": sorted(payload.keys()),
        "reference_manual": REF_DOI,
    }


# ---------------------------------------------------------------------------
# Theorem and glossary lookup (manual chapters 3, 8, 9, 10, 11, 12, 13, 15)
# ---------------------------------------------------------------------------


_THEOREMS: dict[int, dict[str, str]] = {
    1: {
        "chapter": "3.1",
        "name": "Syndrome faithfulness and correction validity",
        "statement": (
            "Let H in F2^(m x n), e in F2^n, s = H e (mod 2). Let D be a "
            "decoder returning c in F2^n. Then: (1) if D is syndrome-"
            "faithful, H c = s; (2) H c = s implies c + e in ker(H); "
            "(3) conversely, c + e in ker(H) implies H c = s."
        ),
    },
    2: {
        "chapter": "3.2",
        "name": "Logical error criterion",
        "statement": (
            "Let e, c in F2^n satisfy H c = H e = s, so c + e in ker(H). Decoding is logically correct "
            "iff c + e lies in the span of the stabilizers acting on this sector (im(H_dual^T) for a CSS "
            "code; equal to im(H^T) only for self-dual codes such as Steane); it suffers an uncorrectable "
            "logical error iff L (c + e) != 0 (mod 2), where L is the sector's logical-observable matrix. "
            "QECTOR scores the second form with the wheel's logicals_matrix()."
        ),
    },
    3: {
        "chapter": "3.3",
        "name": "Path-flipping syndrome faithfulness of MWPM",
        "statement": (
            "Let D be the non-empty defect set and M = {(ui, vi)} a "
            "minimum-weight perfect matching on the complete graph over D. "
            "For each pair (u, v) in M, let P_uv be a minimum-weight path. "
            "The correction c = XOR over (u,v) in M of P_uv satisfies "
            "H c = s (mod 2)."
        ),
    },
    4: {
        "chapter": "5.3",
        "name": "Path-flipping guarantee (Blossom)",
        "statement": (
            "With M a minimum-weight perfect matching on K_D and P_uv "
            "minimum-weight decoding-graph paths, the correction c = XOR "
            "of the P_uv satisfies H c = s (mod 2)."
        ),
    },
    5: {
        "chapter": "6.2",
        "name": "Region growth invariant",
        "statement": (
            "Let R(t) be the set of active regions at time t with radii "
            "obeying d y_R / dt in {+1, 0, -1} by state. If all tight edges "
            "are tracked and no dual constraint is violated for t' < t, the "
            "dual solution stays feasible for all t."
        ),
    },
    6: {
        "chapter": "6.4",
        "name": "Tight-edge restriction and complexity",
        "statement": (
            "Let E_tight(t) = {(u,v) : y_u(t) + y_v(t) + sum z_B = w_uv}. "
            "Any MWPM at time t can be chosen inside E_tight(t); exploring "
            "only edges with collision time t* <= t is sufficient for "
            "optimality."
        ),
    },
    7: {
        "chapter": "6.6",
        "name": "Sparse-algorithm correctness",
        "statement": (
            "The event-driven algorithm with states {Growing, Frozen, "
            "Shrinking} and the collision rule returns a minimum-weight "
            "perfect matching on K_D."
        ),
    },
    8: {
        "chapter": "7.1",
        "name": "Cluster parity algebra",
        "statement": (
            "For disjoint clusters C_1, C_2, pi(C_1 union C_2) = pi(C_1) "
            "xor pi(C_2). A cluster is internally satisfiable iff "
            "pi(C) = 0; otherwise it needs a boundary attachment or a "
            "merge with another odd cluster."
        ),
    },
    9: {
        "chapter": "7.3",
        "name": "Peeling correctness",
        "statement": (
            "Peeling a spanning tree of each grown cluster leaf-to-root "
            "produces a correction with H c = s (mod 2)."
        ),
    },
    10: {
        "chapter": "7.3",
        "name": "Union-Find amortized complexity",
        "statement": (
            "For n = |V| + |E| the decoder runs in amortized O(n alpha(n)) "
            "time and O(V + E) space, with no heap allocation in the "
            "steady-state hot path."
        ),
    },
    11: {
        "chapter": "8.2",
        "name": "BP-OSD residual-solve faithfulness",
        "statement": (
            "Let B be a rank-r column basis of H, and let s_eff = s + "
            "H_fixed e_fixed (mod 2) be the residual after fixing the "
            "reliable columns. Then the system H_B e_B = s_eff has a "
            "solution whenever s is reachable, and every OSD candidate "
            "c = e_fixed + (e_B on B, 0 elsewhere) satisfies H c = s."
        ),
    },
    12: {
        "chapter": "9.2",
        "name": "Ambiguity-cluster component-wise faithfulness",
        "statement": (
            "Let c = e_rel xor (xor_k e_k), where each component is "
            "solved with H_{C_k} e_k = s_res restricted to its support. "
            "Then H c = s (mod 2), independently of the threshold tau."
        ),
    },
    13: {
        "chapter": "10.2",
        "name": "Space-time lifting faithfulness",
        "statement": (
            "Let H_ST be the lifted parity-check matrix with data and "
            "measurement columns. A correction c_ST whose boundary in "
            "the detector graph equals d satisfies H_ST c_ST = d (mod 2); "
            "projecting the measurement columns away yields a spatial "
            "correction whose syndrome differs from the final raw round "
            "only by the final-round measurement error term."
        ),
    },
    14: {
        "chapter": "11.1",
        "name": "AutoDecoder dispatch faithfulness",
        "statement": (
            "Let Auto(s) = D_{k(s)}(s) be the dispatch of syndrome s to "
            "the decoder selected by the policy k(s). If every backend "
            "D_i is syndrome-faithful for the problems it is eligible to "
            "decode, and the policy only selects eligible backends, then "
            "Auto(s) satisfies H c = s whenever any eligible backend can "
            "satisfy it."
        ),
    },
    15: {
        "chapter": "12.1",
        "name": "Two-stage CSS sector faithfulness",
        "statement": (
            "If DecodeX and DecodeZ are syndrome-faithful on their "
            "respective inputs, then the combined correction satisfies "
            "H c = s for the joint CSS code."
        ),
    },
    16: {
        "chapter": "13.2",
        "name": "Bit-identity of batch kernels",
        "statement": (
            "For any graphlike code and any syndrome s, the unweighted "
            "batch kernels produce c_GPU(s) = c_CPU(s) bit for bit."
        ),
    },
}


_THEOREM_BOUNDS: tuple[tuple[float, float, str], ...] = (
    (0.0, 0.0, "Wilson 95% score interval for LER (manual 15.2, z = 1.959963985)"),
)


def tool_theorem_lookup(number: int = 1) -> dict[str, Any]:
    """Return the v1.0.0 reference manual theorem statement by number.

    Covers all 16 theorems (manual chapters 3, 5-13). Pure-Python;
    no decode, no I/O.
    """
    n = _require_integral(number, "number", minimum=1, maximum=16)
    th = _THEOREMS.get(n)
    if th is None:
        return {
            "number": n,
            "found": False,
            "available_numbers": sorted(_THEOREMS.keys()),
            "reference_manual": REF_DOI,
        }
    return {
        "number": n,
        "found": True,
        "chapter": th["chapter"],
        "name": th["name"],
        "statement": th["statement"],
        "scope": (
            "Each theorem is normative: a claim that is not explicitly "
            "scoped here is not made. The reference manual is the "
            "authority for the exact statement."
        ),
        "reference_manual": REF_DOI,
    }


_GLOSSARY: dict[str, dict[str, str]] = {
    "syndrome faithfulness": {
        "chapter": "Appendix B",
        "definition": (
            "The property H c = s (mod 2) for reachable syndromes; the "
            "universal correctness gate of the engine. Theorem 1."
        ),
    },
    "mwpm": {
        "chapter": "Appendix B",
        "definition": "Minimum-weight perfect matching; the exact optimization solved by the blossom decoder.",
    },
    "blossom": {
        "chapter": "Appendix B",
        "definition": "An odd cycle of tight edges contracted during Edmonds' algorithm.",
    },
    "graphlike code": {
        "chapter": "Appendix B",
        "definition": "A code in which every qubit participates in at most two checks; matching decoders apply.",
    },
    "hyperedge": {
        "chapter": "Appendix B",
        "definition": "A mechanism touching three or more detectors; requires BP-OSD.",
    },
    "non-graphlike": {
        "chapter": "Appendix B",
        "definition": "Same as hyperedge; Union-Find family decoders reject such codes (manual 20.8).",
    },
    "bp-osd": {
        "chapter": "Appendix B",
        "definition": "Belief propagation followed by ordered-statistics decoding over GF(2).",
    },
    "osd-0": {
        "chapter": "Appendix B",
        "definition": "Basis solve with free bits from BP hard decisions.",
    },
    "osd-w": {
        "chapter": "Appendix B",
        "definition": "OSD-0 plus a combination sweep of width W = max(2 * osd_order, 6).",
    },
    "union-find decoding": {
        "chapter": "Appendix B",
        "definition": "Cluster-growth decoding with spanning-forest peeling.",
    },
    "dem": {
        "chapter": "Appendix B",
        "definition": "Detector error model: the standard description of a decoding problem.",
    },
    "collapse to graph": {
        "chapter": "Appendix B",
        "definition": "Merging parallel mechanisms between the same detector pair into one edge.",
    },
    "logical operator": {
        "chapter": "Appendix B",
        "definition": "An undetectable error (in ker(H)) outside the stabilizer span of its sector, i.e. one with L e != 0 for the sector's logical-observable matrix L; flipping it changes the logical state undetectably. ker(H) \\ im(H^T) is the same set only for self-dual CSS codes.",
    },
    "wilson interval": {
        "chapter": "Appendix B",
        "definition": "A binomial confidence interval with correct coverage at small k. z = 1.959963985.",
    },
    "bit identity": {
        "chapter": "Appendix B",
        "definition": "GPU batch output equal to CPU reference output, bit for bit, on tested configurations. Theorem 16.",
    },
    "cascade": {
        "chapter": "Appendix B",
        "definition": "A cheap faithful pre-filter with an exact fallback.",
    },
    "mcp": {
        "chapter": "Appendix B",
        "definition": "Model Context Protocol; the JSON-RPC stdio server surface.",
    },
    "css code": {
        "chapter": "2.3",
        "definition": (
            "Calderbank-Shor-Steane code with separate X and Z sectors. "
            "The condition Hx Hz^T = 0 (mod 2) is the commutation guarantee."
        ),
    },
    "steane code": {
        "chapter": "2.7",
        "definition": (
            "The [[7,1,3]] CSS code: 7 qubits, 3 weight-4 X-checks, 3 "
            "weight-4 Z-checks, k = 1 logical qubit. The smallest CSS "
            "example for hand verification."
        ),
    },
    "rotated surface code": {
        "chapter": "2.8",
        "definition": (
            "Graphlike 2D surface code on a d x d grid; weight-4 "
            "plaquette checks on the even sublattice plus weight-2 "
            "boundary checks. k = 1 logical qubit (horizontal top-row string)."
        ),
    },
    "toric code": {
        "chapter": "4 (Table 4.1)",
        "definition": (
            "2D code on an L x L torus with 2 L^2 qubits on the edges "
            "and L^2 vertex checks. k = 2 logical qubits."
        ),
    },
    "color code": {
        "chapter": "4 (Table 4.1)",
        "definition": (
            "Triangular 6.6.6 (C2) color code. k = 2 logicals in the planar version."
        ),
    },
    "phi": {
        "chapter": "8.1",
        "definition": (
            "Box-plus kernel phi(x) = -ln(tanh(x/2)) = ln coth(x/2) for x > 0; "
            "phi(0) = +inf; phi(x) -> 0 for large x."
        ),
    },
    "alpha(n)": {
        "chapter": "Appendix A",
        "definition": "Inverse Ackermann function; amortized complexity of union-find with rank + path compression.",
    },
    "lambda": {
        "chapter": "10.3",
        "definition": (
            "Decay factor of the sliding window (0 <= lambda < 1). "
            "Truncation bound: ||S_W - S_inf||_1 <= lambda^W / (1 - lambda) * ||s||_inf."
        ),
    },
    "wilson 95%": {
        "chapter": "15.2",
        "definition": (
            "Wilson 95% score interval: CI = ( p + z^2/(2n) +/- z*sqrt( "
            "p(1-p)/n + z^2/(4n^2) ) ) / (1 + z^2/n) with z = 1.959963985."
        ),
    },
    "tier": {
        "chapter": "18",
        "definition": (
            "License tier: Community (d <= 7), Pro (d <= 19), Enterprise "
            "(d <= 63, GPU / GNN paths)."
        ),
    },
    "tier resolution order": {
        "chapter": "18.1",
        "definition": (
            "QECTOR_LICENSE_KEY -> QECTOR_LICENSE_FILE -> ~/.qector/license.key. "
            "A set-but-unreadable QECTOR_LICENSE_FILE is invalid, not a "
            "silent Community downgrade."
        ),
    },
    "qector-enforce": {
        "chapter": "18.1",
        "definition": "QECTOR_ENFORCE=1 turns tier violations into hard errors; without it, violations log a warning.",
    },
    "screening estimate": {
        "chapter": "19, 27",
        "definition": (
            "A low-trial LER (e.g. 25 trials) is a screening estimate, "
            "not a converged threshold. Always say 'screening estimate' "
            "when the trial count is small."
        ),
    },
}


def tool_glossary_lookup(term: str = "") -> dict[str, Any]:
    """Return a glossary entry from the v1.0.0 reference manual.

    Pure-Python; no decode, no I/O. Covers the v1.0.0 Appendix B
    glossary plus the manual's notation and operational terms.
    """
    if not isinstance(term, str) or not term.strip():
        return {
            "term": term,
            "found": False,
            "available_terms_sample": sorted(_GLOSSARY.keys())[:10],
            "n_terms": len(_GLOSSARY),
            "reference_manual": REF_DOI,
        }
    key = term.strip().lower()
    entry = _GLOSSARY.get(key)
    if entry is None:
        # Fuzzy: substring match
        matches = sorted(k for k in _GLOSSARY.keys() if key in k or k in key)
        return {
            "term": term,
            "found": False,
            "matches": matches,
            "n_terms": len(_GLOSSARY),
            "reference_manual": REF_DOI,
        }
    return {
        "term": term,
        "found": True,
        "chapter": entry["chapter"],
        "definition": entry["definition"],
        "reference_manual": REF_DOI,
    }


_REPRODUCTION_COMMANDS: dict[str, dict[str, Any]] = {
    "d1_build_smoke": {
        "section": "Appendix D.1",
        "title": "Build and import smoke test",
        "command": "python -c \"import qector_decoder_v3; print(qector_decoder_v3.__version__)\"",
        "description": "Validates wheel installation and stable import of qector-decoder-v3==1.0.1 without app dependency.",
    },
    "d2_validation_suite": {
        "section": "Appendix D.2",
        "title": "Validation suite and reference manual obligations",
        "command": "python scripts/run_manual_math_validation.py && python -m unittest discover -s tests -v",
        "description": "Executes the 16 core theorem finite proof obligations and unit validation suite against the live wheel.",
    },
    "d3_focused_correctness": {
        "section": "Appendix D.3",
        "title": "Focused correctness obligations",
        "command": "python -m unittest tests.test_reference_manual_math.TheoremObligationTests -v",
        "description": "Tests specific mathematical assertions: Theorem 1 (syndrome faithfulness), Theorem 2 (coset scoring), Theorems 3-16.",
    },
    "d4_ler_parity": {
        "section": "Appendix D.4",
        "title": "LER parity workflows with 95% Wilson interval",
        "command": "python scripts/run_threshold_sweep.py --family rotated_surface --distances 3 5 --error-rates 0.01 0.05 0.1 --trials 100 --seed 42",
        "description": "Generates a threshold sweep with exact 95% Wilson score intervals (z=1.959963985) and hashed raw artifact sidecars.",
    },
    "d5_gpu_bit_identity": {
        "section": "Appendix D.5",
        "title": "GPU bit-identity verification",
        "command": "python -c \"from qector_decoder_v3 import CUDABatchDecoder, codes; print('CUDA available:', CUDABatchDecoder.is_available())\"",
        "description": "Probes live CUDA batch kernel capability and asserts bit-identical outputs to CPU reference (Theorem 16).",
    },
    "d6_artifact_hashing": {
        "section": "Appendix D.6",
        "title": "Artifact hashing and integrity sidecar",
        "command": "python scripts/qector_runtime_check.py",
        "description": "Generates and checks SHA-256 metadata sidecars matching chapter 22.3 required metadata block.",
    },
}


def tool_reproduction_command_lookup(section: str = "all") -> dict[str, Any]:
    """Return the reproduction commands from Reference Manual Appendix D (D.1-D.6).

    Pure-Python; no decode, no network, no I/O.
    """
    sec = section.strip().lower() if isinstance(section, str) else "all"
    if sec == "all" or not sec:
        return {
            "section": "all",
            "commands": _REPRODUCTION_COMMANDS,
            "reference_manual": REF_DOI,
            "chapters": "Appendix D (D.1 - D.6)",
        }
    matches = {
        k: v
        for k, v in _REPRODUCTION_COMMANDS.items()
        if sec in k.lower() or sec in v["section"].lower() or sec in v["title"].lower()
    }
    if not matches:
        return {
            "section": section,
            "found": False,
            "available_sections": list(_REPRODUCTION_COMMANDS.keys()),
            "reference_manual": REF_DOI,
        }
    return {
        "section": section,
        "found": True,
        "matches": matches,
        "reference_manual": REF_DOI,
    }


def tool_system_setup(
    confirm: bool = False,
    profile: str = "production",
    install_requirements: bool = True,
    create_artifact_dir: bool = True,
    run_validation_test: bool = True,
    offline_wheelhouse: str | None = None,
) -> dict[str, Any]:
    """Guided first-time system setup tool for the QECTOR quantum decoder package.

    Audits and installs all required system dependencies (numpy, qector-decoder-v3,
    mcp SDK, cryptography), creates evidence artifact paths, and validates
    syndrome faithfulness (Theorem 1).

    SAFETY GATE: When confirm=False (the default), performs a complete read-only
    diagnostic probe and outputs planned actions. Setting confirm=True requires
    explicit user approbation before running pip installations or modifying files.
    Package selection is limited to fixed profiles; arbitrary package
    specifications are intentionally not accepted through MCP.
    """
    root_dir = Path(__file__).resolve().parent.parent
    req_file = root_dir / "requirements.txt"
    if not isinstance(profile, str) or profile not in SETUP_PROFILES:
        raise QECTORInputError(
            f"profile must be one of {sorted(SETUP_PROFILES)}"
        )
    packages_to_install = list(SETUP_PROFILES[profile])
    wheelhouse: Path | None = None
    if offline_wheelhouse is not None:
        if not isinstance(offline_wheelhouse, str) or not offline_wheelhouse.strip():
            raise QECTORInputError("offline_wheelhouse must be a non-empty directory path")
        wheelhouse = Path(offline_wheelhouse).expanduser().resolve()
        if not wheelhouse.is_dir():
            raise QECTORInputError(f"offline_wheelhouse is not a directory: {wheelhouse}")
    if install_requirements and wheelhouse is None:
        # Online pip resolution is egress; refuse it in air-gapped mode even
        # on a dry run so the plan never advertises an action it cannot take.
        qector_airgap.require_network(
            "system_setup(install_requirements=true) without offline_wheelhouse"
        )

    # Gather system diagnostics (read-only)
    py_exe = sys.executable
    py_ver = platform.python_version()
    is_venv = sys.prefix != sys.base_prefix
    has_pip = importlib.util.find_spec("pip") is not None
    numpy_ver = _installed_version("numpy")
    qector_ver = _installed_version("qector-decoder-v3")
    mcp_ver = _installed_version("mcp")
    crypto_ver = _installed_version("cryptography")
    # Same root every other tool uses (per-user data dir unless
    # QECTOR_ARTIFACT_DIR names a real directory; unexpanded ${...} ignored).
    artifact_dir = _artifact_root()

    diagnostics = {
        "python_executable": py_exe,
        "python_version": py_ver,
        "virtual_env": is_venv,
        "pip_available": has_pip,
        "installed_versions": {
            "numpy": numpy_ver,
            "qector_decoder_v3": qector_ver,
            "mcp": mcp_ver,
            "cryptography": crypto_ver,
        },
        "setup_profile": profile,
        "approved_packages": packages_to_install,
        "requirements_file_present": req_file.is_file(),
        "artifact_directory": str(artifact_dir),
        "license_environment": {
            "QECTOR_LICENSE_KEY": bool(os.environ.get("QECTOR_LICENSE_KEY")),
            "QECTOR_LICENSE_FILE": os.environ.get("QECTOR_LICENSE_FILE", "unset"),
            "QECTOR_SILENT": os.environ.get("QECTOR_SILENT", "1"),
        },
    }

    actions_planned: list[str] = []
    if install_requirements:
        actions_planned.append(
            f"Install/verify packages: {', '.join(packages_to_install)}"
            + (f" from offline wheelhouse {wheelhouse}" if wheelhouse else " from the configured package index")
        )
    if create_artifact_dir:
        actions_planned.append(f"Ensure artifact directory exists: {artifact_dir}")
    if run_validation_test:
        actions_planned.append(
            "Execute in-process decoder syndrome faithfulness self-check (H c = s)"
        )

    if not confirm:
        return {
            "status": "dry_run_pending_approval",
            "user_approbation_required": True,
            "user_approbation_granted": False,
            "confirmation_message": (
                "SAFETY GATE: Dry-run probe complete. No changes were made to your system. "
                "To execute the planned installation actions with user approbation, re-run "
                "system_setup with confirm=True."
            ),
            "actions_planned": actions_planned,
            "diagnostics": diagnostics,
            "network_policy": qector_airgap.network_policy(),
            "reference_manual": REF_DOI,
        }

    # User approbation granted (confirm == True)
    actions_executed: list[dict[str, Any]] = []

    # 1. Install requirements
    if install_requirements and has_pip:
        install_cmd = [py_exe, "-m", "pip", "install"]
        if wheelhouse is not None:
            install_cmd.extend(["--no-index", "--find-links", str(wheelhouse)])
        if profile == "production" and req_file.is_file():
            install_cmd.extend(["-r", str(req_file)])
        else:
            install_cmd.extend(packages_to_install)
        try:
            p = subprocess.run(
                install_cmd,
                capture_output=True,
                text=True,
                timeout=120,
                cwd=str(root_dir),
            )
            actions_executed.append(
                {
                    "action": "pip_install",
                    "command": " ".join(install_cmd),
                    "success": p.returncode == 0,
                    "stdout_snippet": p.stdout[-300:] if p.stdout else "",
                    "stderr_snippet": p.stderr[-300:] if p.stderr else "",
                }
            )
        except Exception as exc:
            actions_executed.append(
                {
                    "action": "pip_install",
                    "success": False,
                    "error": str(exc),
                }
            )

    # 2. Create artifact directory
    if create_artifact_dir:
        try:
            artifact_dir.mkdir(parents=True, exist_ok=True)
            test_file = artifact_dir / ".write_test.tmp"
            test_file.write_text("ok", encoding="utf-8")
            test_file.unlink()
            actions_executed.append(
                {
                    "action": "create_artifact_directory",
                    "path": str(artifact_dir),
                    "success": True,
                }
            )
        except Exception as exc:
            actions_executed.append(
                {
                    "action": "create_artifact_directory",
                    "path": str(artifact_dir),
                    "success": False,
                    "error": str(exc),
                }
            )

    # 3. In-process validation self-test
    validation_result: dict[str, Any] = {"passed": False}
    if run_validation_test:
        try:
            import qector_decoder_v3 as qd
            from qector_decoder_v3 import BlossomDecoder, codes

            code = codes.repetition_code(5)
            matrix = np.asarray(code.parity_check_matrix(), dtype=np.uint8)
            syndrome = np.array([1, 0, 0, 1], dtype=np.uint8)
            decoder = BlossomDecoder(code.check_to_qubits, n_qubits=code.n_qubits)
            correction = np.asarray(decoder.decode(syndrome), dtype=np.uint8)
            calculated_syndrome = (
                matrix.astype(np.int64) @ correction.astype(np.int64)
            ) % 2
            is_faithful = np.array_equal(
                calculated_syndrome.astype(np.uint8), syndrome
            )
            validation_result = {
                "passed": is_faithful,
                "decoder_used": "BlossomDecoder",
                "family": "repetition",
                "distance": 5,
                "theorem_1_syndrome_faithful": is_faithful,
                "qector_version": getattr(qd, "__version__", "unknown"),
            }
            actions_executed.append(
                {
                    "action": "in_process_validation_test",
                    "success": is_faithful,
                    "details": validation_result,
                }
            )
        except Exception as exc:
            validation_result = {"passed": False, "error": str(exc)}
            actions_executed.append(
                {
                    "action": "in_process_validation_test",
                    "success": False,
                    "error": str(exc),
                }
            )

    return {
        "status": "ready" if validation_result.get("passed", False) else "configured",
        "user_approbation_required": True,
        "user_approbation_granted": True,
        "actions_planned": actions_planned,
        "actions_executed": actions_executed,
        "diagnostics": diagnostics,
        "validation_result": validation_result,
        "network_policy": qector_airgap.network_policy(),
        "reference_manual": REF_DOI,
    }


def tool_configure_claude_desktop(
    confirm: bool = False,
    remove: bool = False,
    python_path: str | None = None,
) -> dict[str, Any]:
    """Automated connector to configure both QECTOR MCP servers in Claude Desktop.

    Reads %APPDATA%\\Claude\\claude_desktop_config.json on Windows, creates a timestamped
    backup, and safely registers 'qector-library' (8 tools) by default. Research
    and admin servers are opt-in flags on the installer, with an explicit Python
    executable path and forward-slash path normalization.

    SAFETY GATE: When confirm=False (the default), performs a read-only dry run inspection.
    Set confirm=True to write configuration changes to Claude Desktop.
    """
    scripts_dir = Path(__file__).resolve().parent.parent / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    try:
        from configure_claude_desktop import configure_desktop
        res = configure_desktop(dry_run=not confirm, remove=remove, custom_python=python_path)
        res["reference_manual"] = REF_DOI
        return res
    except Exception as exc:
        return {
            "status": "error",
            "message": f"Failed to run desktop configuration: {exc}",
            "reference_manual": REF_DOI,
        }


# ---------------------------------------------------------------------------
# Evidence layer (Provisional)
# ---------------------------------------------------------------------------


def tool_get_capability_matrix() -> dict[str, Any]:
    """Return the static capability matrix for the QECTOR MCP surfaces.

    A *capability* is a coarse-grained feature an agent can request from a
    server. It is not a single tool name; the matrix maps the major QECTOR
    workflows (decode, build code, sweep, license, evidence lookup) onto
    the servers that actually serve them, including the trust-zone each
    surface lives in. Agents use this to choose the right surface for a
    job instead of guessing tool names by topic.
    """
    tools_by_server: dict[str, list[str]] = {
        "qector-library": [
            "list_code_families",
            "list_decoders",
            "get_license_info",
            "decode_syndrome",
            "decode_single",
            "threshold_sweep",
            "build_code_from_matrix",
            "compat_report",
        ],
    }
    # Build the bench tools list from the actual TOOL_FUNCTIONS dict at
    # call time, so adding a new research tool updates the matrix without
    # touching this function. Drop the admin tools that are filtered out
    # of the public surface.
    tools_by_server["qector-research"] = sorted(
        name
        for name in TOOL_FUNCTIONS
        if name not in ADMIN_TOOL_NAMES
    )
    capabilities = [
        {
            "capability": "decode_verified",
            "servers": ["qector-library"],
            "tools": ["decode_syndrome", "decode_single"],
            "stability": "stable",
            "verification": "runtime",
            "notes": "H c = s (mod 2) is verified before the result is returned.",
        },
        {
            "capability": "build_code",
            "servers": ["qector-library"],
            "tools": ["build_code_from_matrix"],
            "stability": "stable",
            "verification": "runtime",
            "notes": "Matrix is validated against MAX_CHECKS, MAX_QUBITS, and graphlike eligibility.",
        },
        {
            "capability": "threshold_sweep",
            "servers": ["qector-library"],
            "tools": ["threshold_sweep"],
            "stability": "stable",
            "verification": "runtime",
            "notes": "Returns a Wilson 95% interval and a hashed raw artifact.",
        },
        {
            "capability": "license_inspection",
            "servers": ["qector-library"],
            "tools": ["get_license_info"],
            "stability": "stable",
            "verification": "runtime",
            "notes": "Reads the live offline license tier, distance limits, and gates.",
        },
        {
            "capability": "code_family_discovery",
            "servers": ["qector-library"],
            "tools": ["list_code_families", "list_decoders"],
            "stability": "stable",
            "verification": "runtime",
            "notes": "Reports the families and decoders the live wheel exposes.",
        },
        {
            "capability": "runtime_compatibility",
            "servers": ["qector-library", "qector-research"],
            "tools": ["compat_report", "env_block"],
            "stability": "stable",
            "verification": "runtime",
            "notes": "PyPI freshness is opt-in (check_pypi=true); default path stays offline.",
        },
        {
            "capability": "reference_lookup",
            "servers": ["qector-research"],
            "tools": ["theorem_lookup", "glossary_lookup", "reproduction_command_lookup"],
            "stability": "provisional",
            "verification": "reference_only",
            "notes": "Pure-Python reference manual lookups; no decoder, no I/O.",
        },
        {
            "capability": "wilson_methodology",
            "servers": ["qector-research"],
            "tools": ["wilson_ci", "wilson_table", "logical_coset_score"],
            "stability": "provisional",
            "verification": "runtime",
            "notes": "Math utilities for the library server's threshold_sweep output.",
        },
        {
            "capability": "dem_pipeline",
            "servers": ["qector-research"],
            "tools": ["dem_inspect", "dem_collapse_parallel"],
            "stability": "provisional",
            "verification": "runtime",
            "notes": "Minimal Stim-style DEM parsing and collapse-rule application.",
        },
        {
            "capability": "code_introspection",
            "servers": ["qector-research"],
            "tools": [
                "code_family_info",
                "code_export_matrices",
                "code_logicals_inspect",
                "code_distance_check",
            ],
            "stability": "provisional",
            "verification": "runtime",
            "notes": "Structural inspection of every code family registered in the wheel.",
        },
        {
            "capability": "ecosystem_compatibility",
            "servers": ["qector-research"],
            "tools": [
                "pymatching_compat_check",
                "sinter_decoder_list",
                "qiskit_plugin_check",
            ],
            "stability": "provisional",
            "verification": "runtime",
            "notes": "Drop-in shim smoke tests and entry-point listing.",
        },
        {
            "capability": "hardware_probe",
            "servers": ["qector-research"],
            "tools": ["hardware_probe"],
            "stability": "provisional",
            "verification": "machine_scoped_measurement",
            "notes": "Local probe; never a portable performance claim.",
        },
        {
            "capability": "evidence_artifacts",
            "servers": ["qector-research"],
            "tools": [
                "artifacts_sha256",
                "artifact_metadata_check",
                "decode_faithfulness_check",
            ],
            "stability": "provisional",
            "verification": "runtime",
            "notes": "SHA-256 hashing is constrained to QECTOR_ARTIFACT_DIR.",
        },
        {
            "capability": "micro_benchmark",
            "servers": ["qector-research"],
            "tools": ["hot_path_microbench", "stim_circuit_probe", "sinter_task_template", "workload_hash"],
            "stability": "provisional",
            "verification": "machine_scoped_measurement",
            "notes": "Per-machine measurements; never portable claims.",
        },
        {
            "capability": "evidence_layer",
            "servers": ["qector-research"],
            "tools": [
                "get_capability_matrix",
                "get_evidence_policy",
                "get_runtime_provenance",
            ],
            "stability": "provisional",
            "verification": "metadata",
            "notes": "Self-describing evidence layer. Read-only; no decoder, no I/O.",
        },
    ]
    return {
        "matrix_version": "1.0.0",
        "servers": {
            "qector-library": {
                "stability": "stable",
                "default_enabled": True,
                "tools": tools_by_server["qector-library"],
                "n_tools": len(tools_by_server["qector-library"]),
            },
            "qector-research": {
                "stability": "provisional",
                "default_enabled": False,
                "tools": tools_by_server["qector-research"],
                "n_tools": len(tools_by_server["qector-research"]),
            },
            "qector-admin": {
                "stability": "admin",
                "default_enabled": False,
                "tools": sorted(ADMIN_TOOL_NAMES),
                "n_tools": len(ADMIN_TOOL_NAMES),
                "note": (
                    "Disabled unless QECTOR_ADMIN_ENABLED=1 is set in the server "
                    "environment; every call requires confirm=true."
                ),
            },
        },
        "capabilities": capabilities,
        "n_capabilities": len(capabilities),
        "reference_manual": REF_DOI,
    }


def tool_get_evidence_policy() -> dict[str, Any]:
    """Return the published QECTOR evidence / verification policy.

    The policy is the same one enforced by the QECTORToolResult envelope in
    ``qector_mcp_contract.py``; this tool is the human-readable, agent-readable
    declaration of what every result means and the *minimum* checks an agent
    must perform before claiming a result is verified, measured, or
    reference-only.
    """
    return {
        "policy_version": "1.0.0",
        "result_statuses": [
            {
                "status": "verified",
                "claim_class": "runtime_verified",
                "meaning": (
                    "The result was produced by running the published decoder "
                    "locally and the H c = s (mod 2) gate (Theorem 1) passed."
                ),
            },
            {
                "status": "measured",
                "claim_class": "machine_scoped_measurement",
                "meaning": (
                    "The result is a per-machine, per-workload, per-build "
                    "measurement. It is NEVER a portable performance claim."
                ),
            },
            {
                "status": "reference_only",
                "claim_class": "reference_only",
                "meaning": (
                    "The result was looked up from the bundled reference manual; "
                    "no decoder was executed and no I/O occurred."
                ),
            },
            {
                "status": "not_checked",
                "claim_class": "metadata_or_unverified",
                "meaning": (
                    "The tool did not perform a mathematical verification. The "
                    "agent must not infer a verified or measured result from this."
                ),
            },
            {
                "status": "error",
                "claim_class": "verification_failed",
                "meaning": (
                    "The tool returned a stable error code. The agent must not "
                    "continue past this point without surfacing the error code."
                ),
            },
        ],
        "stable_error_codes": [
            "INVALID_INPUT",
            "RESOURCE_LIMIT",
            "LICENSE_DENIED",
            "BACKEND_UNAVAILABLE",
            "DEPENDENCY_MISSING",
            "VERIFICATION_FAILED",
            "IO_ERROR",
            "NETWORK_DISABLED",
            "NETWORK_REQUIRED",
            "PERMISSION_DENIED",
            "PROTOCOL_ERROR",
            "RUNTIME_ERROR",
        ],
        "agent_must": [
            "Prefer live MCP/runtime evidence over reference text.",
            "Treat 'measured' as a single-machine datapoint, not a portable claim.",
            "Never collapse 'not_checked' to 'verified'.",
            "Never collapse 'reference_only' to 'runtime capability'.",
            "Surface the stable error code and the tool name together.",
        ],
        "agent_must_not": [
            "Infer a runtime capability from a reference-manual statement.",
            "Publish a benchmark number without a fresh device-local artifact.",
            "Conceal a skipped test or a not_checked result.",
            "Use 'verified' without an explicit verification.checks entry.",
            "Loop threshold_sweep, decode_single, build_code_from_matrix, or admin tools past the per-process call budget.",
        ],
        "reference_manual": REF_DOI,
    }


def tool_get_runtime_provenance(check_pypi: bool = False) -> dict[str, Any]:
    """Return the live runtime provenance block for this server process.

    Always reports the local environment; opt-in PyPI freshness via
    ``check_pypi=true`` (a single HTTPS request to PyPI, cached for the
    lifetime of the process). The block is the same shape the bench server
    uses for hot_path_microbench artifacts, so an agent can compare runs
    with confidence.
    """
    provenance: dict[str, Any] = {
        "server": SERVER_NAME,
        "server_version": SERVER_VERSION,
        "qector_decoder_v3": QECTOR_VERSION,
        "qector_decoder_v3_present": qector_decoder_v3 is not None,
        "mcp_protocol": WORKBENCH_PROTOCOL_VERSION,
        "mcp_sdk": _installed_version("mcp"),
        "environment": _env_block(),
        "stability": "provisional",
        "reference_manual": REF_DOI,
    }
    provenance["pypi_freshness"] = _pypi_block(check_pypi)
    return provenance


# ---------------------------------------------------------------------------
# Tool dispatch
# ---------------------------------------------------------------------------

TOOL_FUNCTIONS: dict[str, Callable[..., Any]] = {
    "wilson_ci": tool_wilson_ci,
    "wilson_table": tool_wilson_table,
    "logical_coset_score": tool_logical_coset_score,
    "dem_inspect": tool_dem_inspect,
    "dem_collapse_parallel": tool_dem_collapse_parallel,
    "code_family_info": tool_code_family_info,
    "code_export_matrices": tool_code_export_matrices,
    "code_logicals_inspect": tool_code_logicals_inspect,
    "code_distance_check": tool_code_distance_check,
    "pymatching_compat_check": tool_pymatching_compat_check,
    "sinter_decoder_list": tool_sinter_decoder_list,
    "qiskit_plugin_check": tool_qiskit_plugin_check,
    "hardware_probe": tool_hardware_probe,
    "license_active_check": tool_license_active_check,
    "env_block": tool_env_block,
    "compat_report": tool_compat_report,
    "artifacts_sha256": tool_artifacts_sha256,
    "artifact_metadata_check": tool_artifact_metadata_check,
    "decode_faithfulness_check": tool_decode_faithfulness_check,
    "hot_path_microbench": tool_hot_path_microbench,
    "stim_circuit_probe": tool_stim_circuit_probe,
    "sinter_task_template": tool_sinter_task_template,
    "workload_hash": tool_workload_hash,
    "theorem_lookup": tool_theorem_lookup,
    "glossary_lookup": tool_glossary_lookup,
    "reproduction_command_lookup": tool_reproduction_command_lookup,
    "get_capability_matrix": tool_get_capability_matrix,
    "get_evidence_policy": tool_get_evidence_policy,
    "get_runtime_provenance": tool_get_runtime_provenance,
}


TOOL_DEFAULTS: dict[str, dict[str, Any]] = {
    "wilson_ci": {"k": 10, "n": 1000, "z": Z95},
    "wilson_table": {"n": 1000, "k_list": [0, 1, 5, 10, 50, 100], "z": Z95},
    "logical_coset_score": {},
    "dem_inspect": {},
    "dem_collapse_parallel": {"observable_rule": "most_likely"},
    "code_family_info": {"family": "rotated_surface", "size": 5},
    "code_export_matrices": {
        "family": "rotated_surface",
        "size": 5,
        "include_logicals": True,
    },
    "code_logicals_inspect": {"family": "rotated_surface", "size": 5},
    "code_distance_check": {"family": "rotated_surface", "size": 5},
    "pymatching_compat_check": {"family": "rotated_surface", "size": 5},
    "sinter_decoder_list": {},
    "qiskit_plugin_check": {},
    "hardware_probe": {},
    "license_active_check": {},
    "env_block": {"check_pypi": False},
    "compat_report": {"check_pypi": False},
    "artifacts_sha256": {"paths": []},
    "artifact_metadata_check": {
        "family": "rotated_surface",
        "size": 5,
        "decoder_name": "blossom",
        "trials": 100,
        "error_rates": [0.01, 0.05, 0.1],
        "seed": 42,
        "artifact_path": None,
    },
    "decode_faithfulness_check": {"H_matrix": [], "syndrome": [], "correction": []},
    "hot_path_microbench": {
        "family": "rotated_surface",
        "size": 5,
        "shots": 64,
        "decoder_name": "blossom",
        "seed": 42,
    },
    "stim_circuit_probe": {"circuit_text": ""},
    "sinter_task_template": {
        "family": "rotated_surface",
        "size": 5,
        "decoder_name": "blossom",
        "error_rate": 0.05,
        "shots": 1000,
        "seed": 42,
    },
    "workload_hash": {"H_matrix": None, "syndrome": None, "correction": None},
    "theorem_lookup": {"number": 1},
    "glossary_lookup": {"term": ""},
    "reproduction_command_lookup": {"section": "all"},
    "get_capability_matrix": {},
    "get_evidence_policy": {},
    "get_runtime_provenance": {"check_pypi": False},
}


def _merged_arguments(name: str, arguments: Mapping[str, Any] | None) -> dict[str, Any]:
    if name not in TOOL_FUNCTIONS:
        raise QECTORInputError(
            f"Unknown tool {name!r}; choose one of {sorted(TOOL_FUNCTIONS)}"
        )
    merged = dict(TOOL_DEFAULTS[name])
    if arguments:
        merged.update(dict(arguments))
    return merged


def dispatch_tool(
    name: str, arguments: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    function = TOOL_FUNCTIONS.get(name)
    if function is None:
        raise QECTORInputError(
            f"Unknown tool {name!r}; choose one of {sorted(TOOL_FUNCTIONS)}"
        )
    consume_call_budget(name)
    try:
        return function(**_merged_arguments(name, arguments))
    except (QECTORInputError, QECTORUnsupportedError):
        refund_call_budget(name)
        raise


def _tool_schema() -> list[Any]:
    return [
        make_tool(
            name="wilson_ci",
            description="Wilson 95% score interval (manual 15.2). k, n, optional z.",
            input_schema={
                "type": "object",
                "properties": {
                    "k": {"type": "integer", "minimum": 0, "default": 10},
                    "n": {"type": "integer", "minimum": 1, "default": 1000},
                    "z": {"type": "number", "exclusiveMinimum": 0, "default": Z95},
                },
                "additionalProperties": False,
            },
        ),
        make_tool(
            name="wilson_table",
            description="Batch Wilson 95% CI table for a series of k values at fixed n.",
            input_schema={
                "type": "object",
                "properties": {
                    "n": {"type": "integer", "minimum": 1, "default": 1000},
                    "k_list": {
                        "type": "array",
                        "items": {"type": "integer", "minimum": 0},
                        "default": [0, 1, 5, 10, 50, 100],
                    },
                    "z": {"type": "number", "exclusiveMinimum": 0, "default": Z95},
                },
                "additionalProperties": False,
            },
        ),
        make_tool(
            name="logical_coset_score",
            description="Score a batch of (predicted, sampled) logical observables on the logical coset (Theorem 2).",
            input_schema={
                "type": "object",
                "properties": {
                    "predicted_logicals": {
                        "type": "array",
                        "items": {
                            "type": "array",
                            "items": {"type": "integer", "enum": [0, 1]},
                        },
                    },
                    "sampled_logicals": {
                        "type": "array",
                        "items": {
                            "type": "array",
                            "items": {"type": "integer", "enum": [0, 1]},
                        },
                    },
                },
                "required": ["predicted_logicals", "sampled_logicals"],
                "additionalProperties": False,
            },
        ),
        make_tool(
            name="dem_inspect",
            description="Parse a minimal Stim-style DEM text; report structure, weight histogram, and routing hint (manual 14).",
            input_schema={
                "type": "object",
                "properties": {
                    "dem_text": {"type": "string"},
                },
                "required": ["dem_text"],
                "additionalProperties": False,
            },
        ),
        make_tool(
            name="dem_collapse_parallel",
            description="Apply the manual 14.1 collapse rule to a DEM; report collapsed graph edges and the worked-example sanity check.",
            input_schema={
                "type": "object",
                "properties": {
                    "dem_text": {"type": "string"},
                    "observable_rule": {
                        "type": "string",
                        "enum": ["most_likely", "union", "first"],
                        "default": "most_likely",
                    },
                },
                "required": ["dem_text"],
                "additionalProperties": False,
            },
        ),
        make_tool(
            name="code_family_info",
            description="Return live structural info about a code family at a given size (manual 4).",
            input_schema={
                "type": "object",
                "properties": {
                    "family": {
                        "type": "string",
                        "enum": sorted(FAMILY_FACTORY),
                        "default": "rotated_surface",
                    },
                    "size": {"type": "integer", "minimum": 2, "default": 5},
                },
                "required": ["family", "size"],
                "additionalProperties": False,
            },
        ),
        make_tool(
            name="code_export_matrices",
            description="Export a code's parity_check_matrix, logicals_matrix, and check_to_qubits in JSON form (manual 16.1).",
            input_schema={
                "type": "object",
                "properties": {
                    "family": {
                        "type": "string",
                        "enum": sorted(FAMILY_FACTORY) + ["custom"],
                        "default": "rotated_surface",
                    },
                    "size": {"type": "integer", "minimum": 2, "default": 5},
                    "H_matrix": {
                        "type": "array",
                        "items": {
                            "type": "array",
                            "items": {"type": "integer", "enum": [0, 1]},
                        },
                    },
                    "include_logicals": {"type": "boolean", "default": True},
                },
                "required": ["family", "size"],
                "additionalProperties": False,
            },
        ),
        make_tool(
            name="code_logicals_inspect",
            description="Return a code's logical observables or a clear statement that logical scoring is unavailable (manual 3.2 / 16.1).",
            input_schema={
                "type": "object",
                "properties": {
                    "family": {
                        "type": "string",
                        "enum": sorted(FAMILY_FACTORY),
                        "default": "rotated_surface",
                    },
                    "size": {"type": "integer", "minimum": 2, "default": 5},
                },
                "required": ["family", "size"],
                "additionalProperties": False,
            },
        ),
        make_tool(
            name="code_distance_check",
            description="Return the documented distance and structure for a code at a given size (manual 16.1).",
            input_schema={
                "type": "object",
                "properties": {
                    "family": {
                        "type": "string",
                        "enum": sorted(FAMILY_FACTORY),
                        "default": "rotated_surface",
                    },
                    "size": {"type": "integer", "minimum": 2, "default": 5},
                },
                "required": ["family", "size"],
                "additionalProperties": False,
            },
        ),
        make_tool(
            name="pymatching_compat_check",
            description="Smoke-test a QECTOR code against a pymatching.Matching pipeline; report bitwise correction agreement (manual 17.1).",
            input_schema={
                "type": "object",
                "properties": {
                    "family": {
                        "type": "string",
                        "enum": sorted(FAMILY_FACTORY),
                        "default": "rotated_surface",
                    },
                    "size": {"type": "integer", "minimum": 2, "default": 5},
                },
                "required": ["family", "size"],
                "additionalProperties": False,
            },
        ),
        make_tool(
            name="sinter_decoder_list",
            description="List the sinter decoder entry points exposed by the wheel (manual 17.2).",
            input_schema={
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        ),
        make_tool(
            name="qiskit_plugin_check",
            description="Probe the optional Qiskit plugin (manual 17.3).",
            input_schema={
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        ),
        make_tool(
            name="hardware_probe",
            description="Live probe of CUDA / OpenCL availability and license tier (manual 18, no assumptions).",
            input_schema={
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        ),
        make_tool(
            name="license_active_check",
            description="Read the live offline license tier and feature gates (manual 18.1).",
            input_schema={
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        ),
        make_tool(
            name="env_block",
            description=(
                "Return the environment block (manual 22.3). Set "
                "check_pypi=true to also query PyPI for a newer "
                "qector-decoder-v3 release (single outbound HTTPS call, "
                "cached for the process lifetime); default stays fully offline."
            ),
            input_schema={
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
        make_tool(
            name="compat_report",
            description=(
                "Bench-server compatibility report: numpy / mcp SDK / "
                "qector-decoder-v3 / pymatching-compat availability, plus "
                "the Provisional-surface boundary map. Companion to the "
                "library server's compat_report. Set check_pypi=true to "
                "also query PyPI for a newer qector-decoder-v3 release "
                "(single outbound HTTPS call, cached for the process "
                "lifetime); default stays fully offline."
            ),
            input_schema={
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
        make_tool(
            name="artifacts_sha256",
            description="Compute SHA-256 of one or more files for the chapter 22.3 metadata sidecar.",
            input_schema={
                "type": "object",
                "properties": {
                    "paths": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": ["paths"],
                "additionalProperties": False,
            },
        ),
        make_tool(
            name="artifact_metadata_check",
            description="Check a threshold_sweep artifact's chapter 22.3 required metadata and .sha256 sidecar (artifact_path), or emit the template it must carry.",
            input_schema={
                "type": "object",
                "properties": {
                    "family": {
                        "type": "string",
                        "enum": sorted(FAMILY_FACTORY),
                        "default": "rotated_surface",
                    },
                    "size": {"type": "integer", "minimum": 2, "default": 5},
                    "decoder_name": {
                        "type": "string",
                        "enum": sorted(DECODER_CLASS_HINTS),
                        "default": "blossom",
                    },
                    "trials": {"type": "integer", "minimum": 1, "default": 100},
                    "error_rates": {
                        "type": "array",
                        "items": {"type": "number", "minimum": 0, "maximum": 1},
                        "default": [0.01, 0.05, 0.1],
                    },
                    "seed": {"type": "integer", "minimum": 0, "default": 42},
                    "artifact_path": {
                        "type": ["string", "null"],
                        "default": None,
                        "description": "A .json artifact inside QECTOR_ARTIFACT_DIR to check; omit for the template.",
                    },
                },
                "additionalProperties": False,
            },
        ),
        make_tool(
            name="decode_faithfulness_check",
            description="Re-verify the H c = s (mod 2) gate (Theorem 1) externally.",
            input_schema={
                "type": "object",
                "properties": {
                    "H_matrix": {
                        "type": "array",
                        "items": {
                            "type": "array",
                            "items": {"type": "integer", "enum": [0, 1]},
                        },
                    },
                    "syndrome": {
                        "type": "array",
                        "items": {"type": "integer", "enum": [0, 1]},
                    },
                    "correction": {
                        "type": "array",
                        "items": {"type": "integer", "enum": [0, 1]},
                    },
                },
                "required": ["H_matrix", "syndrome", "correction"],
                "additionalProperties": False,
            },
        ),
        make_tool(
            name="hot_path_microbench",
            description="Per-machine hot-path latency sample; never a portable claim (manual 22.5).",
            input_schema={
                "type": "object",
                "properties": {
                    "family": {
                        "type": "string",
                        "enum": sorted(FAMILY_FACTORY),
                        "default": "rotated_surface",
                    },
                    "size": {"type": "integer", "minimum": 2, "default": 5},
                    "shots": {"type": "integer", "minimum": 1, "default": 64},
                    "decoder_name": {
                        "type": "string",
                        "enum": sorted(DECODER_CLASS_HINTS),
                        "default": "blossom",
                    },
                    "seed": {"type": "integer", "minimum": 0, "default": 42},
                },
                "additionalProperties": False,
            },
        ),
        make_tool(
            name="stim_circuit_probe",
            description=(
                "Parse a small Stim circuit text; return its structure "
                "(n_qubits, ticks, instruction counts). Permissive "
                "parser for the subset used in the reference manual. "
                "Workbench-free; does not require the Stim package."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "circuit_text": {"type": "string"},
                },
                "required": ["circuit_text"],
                "additionalProperties": False,
            },
        ),
        make_tool(
            name="sinter_task_template",
            description=(
                "Generate a sinter task template (manual 17.2) for a "
                "code / decoder / error rate. Returns a JSON-friendly "
                "task; does not execute the task."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "family": {
                        "type": "string",
                        "enum": sorted(FAMILY_FACTORY),
                        "default": "rotated_surface",
                    },
                    "size": {"type": "integer", "minimum": 2, "default": 5},
                    "decoder_name": {
                        "type": "string",
                        "enum": sorted(DECODER_CLASS_HINTS),
                        "default": "blossom",
                    },
                    "error_rate": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                        "default": 0.05,
                    },
                    "shots": {"type": "integer", "minimum": 1, "default": 1000},
                    "seed": {"type": "integer", "minimum": 0, "default": 42},
                },
                "required": ["family"],
                "additionalProperties": False,
            },
        ),
        make_tool(
            name="workload_hash",
            description=(
                "Compute a stable SHA-256 over a (H, syndrome, "
                "correction) workload (manual 22.3 artifact sidecar)."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "H_matrix": {
                        "type": "array",
                        "items": {
                            "type": "array",
                            "items": {"type": "integer", "enum": [0, 1]},
                        },
                    },
                    "syndrome": {
                        "type": "array",
                        "items": {"type": "integer", "enum": [0, 1]},
                    },
                    "correction": {
                        "type": "array",
                        "items": {"type": "integer", "enum": [0, 1]},
                    },
                },
                "additionalProperties": False,
            },
        ),
        make_tool(
            name="theorem_lookup",
            description=(
                "Return the v1.0.0 reference manual theorem statement by "
                "number (1-16). Pure-Python; no decode, no I/O."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "number": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 16,
                        "default": 1,
                    },
                },
                "required": ["number"],
                "additionalProperties": False,
            },
        ),
        make_tool(
            name="glossary_lookup",
            description=(
                "Return a v1.0.0 reference manual glossary entry. "
                "Covers the Appendix B glossary and the manual's "
                "operational terms. Pure-Python; no decode, no I/O."
            ),
            input_schema={
                "type": "object",
                "properties": {
                    "term": {"type": "string"},
                },
                "required": ["term"],
                "additionalProperties": False,
            },
        ),
        make_tool(
            name="reproduction_command_lookup",
            description="Return reproduction commands from Reference Manual Appendix D (D.1-D.6). Pure-Python; no decode, no I/O.",
            input_schema={
                "type": "object",
                "properties": {
                    "section": {
                        "type": "string",
                        "enum": [
                            "all",
                            "smoke",
                            "validation",
                            "correctness",
                            "ler",
                            "gpu",
                            "hash",
                            "d1_build_smoke",
                            "d2_validation_suite",
                            "d3_focused_correctness",
                            "d4_ler_parity",
                            "d5_gpu_bit_identity",
                            "d6_artifact_hashing",
                        ],
                        "default": "all",
                        "description": "Appendix D section name or 'all'.",
                    },
                },
                "additionalProperties": False,
            },
        ),
        make_tool(
            name="get_capability_matrix",
            description=(
                "Return the static capability matrix for the QECTOR MCP surfaces. "
                "Maps coarse-grained workflows (decode, build code, threshold, "
                "evidence lookup, ...) onto the servers that actually serve them, "
                "including the trust zone each surface lives in. Read-only; no "
                "decoder, no I/O."
            ),
            input_schema={
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        ),
        make_tool(
            name="get_evidence_policy",
            description=(
                "Return the published QECTOR evidence / verification policy: the "
                "meaning of every result status, the closed list of stable error "
                "codes, and the agent must / must-not rules. Read-only; no decoder, "
                "no I/O."
            ),
            input_schema={
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        ),
        make_tool(
            name="get_runtime_provenance",
            description=(
                "Return the live runtime provenance block for this server process. "
                "Includes the local environment, the negotiated MCP protocol, the "
                "QECTOR decoder version, and an opt-in PyPI freshness field. PyPI "
                "is contacted only when check_pypi=true; default path stays fully "
                "offline."
            ),
            input_schema={
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


TOOLS = apply_tool_contract(
    [tool for tool in _tool_schema() if tool.name not in ADMIN_TOOL_NAMES],
    surface="research",
)
TOOL_BY_NAME = {tool.name: tool for tool in TOOLS}


async def _dispatch_mcp_call(name: str, arguments: Mapping[str, Any] | None):
    started = time.perf_counter()
    try:
        tool = TOOL_BY_NAME.get(name)
        if tool is None:
            raise QECTORUnknownToolError(f"Unknown tool {name!r}; choose one of {sorted(TOOL_BY_NAME)}")
        validated = validate_arguments(tool, arguments)
        result = dispatch_tool(name, validated)
        envelope = result_envelope(
            result,
            tool_name=name,
            server_name=SERVER_NAME,
            server_version=SERVER_VERSION,
            stability="provisional",
            elapsed_ms=(time.perf_counter() - started) * 1e3,
        )
        validate_envelope(tool, envelope)
        return call_tool_result(envelope)
    except Exception as exc:
        return call_tool_result(
            error_envelope(
                exc,
                tool_name=name if name in TOOL_BY_NAME else "unknown_tool",
                server_name=SERVER_NAME,
                server_version=SERVER_VERSION,
                stability="provisional",
                elapsed_ms=(time.perf_counter() - started) * 1e3,
            ),
            is_error=True,
        )


INSTRUCTIONS = (
    "QECTOR provisional research tools. Companion to the 8-tool library server. "
    "Wilson CI, DEM inspection, code-family introspection, hardware "
    "probes, and micro-benchmarks. No portable claims. Air-gapped by default."
)


def _build_low_level_server() -> Any:
    async def _list_tools():
        return TOOLS

    return build_server(
        name=SERVER_NAME,
        version=SERVER_VERSION,
        instructions=INSTRUCTIONS,
        list_tools=_list_tools,
        call_tool=_dispatch_mcp_call,
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="QECTOR Decoder v3 research MCP server (Provisional)")
    parser.add_argument("--transport", choices=("stdio",), default="stdio")
    parser.parse_args(argv)
    qector_airgap.install()
    server = _build_low_level_server()
    run_stdio(server, name=SERVER_NAME, version=SERVER_VERSION, instructions=INSTRUCTIONS)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
