---
name: qector-sinter
description: >-
  Sinter decoder entry points for QECTOR (manual 17.2). Covers
  `qector_sinter_decoders()` returning qector_blossom,
  qector_belief, qector_unionfind, qector_bposd,
  qector_unionfind_unweighted, the role of these in the
  community-standard sinter benchmark harness, and the
  qector-research.sinter_decoder_list probe. Load for any question
  about sinter, the community benchmark, or head-to-head LER
  comparisons.
---

# QECTOR Sinter

Source of authority: v1.0.0 reference manual, section 17.2.

## The sinter surface

```python
from qector_decoder_v3 import qector_sinter_decoders
decoders = qector_sinter_decoders()
# -> {
#      "qector_blossom": <sinter.Decoder>,
#      "qector_belief": <sinter.Decoder>,
#      "qector_unionfind": <sinter.Decoder>,
#      "qector_bposd": <sinter.Decoder>,
#      "qector_unionfind_unweighted": <sinter.Decoder>,
#    }
```

These are `sinter.Decoder` entry points, so logical-error rates can
be compared head-to-head in the community-standard harness with no
QECTOR-specific tooling.

## How to use them

```python
import sinter
from qector_decoder_v3 import qector_sinter_decoders

decoders = qector_sinter_decoders()
# Run sinter with these decoders the same way you would any
# other sinter.Decoder:
results = sinter.collect(
    num_workers=4,
    tasks=[...],
    decoders=[decoders["qector_blossom"], decoders["qector_unionfind"]],
    max_shots=10_000,
)
```

The output is the standard sinter `Stat` collection, which you
score with `sinter.fit_binomial` or with the QECTOR
`qector-research.wilson_ci` for a 95% Wilson interval.

## What each entry point does

- `qector_blossom` -> exact Blossom (MWPM), weighted by
  `log((1-p)/p)`.
- `qector_belief` -> belief-matching: reweight the matching graph
  with BP posteriors per shot.
- `qector_unionfind` -> Union-Find with weighted growth.
- `qector_unionfind_unweighted` -> Union-Find unweighted; useful
  for code_capacity baselines.
- `qector_bposd` -> BP-OSD; for non-graphlike inputs.

## How to probe

`qector-research.sinter_decoder_list` returns:

- `sinter_exposed` (bool)
- `sinter_decoders` (list of `{"name", "type"}`)
- a note if `qector_sinter_decoders` is absent from the installed
  wheel.

The shipped `qector_decoder_v3 1.0.0` wheel exposes the function;
older or source builds may not. Always probe on the target device
before publishing a sinter-based result.

## Reference manual quote

> qector_sinter_decoders() exposes qector_blossom, qector_belief,
> qector_unionfind, qector_bposd, and qector_unionfind_unweighted
> as sinter.Decoder entry points, so logical-error rates can be
> compared head-to-head in the community-standard harness with no
> QECTOR-specific tooling.

## Common pitfalls

- **Comparing sinter results across noise models** -> refused by
  the competitive harness (manual 15.3). Tag the run.
- **Comparing sinter results without a Wilson interval** -> manual
  15.2 requires a 95% Wilson interval for any published LER.
- **Asserting "QECTOR sinter is fastest" without an artifact** ->
  per-machine, per-workload only (manual 22.5).
- **Mixing `qector_blossom` weighted and unweighted without
  flagging the difference** -> the weight is in the DEM, not in
  the sinter entry point; the entry point always reads weights
  from the DEM.
- **Using `qector_bposd` on a graphlike code** -> it works, but
  the matching decoders are faster on tested configurations.

## How the bench server helps

- `qector-research.sinter_decoder_list` is the live probe.
- `qector-research.wilson_ci` and `wilson_table` are the math
  utilities for the LER output.
- `qector-research.logical_coset_score` scores a batch of
  `(predicted, sampled)` logical observables on the logical coset
  (Theorem 2).
- `qector-research.artifact_metadata_check` generates the
  chapter 22.3 metadata block for a sinter-based artifact.
