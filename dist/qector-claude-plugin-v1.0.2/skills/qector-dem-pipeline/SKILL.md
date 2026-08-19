---
name: qector-dem-pipeline
description: >-
  Detector error model (DEM) parsing, collapse, priors, and routing for
  QECTOR. Covers the manual 14 collapse rule (independent-XOR
  combination p = p1(1-p2) + p2(1-p1)), per-mechanism prior
  recalibration, the graphlike/hyperedge boundary, and the worked
  example p1=0.01, p2=0.02 -> p=0.0296, weight=ln(0.9704/0.0296)=3.489.
  Load for any DEM-related work: parsing .stim DEMs, building
  decoders from a DEM, weight calculations, and the matching-graph
  vs BP-OSD routing decision.
---

# QECTOR DEM Pipeline

The detector error model is the standard machine-readable description of
a decoding problem (manual 14). The QECTOR pipeline accepts a Stim DEM
(object or text), collapses it to a graph, applies per-mechanism priors
and weights, and returns a faithful decoder.

## The two surfaces

1. **Library bench server (Provisional)** — `qector-bench.dem_inspect`
   and `qector-bench.dem_collapse_parallel`. A minimal Stim-style
   parser that is enough for the small fixtures the reference manual
   uses; it does not require Stim or the optional direct-wheel `dem`
   module.
2. **Optional direct-wheel `dem` module** (Provisional, manual 16.4)
   — `dem.from_stim(text)`, `model.collapse_to_graph()`,
   `model.make_decoder('blossom')`. Verify the exact API on the target
   device by introspecting the installed wheel.

## The collapse rule (manual 14.1)

Parallel mechanisms between the same detector pair are merged into one
edge. For two mechanisms `p1` and `p2` the combined probability is

    p = p1 (1 - p2) + p2 (1 - p1)

(the independent-XOR rule, also what `stim`'s
`detector_error_model(decompose_errors=True)` produces). The merged
edge keeps the **observable set of the more likely member**. The
matching decoders only ever use the lowest-weight edge between two
detectors, so the collapse is exactly what PyMatching does, and it
preserves logical accuracy on the tested workloads.

For `n` mechanisms the cumulative form is

    p_combined = (1 - prod_i (1 - 2 p_i)) / 2

but the manual 14 worked example uses the two-mechanism explicit form
and the regression tests assert it.

## Weights (manual 2.5, 4.2, 8.2)

For graphlike models, edge weight is the log-likelihood ratio of the
mechanism:

    w = -ln(p / (1 - p))  =  ln((1 - p) / p)

For `p = 0.001`, `w ~ 6.907`; for `p = 0.005`, `w ~ 5.293`; for
`p = 0.0296`, `w ~ 3.489`. Weighted growth is the documented
production path; without weights a decoder cannot distinguish
`p = 1e-4` from `p = 1e-2`, which materially degrades accuracy under
circuit-level noise. Under code-capacity noise with a single uniform
`p`, weighted and unweighted decoders agree.

## Hyperedges (manual 2.6)

Mechanisms of weight > 2 are non-graphlike; matching decoders are not
valid on them. The pipeline routes such problems to BP-OSD. A
hyperedge is the explicit contract of the Union-Find rejection
(manual 20.8), not a bug.

## Priors and recalibration (manual 14.2)

Priors can be estimated empirically from detection events:

- **weight-1**: the detector firing rate is the estimate.
- **weight-2**: the correlated (XOR) probability
  `P(d1 xor d2) = 2 p (1 - p)` is inverted in closed form:
  `p = (1 - sqrt(1 - 2 P_xor)) / 2`.
- **weight > 2 (hyperedges)**: take the maximum firing rate among the
  detectors.

A model can be recalibrated from measured events before decoding. The
optional direct-wheel `dem.recalibrate(events)` accepts a numpy array
of measured detector firings; verify the exact signature by
introspection on the target device.

## Worked example (manual 14.3, appendix E.3)

```
p1 = 0.01, p2 = 0.02
p = 0.01 * 0.98 + 0.02 * 0.99
  = 0.0098 + 0.0198
  = 0.0296
weight = ln(0.9704 / 0.0296)
       = ln(32.78)
       = 3.489
observable set = the one of p1 (most likely member)
```

The regression tests verify this on designed parallel-edge fixtures
(`test_dem_collapse_probability.py`,
`test_dem_collapse_parallel_edges.py`).

## Two-stage CSS via DEM (manual 12)

The library has no top-level `two_stage_dem` helper. The pattern is
manual: parse the X DEM and Z DEM, run X decode, compute the induced
Z syndrome `s'_Z = s_Z + H_{Z,X} c_X`, run Z decode, XOR the
corrections. Theorem 13 (manual 12.1) guarantees joint faithfulness
when both stages are faithful on their inputs.

## Cross-references

- `qector-decoders-deep-dive` — for the decoders this pipeline
  produces.
- `qector-math-foundations` M0, M2 (Theorems 11, 13) — for the
  algebraic guarantees.
- `qector-codes-builder` — for building a `Code` from a parity-check
  matrix when the DEM is already collapsed.
- `qector-ler-methodology` M4 — for the LER methodology that the
  pipeline feeds.

## What the bench server's DEM tools do and do not do

- `dem_inspect` parses a minimal Stim-style text and reports
  structure, weight histogram, and routing hint (matching vs
  BP-OSD). It does **not** parse every Stim instruction; the full
  Stim path uses the optional direct-wheel `dem` module.
- `dem_collapse_parallel` applies the manual 14.1 rule to a parsed
  text and includes a worked-example sanity check (the
  `expected_p_combined = 0.0296` and
  `expected_weight_log = 3.489` it returns must match what you
  compute from the rule by hand).
