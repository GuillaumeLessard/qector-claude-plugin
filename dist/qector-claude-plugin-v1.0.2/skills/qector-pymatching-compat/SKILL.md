---
name: qector-pymatching-compat
description: >-
  The PyMatching-compatible shim in qector-decoder-v3 (manual 17.1).
  Covers `qector_decoder_v3.pymatching_compat.Matching` as a drop-in
  for `pymatching.Matching`, the supported methods
  (from_check_matrix, from_detector_error_model, add_edge,
  add_boundary_edge, decode, decode_batch,
  decode_to_edges_array), the fact that it is backed by the exact
  Blossom decoder, the one-line import swap, and the smoke test
  pattern via `qector-bench.pymatching_compat_check`. Load for any
  question about PyMatching compatibility, Stim / PyMatching
  pipelines, or a one-line decoder swap.
---

# QECTOR PyMatching Compatibility

Source of authority: v1.0.0 reference manual, section 17.1.

## The drop-in shim

```python
import qector_decoder_v3.pymatching_compat as pm_qector
# -or, more conventionally, alias the Matching class:
from qector_decoder_v3.pymatching_compat import Matching
```

`Matching` is a drop-in for the subset of `pymatching.Matching`
most code uses:

- `Matching.from_check_matrix(H)` - build from a dense
  `(n_checks, n_qubits)` 0/1 matrix.
- `Matching.from_detector_error_model(dem)` - build from a Stim
  detector error model.
- `add_edge(u, v, weight=...)` - add an edge between detectors.
- `add_boundary_edge(u, weight=...)` - add a boundary edge.
- `decode(syndrome)` - decode a single binary syndrome.
- `decode_batch(syndromes)` - decode a batch of syndromes.
- `decode_to_edges_array(syndrome)` - return the matched edges as
  an array.

It is backed by the **exact Blossom decoder**, so existing
Stim / PyMatching pipelines swap in QECTOR with a one-line import
change.

## Why the swap is safe

- The QECTOR shim returns a correction that satisfies
  `H c = s (mod 2)` (Theorem 1) for reachable syndromes on
  graphlike codes.
- The exact Blossom back-end is the same one the library
  `qector-decoder-v3.BlossomDecoder` exposes.
- The supported method subset is the most-used surface; methods
  not listed are not part of the contract and may be absent from
  the shim.

## Smoke test pattern

`qector-bench.pymatching_compat_check` is a built-in smoke test.
For a chosen family and size it:

1. Generates a random `error` with `Code.random_error(0.05)`.
2. Computes `syndrome = H @ error (mod 2)`.
3. Decodes with `qector_decoder_v3.BlossomDecoder` and verifies
   `H c = s`.
4. If `pymatching` is installed, decodes the same syndrome with
   `pymatching.Matching(H)`.
5. Reports `bitwise_equal` if both decoders are present, with an
   explicit note:

> Both decoders produce syndrome-valid corrections (Theorem 1).
> Bitwise equality is the coset-representative equality QECTOR
> and pymatching may not share (degeneracy, Theorem 1 corollary).

## When to use the shim

Use `qector_decoder_v3.pymatching_compat.Matching` when:

- You have a Stim / PyMatching pipeline already.
- The decoder is the bottleneck and you want exact weighted MWPM
  with one-line integration.
- You do not need any feature outside the supported method
  subset.

Use the library `qector_decoder_v3` decoders directly when:

- You want the stable symbol set (manual 16.1):
  `UnionFindDecoder`, `FastUnionFindDecoder`, `BlossomDecoder`,
  `SparseBlossomDecoder`, `NativeAutoDecoder`.
- You need a decoder that is not MWPM (BP-OSD, hybrid cascade,
  etc.).
- You want to consume the stable `DecodeResult` type for telemetry.

## Common pitfalls

- **Treating the shim as a complete PyMatching replacement** -> the
  shim is a drop-in for the most-used subset; methods outside it
  are not part of the contract.
- **Comparing QECTOR vs pymatching latency on the same machine
  without an artifact** -> per-machine, per-workload only (manual
  22.5).
- **Using the shim with a non-graphlike parity-check matrix** ->
  it is backed by Blossom, which is matching-only; non-graphlike
  inputs must route to `BPOSDDecoder` (manual 11.1).
- **Asserting "QECTOR matches pymatching" without a smoke run** ->
  always run `pymatching_compat_check` on the target device first;
  the comparison is per-workload.

## How the bench server helps

- `qector-bench.pymatching_compat_check` is the smoke test.
- `qector-bench.code_family_info` reports whether a code is
  graphlike (matching decoders eligible).
- `qector-bench.decode_faithfulness_check` re-verifies
  `H c = s` for any decode output.
- `qector-bench.artifact_metadata_check` generates the
  chapter 22.3 metadata block for a PyMatching-comparison
  artifact.

## Reference: one-line import swap

```python
# Before
import pymatching
matching = pymatching.Matching(H)
correction = matching.decode(syndrome)

# After (one-line change)
from qector_decoder_v3.pymatching_compat import Matching
matching = Matching(H)                     # same constructor
correction = matching.decode(syndrome)     # same return type

# Or, if you already had the import-swap pattern:
import qector_decoder_v3.pymatching_compat as pymatching
```
