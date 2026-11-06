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

## Before publishing

`qector-decoder-v3==1.0.1` must be on PyPI before a plain `pip install -r
requirements.lock` works off the bundled Desktop extension. The lock carries the
Linux x86_64 digests of the release-build wheels; run `scripts/update_lock.py`
after the decoder's release workflow publishes all 18 wheels to add Windows and
macOS, then rebuild.

See `CHANGELOG.md` for the full list.
