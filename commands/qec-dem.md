---
description: Inspect and parse Detector Error Models (DEM), Stim circuit definitions, and parallel fault collapse rules.
---

Inspect Detector Error Models (DEM) and Stim circuits for circuit-level noise analysis under the QECTOR framework.

Arguments: `$ARGUMENTS` (e.g. `--file circuit.dem`, `--circuit circuit.stim`, or inline DEM text).

1. **Step 1 - Parse & Inspect**:
   - Call MCP tool `dem_inspect(dem_text=...)` or `stim_circuit_probe(circuit_text=...)` on `qector-bench`.
   - Extract:
     - Number of detectors ($D$) and logical observables ($L$).
     - Error mechanisms, hyperedges, and edge probabilities.
     - Natural log likelihood edge weights: $w = \ln((1-p)/p)$ (Chapter 14).

2. **Step 2 - Parallel Collapse & Analysis**:
   - If multiple error mechanisms trigger the same detector pair, invoke `dem_collapse_parallel`:
     $$p_{\mathrm{merged}} = p_1(1-p_2) + p_2(1-p_1)$$
     keeping the logical observable mask of the more likely mechanism.
   - Verify graphlike compatibility (Theorem 14) and output routing recommendations.
