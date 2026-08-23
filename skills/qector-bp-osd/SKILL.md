---
name: qector-bp-osd
description: >-
  Belief propagation with ordered-statistics post-processing
  (BP-OSD) for QECTOR. Covers the box-plus kernel phi(x) =
  -ln(tanh(x/2)), the log-domain sum-product / min-sum / relay
  schedules, the OSD-0 / OSD-W solve (Theorem 11), the
  ambiguity-cluster partition (Theorem 12), and the worked
  examples from the v1.0.0 reference manual (chapters 8 and 9).
  Load for any qLDPC, hyperedge, or non-graphlike question, or
  for the BP-OSD tuning surface.
---

# QECTOR BP-OSD

Source of authority: v1.0.0 reference manual, chapters 8, 9.

## Where BP-OSD applies

BP-OSD is the only decoder defined for **arbitrary GF(2) parity-check
matrices** (manual 11.1). The matching decoders reject any code with
a qubit of degree > 2; the Union-Find rejection is the explicit
contract, not a bug (manual 20.8). BP-OSD handles:

- qLDPC codes (bicycle, bivariate-bicycle, hypergraph-product).
- Color codes (`codes.color_code`).
- Any code with hyperedges (weight > 2 mechanisms).
- Codes fed by a DEM with mechanisms that cannot be collapsed to
  graph edges.

## The belief-propagation update (manual 8.1)

Let `gamma_q = LLR_prior(q) + sum_{c in N(q)} m_{c->q}` be the
posterior LLR of qubit `q`. The check-node update is the **box-plus
kernel** in the log domain:

    phi(x) = -ln(tanh(x/2)) = ln coth(x/2)        for x > 0
    phi(0) = +inf
    phi(x) -> 0 for large x

Three schedules are supported:

| Schedule           | Formula                                                  | Notes                                    |
| ------------------ | -------------------------------------------------------- | ---------------------------------------- |
| Exact sum-product  | `m_{c->q} = sgn * phi( sum_{q'} phi(|m_{q'->c}|) )`      | default; numerically stable             |
| Min-sum            | `m_{c->q} = sgn * min_{q'} |m_{q'->c}|`                   | classical approximation, opt-in         |
| Relay (layered)    | same kernel; checks processed sequentially                | faster convergence on loopy graphs      |

The Rust implementation evaluates `phi` exactly below `0.25` and
uses a `2^16`-entry linearly-interpolated table above it, with
maximum interpolation error about `2e-7` on the tabulated range.

## The OSD stage (manual 8.2)

- **OSD-0**: sort columns by ascending `|LLR|` (least reliable
  first), extract a rank-r independent basis by GF(2) Gaussian
  elimination, keep the BP hard decision on the free (most
  reliable) columns, solve the basis for the residual syndrome.
- **OSD-W** (`osd_order >= 1`): additionally sweep combinations of
  the `W = max(2 * osd_order, 6)` least-reliable columns and keep
  the lowest-weight faithful candidate.

## Theorem 11 (residual-solve faithfulness, manual 8.2)

> Let `B` be a rank-r column basis of `H`, and let
> `s_eff = s + H_fixed e_fixed (mod 2)` be the residual after
> fixing the reliable columns. Then the system
> `H_B e_B = s_eff` has a solution whenever `s` is reachable, and
> every OSD candidate
> `c = e_fixed + (e_B on B, 0 elsewhere)` satisfies `H c = s`.

The algebraic guarantee is **independent of BP convergence
quality**: LLRs only influence which coset is selected, never
whether the returned correction reproduces the syndrome.

## The reliability partition and component-wise solving (manual 9)

- Threshold `tau` on `|LLR|`. Split qubits into
  `Q_rel = {q : |gamma_q| >= tau}` and `Q_amb = {q : |gamma_q| < tau}`.
- Freeze `Q_rel` to hard decisions `e_rel`. Compute the residual
  `s_res = s + H_rel e_rel (mod 2)`. If `s_res = 0` the decode is
  complete.
- Otherwise the Tanner-induced subgraph on `Q_amb` splits into
  connected components `C_k`. Each component with
  `size <= K_max` (default 12) is solved exactly by enumeration
  over its `2^k` error patterns, minimizing weight among faithful
  solutions. Larger components use a restricted OSD-0 over the
  cluster columns.

## Theorem 12 (component-wise faithfulness, manual 9.2)

> Let `c = e_rel xor (xor_k e_k)`, where each component is solved
> with `H_{C_k} e_k = s_res` restricted to its support. Then
> `H c = s (mod 2)`, independently of the threshold `tau`.

## Tuning kwargs (manual 16.2 - Provisional)

The `BPOSDDecoder` tuning kwarg names are stable; defaults may shift
in 1.x. Verify the live values via introspection; do not hard-code.

- `bp_method`: `"sum_product"` (default) or `"min_sum"`.
- `osd_order`: integer, default 0; `>= 1` enables OSD-W with
  `W = max(2 * osd_order, 6)`.
- `max_bp_iters`: integer; default typically 50.
- `tau`: reliability threshold; default typically 0.0 (no
  ambiguity clustering).

## Worked example (manual 8.5)

`H = [[1,1,0],[0,1,1]]` over F2, syndrome `s = [1,0]`.

- BP's hard decision: `e_hard = [1,0,0]`, residual zero, decode
  returns immediately. `H e = [1,0] = s`.
- If BP were uncertain and produced `e_hard = [0,1,0]`, residual
  `s_eff = [0,1]`. The most reliable column (column 1) is fixed at
  its BP hard decision 0; the basis `{0, 2}` must solve
  `H_B e_B = s_eff`. Column 2 alone contributes `[0,1]`, so
  `e_B = (0, 1)` on the basis columns and `c = [0,1,1]`. `H c = s`.

The example shows the division of labour: **BP proposes, OSD
repairs, and the repaired correction always satisfies the
syndrome**.

## Numerical stability

The `phi` LUT keeps the update numerically stable across the full
dynamic range. `qector_decoder_v3.bp_osd` exposes the
`plausibility_guard`; the regression suite includes
`test_bp_numerical_stability.py` and `test_bposd_osd_orders.py`.

## Common pitfalls

- **Calling `bposd` on a graphlike code** -> it works, but the
  matching decoders are faster on tested configurations. Use
  `bposd` only when the parity-check matrix is non-graphlike.
- **Ignoring `max_bp_iters`** -> the decoder may return before
  convergence. The hard-decision return short-circuits when
  `H e_hard = s`; otherwise OSD repairs.
- **Comparing BP-OSD accuracy to a matching decoder** without
  identical parity-check matrix and noise model -> the harness
  drives both through the same pipeline (manual 15.3).
- **Hardcoding tuning kwargs** -> names are stable, defaults may
  shift in 1.x (manual 16.2).

## How the bench server helps

- `qector-research.code_family_info` reports whether a code is
  graphlike and the routing hint.
- `qector-research.decode_faithfulness_check` re-verifies
  `H c = s` externally for any decoder output.
- `qector-research.pymatching_compat_check` is a related smoke test
  (graphlike codes only).
