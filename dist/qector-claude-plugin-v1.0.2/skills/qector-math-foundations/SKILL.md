---
name: qector-math-foundations
description: >-
  The strict mathematical ground rules for every QECTOR claim.
  Encodes the F2 notation, the 16 correctness theorems, the
  Wilson 95% score interval for LER, the required-artifact-
  metadata contract, safe-wording rules, and the published
  limitations that must travel with every claim (reference
  manual v1.0.0, DOI 10.5281/zenodo.21941046). Load whenever
  any number, theorem, comparison, or benchmark is produced,
  repeated, or quoted - the rules here are the authority and
  nothing may contradict them.
---

# QECTOR Math Foundations - Strict Ground Truth Rules

Source of authority: QECTOR Decoder v3 reference manual v1.0.0 (DOI
`10.5281/zenodo.21941046`), chapters 2, 3, 4-13, 15, 19, 20, 22.
The source document is not redistributed here. These rules are
**normative**: every statement the plugin produces must satisfy
them.

## Rule M0 - Provenance and resolve

- All arithmetic is over the binary field F2 = {0, 1}; addition is
  XOR (mod 2), multiplication is AND. Vectors are columns by
  default.
- Syndrome faithfulness is written **H c = s (mod 2)**.
- `ker(H) = { v : H v = 0 }`. In the stabilizer / CSS setting,
  where the relevant checks are self-orthogonal (`H H^T = 0`),
  `im(H^T)` is a subspace of `ker(H)`; only then does
  `ker(H) \ im(H^T)` describe non-trivial logical operators.
  Arbitrary matrices require code-provided stabilizer and logical
  matrices.
- A claim only exists if you can point to (a) this manual /
  theorem, (b) a live execution recorded in this package, or
  (c) a surviving artifact with the metadata of Rule M5.
  Otherwise mark it "not verified".

## Rule M1 - The core theorems (chapter 3)

- **Theorem 1 (syndrome faithfulness and correction validity)**.
  For `H` in F2^(m x n), true error `e` in F2^n, syndrome
  `s = H e`: a decoder returning `c` is faithful iff `H c = s`;
  moreover `H c = s` implies `c + e` in `ker(H)`.
- **Theorem 2 (logical error criterion)**. For a valid
  stabilizer / CSS sector with `rank(H) = r`, self-orthogonal
  checks, and `H c = H e = s`, decoding is *logically correct*
  iff `c + e` in `im(H^T)`; a logical error occurs iff
  `c + e` in `ker(H) \ im(H^T)`. Score on the logical coset,
  never on raw correction equality (degeneracy is respected).
  For arbitrary input matrices, use the code-provided stabilizer
  / logical matrices instead.
- **Theorem 3 (path-flipping faithfulness of MWPM)**. For
  non-empty defect set `D` and `M` a minimum-weight perfect
  matching on the decoding graph, the correction is faithful:
  `H c = s`.
- Exactness: Blossom = exact weighted MWPM on audited small
  matching graphs. Theorems 1-3 establish faithfulness and the
  logical-error partition; they do **NOT** establish optimality
  or threshold claims on arbitrary graphs.

## Rule M2 - Additional theorems (chapters 5-13)

4. **Theorem 4 (manual 5.3)**: path-flipping guarantee for
   matching; the path-flipping theorem and the matching
   primal/dual LP.
5. **Theorem 5 (manual 6.2)**: sparse-blossom region-growth
   invariant; `dy_R/dt` in {+1, 0, -1} by state.
6. **Theorem 6 (manual 6.4)**: sparse-blossom tight-edge
   restriction; an MWPM at time `t` can be chosen inside
   `E_tight(t)`.
7. **Theorem 7 (manual 6.6)**: sparse-algorithm correctness;
   the event-driven algorithm returns a minimum-weight perfect
   matching on `K_D`.
8. **Theorem 8 (manual 7.1)**: cluster parity algebra; for
   disjoint clusters `pi(C_1 union C_2) = pi(C_1) xor pi(C_2)`.
9. **Theorem 9 (manual 7.3)**: peeling correctness; a spanning
   tree of each grown cluster, peeled leaf-to-root, produces a
   correction with `H c = s (mod 2)`.
10. **Theorem 10 (manual 7.3 / 7.4)**: Union-Find amortized
    `O(n alpha(n))` time, `O(V + E)` space, no heap allocation
    in the steady-state hot path.
11. **Theorem 11 (manual 8.2)**: BP-OSD residual-solve
    faithfulness; independent of BP convergence quality; LLRs
    only influence which coset is selected, never whether
    `H c = s` holds.
12. **Theorem 12 (manual 9.2)**: ambiguity-cluster parity
    decomposition; `H c = s (mod 2)` for the combined
    correction, independent of the threshold `tau`.
