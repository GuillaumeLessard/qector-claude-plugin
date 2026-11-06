# Upstream defect report: `codes.rotated_surface_code(d)` has distance 2 for every d

> **Status: fixed in qector-decoder-v3 1.0.1 (2026-11-05).** The 1.0.1 wheel
> builds `rotated_surface_code(d)` at distance `d` (`n = d²`, `k = 1`), and also
> corrects `unrotated_surface_code` and `color_code` (both encoded no logical
> qubit in 1.0.0) and `heavy_hex_code` (distance `2d − 1` in 1.0.0). Its own
> `codes.code_distance()` and `python/tests/test_code_distances.py` verify every
> family exactly. Plugin 2.0.1 pins 1.0.1, and its live probe reports
> `verified` for each of them. The report below is kept as the 1.0.0 record.

**Package:** `qector-decoder-v3` 1.0.0 (PyPI wheel, Rust/PyO3)
**Component:** `qector_decoder_v3.codes.rotated_surface_code`
**Severity:** high — every logical-error-rate study on this family is
invalid; the label `code.distance == d` is wrong for all d
**Found by:** the Claude plugin's effective-distance probe during the 2.0.0
release review; confirmed independently by brute force
(`scripts/probe_wheel_distance.py` in this repository, which uses no plugin
code)

## Symptom

A weight-2 X error is undetectable and flips the logical observable at every
size. `threshold_sweep` shows no distance scaling:

| family | d | n | checks | label | true min logical weight | witness qubits |
|:--|--:|--:|--:|--:|--:|:--|
| rotated_surface_code | 3 | 9 | 4 | 3 | **2** | (0, 3) |
| rotated_surface_code | 5 | 25 | 12 | 5 | **2** | (0, 5) |
| rotated_surface_code | 7 | 49 | 24 | 7 | **2** | (0, 7) |

For comparison `toric_code(L)`, `repetition_code(d)` and `ring_code(n)`
verify as labelled; `heavy_hex_code(3)` is understated (true 5).

## Root cause (d = 3, qubits numbered row-major 0..8)

`check_to_qubits` returned by the wheel:

```
[0, 1, 3, 4]   plaquette
[4, 5, 7, 8]   plaquette
[6, 7]         boundary
[1, 2]         boundary
```

The two plaquettes form the {0,1,3,4}/{4,5,7,8} checkerboard of one
stabilizer type, but the two boundary checks `{6,7}` and `{1,2}` belong to
the *other* type's boundary. Consequently columns 0 and 3 of H are identical
(both appear only in check 0), as are columns 5 and 8; the error on qubits
{0, 3} has zero syndrome and anticommutes with the logical `{0, 1, 2}`.

For the {0,1,3,4}/{4,5,7,8} checkerboard the boundary checks must be
`{2, 5}` and `{3, 6}`. With those four rows and the same logical `{0,1,2}`
the brute-force minimum logical weight is 3 (verified). The same
mis-pairing repeats at every d (the duplicate pairs are always
`(0, d)`, `(2d-1, 3d-1)`, ...).

## Reproducer (no plugin code)

```python
import itertools, numpy as np
from qector_decoder_v3 import codes
c = codes.rotated_surface_code(3)
H = np.asarray(c.parity_check_matrix(), dtype=int)
L = np.asarray(c.logicals_matrix(), dtype=int)
e = np.zeros(9, dtype=int); e[[0, 3]] = 1
assert not ((H @ e) % 2).any()      # undetectable
assert ((L @ e) % 2).any()          # logical flip
print(c.distance)                   # prints 3
```

or `python scripts/probe_wheel_distance.py`.

## Requested fix

1. Correct the boundary-check construction so both boundary pairs belong to
   the same stabilizer type as the plaquettes (for the d=3 layout above:
   `{2,5}` and `{3,6}`), and add the brute-force distance check to the
   wheel's test suite for d = 3, 5 (and a duplicate-column assertion for
   larger d).
2. Until 1.0.1 ships, consumers should not trust `Code.distance`; the plugin
   reports `effective_distance` on every result and marks the family `weak`,
   and offers `rotated_surface_corrected`, a pure-Python construction with
   the same-type boundary checks (`mcp/qector_codes.py`) whose distance is
   verified exactly at construction (3, 5, 7, 9, 11 checked in the test
   suite; the family's threshold sweeps show the expected distance scaling).

## Impact on published numbers

Any logical-error-rate curve produced with `rotated_surface_code` on 1.0.0
measures a distance-2 code and must be withdrawn or relabelled. The
plugin's `threshold_sweep` refuses to present such rows without the
`effective_distance` field since 2.0.0.
