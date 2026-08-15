"""Public, dependency-light mathematical ground truth for QECTOR.

The reference manual is the normative mathematical source. This module turns
its finite algebraic obligations into executable checks without depending on
the proprietary decoder core. It is deliberately small and explicit so that a
reviewer can inspect every operation over F2.

These functions are proof obligations for concrete instances, not a claim that
finite tests replace the mathematical proofs in the manual. The test suite
uses them to validate the shipped implementation against those proofs.
"""

from __future__ import annotations

import itertools
import math
from numbers import Integral, Real
from typing import Any, Iterable, Sequence


REFERENCE_MANUAL_VERSION = "1.0.0"
REFERENCE_MANUAL_DOI = "10.5281/zenodo.21941046"
Z95 = 1.959963985


def _bit(value: Any) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, Integral) and int(value) in (0, 1):
        return int(value)
    raise ValueError("F2 values must be 0 or 1")


def binary_vector(vector: Sequence[int]) -> tuple[int, ...]:
    return tuple(_bit(value) for value in vector)


def binary_matrix(matrix: Sequence[Sequence[int]]) -> tuple[tuple[int, ...], ...]:
    if len(matrix) == 0:
        raise ValueError("matrix must contain at least one row")
    rows = tuple(binary_vector(row) for row in matrix)
    width = len(rows[0])
    if width == 0 or any(len(row) != width for row in rows):
        raise ValueError("matrix must be non-empty and rectangular")
    return rows


def xor_vectors(left: Sequence[int], right: Sequence[int]) -> tuple[int, ...]:
    left_bits = binary_vector(left)
    right_bits = binary_vector(right)
    if len(left_bits) != len(right_bits):
        raise ValueError("vectors must have equal length")
    return tuple(a ^ b for a, b in zip(left_bits, right_bits))


def f2_mat_vec(
    matrix: Sequence[Sequence[int]], vector: Sequence[int]
) -> tuple[int, ...]:
    rows = binary_matrix(matrix)
    values = binary_vector(vector)
    if len(rows[0]) != len(values):
        raise ValueError("matrix and vector dimensions do not agree")
    return tuple(
        sum(entry * value for entry, value in zip(row, values)) % 2 for row in rows
    )


def f2_mat_mat(
    left: Sequence[Sequence[int]], right: Sequence[Sequence[int]]
) -> tuple[tuple[int, ...], ...]:
    left_rows = binary_matrix(left)
    right_rows = binary_matrix(right)
    if len(left_rows[0]) != len(right_rows):
        raise ValueError("matrix dimensions do not agree")
    right_columns = tuple(zip(*right_rows))
    return tuple(
        tuple(sum(a * b for a, b in zip(row, column)) % 2 for column in right_columns)
        for row in left_rows
    )


def gf2_rank(matrix: Sequence[Sequence[int]]) -> int:
    """Gaussian-elimination rank over F2."""
    rows = [list(row) for row in binary_matrix(matrix)]
    row_count = len(rows)
    column_count = len(rows[0])
    rank = 0
    for column in range(column_count):
        pivot = next((i for i in range(rank, row_count) if rows[i][column]), None)
        if pivot is None:
            continue
        rows[rank], rows[pivot] = rows[pivot], rows[rank]
        for i in range(row_count):
            if i != rank and rows[i][column]:
                rows[i] = [a ^ b for a, b in zip(rows[i], rows[rank])]
        rank += 1
        if rank == row_count:
            break
    return rank


def row_space_contains(rows: Sequence[Sequence[int]], vector: Sequence[int]) -> bool:
    """Test membership in the row space using rank invariance."""
    target = binary_vector(vector)
    if not rows:
        return not any(target)
    normalized = binary_matrix(rows)
    if len(normalized[0]) != len(target):
        raise ValueError("row-space dimensions do not agree")
    return gf2_rank(normalized) == gf2_rank((*normalized, target))


