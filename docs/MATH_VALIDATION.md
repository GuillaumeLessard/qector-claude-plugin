# QECTOR Mathematical Validation

This file defines the public executable ground truth for the QECTOR Decoder v3
reference manual v1.0.0 (DOI `10.5281/zenodo.21941046`). The implementation is
in `python/qector_math_ground_truth.py`; live integration tests are in
`tests/test_reference_manual_math.py`.

Run the complete local gate with:

```text
python scripts/run_manual_math_validation.py
```

## What Is Checked

| Manual claim | Executable obligation | Scope |
| --- | --- | --- |
| Theorem 1 | Exhaustive F2 equivalence on a repetition matrix; live `H c = s` checks | Finite matrices and live wheel inputs |
| Theorem 2 | Stabilizer-span versus logical-coset classification | Steane worked instance |
| Theorem 3 | Ring path boundary and syndrome faithfulness | Ring d=5 instance |
| Theorem 4 | Symmetric difference of two paths is a kernel vector | Ring d=5 instance |
| Theorems 5-6 | Collision time and non-negative tight-edge slack | Finite growth equation |
| Theorem 7 | Sparse Blossom syndrome faithfulness | Rotated surface d=3 instance |
| Theorem 8 | Cluster parity additivity | Finite binary clusters |
| Theorem 9 | Leaf-to-root tree peeling | Finite rooted detector tree |
| Theorem 10 | Linear finite peeling work witness | Rooted-tree edge count; not an asymptotic proof |
| Theorem 11 | GF(2) residual solve from the BP-OSD example | Manual H and residual |
| Theorem 12 | Disjoint ambiguity-component sum | Block-support matrix |
| Theorem 13 | Space-time differencing and telescope identity | Three-round glitch |
| Theorem 14 | Structural graphlike eligibility guard | Graphlike and non-graphlike fixtures |
| Theorem 15 | Two-stage CSS feed-forward identity | Manual matrices and independent correction |
| Theorem 16 | Exact bit equality predicate | Explicit bit-vector fixtures; no live GPU execution |
| Appendix E.1 | Steane syndrome `[1,1,0]` | Independent F2 recomputation |
| Appendix E.2 | Wilson 95% interval for 10/1000 | Independent formula plus live library |
| Appendix E.3 | DEM collapse `p=0.0296` and weight | Independent arithmetic |
| Appendix E.4 | CSS feed-forward worked example | Independent arithmetic |

## Claim Boundary

Finite executable obligations validate concrete instances and the live wheel;
they do not replace the universal proofs in the reference manual. The runner
explicitly records GPU paths as not executed when no supported device is
available, and it does not turn asymptotic complexity statements into runtime
claims. No threshold, throughput, or speed claim is produced by this gate.

Every live decode is checked before logical scoring. Any failed
`H c = s (mod 2)` check fails the test rather than being counted as a logical
error. LER artifacts are tagged `code_capacity` and carry Wilson 95% intervals;
their raw path and externally recorded SHA-256 sidecar must be retained, and
they must not be compared with `circuit_level` artifacts.
