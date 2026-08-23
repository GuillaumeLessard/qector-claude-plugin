---
name: qector-decoders-deep-dive
description: >-
  Per-decoder internals from the v1.0.0 reference manual. For each of the
  fifteen specialised backends, gives the algorithm, the theorem(s) it
  inherits, its claim boundary, and a one-line code snippet. Load when a
  question asks "how does X work", "which decoder is right for Y", or
  "what is the difference between A and B" at the algorithmic level
  (manual chapters 4-13).
---

# QECTOR Decoders Deep Dive

Ground every answer in the v1.0.0 reference manual (DOI
`10.5281/zenodo.21941046`). The summary below mirrors Table 4.1 and the
per-decoder chapters. The **Claim boundary** column is normative; a
statement that is not explicitly scoped there is not made.

## Universal contract

Every decoder shares the same input/output contract (manual 4):

- `check_to_qubits`: list of lists; one entry per check, each a list of
  qubit indices. `n_qubits` is optional when inferable.
- `syndrome`: 1D `uint8` array.
- `correction`: 1D `uint8` array of length `n_qubits`.
- Correctness: `H c = s (mod 2)` for reachable syndromes (Theorem 1).

## The five stable decoders (manual 16.1)

| Name          | Class                  | Domain        | Algorithm                                | Claim boundary                                        |
| ------------- | ---------------------- | ------------- | ---------------------------------------- | ----------------------------------------------------- |
| union_find    | `UnionFindDecoder`     | graphlike     | cluster growth + spanning-forest peel    | faithful on matching graphs; not minimum-weight       |
| fast_union_find | `FastUnionFindDecoder` | graphlike   | lower-overhead path; bit-identical       | same as `union_find`                                   |
| blossom       | `BlossomDecoder`       | graphlike     | exact weighted MWPM (Edmonds primal-dual)| exact on audited small matching codes                 |
| sparse_blossom| `SparseBlossomDecoder` | graphlike     | event-driven region growth on radix heap | faithful; near-optimal (>= 99% of exact on small)     |
| native_auto   | `NativeAutoDecoder`    | any           | native routing with license enforcement  | routes; contract inherited from the target backend    |

## Provisional decoders (manual 16.2 — labelled, never quoted as contract)

| Name             | Class                       | Notes                                                     |
| ---------------- | --------------------------- | --------------------------------------------------------- |
| bposd            | `BPOSDDecoder`              | sum-product / min-sum BP + OSD-0/W; qLDPC, hyperedges     |
| batch            | `CPUBatchDecoder` / `BatchDecoder` | batch shape stable; performance workload-sensitive  |
| cuda_batch       | `CUDABatchDecoder`          | per-thread port of UF; bit-identity tested                |
| opencl_batch     | `OpenCLBatchDecoder`        | source build only; bit-identity tested                    |
| cuda_bposd       | `CUDABpOsdDecoder`          | batched BP+OSD; single-shot CPU preferred                 |
| lookup_table     | `LookupTableDecoder`        | exhaustive for n_qubits <= 20; UF fallback                |
| ambiguity_cluster| `AmbiguityClusterDecoder`   | BP + exact enumeration on clusters <= 12                  |
| two_stage        | `TwoStageDecoder`           | X/Z sector coupling for depolarising noise                 |
| space_time       | `SpaceTimeDecoder`          | (2+1)D detector-lattice matching                          |
| streaming        | `StreamingDecoder`          | OR-accumulated history (simulation workflow)              |
| sliding_window   | `SlidingWindowDecoder`      | exponentially decayed window; bounded tail                |
| auto             | `AutoDecoder`               | 7-tier self-debugging fallback (behaviour, not contract)  |
| hybrid_cascade   | `HybridCascadeDecoder`      | UF pre-filter with exact fallback                         |
| hybrid           | `HybridDecoder`             | GNN-weighted sparse blossom (research-grade)              |

## Theorems each decoder inherits (manual chapters 3, 5-13)

- **All matching decoders** inherit Theorems 1, 2, 3 (manual 3.1-3.3).
- **Sparse Blossom** adds Theorem 5 (region-growth invariant, manual 6.2),
  Theorem 6 (tight-edge restriction, manual 6.4), and Theorem 7
  (sparse-algorithm correctness, manual 6.6). The shipped implementation
  is documented as **near-optimal**, not exact on every instance.
- **Union-Find** adds Theorem 8 (cluster parity, manual 7.1), Theorem 9
  (peeling correctness, manual 7.3), and Theorem 10
  (`O(n alpha(n))` time, zero-allocation hot path, manual 7.3 / 7.4).
- **BP-OSD** adds Theorem 11 (residual-solve faithfulness, manual 8.2)
  — the algebraic guarantee is independent of BP convergence quality.
- **Ambiguity Cluster** adds Theorem 12 (component-wise partition,
  manual 9.2).
- **Two-Stage** adds Theorem 13 (CSS sector faithfulness, manual 12.1).
- **Space-Time** adds Theorem 13 (lifting faithfulness, manual 10.2).
- **AutoDecoder** adds Theorem 14 (dispatch faithfulness, manual 11.1).
- **GPU batch** adds Theorem 16 (bit-identity, manual 13.2) for
  graphlike codes on the unweighted path; the weighted path is
  validated by the bit-identity regression on tested configurations.

## Choosing a decoder (manual 11.1 routing policy)

1. Compute `max_qubit_degree` of the parity-check structure.
2. If `> 2`, route to `bposd` (the only decoder defined for arbitrary
   GF(2) matrices). Matching decoders are not eligible.
3. If graphlike, pick by accuracy/speed/balanced priority:
   - **accuracy**: small/moderate codes -> `blossom` (exact); large ->
     `sparse_blossom` (near-optimal, faster).
   - **speed**: `fast_union_find` (single-shot) or `cuda_batch` (large
     batches on hardware-gated platforms).
   - **balanced**: interpolate by batch size and code size; the Python
     `AutoDecoder` controller does this with a 7-tier self-debugging
     chain.
4. The `native_auto` Rust class is the routing primitive; the Python
   `AutoDecoder` is the 7-tier self-debugging controller (manual 11.2).
   `native_auto` enforces the license tier at construction time.

## Worked examples (manual 5.4, 7.5, 8.4)

- **Ring d=5, syndrome [1,0,1,0,0]**: short arc through qubits 1,2
  gives `c = [0,1,1,0,0]`; `H c = s` (manual 5.4).
- **Repetition d=5, syndrome [1,0,0,0]**: left boundary edge
  `c = [1,0,0,0,0]`; parity absorbed by virtual boundary (manual 7.5).
- **BP-OSD residual (manual 8.5)**: `H = [[1,1,0],[0,1,1]]`,
  `s = [1,0]`, BP proposes `e_hard = [1,0,0]`, residual zero, decode
  returns immediately. If BP proposed `[0,1,0]` instead, residual
  `[0,1]` forces `c = [0,1,1]`; `H c = s` either way.

## Common pitfalls

- **Non-graphlike input to a matching decoder** -> the decoder raises
  or returns an unfaithful result. Verify `code.is_matching_graph()` or
  the library `qector-research.code_family_info` first.
- **Hard-coding a check count** -> always read `code.n_checks` /
  `code.n_qubits` at runtime (manual 16.1 + M3).
- **Comparing code_capacity to circuit_level LER** -> refused by the
  competitive harness (manual 15.3); tag the run before comparing.
- **Calling the Workbench decoder names** without first running
  `tools/list` on the target device -> never assume; the Workbench
  surface is device-local (manual 17.5).
