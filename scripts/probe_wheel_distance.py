#!/usr/bin/env python3
"""Independent check of the code families' distance labels in qector-decoder-v3.

Brute-forces the minimum weight of an undetectable logical error
(``H e = 0`` and ``L e != 0``) for every size-based family the wheel builds,
without using any plugin code, and compares it with the ``distance`` label
the wheel assigns. Written for the upstream issue report on
``codes.rotated_surface_code``; usable as evidence by anyone with the wheel.

    python scripts/probe_wheel_distance.py            # default sizes
    python scripts/probe_wheel_distance.py --json     # machine-readable
"""

from __future__ import annotations

import argparse
import itertools
import json
import sys

import numpy as np

FAMILIES = {
    "rotated_surface_code": (3, 5, 7),
    "unrotated_surface_code": (3,),
    "toric_code": (2, 3),
    "repetition_code": (3, 5),
    "ring_code": (4, 6),
    "heavy_hex_code": (3, 5, 7),
    "color_code": (3, 5),
}


def min_logical_weight(H: np.ndarray, L: np.ndarray | None, max_weight: int) -> int | None:
    n = H.shape[1]
    if L is None:
        return None
    for weight in range(1, min(n, max_weight) + 1):
        for support in itertools.combinations(range(n), weight):
            e = np.zeros(n, dtype=np.int64)
            e[list(support)] = 1
            if ((H @ e) % 2).any():
                continue
            if ((L @ e) % 2).any():
                return weight
    return None


def graphlike_min_logical(H: np.ndarray, L: np.ndarray) -> tuple[int, list[int]] | None:
    """Exact minimum logical weight for a graphlike code (every qubit in <= 2 checks).

    Qubits are edges of a graph whose nodes are the checks plus one boundary
    node; undetectable errors are its cycles; the minimum logical weight is
    the shortest cycle whose edges hit the logical observables an odd number
    of times. Found by BFS over (node, parity) states from every node, so the
    answer is exact and polynomial, independent of the plugin code.
    """
    from collections import deque

    n_checks, n_qubits = H.shape
    boundary = n_checks
    k = L.shape[0]
    adjacency: list[list[tuple[int, int, int]]] = [[] for _ in range(n_checks + 1)]
    for qubit in range(n_qubits):
        rows = np.flatnonzero(H[:, qubit])
        if len(rows) == 0:
            continue
        a, b = (int(rows[0]), int(rows[1])) if len(rows) == 2 else (int(rows[0]), boundary)
        parity = 0
        for row in range(k):
            if L[row, qubit]:
                parity |= 1 << row
        adjacency[a].append((b, parity, qubit))
        adjacency[b].append((a, parity, qubit))
    best: tuple[int, list[int]] | None = None
    states = 1 << k
    for start in range(n_checks + 1):
        if not adjacency[start]:
            continue
        dist = [[-1] * states for _ in range(n_checks + 1)]
        via: list[list[tuple[int, int, int] | None]] = [[None] * states for _ in range(n_checks + 1)]
        dist[start][0] = 0
        queue = deque([(start, 0)])
        found = None
        while queue and found is None:
            node, par = queue.popleft()
            depth = dist[node][par]
            if best is not None and depth + 1 >= best[0]:
                break
            for neighbour, edge_parity, qubit in adjacency[node]:
                new_par = par ^ edge_parity
                if neighbour == start and new_par != 0:
                    found = (depth + 1, node, par, qubit)
                    break
                if dist[neighbour][new_par] == -1:
                    dist[neighbour][new_par] = depth + 1
                    via[neighbour][new_par] = (node, par, qubit)
                    queue.append((neighbour, new_par))
        if found and (best is None or found[0] < best[0]):
            weight, node, par, qubit = found
            counts = {qubit: 1}
            while not (node == start and par == 0):
                step = via[node][par]
                if step is None:
                    break
                node, par, q = step
                counts[q] = counts.get(q, 0) + 1
            best = (weight, sorted(q for q, c in counts.items() if c % 2 == 1))
    return best


def duplicate_columns(H: np.ndarray) -> list[tuple[int, int]]:
    seen: dict[bytes, int] = {}
    pairs = []
    for j in range(H.shape[1]):
        key = H[:, j].tobytes()
        if key in seen:
            pairs.append((seen[key], j))
        else:
            seen[key] = j
    return pairs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--max-weight", type=int, default=7)
    args = parser.parse_args(argv)
    try:
        import qector_decoder_v3
        from qector_decoder_v3 import codes
    except ImportError as exc:
        print(f"qector-decoder-v3 is not installed: {exc}", file=sys.stderr)
        return 2
    rows = []
    for factory_name, sizes in FAMILIES.items():
        factory = getattr(codes, factory_name, None)
        if factory is None:
            continue
        for size in sizes:
            code = factory(size)
            H = np.asarray(code.parity_check_matrix(), dtype=np.int64)
            logicals = code.logicals_matrix()
            L = None if logicals is None else np.asarray(logicals, dtype=np.int64)
            dups = duplicate_columns(H)
            graphlike = bool(H.sum(axis=0).max(initial=0) <= 2)
            exact = False
            witness: list[int] | None = None
            if L is not None and graphlike:
                cycle = graphlike_min_logical(H, L)
                found = cycle[0] if cycle else None
                witness = cycle[1] if cycle else None
                exact = True
            else:
                found = min_logical_weight(H, L, args.max_weight)
                exact = found is not None
            # Cross-check any exact answer against the brute force on small codes.
            if exact and L is not None and H.shape[1] <= 30:
                brute = min_logical_weight(H, L, H.shape[1])
                if brute != found:
                    raise SystemExit(f"internal disagreement on {factory_name}({size}): graph {found} vs brute force {brute}")
            rows.append(
                {
                    "family": factory_name,
                    "size": size,
                    "n_qubits": int(H.shape[1]),
                    "n_checks": int(H.shape[0]),
                    "nominal_distance": code.distance,
                    "num_logical_qubits": code.num_logical_qubits,
                    "duplicate_columns": dups[:4],
                    "min_logical_weight": found,
                    "exact": exact,
                    "witness": witness,
                    "searched_up_to": None if exact else min(int(H.shape[1]), args.max_weight),
                    "label_correct": None if found is None else found == code.distance,
                }
            )
    if args.json:
        print(json.dumps({"qector_decoder_v3": getattr(qector_decoder_v3, "__version__", "unknown"), "rows": rows}, indent=2))
        return 0
    print(f"qector-decoder-v3 {getattr(qector_decoder_v3, '__version__', 'unknown')}")
    print(f"{'family':24s} {'size':>4s} {'n':>5s} {'m':>5s} {'k':>2s} {'label':>5s} {'found':>5s}  verdict")
    for r in rows:
        found = "-" if r["min_logical_weight"] is None else str(r["min_logical_weight"])
        if r["label_correct"] is None:
            verdict = "unscorable (no logicals)" if r["num_logical_qubits"] == 0 else f"none <= {r['searched_up_to']} (bounded search)"
        elif r["label_correct"]:
            verdict = "ok (exact)" if r["exact"] else "ok"
        elif r["min_logical_weight"] < r["nominal_distance"]:
            verdict = f"OVERSTATED: true distance {r['min_logical_weight']} (duplicate columns {r['duplicate_columns'][:2]})"
        else:
            verdict = f"understated: true distance {r['min_logical_weight']} > label (harmless)"
        print(f"{r['family']:24s} {r['size']:4d} {r['n_qubits']:5d} {r['n_checks']:5d} {r['num_logical_qubits']:2d} {str(r['nominal_distance']):>5s} {found:>5s}  {verdict}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
