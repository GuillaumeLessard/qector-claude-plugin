"""Plugin-constructed code families with verified distances.

The decoder wheel ``qector-decoder-v3==1.0.0`` labelled ``rotated_surface_code(d)``
with distance ``d`` but built it with duplicate parity-check columns, so its
true distance was 2 at every size (``docs/UPSTREAM_ISSUE_rotated_surface_distance.md``).
Plugin 2.0.0 therefore built the single-sector rotated surface code itself, in
pure Python, as the family ``rotated_surface_corrected``. qector-decoder-v3
1.0.1 fixed the wheel; the family is kept so that 2.0.0 requests naming it keep
working, and it remains a useful independent cross-check of the wheel. Every construction is checked at build
time by :func:`mcp_server_library.effective_distance` (exact for graphlike
codes); a code whose checked distance differs from the requested one is
refused rather than returned.

The objects mimic the subset of the wheel's ``Code`` API that the servers use
(``check_to_qubits``, ``n_qubits``, ``n_checks``, ``parity_check_matrix()``,
``logicals_matrix()``, ``num_logical_qubits``, ``is_matching_graph()``,
``max_qubit_degree()``, ``random_error(p, rng=)``, ``syndrome(e)``,
``distance``, ``name``, ``description``). Decoders take ``check_to_qubits``
lists, so every QECTOR decoder works on them unchanged.
"""

from __future__ import annotations

from typing import Sequence

import numpy as np


class PluginCode:
    """A single-sector binary code defined by explicit checks and logicals."""

    def __init__(
        self,
        *,
        name: str,
        description: str,
        check_to_qubits: Sequence[Sequence[int]],
        n_qubits: int,
        logicals: Sequence[Sequence[int]],
        distance: int,
    ) -> None:
        self.name = name
        self.description = description
        self.check_to_qubits = [sorted(int(q) for q in check) for check in check_to_qubits]
        self.n_qubits = int(n_qubits)
        self.n_checks = len(self.check_to_qubits)
        self.distance = int(distance)
        self._H = np.zeros((self.n_checks, self.n_qubits), dtype=np.uint8)
        for row, check in enumerate(self.check_to_qubits):
            for qubit in check:
                self._H[row, qubit] ^= 1
        self._L = np.zeros((len(logicals), self.n_qubits), dtype=np.uint8)
        for row, support in enumerate(logicals):
            for qubit in support:
                self._L[row, int(qubit)] ^= 1
        self.num_logical_qubits = int(self._L.shape[0])

    def parity_check_matrix(self) -> np.ndarray:
        return self._H.copy()

    def logicals_matrix(self) -> np.ndarray | None:
        return self._L.copy() if self._L.shape[0] else None

    def max_qubit_degree(self) -> int:
        return int(self._H.sum(axis=0).max(initial=0))

    def is_matching_graph(self) -> bool:
        return self.max_qubit_degree() <= 2

    def syndrome(self, error: Sequence[int]) -> np.ndarray:
        e = np.asarray(error, dtype=np.uint8).reshape(-1)
        if e.shape[0] != self.n_qubits:
            raise ValueError(f"error vector must have {self.n_qubits} entries")
        return ((self._H.astype(np.int64) @ e.astype(np.int64)) % 2).astype(np.uint8)

    def random_error(self, p: float, rng: np.random.Generator | None = None) -> np.ndarray:
        generator = rng if rng is not None else np.random.default_rng()
        return (generator.random(self.n_qubits) < float(p)).astype(np.uint8)

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"PluginCode({self.name!r}, n={self.n_qubits}, m={self.n_checks}, k={self.num_logical_qubits}, d={self.distance})"


def rotated_surface_checks(distance: int) -> tuple[list[list[int]], list[list[int]], int]:
    """Checks, logicals and qubit count of the single-sector rotated surface code.

    Data qubits sit on a ``d x d`` grid, numbered row-major. The checks of
    one stabilizer type are the plaquettes of a checkerboard
    (``(r + c)`` even, weight 4) plus the weight-2 boundary checks that
    continue the same checkerboard on the left and right edges. The logical
    observable of this sector is the top row, a string joining the two
    boundaries that carry no check of this type. The wheel's construction
    uses boundary checks of the *other* type, which is the defect.
    """
    d = int(distance)
    if d < 2:
        raise ValueError("rotated surface code needs distance >= 2")

    def q(r: int, c: int) -> int:
        return r * d + c

    checks: list[list[int]] = []
    for r in range(d - 1):
        for c in range(d - 1):
            if (r + c) % 2 == 0:
                checks.append([q(r, c), q(r, c + 1), q(r + 1, c), q(r + 1, c + 1)])
    for r in range(d - 1):
        if r % 2 == 1:
            checks.append([q(r, 0), q(r + 1, 0)])
        if (r + d - 1) % 2 == 0:
            checks.append([q(r, d - 1), q(r + 1, d - 1)])
    logicals = [[q(0, c) for c in range(d)]]
    return checks, logicals, d * d


def rotated_surface_corrected(distance: int) -> PluginCode:
    """Rotated surface code with the boundary checks of the right type.

    The returned code's distance is verified (exactly, via the matching
    graph) before it is handed out; a construction that fails its own check
    raises instead of returning a mislabelled code.
    """
    checks, logicals, n_qubits = rotated_surface_checks(distance)
    code = PluginCode(
        name=f"rotated_surface_corrected_d{int(distance)}",
        description=(
            "Rotated surface code built by the plugin with same-type boundary checks "
            "(independent construction; same parameters as the wheel's rotated_surface_code since 1.0.1); "
            "distance verified at construction"
        ),
        check_to_qubits=checks,
        n_qubits=n_qubits,
        logicals=logicals,
        distance=int(distance),
    )
    _verify_distance(code)
    return code


def _verify_distance(code: PluginCode) -> None:
    from mcp_server_library import effective_distance

    report = effective_distance(code.parity_check_matrix(), code.logicals_matrix(), nominal=code.distance)
    if not report["exact"] or report["min_logical_weight"] != code.distance:
        raise RuntimeError(
            f"{code.name}: construction self-check failed (expected distance {code.distance}, "
            f"probe says {report['min_logical_weight']} exact={report['exact']}); refusing to serve it"
        )


FAMILIES: dict[str, str] = {
    # family name -> factory in this module
    "rotated_surface_corrected": "rotated_surface_corrected",
}
