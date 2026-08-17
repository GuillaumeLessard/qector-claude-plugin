---
name: qector-math-foundations
description: >-
  The strict mathematical ground rules for every QECTOR claim. Encodes
  the F2 notation, the 16 correctness theorems, the Wilson score interval for LER,
  the required-artifact-metadata contract, safe-wording rules, and the published
  limitations that must travel with every claim (reference manual v1.0.0, DOI
  10.5281/zenodo.21941046). Load whenever any number, theorem, comparison, or
  benchmark is produced, repeated, or quoted - the rules here are the authority
  and nothing may contradict them.
---

# QECTOR Math Foundations - Strict Ground Truth Rules

Source of authority: QECTOR Decoder v3 reference manual v1.0.0 (DOI
`10.5281/zenodo.21941046`), chapters 2, 3, 4-13, 15, 19, 20, 22. The source
document is not redistributed here. These rules are **normative**: every
statement the plugin produces must satisfy them.

## Rule M0 - Provenance and resolve

- All arithmetic is over the binary field F2 = {0, 1}; addition is XOR (mod 2),
  multiplication is AND. Vectors are columns by default.
- Syndrome faithfulness is written **H c = s (mod 2)**.
- ker(H) = { v : H v = 0 }. In the stabilizer/CSS setting, where the relevant
  checks are self-orthogonal (`H H^T = 0`), im(H^T) is a subspace of ker(H);
  only then does ker(H) \ im(H^T) describe non-trivial logical operators.
  Arbitrary matrices require code-provided stabilizer and logical matrices.
- A claim only exists if you can point to (a) this manual/theorem, (b) a live
  execution recorded in this package, or (c) a surviving artifact with the
  metadata of Rule M5. Otherwise mark it "not verified".

## Rule M1 - The core theorems (chapter 3)

- **Theorem 1 (syndrome faithfulness and correction validity).** For H in
  F2^(m x n), true error e in F2^n, syndrome s = H e: a decoder returning c is
  faithful iff H c = s; moreover H c = s implies c + e in ker(H).
- **Theorem 2 (logical error criterion).** For a valid stabilizer/CSS sector
  with rank(H) = r, self-orthogonal checks, and H c = H e = s, decoding is
  *logically correct* iff c + e in im(H^T); a logical error occurs iff
  c + e in ker(H) \ im(H^T). Score on the logical coset, never on raw
  correction equality (degeneracy is respected). For arbitrary input matrices,
  use the code-provided stabilizer/logical matrices instead.
- **Theorem 3 (path-flipping faithfulness of MWPM).** For non-empty defect set
  D and M a minimum-weight perfect matching on the decoding graph, the
  correction is faithful: H c = s.
- Exactness: Blossom = exact weighted MWPM on audited small matching graphs.
  Theorems 1-3 establish faithfulness and the logical-error partition; they do
  NOT establish optimality or threshold claims on arbitrary graphs.

## Rule M2 - Additional theorems (chapters 5-13)

4. Path-flipping guarantee for matching; 5-7. Sparse-blossom region-growth
collision and tight-edge completeness; 8-9. Cluster parity and spanning-tree
peeling (H c = s); 10. Union-Find amortized O(n alpha(n)) time, O(V+E) space;
11. BP-OSD residual-solve faithfulness (independent of BP convergence quality);
12. Ambiguity-cluster parity decomposition; 13. Space-time lifting faithfulness
(joint X/Z sector faithfulness under two-stage CSS); 14. AutoDecoder dispatch
faithfulness H c = s whenever any eligible backend can satisfy it;
15. Two-stage sector faithfulness; 16. Bit-identity of batch kernels: for any
graphlike code and syndrome, unweighted batch kernels give c_GPU(s) = c_CPU(s).

Cite by number (e.g. "Theorem 14"), never paraphrase a theorem as your own.

## Rule M3 - Verified-API-only math (chapter 16)