def all_binary_vectors(length: int) -> Iterable[tuple[int, ...]]:
    if length < 0:
        raise ValueError("length cannot be negative")
    return itertools.product((0, 1), repeat=length)


def theorem_1_obligation(
    matrix: Sequence[Sequence[int]],
    error: Sequence[int],
    correction: Sequence[int],
) -> dict[str, Any]:
    """Check Theorem 1 for one error/correction pair.

    The returned equivalence is the executable identity
    ``H c = H e <=> H(c + e) = 0`` over F2.
    """
    syndrome = f2_mat_vec(matrix, error)
    correction_syndrome = f2_mat_vec(matrix, correction)
    residual = xor_vectors(error, correction)
    residual_syndrome = f2_mat_vec(matrix, residual)
    faithful = correction_syndrome == syndrome
    residual_in_kernel = not any(residual_syndrome)
    return {
        "syndrome": syndrome,
        "correction_syndrome": correction_syndrome,
        "residual": residual,
        "residual_syndrome": residual_syndrome,
        "faithful": faithful,
        "residual_in_kernel": residual_in_kernel,
        "equivalent": faithful == residual_in_kernel,
    }


def theorem_2_obligation(
    matrix: Sequence[Sequence[int]],
    error: Sequence[int],
    correction: Sequence[int],
    stabilizer_generators: Sequence[Sequence[int]] | None = None,
) -> dict[str, Any]:
    """Check the logical-coset partition from Theorem 2.

    For a sector represented by ``matrix``, the stabilizer generators default
    to its rows, so ``im(H^T)`` is tested as the row space of H.
    """
    theorem_1 = theorem_1_obligation(matrix, error, correction)
    if not theorem_1["faithful"]:
        raise ValueError("Theorem 2 requires H c = H e")
    residual = theorem_1["residual"]
    generators = matrix if stabilizer_generators is None else stabilizer_generators
    stabilizer = row_space_contains(generators, residual)
    return {
        "faithful": True,
        "residual_in_kernel": theorem_1["residual_in_kernel"],
        "residual_in_stabilizer_span": stabilizer,
        "logical_failure": not stabilizer,
    }


def wilson_ci(k: int, n: int, z: float = Z95) -> tuple[float, float]:
    """Wilson score interval used by manual chapter 15.2."""
    if not isinstance(k, Integral) or not isinstance(n, Integral):
        raise ValueError("k and n must be integers")
    k, n = int(k), int(n)
    if n <= 0 or not 0 <= k <= n:
        raise ValueError("require 0 <= k <= n and n > 0")
    p = k / n
    denominator = 1.0 + z * z / n
    center = (p + z * z / (2.0 * n)) / denominator
    margin = z * math.sqrt(p * (1.0 - p) / n + z * z / (4.0 * n * n)) / denominator
    return max(0.0, center - margin), min(1.0, center + margin)


def dem_collapse_probability(p1: float, p2: float) -> float:
    """Independent-XOR probability for two parallel DEM mechanisms."""
    if not all(isinstance(p, Real) and math.isfinite(float(p)) for p in (p1, p2)):
        raise ValueError("probabilities must be finite")
    if not all(0.0 <= float(p) <= 1.0 for p in (p1, p2)):
        raise ValueError("probabilities must lie in [0, 1]")
    p1, p2 = float(p1), float(p2)
    return p1 * (1.0 - p2) + p2 * (1.0 - p1)


def dem_weight(probability: float) -> float:
    """Return w = log((1-p)/p), including the mathematical limits."""
    if not isinstance(probability, Real) or not math.isfinite(float(probability)):
        raise ValueError("probability must be finite")
    probability = float(probability)
    if not 0.0 <= probability <= 1.0:
        raise ValueError("probability must lie in [0, 1]")
    if probability == 0.0:
        return math.inf
    if probability == 1.0:
        return -math.inf
    return math.log((1.0 - probability) / probability)


