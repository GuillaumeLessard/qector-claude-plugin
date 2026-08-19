---
description: Look up exact mathematical formulations and verification obligations for Theorems 1-16 from the Reference Manual.
---

Query the authoritative mathematical foundation for the QECTOR Decoder v3 Reference Manual v1.0.0 (DOI `10.5281/zenodo.21941046`).

Arguments: `$ARGUMENTS` (Theorem number 1 to 16, or name, e.g. `1`, `2`, `wilson`, `feedforward`).

1. **Step 1 - Lookup Formulation**:
   - Call MCP tool `theorem_lookup(number=$ARGUMENTS)` or consult `skills/qector-math-foundations`.
   - Core Theorems:
     - `Theorem 1`: Syndrome faithfulness ($H c \equiv s \pmod 2$) and kernel decomposition ($c \oplus e \in \ker H$).
     - `Theorem 2`: Logical error criterion on the logical coset ($\ker H / \mathrm{im} H^T$).
     - `Theorem 3`: Path-flipping syndrome faithfulness of Minimum Weight Perfect Matching (MWPM).
     - `Theorem 4`: Cycle symmetric difference identity ($c_1 \oplus c_2 \in \ker H$).
     - `Theorems 5-6`: Blossom dual growth, non-negative slack, and collision time calculation.
     - `Theorem 7`: Sparse Blossom graph contraction syndrome faithfulness.
     - `Theorem 8`: Cluster parity additivity over disjoint clusters.
     - `Theorem 9`: Leaf-to-root tree peeling syndrome satisfaction on trees.
     - `Theorem 10`: Linear peeling complexity $\mathcal{O}(|V| + |E|)$.
     - `Theorem 11`: BP-OSD residual GF(2) linear solve faithfulness ($H_B y = s \oplus H \hat{x}$).
     - `Theorem 12`: Disjoint ambiguity component linear weight summation.
     - `Theorem 13`: Space-time detector differencing and glitch telescoping identity.
     - `Theorem 14`: Structural graphlike eligibility guard (max check weight $\le 2$).
     - `Theorem 15`: Two-stage CSS feedforward decoupling identity ($s_Z = H_Z e_Z \oplus \Delta_Z(c_X)$).
     - `Theorem 16`: Deterministic bit-identity between CPU and GPU graphlike backends.

2. **Step 2 - Verification Status**:
   - Report the executable proof obligation implemented in `tests/test_reference_manual_math.py`.
