---
name: qector-two-stage-css
description: >-
  Two-stage CSS decoding for QECTOR (manual chapter 12). Independent
  X and Z decoders assume P(X, Z) = P(X) P(Z); depolarising noise
  violates this. Two-stage decoding removes the cross-talk
  explicitly. Load for any question about depolarising noise, CSS
  sector coupling, feedforward X->Z syndrome updates, or the
  Theorem 13 joint-faithfulness guarantee.
---

# QECTOR Two-Stage CSS Decoding

Source of authority: v1.0.0 reference manual, chapter 12.

## The problem with independent X/Z decoders

A CSS code splits stabilizers into X-type and Z-type. Independent X
and Z decoders assume

    P(X, Z) = P(X) P(Z)

Depolarising noise violates this: a `Y` error flips both sectors, so
the X and Z syndromes share information. The standard
single-stage correction is a residual logical failure that a
two-stage pass can avoid.

## The feedforward construction (manual 12.1)

```
c_X    <-  DecodeX(s_X)
s'_Z   =   s_Z  xor  H_{Z,X} c_X         (mod 2)
c_Z    <-  DecodeZ(s'_Z)
c      =   c_X  xor  c_Z
```

The X correction `c_X` induces a syndrome on the Z sector through
the cross-coupling `H_{Z,X}`; subtracting it before the Z decode
removes the cross-talk. Both stages may use any faithful decoder
(Blossom, Sparse Blossom, Union-Find, BP-OSD).

## Theorem 13 (joint faithfulness, manual 12.1)

> If `DecodeX` and `DecodeZ` are syndrome-faithful on their
> respective inputs, then the combined correction satisfies
> `H c = s` for the joint CSS code.

The proof uses the fact that the full parity-check matrix of the
CSS code applies `H_X` to the X sector and `H_Z` to the Z sector
with the cross-coupling accounted by the update:

    H c = (H_X c_X, H_Z (c_X xor c_Z))
        = (s_X, H_{Z,X} c_X xor s_Z xor H_{Z,X} c_X)
        = (s_X, s_Z) = s

## Worked example (manual 12, appendix E.4)

```
H_X    =  [[1, 1, 0], [0, 1, 1]]
H_Z    =  [[0, 1, 1], [1, 1, 0]]
H_{Z,X} = [[0, 1, 0], [1, 0, 0]]
s_X    =  [1, 0]
c_X    =  DecodeX(s_X) = [1, 0, 0]
H_{Z,X} c_X  =  [0, 1]
s'_Z   =  s_Z + [0, 1]
c_Z    =  DecodeZ(s'_Z)
c      =  c_X xor c_Z
```

## What the engine ships

- **Library (Provisional, manual 16.2)**: `TwoStageDecoder`. The
  constructor takes two parity-check matrices `H_X` and `H_Z` plus
  a per-sector decoder factory.
- **Library (manual 16.4)**: the optional direct-wheel
  `qector_decoder_v3.dem` module can be combined with a
  per-sector decode by hand, but there is no top-level
  `two_stage_dem` helper.

## What is **not** claimed

> Any stronger claim - for example that two-stage decoding achieves
> a higher threshold than independent decoding under depolarising
> noise - requires a surviving artifact and is therefore scoped or
> excluded here. (manual 12)

This is the same scope rule as every other claim in the manual:
**per-machine, per-workload, per-artifact only**. Do not publish a
threshold comparison without a dated, reproducible artifact.

## Common pitfalls

- **Reusing one decoder for both stages when the sectors differ** ->
  pick the right decoder per sector. The X and Z sectors may have
  different graphlike structure.
- **Ignoring the cross-coupling `H_{Z,X}`** -> the X correction
  leaves a residual on the Z sector, the Z decode is wrong, the
  joint decode is wrong.
- **Comparing two-stage LER to independent LER across noise models**
  -> tag the run first (manual 15.3).
- **Asserting "two-stage beats independent" without an artifact** ->
  never published.

## How the bench server helps

- `qector-research.code_export_matrices` exports
  `parity_check_matrix` and `logicals_matrix` in JSON form, useful
  when feeding a two-stage pipeline by hand.
- `qector-research.decode_faithfulness_check` re-verifies
  `H c = s` for the joint correction externally.
- `qector-research.logical_coset_score` scores the joint correction
  against the joint logical observables.
- `qector-research.artifact_metadata_check` generates the chapter
  22.3 metadata block for a two-stage artifact.
