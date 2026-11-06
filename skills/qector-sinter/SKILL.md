---
name: qector-sinter
description: >-
  Sinter decoder entry points for QECTOR (manual 17.2). Covers
  `qector_decoder_v3.sinter_compat.qector_sinter_decoders()`
  (qector_blossom, qector_belief, qector_unionfind, qector_bposd),
  its dependency on the optional `sinter` package, the role of these
  shims in the community-standard sinter benchmark harness, and the
  qector-research.sinter_decoder_list probe. Load for any question
  about sinter, the community benchmark, or head-to-head LER
  comparisons.
---

# QECTOR Sinter

Source of authority: v1.0.0 reference manual, section 17.2.

## The sinter surface

```python
from qector_decoder_v3.sinter_compat import qector_sinter_decoders  # not a top-level export
decoders = qector_sinter_decoders()
# -> {   (qector-decoder-v3 1.0.1)
#      "qector_blossom": QectorBlossomSinterDecoder(),            # kind "blossom"
#      "qector_belief": QectorBeliefSinterDecoder(),              # kind "belief"
#      "qector_unionfind": QectorUnionFindSinterDecoder(),        # kind "unionfind"
#      "qector_unionfind_unweighted": QectorUnionFindUnweightedSinterDecoder(),
#      "qector_bposd": QectorBpOsdSinterDecoder(),                # kind "bposd"
#    }
```

Since wheel 1.0.1 the factory returns these five `sinter.Decoder`
shims, one preset class each (1.0.0 returned four, without
`qector_unionfind_unweighted`, and its `sinter_decoder` entry points
all resolved to one class that defaulted to belief-matching). It raises `ImportError: sinter is not installed (pip install
sinter)` unless the optional `sinter` package is present. `sinter`
is not part of `requirements.lock`; installing it is a network action
outside the air-gapped default, so in a lab deployment the honest
answer is "no sinter shim available on this host".

## How to use them

```python
import sinter
from qector_decoder_v3.sinter_compat import qector_sinter_decoders

custom = qector_sinter_decoders()          # the custom_decoders mapping
results = sinter.collect(
    num_workers=4,
    tasks=[...],
    custom_decoders=custom,                # name -> sinter.Decoder
    decoders=["qector_blossom", "qector_unionfind"],   # names, not objects
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
- `qector_bposd` -> BP-OSD; for non-graphlike inputs.

## How to probe

`qector-research.sinter_decoder_list` returns:

- `sinter_exposed` (bool): true only when the factory ran and
  returned shims
- `factory`: the module path of the factory, or null
- `sinter_installed` (bool)
- `sinter_decoders` (list of `{"name", "type"}`)
- `note` / `error` explaining a false `sinter_exposed`

On the pinned wheel without `sinter` the probe reports
`sinter_exposed: false`, `factory:
"qector_decoder_v3.sinter_compat.qector_sinter_decoders"`,
`sinter_installed: false`. Report exactly that; never list shim names
the probe did not return. Always probe on the target device before
publishing a sinter-based result.

## Reference manual quote

> qector_sinter_decoders() exposes qector_blossom, qector_belief,
> qector_unionfind, qector_bposd, and qector_unionfind_unweighted
> as sinter.Decoder entry points, so logical-error rates can be
> compared head-to-head in the community-standard harness with no
> QECTOR-specific tooling.

The manual's fifth name, `qector_unionfind_unweighted`, was missing
from the 1.0.0 wheel's factory and is present from 1.0.1. As always,
report the names the live probe returns, not the manual's list.

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
- `qector-research.artifact_metadata_check` checks a sweep
  artifact's chapter 22.3 metadata and sidecar (`artifact_path`),
  or returns the template a sinter-based artifact must carry.
