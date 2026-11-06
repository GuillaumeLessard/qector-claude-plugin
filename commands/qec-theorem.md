---
description: Look up the exact statement and executable proof obligation of Theorems 1-16 from the Reference Manual.
argument-hint: "<theorem number 1-16>"
---

Query the mathematical foundation of the QECTOR Decoder v3 Reference Manual v1.0.0 (DOI `10.5281/zenodo.21941046`).

Arguments: `$ARGUMENTS` — a theorem number from 1 to 16. The tool takes an integer only; map a name to its number first using the table below.

1. **Look up the formulation**
   - Call `theorem_lookup(number=<integer>)` (research profile) and quote its `statement`; it is the authoritative text. Without the research profile, consult `skills/qector-math-foundations`.
   - Numbering and chapters, as the tool reports them:
     - 1 (3.1) Syndrome faithfulness and correction validity — `H c = s (mod 2)` and `c ⊕ e ∈ ker H`.
     - 2 (3.2) Logical error criterion — failure iff `L (c ⊕ e) ≠ 0` with the sector's logical matrix (the `ker H \ im H^T` form holds only for self-dual codes).
     - 3 (3.3) Path-flipping syndrome faithfulness of MWPM.
     - 4 (5.3) Path-flipping guarantee (Blossom).
     - 5 (6.2) Region growth invariant.
     - 6 (6.4) Tight-edge restriction and complexity.
     - 7 (6.6) Sparse-algorithm correctness.
     - 8 (7.1) Cluster parity algebra.
     - 9 (7.3) Peeling correctness.
     - 10 (7.3) Union-Find amortized complexity, `O(n α(n))`.
     - 11 (8.2) BP-OSD residual-solve faithfulness.
     - 12 (9.2) Ambiguity-cluster component-wise faithfulness.
     - 13 (10.2) Space-time lifting faithfulness.
     - 14 (11.1) AutoDecoder dispatch faithfulness.
     - 15 (12.1) Two-stage CSS sector faithfulness.
     - 16 (13.2) Bit-identity of batch kernels.

2. **Verification status**
   - Report which executable obligation in `tests/test_reference_manual_math.py` covers the theorem and whether it exercises the live wheel (Theorem 1 via every decode tool and Theorem 7's live Sparse Blossom check do; most others check the ground-truth helpers in `python/qector_math_ground_truth.py`). Do not describe a helper-only test as a proof about the decoder.