- Only stable symbols may appear in delivered code: `UnionFindDecoder`,
  `FastUnionFindDecoder`, `BlossomDecoder`, `SparseBlossomDecoder`,
  `NativeAutoDecoder`, `generate_repetition_code_checks`,
  `generate_ring_code_checks`, `generate_surface_code_checks`,
  `set_license_key` / `get_license_info`, `record_shots` /
  `get_accumulated_shots`, `DecodeResult`.
- Provisional symbols (BpOsdDecoder tuning kwargs, batch/streaming/GPU decoders,
  AutoDecoder ordering, and upstream network services) may be used but must be
  labelled Provisional and never quoted as contract. The bundled local stdio
  MCP wrapper is the supported service surface in this package.
- Verified-but-non-frozen wheel surfaces exist and are real (rest_api HTTP
  routes, run_grpc_server, start_metrics_server, decode_mmap,
  get_decoder/get_decoder_pool/clear_decoder_cache, opencl_is_available -
  see qector-core `references/qector_verified_api.md`): treat them as
  Provisional, never as stable contract.
- Legacy generators return `(checks, n_qubits)` tuples - unpack before
  passing to a decoder.
- `seed=` is not a kwarg of `random_error`; use rng=np.random.default_rng(seed).
  `logicals_matrix()` and `parity_check_matrix()` are methods (call them).

## Rule M4 - LER methodology (chapter 15)

- Every LER report must carry: circuit generator or .stim file; DEM settings
  (decompose_errors, graphlike collapse); distance and rounds; physical noise
  value; shots and seed; logical errors and LER; a confidence interval; reference
  package versions; environment block.
- Report the **Wilson score interval at 95%** with z = 1.959963985:

      CI = ( p + z^2/(2n) +/- z*sqrt( p(1-p)/n + z^2/(4n^2) ) ) / (1 + z^2/n)

  The Wilson interval never leaves [0,1] and keeps coverage at small k and
  extreme p (Wald does not).
- Tag results `code_capacity` or `circuit_level`; **refuse to compare across
  models**. A large-n screening estimate is not a converged LER; say "screening
  estimate" when n does not support a statement of accuracy.

## Rule M5 - Required artifact metadata (chapter 22.3)

Every evidence artifact must include: code family; distance/size (rounds,
checks, qubits, detectors); noise model + tag; decoder exact class and mode
(weighted/batch/GPU flags); sample count (trials, shots, warmup, seed); metric
(correctness, LER, latency, throughput, memory, bit-identity, scaling);
environment (OS, CPU, RAM, package versions, git commit); artifact (raw
JSON/CSV path plus an externally recorded SHA-256 manifest or sidecar). A benchmark without these fields is a smoke test,
not public evidence.

## Rule M6 - Safe wording (chapter 22.5)

- Safe: "on this machine, for this code/distance/noise/seed/batch configuration,
  decoder A had median hot-path latency X and p99 Y."
- **Unsafe and never published:** "decoder A is universally faster". No speed
  superlative without a surviving artifact.

## Rule M7 - Limitations that travel with every claim (chapter 20)

1. No bundled pass/fail count or portable performance result is claimed.
2. Performance figures are hardware-dependent and require a fresh artifact.
3. GPU, OpenCL, streaming, and learned-decoder behavior must be checked on the
   target device and kept within the manual's stated scope.
4. Network services beyond this local stdio wrapper are Provisional and require
   deployment review before production use.

## Rule M8 - Binary p/h, weights, honesty

- DEM edge weight = log((1-p)/p); collapse of two mechanisms keeps the
  observable set of the more likely member. Never fabricate a weight.
- `cuda_is_available()` / `CUDABatchDecoder.is_available()` report hardware;
  licensing is a separate gate. Report live `get_license_info` and any
  target-device hardware response instead of hard-coding a tier.

Grounding check for every deliverable: each number is traceable to M0-M8. If it
is not, say so. Sanity-check with the manual's worked examples (Appendix E:
Steane syndrome [1,1,0]; Wilson interval worked by hand: 10/1000 errors ->
(0.00544, 0.01831); DEM collapse 0.01/0.02 -> p=0.0296, weight 3.489).
