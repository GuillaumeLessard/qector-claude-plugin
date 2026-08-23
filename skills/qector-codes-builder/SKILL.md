---
name: qector-codes-builder
description: >-
  Building and inspecting QEC codes for QECTOR. Covers the v1.0.0
  library code families (repetition, ring, rotated_surface,
  unrotated_surface, toric, heavy_hex, color_code), the legacy
  `generate_*_checks` generators, and the custom-matrix /
  hypergraph-product / bicycle paths. Load when a question asks
  "what code should I use?", "how do I build a code from H?", or
  "is this code graphlike?".
---

# QECTOR Codes Builder

The library exposes **graphlike code families** for the matching
decoders and the **`from_parity_check_matrix` / `hypergraph_product` /
`bicycle_code`** paths for arbitrary GF(2) parity checks that may be
non-graphlike (and therefore require BP-OSD).

## The stable graphlike families (manual 16.1, 4)

| Family             | Factory                       | Domain       | Logical X observable            |
| ------------------ | ----------------------------- | ------------ | ------------------------------- |
| `repetition`       | `codes.repetition_code(d)`    | 1D open      | boundary edge `{0}`             |
| `ring`             | `codes.ring_code(n)`          | 1D periodic  | the full cycle                  |
| `rotated_surface`  | `codes.rotated_surface_code(d)` | 2D graphlike | top-row horizontal string     |
| `unrotated_surface`| `codes.unrotated_surface_code(d)` | 2D graphlike| k = 0; no logicals_matrix       |
| `toric`            | `codes.toric_code(L)`         | 2D torus     | two logicals (Lx, Lz)           |
| `heavy_hex`        | `codes.heavy_hex_code(d)`     | 1.5D graphlike| top-row string                 |
| `color_code`       | `codes.color_code(d)`         | triangular   | two logicals (k = 2)            |

All matching-graph families return `is_matching_graph() == True` and
`max_qubit_degree() <= 2`. They are single-sector; for LER studies
use the family whose `logicals_matrix()` is not `None`.

## `logicals_matrix()` returns - what to expect (verified)

- `rotated_surface(d)`: `n_logicals == 1`, returns a 1 x n_qubits
  `uint8` matrix.
- `toric(L)`: `n_logicals == 2`, returns a 2 x n_qubits matrix.
- `color_code(d)`: `n_logicals == 2`, returns a 2 x n_qubits matrix.
- `unrotated_surface(d)`: `n_logicals == 0`, returns `None`.
  Theorem 2 logical-coset scoring is **unavailable**; the code can
  still be decoded (Theorem 1 holds), but LER cannot be defined
  without an explicit observable basis.
- `repetition(d)` and `ring(n)`: each has one logical; returns
  `n_logicals == 1`.

The library `qector-research.code_logicals_inspect` returns the same
information plus the explicit scoring note for `None`-matrix
families.

## Constructing a `Code` from a parity-check matrix

The library `codes.from_parity_check_matrix(H, name=..., distance=...)`
accepts a dense `numpy.ndarray` or a `scipy.sparse` matrix. Rows
are checks, columns are qubits. The MCP tool
`qector-library.build_code_from_matrix` validates an `(n_checks,
n_qubits)` 0/1 matrix and reports the rank, shape, and whether the
code is graphlike.

Common misuse to avoid: passing a `check_to_qubits` adjacency list
(qubit indices per check) where the function expects a dense 0/1
matrix. The library surfaces raise `ValueError` for the dense
case but historically would silently mis-decode if the inputs were
swapped. Always call the documented constructor for the form you
have.

## Hypergraph-product and bicycle codes (manual 16.1)

`codes.hypergraph_product(A, B)` builds a qLDPC code from two input
matrices. `bivariate_bicycle_code(...)` and `bicycle_code(...)` are
the Panteleev-Kalachev-style bivariate-bicycle qLDPCs. The
**`bposd` decoder is the documented production path for these
codes** (the matching decoders reject them because they have qubits
of degree > 2).

## The legacy `generate_*_checks` helpers (manual 16.1)

| Helper                              | Returns                         | Notes |
| ----------------------------------- | ------------------------------- | ----- |
| `generate_repetition_code_checks(d)` | `(checks, n_qubits)` tuple     | open chain, n = d        |
| `generate_ring_code_checks(n)`       | `(checks, n_qubits)` tuple     | n checks, n qubits       |
| `generate_surface_code_checks(d)`    | `(checks, n_qubits)` tuple     | **legacy toric-weight-4, NOT graphlike**; use `codes.rotated_surface_code` for graphlike surface checks |

Always **unpack the tuple**:

```python
checks, n = generate_repetition_code_checks(5)  # (4 checks, 5 qubits)
decoder = BlossomDecoder(checks, n_qubits=n)
```

Never pass the tuple as `c2q` — the decoder constructor expects a
list of lists, and a tuple would be a silent shape error.

## Distinguishing graphlike from non-graphlike

- Library: `code.is_matching_graph()` returns `True` iff every qubit
  participates in at most 2 checks.
- Library: `code.max_qubit_degree()` returns the largest qubit
  degree.
- Bench server: `qector-research.code_family_info` reports both
  plus a routing hint (`matching decoders` vs `BP-OSD`).
- DEM path: `dem.is_graphlike` on the parsed model; non-graphlike
  models must route to BP-OSD.

## Common pitfalls

- **n_qubits wrong** -> the decoder returns a correction of the wrong
  length with no error. Always call `code.n_qubits` or pass
  `n_qubits=` explicitly to the decoder constructor (manual 16.1).
- **`parity_check_matrix()` vs `H`** -> `H` is a bound method; call
  the parentheses (manual M3).
- **Forgetting `random_error(p, rng=...)`** -> `seed=` is not a
  keyword of `random_error`; pass `rng=np.random.default_rng(seed)`
  (manual M3).
- **Stable symbols only in delivered code** -> the seven stable
  symbols in manual 16.1 are the only ones safe to use in shipped
  libraries. The seven provisional classes (manual 16.2) must be
  labelled Provisional.

## Worked example (manual 2.7, 2.8)

- **Steane [[7,1,3]]**: build a `Code` with
  `from_parity_check_matrix` from the 3 weight-4 rows, or
  hand-build using `codes.repetition_code(3)` as a smaller starting
  point. The X and Z sectors coincide up to relabelling.
- **Rotated surface d=3**: `codes.rotated_surface_code(3)` returns
  a 9-qubit, 4-check matching graph with `n_logicals == 1`. The
  logical observable is the top row.
