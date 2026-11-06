# QECTOR Claude Plugin 2.0.1 — release notes

**Theme: the backend caught up.** 2.0.0 measured every code family's distance
live and found the decoder wheel's labels wrong (rotated surface code at
distance 2 for every d, unrotated and colour codes with no logical qubit).
`qector-decoder-v3` 1.0.1 fixes those upstream, along with its Union-Find
peeling, GPU parity, Sinter entry points and network isolation. 2.0.1 pins it.

## What changes for users

1. `rotated_surface`, `unrotated_surface`, `heavy_hex` and `color_code` now
   report `ok` at their labelled distance; threshold sweeps on the wheel's
   own families show real distance scaling.
2. `color_code` is listed with `single_decode: false`: it is a genuine 6.6.6
   colour code now, and not graphlike.
3. In air-gapped mode the decoder's native core is also switched offline
   (`QECTOR_OFFLINE=1`); `airgap_status` shows `wheel_offline_flag: true`.
4. The licensing skill reflects 1.0.1 entitlements: every paid (Pro or
   Enterprise) token unlocks GPU batch decoding.
5. Tool names, profiles, envelopes and every schema except `airgap_status`
   (one added boolean) are unchanged.

## Install and verify

- `qector-decoder-v3==1.0.1` is on PyPI (18 wheels, CPython 3.9-3.14, Linux,
  Windows, macOS, each with PyPI provenance). `requirements.lock` pins every
  dependency by SHA-256 for Python 3.10-3.13 on Linux, Windows and macOS:
  `pip install --require-hashes -r requirements.lock`.
- `qector-claude-desktop-2.0.1-bundled-linux-x86_64-py313.mcpb` carries an
  offline wheelhouse; the decoder wheel in it is byte-identical to PyPI's.
- Verify the release: `sha256sum -c` against `SHA256SUMS`, then
  `python scripts/sign_release.py --verify . --pubkey kYwkMApz4zMgQmJsOya1UZuByvnuikzlxQkQiA8NOJg=`
  (full key and fingerprint `6726953d…99dc` in `release-manifest.json`).
