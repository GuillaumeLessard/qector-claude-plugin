---
description: Inspect and parse Detector Error Models (DEM), Stim circuit definitions, and parallel fault collapse rules.
argument-hint: "<inline DEM text> | --file circuit.dem | --circuit circuit.stim"
---

Inspect Detector Error Models (DEM) and Stim circuits for circuit-level noise analysis under the QECTOR framework.

Arguments: `$ARGUMENTS` (e.g. `--file circuit.dem`, `--circuit circuit.stim`, or inline DEM text).

1. **Step 1 - Parse & Inspect**:
   - Call `dem_inspect(dem_text=...)` or `stim_circuit_probe(circuit_text=...)` (research profile). The DEM parser accepts flattened Stim models only: `error(p) D.. L..`, Stim's `^` decomposition, `detector`, `logical_observable`, `shift_detectors`; a `repeat` block is refused with instructions to flatten first, and a probability outside `[0, 1]` is `INVALID_INPUT`.
   - Extract:
     - Number of detectors ($D$) and logical observables ($L$).
     - Error mechanisms, hyperedges, and edge probabilities.
     - Natural log likelihood edge weights: $w = \ln((1-p)/p)$ (Chapter 14).

2. **Step 2 - Parallel Collapse & Analysis**:
   - If several mechanisms hit the same detector set (an edge, or a single boundary detector), call `dem_collapse_parallel(dem_text=..., observable_rule="most_likely")`. For `n` members the rule is the independent-XOR combination `p = (1 − ∏(1 − 2 p_i)) / 2` (which is `p_1(1−p_2) + p_2(1−p_1)` for two), keeping the observable mask of the most likely member. A merged probability of exactly 0 or 1 has no finite weight: `weight_log` is null and a warning says so.
   - Report `hyperedges` (three or more detectors) as not collapsible and route them to BP-OSD; graphlike eligibility is the Theorem 14 dispatch guard (`is_graphlike` in `dem_inspect`).
