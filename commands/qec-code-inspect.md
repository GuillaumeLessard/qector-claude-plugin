---
description: Inspect a code family's parity-check matrix, logical observables, and checked effective distance.
argument-hint: "--family rotated_surface --size 5"
---

Inspect the structural and algebraic parameters of a code family supported by QECTOR.

Arguments: `$ARGUMENTS` (e.g. `--family rotated_surface --size 5` or `--family ring --size 6`).

The research-profile tools below take `family` and `size` (both required); there is no `distance` argument. The safe profile offers `list_code_families` instead, whose per-family `health` block already carries `effective_distance` at the probe size.

1. **Code introspection**
   - Call `code_family_info(family=..., size=...)` for `n`, `m`, graphlike flag and maximum qubit degree.
   - Call `code_distance_check(family=..., size=...)`: it does not echo the wheel's label. Read `nominal_distance`, `effective_distance` (`min_logical_weight`, `exact`, `lower_bound`, `witness`, `method`) and `verdict` (`verified`, `contradicted`, `bounded`, `unscorable`).
   - Call `code_logicals_inspect(family=..., size=...)` for the logical-observable matrix and `k`; `logicals_present: false` means Theorem 2 scoring is undefined for the family.
   - Optionally call `code_export_matrices(family=..., size=..., include_logicals=true)` for the full `H` (and `L`).

2. **Report structural characteristics**
   - Present `[[n, k, d]]` with `d` taken from `code_distance_check`: write the nominal value and the checked value separately, and flag a `contradicted` verdict prominently (for example the wheel's `rotated_surface` has duplicate columns and an effective distance of 2 at every size).
   - Number of physical qubits `n` and checks `m`; maximum qubit degree (graphlike iff ≤ 2); self-orthogonality is **not** reported by these tools — do not claim `H H^T = 0` unless you computed it from the exported matrix.
