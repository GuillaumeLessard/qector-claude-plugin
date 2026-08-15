"""Run a strict, local QECTOR code-capacity LER sweep.

The script targets the published ``qector-decoder-v3==1.0.0`` wheel directly.
It uses logical-coset scoring, fails closed on any syndrome-faithfulness
violation, writes a raw JSON artifact, and prints the artifact SHA-256.

Canonical family names are ``repetition``, ``ring``, ``rotated_surface``,
``unrotated_surface``, ``toric``, ``heavy_hex``, and ``color_code``. The old
``*_code`` spellings remain accepted as explicit aliases for this script only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, Sequence

# Keep the command's stdout machine-readable and avoid the wheel banner in
# captured artifacts; licensing details remain available through get_license_info.
os.environ.setdefault("QECTOR_SILENT", "1")

import numpy as np
import qector_decoder_v3 as qector

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from qector_math_ground_truth import REFERENCE_MANUAL_DOI, wilson_ci  # noqa: E402


EXPECTED_VERSION = "1.0.0"
if getattr(qector, "__version__", None) != EXPECTED_VERSION:
    raise RuntimeError(
        f"qector-decoder-v3=={EXPECTED_VERSION} is required; "
        f"found {getattr(qector, '__version__', 'unknown')}"
    )

NOISE_TAG = "code_capacity"
FAMILY_ALIASES = {
    "repetition_code": "repetition",
    "ring_code": "ring",
    "rotated_surface_code": "rotated_surface",
    "unrotated_surface_code": "unrotated_surface",
    "toric_code": "toric",
    "heavy_hex_code": "heavy_hex",
}
FAMILY_FACTORIES: dict[str, Callable[[int], Any]] = {
    "repetition": qector.codes.repetition_code,
    "ring": qector.codes.ring_code,
    "rotated_surface": qector.codes.rotated_surface_code,
    "unrotated_surface": qector.codes.unrotated_surface_code,
    "toric": qector.codes.toric_code,
    "heavy_hex": qector.codes.heavy_hex_code,
    "color_code": qector.codes.color_code,
}
DECODERS = {
    "union_find": qector.UnionFindDecoder,
    "fast_union_find": qector.FastUnionFindDecoder,
    "blossom": qector.BlossomDecoder,
    "sparse_blossom": qector.SparseBlossomDecoder,
    "native_auto": qector.NativeAutoDecoder,
}
MAX_DISTANCE = int(os.environ.get("QECTOR_SWEEP_MAX_DISTANCE", "63"))
MAX_TRIALS = int(os.environ.get("QECTOR_SWEEP_MAX_TRIALS", "100000"))
MAX_POINTS = int(os.environ.get("QECTOR_SWEEP_MAX_POINTS", "256"))


def _validate_int(
    value: Any, name: str, minimum: int, maximum: int | None = None
) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)):
        raise ValueError(f"{name} must be an integer")
    value = int(value)
    if value < minimum or (maximum is not None and value > maximum):
        bound = (
            f" in [{minimum}, {maximum}]" if maximum is not None else f" >= {minimum}"
        )
        raise ValueError(f"{name} must be{bound}")
    return value


def _validate_rate(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(
        value, (int, float, np.integer, np.floating)
    ):
        raise ValueError("error rates must be finite numbers in [0, 1]")
    value = float(value)
    if not math.isfinite(value) or not 0.0 <= value <= 1.0:
        raise ValueError("error rates must be finite numbers in [0, 1]")
    return value


def _canonical_family(family: str) -> str:
    family = FAMILY_ALIASES.get(family, family)
    if family not in FAMILY_FACTORIES:
        raise ValueError(
            f"unknown family {family!r}; choose from {sorted(FAMILY_FACTORIES)}"
        )
    return family


def _environment() -> dict[str, Any]:
    return {
        "os": platform.system(),
        "platform": platform.platform(),
        "cpu": platform.processor() or "unknown",
        "python": platform.python_version(),
        "numpy": np.__version__,
        "qector_decoder_v3": qector.__version__,
        "git_commit": os.environ.get("QECTOR_GIT_COMMIT", "not available"),
    }


def _faithful(matrix: np.ndarray, correction: np.ndarray, syndrome: np.ndarray) -> bool:
    calculated = (matrix.astype(np.int64) @ correction.astype(np.int64)) % 2
    return bool(np.array_equal(calculated.astype(np.uint8), syndrome))


def run_sweep(
    family: str,
    distances: Sequence[int],
    error_rates: Sequence[float],
    trials: int,
    seed: int,
    decoder_name: str = "blossom",
) -> dict[str, Any]:
    family = _canonical_family(family)
    distances = [
        _validate_int(value, "distance", 1, MAX_DISTANCE) for value in distances
    ]
    error_rates = [_validate_rate(value) for value in error_rates]
    trials = _validate_int(trials, "trials", 1, MAX_TRIALS)
    seed = _validate_int(seed, "seed", 0)
    if not error_rates or not distances:
        raise ValueError("distances and error_rates must not be empty")
    if len(distances) * len(error_rates) > MAX_POINTS:
        raise ValueError(f"sweep exceeds the {MAX_POINTS}-point limit")
    if decoder_name not in DECODERS:
        raise ValueError(
            f"unknown decoder {decoder_name!r}; choose from {sorted(DECODERS)}"
        )

    rows: list[dict[str, Any]] = []
    sizes: list[dict[str, int]] = []
    for distance in distances:
        code = FAMILY_FACTORIES[family](distance)
        matrix = np.asarray(code.parity_check_matrix(), dtype=np.uint8)
        logicals = code.logicals_matrix()
        if logicals is None:
            raise ValueError(
                f"{family!r} does not expose logical observables for LER scoring"
            )
        logicals = np.asarray(logicals, dtype=np.uint8)
        if not code.is_matching_graph() and decoder_name != "native_auto":
            raise ValueError(f"{decoder_name!r} requires a graphlike code")
        sizes.append(
            {"distance": distance, "n_checks": code.n_checks, "n_qubits": code.n_qubits}
        )
        decoder = DECODERS[decoder_name](code.check_to_qubits, n_qubits=code.n_qubits)
        for error_rate in error_rates:
            logical_errors = 0
            theorem1_violations = 0
            for trial in range(trials):
                rng = np.random.default_rng(seed + trial)
                error = np.asarray(
                    code.random_error(error_rate, rng=rng), dtype=np.uint8
                )
                syndrome = np.asarray(code.syndrome(error), dtype=np.uint8)
                correction = np.asarray(decoder.decode(syndrome), dtype=np.uint8)
                if not _faithful(matrix, correction, syndrome):
                    theorem1_violations += 1
                    raise RuntimeError(
                        f"Theorem 1 violation at family={family}, distance={distance}, "
                        f"p={error_rate}, trial={trial}"
                    )
                residual = correction ^ error
                if bool(
                    ((logicals.astype(np.int64) @ residual.astype(np.int64)) % 2).any()
                ):
                    logical_errors += 1
            lo, hi = wilson_ci(logical_errors, trials)
            rows.append(
                {
                    "distance": distance,
                    "n_checks": code.n_checks,
                    "n_qubits": code.n_qubits,
                    "error_rate": error_rate,
                    "logical_errors": logical_errors,
                    "trials": trials,
                    "logical_error_rate": logical_errors / trials,
                    "wilson_95": [lo, hi],
                    "theorem1_violations": theorem1_violations,
                }
            )

    return {
        "schema_version": "1.0",
        "reference_manual": REFERENCE_MANUAL_DOI,
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
            "distance_size": sizes,
            "noise_model": {"tag": NOISE_TAG, "source": "Code.random_error"},
            "dem_settings": {
                "decompose_errors": None,
                "graphlike_collapse": None,
                "applicable": False,
            },
            "decoder": {
                "class": DECODERS[decoder_name].__name__,
                "weighted": False,
                "batch": False,
                "gpu": False,
            },
            "sample_count": {"trials_per_point": trials, "seed": seed},
            "metric": "logical_error_rate (logical coset scoring, Theorem 2)",
            "environment": _environment(),
        },
        "harness": {
            "theorem1_violations": 0,
            "faithfulness_policy": "fail closed before logical scoring",
        },
        "results": rows,
        "caveat": (
            "Screening estimate for the requested trial count; not a converged threshold. "
            "Do not compare code_capacity values with circuit_level values."
        ),
    }


def _write_artifact(
    document: dict[str, Any], requested: str | None
) -> tuple[Path, str]:
    if requested:
        output = Path(requested).expanduser()
        if output.suffix.lower() != ".json":
            output /= "threshold_sweep.json"
    else:
        output = Path("artifacts") / f"qector_threshold_{time.time_ns()}.json"
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    document["required_metadata"]["artifact"] = {
        "path": str(output),
        "format": "raw JSON",
        "sha256_sidecar": f"{output}.sha256",
    }
    payload = json.dumps(document, sort_keys=True, indent=2).encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    temporary: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=output.parent,
            prefix=f".{output.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = handle.name
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, output)
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)
    sidecar = Path(f"{output}.sha256")
    sidecar.write_text(f"{digest}  {output.name}\n", encoding="ascii")
    return output, digest


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="QECTOR v1.0.0 strict-math threshold sweep"
    )
    parser.add_argument(
        "--family", default="rotated_surface", help="canonical QECTOR code family"
    )
    parser.add_argument("--distances", type=int, nargs="+", default=[3, 5, 7])
    parser.add_argument(
        "--error-rates", type=float, nargs="+", default=[0.01, 0.05, 0.1]
    )
    parser.add_argument("--trials", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--decoder", default="blossom", choices=sorted(DECODERS))
    parser.add_argument(
        "--out", default=None, help="raw JSON path; defaults to artifacts/"
    )
    args = parser.parse_args(argv)
    document = run_sweep(
        args.family,
        args.distances,
        args.error_rates,
        args.trials,
        args.seed,
        args.decoder,
    )
    output, digest = _write_artifact(document, args.out)
    print(f"Artifact written: {output}")
    print(f"SHA-256: {digest}")
    print(json.dumps(document["results"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