def detector_differences(
    rounds: Sequence[Sequence[int]],
) -> tuple[tuple[int, ...], ...]:
    """Compute d_t = s_t XOR s_(t-1), with an all-zero initial round."""
    if not rounds:
        return ()
    normalized = tuple(binary_vector(row) for row in rounds)
    width = len(normalized[0])
    if any(len(row) != width for row in normalized):
        raise ValueError("rounds must have equal detector width")
    previous = (0,) * width
    differences = []
    for current in normalized:
        differences.append(xor_vectors(current, previous))
        previous = current
    return tuple(differences)


def telescope_differences(differences: Sequence[Sequence[int]]) -> tuple[int, ...]:
    if not differences:
        return ()
    result = (0,) * len(differences[0])
    for difference in differences:
        result = xor_vectors(result, difference)
    return result


def collision_time(
    current_time: float,
    weight: float,
    radius_a: float,
    radius_b: float,
    speed_a: float,
    speed_b: float,
    blossom_dual: float = 0.0,
    blossom_speed: float = 0.0,
) -> float | None:
    """Compute the event time from the sparse-blossom growth equation."""
    denominator = speed_a + speed_b + blossom_speed
    if denominator <= 0.0:
        return None
    numerator = weight - radius_a - radius_b - blossom_dual
    return current_time + numerator / denominator


def edge_slack(
    weight: float,
    radius_a: float,
    radius_b: float,
    blossom_dual: float = 0.0,
) -> float:
    """Return f_uv = w_uv - dual contribution."""
    return weight - radius_a - radius_b - blossom_dual


def ambiguity_component_sum(
    matrix: Sequence[Sequence[int]],
    components: Sequence[Sequence[int]],
    values: Sequence[int],
) -> tuple[int, ...]:
    """Sum disjoint component contributions in the ambiguity proof."""
    normalized_matrix = binary_matrix(matrix)
    normalized_values = binary_vector(values)
    if len(normalized_matrix[0]) != len(normalized_values):
        raise ValueError("component values do not match matrix columns")
    result = (0,) * len(normalized_matrix)
    used: set[int] = set()
    for component in components:
        columns = tuple(int(column) for column in component)
        if len(set(columns)) != len(columns):
            raise ValueError("ambiguity components cannot repeat a column")
        if used.intersection(columns):
            raise ValueError("ambiguity components must have disjoint supports")
        used.update(columns)
        contribution = [0] * len(normalized_matrix)
        for column in columns:
            if not 0 <= column < len(normalized_values):
                raise ValueError("component column is out of range")
            for row_index, row in enumerate(normalized_matrix):
                contribution[row_index] ^= row[column] & normalized_values[column]
        result = xor_vectors(result, contribution)
    return result


def peeling_work(parent: Sequence[int | None]) -> int:
    """Return the finite edge-visit count for a rooted-tree peel."""
    if not parent:
        return 0
    if sum(value is None for value in parent) != 1:
        raise ValueError("tree must have exactly one root")
    for vertex, ancestor in enumerate(parent):
        if ancestor is not None and (
            not isinstance(ancestor, Integral) or not 0 <= int(ancestor) < len(parent)
        ):
            raise ValueError(f"invalid parent index at vertex {vertex}")
    return sum(value is not None for value in parent)


def two_stage_css_obligation(
    hx: Sequence[Sequence[int]],
    hz: Sequence[Sequence[int]],
    cross_coupling: Sequence[Sequence[int]],
    sx: Sequence[int],
    sz: Sequence[int],
    cx: Sequence[int],
    cz: Sequence[int],
) -> dict[str, Any]:
    """Check the feed-forward identity from manual Theorem 15."""
    if f2_mat_vec(hx, cx) != binary_vector(sx):
        raise ValueError("X stage is not faithful")
    induced_z = f2_mat_vec(cross_coupling, cx)
    updated_z = xor_vectors(sz, induced_z)
    if f2_mat_vec(hz, cz) != updated_z:
        raise ValueError("Z stage is not faithful to the feed-forward syndrome")
    combined_z = xor_vectors(induced_z, f2_mat_vec(hz, cz))
    return {
        "x_syndrome": f2_mat_vec(hx, cx),
        "induced_z": induced_z,
        "updated_z": updated_z,
        "combined_z": combined_z,
        "joint_syndrome": (binary_vector(sx), binary_vector(sz)),
        "faithful": combined_z == binary_vector(sz),
    }


