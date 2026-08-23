# Provenance

`release-manifest.json` is the machine-readable release registry. It records
the public version, license, runtime pins, supported Claude surfaces, and
evidence hashes.

The release's normative mathematical source is **QECTOR Decoder v3 - Reference
Manual v1.0.0**, DOI `10.5281/zenodo.21941046`. The supplied external proof
suite is pinned by SHA-256 and covers Theorems 1-16, Appendix E arithmetic, and
live-wheel decoder faithfulness for `qector-decoder-v3==1.0.0`.

Validate a local copy of the evidence files without copying them into this
repository:

```bash
python scripts/release_validate.py \
  --manual /path/QectorDecoder_v3_Reference_Manual_v1.0.0.pdf \
  --proof-suite /path/test_qector_decoder_v3_proofs.py
```

The plugin license, decoder-wheel license, third-party dependency licenses,
and reference-manual terms are separate artifacts and must not be conflated.