13. **Theorem 13 (manual 10.2 / 12.1)**: space-time lifting
    faithfulness; joint X / Z sector faithfulness under two-
    stage CSS.
14. **Theorem 14 (manual 11.1)**: AutoDecoder dispatch
    faithfulness; `H c = s` whenever any eligible backend can
    satisfy it.
15. **Theorem 15 (manual 12.1)**: two-stage sector faithfulness;
    combined correction `c = c_X xor c_Z` is faithful for the
    joint CSS code.
16. **Theorem 16 (manual 13.2)**: bit-identity of batch kernels;
    for any graphlike code and syndrome, unweighted batch
    kernels give `c_GPU(s) = c_CPU(s)`.

Cite by number (e.g. "Theorem 14"), never paraphrase a theorem as
your own.

## Rule M3 - Verified-API-only math (chapter 16)

- **Stable symbols** (manual 16.1) may appear in delivered code:
  `UnionFindDecoder`, `FastUnionFindDecoder`, `BlossomDecoder`,
  `SparseBlossomDecoder`, `NativeAutoDecoder`,
  `generate_repetition_code_checks`, `generate_ring_code_checks`,
  `generate_surface_code_checks` (legacy toric-weight-4),
  `set_license_key` / `get_license_info`, `record_shots` /
  `get_accumulated_shots`, `DecodeResult`.
- **Provisional symbols** (manual 16.2) may be used but must be
  labelled Provisional and never quoted as contract:
  `BpOsdDecoder` tuning kwargs, `CPUBatchDecoder` / `BatchDecoder`,
  `StreamingDecoder` / `SlidingWindowDecoder`, `AutoDecoder`
  (7-tier ordering is behaviour, not contract), the GPU batch
  decoders, and the upstream network services (REST, gRPC, MCP,
  metrics). The bundled local stdio MCP wrapper is the supported
  service surface in this package.
- **Verified-but-non-frozen wheel surfaces** (manual 16.2, all
  Provisional) include `rest_api.py` (FastAPI HTTP), `run_grpc_server`,
  `start_metrics_server`, `decode_mmap`,
  `get_decoder` / `get_decoder_pool` / `clear_decoder_cache`,
  `opencl_is_available`, `qiskit_plugin`. Verify by introspection
  on the target device; never assume.
- Legacy generators return `(checks, n_qubits)` tuples - unpack
  before passing to a decoder.
- `seed=` is not a kwarg of `random_error`; use
  `rng=np.random.default_rng(seed)`.
- `logicals_matrix()` and `parity_check_matrix()` are methods
  (call the parens).
- Library MCP **8 tools** are frozen at v1.0.0
  (`list_code_families`, `list_decoders`, `get_license_info`,
  `decode_syndrome`, `decode_single`, `threshold_sweep`,
  `build_code_from_matrix`, `compat_report`).
  Companion bench server tools (`qector-bench.*`) are
  Provisional, never quoted as contract.

## Rule M4 - LER methodology (chapter 15)

- Every LER report must carry: circuit generator or .stim file;
  DEM settings (decompose_errors, graphlike collapse);
  distance and rounds; physical noise value; shots and seed;
  logical errors and LER; a confidence interval; reference
  package versions; the environment block.
- Report the **Wilson 95% score interval** with
  `z = 1.959963985`:

      CI = ( p + z^2/(2n) +/- z*sqrt( p(1-p)/n + z^2/(4n^2) ) ) / (1 + z^2/n)

  The Wilson interval never leaves [0, 1] and keeps coverage at
  small `k` and extreme `p` (Wald does not). The
  `qector-bench.wilson_ci` tool returns exactly the manual
  values; `qector-bench.wilson_table` is the batch utility.
- Tag results `code_capacity` or `circuit_level`; **refuse to
  compare across models**. A large-n screening estimate is not
  a converged LER; say "screening estimate" when n does not
  support a statement of accuracy.
- LER scoring: `correction != error` is **explicitly rejected**
  (manual 15). Use the logical-observable matrix (Theorem 2).

## Rule M5 - Required artifact metadata (chapter 22.3)

Every evidence artifact must include: code family;
distance/size (rounds, checks, qubits, detectors); noise model
+ tag; decoder exact class and mode (weighted / batch / GPU
flags); sample count (trials, shots, warmup, seed); metric
(correctness, LER, latency, throughput, memory, bit-identity,
scaling); environment (OS, CPU, RAM, package versions, git
commit); artifact (raw JSON / CSV path plus SHA-256 sidecar).
A benchmark without these fields is a smoke test, not public
evidence. `qector-bench.artifact_metadata_check` generates the
block; `qector-library.threshold_sweep` already emits the
block plus the SHA-256 sidecar.