def cluster_parity(syndrome_bits: Iterable[int]) -> int:
    parity = 0
    for bit in syndrome_bits:
        parity ^= _bit(bit)
    return parity


def peel_tree(
    parent: Sequence[int | None],
    syndrome: Sequence[int],
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    """Peel a rooted tree leaf-to-root as in the Union-Find proof.

    ``parent[v]`` is the parent vertex of v; the root has parent None. The
    returned correction is indexed by child vertex and the second tuple is the
    residual parity at every vertex after peeling.
    """
    bits = list(binary_vector(syndrome))
    if len(parent) != len(bits):
        raise ValueError("parent and syndrome lengths must agree")
    roots = [index for index, value in enumerate(parent) if value is None]
    if len(roots) != 1:
        raise ValueError("tree must have exactly one root")

    def depth(vertex: int, trail: set[int] | None = None) -> int:
        trail = set() if trail is None else trail
        if vertex in trail:
            raise ValueError("parent relation contains a cycle")
        ancestor = parent[vertex]
        if ancestor is None:
            return 0
        ancestor = int(ancestor)
        if not 0 <= ancestor < len(bits):
            raise ValueError("invalid parent index")
        trail.add(vertex)
        return 1 + depth(ancestor, trail)

    correction = [0] * len(bits)
    # Leaves must be handled before ancestors; vertex numbering is not a
    # mathematical ordering and cannot be used as a peeling schedule.
    order = sorted(
        (vertex for vertex, ancestor in enumerate(parent) if ancestor is not None),
        key=depth,
        reverse=True,
    )
    for child in order:
        ancestor = parent[child]
        if ancestor is None:
            continue
        ancestor = int(ancestor)
        if not 0 <= ancestor < len(bits) or ancestor == child:
            raise ValueError("invalid parent index")
        if bits[child]:
            correction[child] = 1
            bits[ancestor] ^= 1
        bits[child] = 0
    return tuple(correction), tuple(bits)


def gf2_solve(
    matrix: Sequence[Sequence[int]], rhs: Sequence[int]
) -> tuple[int, ...] | None:
    """Return one solution to A x = b over F2, or None if inconsistent."""
    rows = [list(row) + [_bit(value)] for row, value in zip(binary_matrix(matrix), rhs)]
    normalized = binary_matrix(matrix)
    if len(rhs) != len(normalized):
        raise ValueError("rhs length must equal matrix row count")
    width = len(normalized[0])
    rank = 0
    pivots: list[int] = []
    for column in range(width):
        pivot = next((i for i in range(rank, len(rows)) if rows[i][column]), None)
        if pivot is None:
            continue
        rows[rank], rows[pivot] = rows[pivot], rows[rank]
        for i in range(len(rows)):
            if i != rank and rows[i][column]:
                rows[i] = [a ^ b for a, b in zip(rows[i], rows[rank])]
        pivots.append(column)
        rank += 1
    for row in rows:
        if not any(row[:-1]) and row[-1]:
            return None
    solution = [0] * width
    for row, column in zip(rows[:rank], pivots):
        solution[column] = row[-1]
    return tuple(solution)


def graphlike(check_to_qubits: Sequence[Sequence[int]]) -> bool:
    degrees: dict[int, int] = {}
    for check in check_to_qubits:
        for qubit in check:
            degrees[int(qubit)] = degrees.get(int(qubit), 0) + 1
    return max(degrees.values(), default=0) <= 2


def bit_identity(left: Sequence[int], right: Sequence[int]) -> bool:
    return binary_vector(left) == binary_vector(right)
