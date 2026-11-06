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

## 2.0.0 release provenance chain

1. `requirements.lock` fixes the exact runtime closure; `scripts/build_wheelhouse.py`
   turns it into wheels with a `SHA256SUMS` that the offline installer verifies.
2. `INTEGRITY.json` (repository root and inside every archive) lists the SHA-256 of
   every runtime file; `qector-secure` refuses to start when it does not match.
3. `scripts/build_release.py` refuses to build from an uncommitted tree, writes
   `provenance.json` with the exact commit, uses fixed zip timestamps, and keeps
   `server.json` out of the archives so the build is a fixed point: two builds of
   the same commit are byte-identical (verified for all three artifacts).
4. `dist/SHA256SUMS`, per-artifact `.sha256` sidecars and the SPDX-2.3 SBOM over the
   full locked closure accompany every release.
5. Every archive's `INTEGRITY.json` and the release `SHA256SUMS` are signed
   (Ed25519, `scripts/sign_release.py`; key fingerprint in SECURITY.md and
   `release-manifest.json#signing`); the publish workflow adds a Sigstore
   keyless signature of `SHA256SUMS` to the public transparency log.
6. `RELEASE_COMMIT` inside every archive records the exact commit, so the
   MCPB rebuilds byte-identically from the source archive without `.git`.
7. `server.json` (MCP Registry descriptor) is rewritten by the publish workflow
   (`build_release.py --patch-server-json`) with the digest of the MCPB built at the
   tagged commit; the value committed in the repository is the last published one.
