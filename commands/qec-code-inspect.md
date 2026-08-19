---
description: Inspect quantum code family properties, parity check matrices, transversals, and distance bounds.
---

Inspect the structural and algebraic parameters of any quantum code supported by QECTOR.

Arguments: `$ARGUMENTS` (e.g. `--family rotated_surface --distance 5` or `--family ring --distance 6`).

1. **Step 1 - Code Introspection**:
   - Call MCP tool `code_family_info(family=...)` and `code_distance_check(family=..., distance=...)`.
   - Call `code_logicals_inspect(family=..., distance=...)` to retrieve the logical operator matrix and number of encoded logical qubits ($k$).
   - Optionally call `code_export_matrices` to inspect $H_X, H_Z$ or the matching graph check matrix.

2. **Step 2 - Report Structural Characteristics**:
   - Present a summary table containing:
     - Code parameters: $[[n, k, d]]$.
     - Number of physical qubits $n$ and checks $m$.
     - Maximum row/column check weights (graphlike verification).
     - Self-orthogonality status ($H H^T = 0 \pmod 2$).