## Rule M6 - Safe wording (chapter 22.5)

- **Safe**: "on this machine, for this code/distance/noise/seed/
  batch configuration, decoder A had median hot-path latency X
  and p99 Y."
- **Unsafe and never published**: "decoder A is universally
  faster". No speed superlative without a surviving artifact.

## Rule M7 - Limitations that travel with every claim (chapter 20)

1. **Test-count claims**. The frozen tree records a v0.5 local
   validation report of 832 Python and 87 Rust tests, but the
   tree itself marks that table stale for post-0.5 builds. No
   current pass / fail count is claimed; the reader is pointed
   at `docs/CORRECTNESS_AUDIT.md` and the live suite.
2. **Performance**. All latency, throughput, memory, and GPU
   figures in the earlier manual and in the benchmark
   artifacts are hardware-dependent and were withdrawn for the
   current core; none are reproduced here.
3. **GPU contexts**. The native CUDA batch path creates a
   driver-API context while CuPy uses the primary context. A
   known intermittent access violation was observed when both
   paths are exercised in one process under load on one tested
   configuration; the documented workaround is to run the two
   workloads in separate processes or hide the device for
   monolithic suite runs.
4. **OpenCL distribution**. Published wheels are CUDA-only by
   design; OpenCL requires a documented source build.
   `opencl_is_available()` probes in a child process because
   some drivers abort during kernel setup.
5. **Streaming scope**. The Python streaming layer and the Rust
   streaming primitives decode per-round or windowed syndromes;
   they do not implement full circuit-level space-time matching
   unless the 3D `SpaceTimeDecoder` is used.
6. **Learned decoders**. Neural / GNN surfaces are research-
   grade and training-dependent; their accuracy effect is not
   claimed without a surviving artifact.
7. **Network surfaces**. REST, gRPC, MCP, and metrics are
   Provisional and require a deployment review before
   production use.
8. **Known hypergraph rejection**. Union-Find family decoders
   reject codes in which any qubit participates in more than
   two checks; this is an explicit contract, not a bug, and the
   correct path for such codes is BP-OSD.

## Rule M8 - Binary p/h, weights, honesty

- DEM edge weight = `log((1-p)/p)`; collapse of two mechanisms
  keeps the observable set of the more likely member. Never
  fabricate a weight.
- `cuda_is_available()` / `CUDABatchDecoder.is_available()` report
  hardware; licensing is a separate gate. Report live
  `get_license_info` and any target-device hardware response
  instead of hard-coding a tier.
- License tier limits are enforced in the Rust core:
  Community d<=7, Pro d<=19, Enterprise d<=63.
- The shipped wheel's compatibility report and the
  `qector-bench.hardware_probe` / `qector-bench.license_active_check`
  tools return the live state on the target device; never
  assume a value from another machine.

## Symbol table (Appendix A)

| Symbol       | Meaning                                       |
| ------------ | --------------------------------------------- |
| F2           | Binary field {0, 1}                           |
| H            | Parity-check matrix in F2^(m x n)             |
| Hx, Hz       | CSS sector check matrices                      |
| s            | Syndrome vector s = H e (mod 2)               |
| e            | True physical error vector                    |
| c            | Decoder correction vector                     |
| ker(H)       | Right kernel of H                              |
| im(H^T)      | Row space of H (stabilizer span)              |
| L            | Logical-observable matrix                     |
| gamma_q      | Posterior LLR of qubit q                       |
| phi(x)       | Box-plus kernel -ln(tanh(x/2))                |
| pi(C)        | Parity of fired detectors in cluster C        |
| alpha(n)     | Inverse Ackermann function                     |
| w_uv         | Edge weight log((1-p)/p)                      |
| d_{c,t}      | Detector difference s_{c,t} xor s_{c,t-1}     |
| lambda       | Decay factor of the sliding window (0<=lambda<1) |
| W            | OSD sweep width max(2 * osd_order, 6)         |

## Grounding check for every deliverable

Each number is traceable to M0-M8. If it is not, say so.
Sanity-check with the manual's worked examples:

- Steane syndrome `[1,1,0]` for the error `[0,0,0,0,0,1,0]`
  (Appendix E.1).
- Wilson interval for 10 errors in 1000 shots:
  `(0.00544, 0.01831)` (Appendix E.2).
- DEM collapse: `p1=0.01, p2=0.02` -> `p=0.0296`, weight
  `3.489` (Appendix E.3).
- Two-stage CSS `Hx = [[1,1,0],[0,1,1]]`, `Hz = [[0,1,1],[1,1,0]]`,
  `H_{Z,X} = [[0,1,0],[1,0,0]]`, `s_X = [1,0]` -> `c = [0,1,1]`
  (Appendix E.4).
