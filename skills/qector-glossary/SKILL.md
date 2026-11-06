---
name: qector-glossary
description: >-
  QECTOR terminology, notation, and symbols from the v1.0.0
  reference manual (Appendix A and B). Load for any question
  about what a term means, what symbol is used, or how the
  notation is written.
---

# QECTOR Glossary and Notation

> **Scope note (plugin 2.0.0).** File names such as `tests/test_*_faithfulness.py`,
> `scripts/competitive_*.py`, `docs/CORRECTNESS_AUDIT.md`, `docs/API_STABILITY.md`
> and `docs/RELEASING.md` cited below belong to the **upstream qector-decoder-v3
> source tree**, not to this plugin. The plugin's own executable gates are
> `tests/` (unittest), `scripts/release_validate.py`, `scripts/export_schemas.py
> --check`, `scripts/generate_integrity_manifest.py --check` and
> `mcp/tests/test_mcp_stdio.py`. Never claim a file exists here that this note
> attributes to the upstream tree.

Source of authority: v1.0.0 reference manual, Appendices A and B.

## Notation (Appendix A)

| Symbol       | Meaning                                                                                |
| ------------ | -------------------------------------------------------------------------------------- |
| F2           | Binary field {0, 1}                                                                    |
| H            | Parity-check matrix in F2^(m x n)                                                      |
| Hx, Hz       | CSS sector check matrices                                                               |
| s            | Syndrome vector s = H e (mod 2)                                                         |
| e            | True physical error vector                                                             |
| c            | Decoder correction vector                                                              |
| ker(H)       | Right kernel of H                                                                       |
| im(H^T)      | Row space of H; equals the stabilizer span of the sector only when `H H^T = 0` (self-dual) |
| L            | Logical-observable matrix                                                              |
| gamma_q      | Posterior LLR of qubit q                                                                |
| phi(x)       | Box-plus kernel -ln(tanh(x/2))                                                         |
| pi(C)        | Parity of fired detectors in cluster C                                                 |
| alpha(n)     | Inverse Ackermann function                                                              |
| w_uv         | Edge weight log((1-p)/p)                                                               |
| d_{c,t}      | Detector difference s_{c,t} xor s_{c,t-1}                                              |
| lambda       | Decay factor of the sliding window (0 <= lambda < 1)                                    |
| W            | OSD sweep width max(2 * osd_order, 6)                                                  |

## Glossary (Appendix B)

**Syndrome faithfulness.** The property `H c = s (mod 2)` for
reachable syndromes; the universal correctness gate of the
engine. Theorem 1.

**MWPM.** Minimum-weight perfect matching; the exact optimization
solved by the blossom decoder.

**Blossom.** An odd cycle of tight edges contracted during
Edmonds' algorithm.

**Graphlike code.** A code in which every qubit participates in
at most two checks; matching decoders apply.

**Hyperedge / non-graphlike.** A mechanism touching three or
more detectors; requires BP-OSD.

**BP-OSD.** Belief propagation followed by ordered-statistics
decoding over GF(2).

**OSD-0 / OSD-W.** Basis solve with free bits from BP hard
decisions / plus a combination sweep of width W.

**Union-Find decoding.** Cluster-growth decoding with
spanning-forest peeling.

**DEM.** Detector error model: the standard description of a
decoding problem.

**Collapse to graph.** Merging parallel mechanisms between the
same detector pair into one edge.

**Logical operator.** An undetectable error (in `ker(H)`) outside
the stabilizer span of its sector, i.e. one with `L e != 0` for the
sector's logical-observable matrix `L`; flipping it changes the
logical state undetectably. `ker(H) \ im(H^T)` is the same set only
for self-dual CSS codes (Steane), not for the graphlike `codes`
families, which is why every QECTOR tool scores with `L`.

**Wilson interval.** A binomial confidence interval with correct
coverage at small k.

**Bit identity.** GPU batch output equal to CPU reference output,
bit for bit, on tested configurations.

**Cascade.** A cheap faithful pre-filter with an exact fallback.

**MCP.** Model Context Protocol; the JSON-RPC stdio server
surface.

**CSS code.** Calderbank-Shor-Steane code with separate X and Z
sectors. The condition `Hx Hz^T = 0 (mod 2)` is the commutation
guarantee.

**Steane code.** The [[7,1,3]] CSS code, the smallest CSS
example on which every sector-level statement of chapters 3, 8,
9, and 12 can be verified by hand (manual 2.7, appendix E.1).

**Steane syndrome [1,1,0].** The syndrome of the error
`e = [0,0,0,0,0,1,0]` (qubit 5) on the Steane X-checks. A
canonical reference example.

**Rotated surface code.** A 2D surface code on a d x d grid with
weight-4 plaquette checks plus weight-2 boundary checks so that
each interior qubit is shared by two checks; one logical qubit
(the horizontal top-row string). Graphlike. Wheel defect (1.0.0):
`codes.rotated_surface_code(d)` has duplicate parity-check columns at
every d, so a weight-2 error is undetectable and the effective
distance is 2; the plugin marks the family `weak` and reports
`effective_distance` on every result.

**Unrotated surface code.** A 2D surface code on a d x d vertex
lattice; the canonical Z-stabilizer construction. The single-
sector matching graph in the v1.0.0 library has `k = 0`, so
`logicals_matrix()` is `None`; LER cannot be defined.

**Toric code.** A 2D code on an L x L torus with 2 L^2 qubits
on the edges and L^2 vertex checks; two logical qubits.

**Heavy-hex code.** A heavy-hex lattice interleaving data and
flag qubits on a brick-wall pattern; the v1.0.0 helper builds the
graphlike Z-sector.

**Color code.** A 2D colour code (textbook: triangular 6.6.6 with
k = 1 planar, 4.8.8 variants). Since wheel 1.0.1,
`codes.color_code(d)` is the triangular 6.6.6 code: odd d,
n = (3d²+1)/4, k = 1, distance d, not graphlike (1.0.0 exposed no
logical observables and was degenerate at d = 3). The plugin lists
it but does not offer it to its matching decoders.

**Hamming weight.** The number of 1s in a binary vector.

**Logical coset.** The equivalence class of a correction modulo the
sector's stabilizer span (`ker(H) / im(H^T)` for a self-dual code).
Two corrections in the same coset produce the same logical outcome;
QECTOR tests this as `L (c + e) = 0 (mod 2)`.

**Logical failure.** A non-trivial logical operator applied to
the state; the decoder returned a correction whose residual with
the true error satisfies `L (c + e) != 0 (mod 2)` (`decode_single`
and `threshold_sweep` report it as `logical_failure`).

**AutoDecoder.** The multi-tier self-debugging fallback chain in the
Python layer; `native_auto` is the Rust routing primitive.

**NativeAutoDecoder.** The Rust class for native routing with
license enforcement. The Python `AutoDecoder` is the multi-tier
self-debugging controller.

**Planted error.** A known error used in correctness tests; the
syndrome is computed as `s = H e (mod 2)` and the decoder is
expected to return a correction `c` with `H c = s` (Theorem 1)
and the same logical coset as `e` (Theorem 2).

**Stale test-count policy.** The shipped 0.5 validation report
(832 Python tests, 87 Rust tests) is marked stale for post-0.5
builds; the reader is pointed at the decoder tree's
`docs/CORRECTNESS_AUDIT.md` and its live suite. No current pass /
fail count is claimed.

**Withdrawn benchmark policy.** The competitive and throughput
tables published for earlier cores were withdrawn in the frozen
tree because the measured figures did not survive a core
fingerprint change. No performance number in the manual is
intended to replace a regenerated artifact.

**License tiers.** Community d<=7 (free, source-available),
Pro d<=19 (Ed25519-signed token), Enterprise d<=63 (Ed25519-
signed token, GPU/GNN paths).

**Token formats.** v2 (generic), `QECT-PRO-*` (Pro prefix),
`QECT-ENT-*` (Enterprise prefix). All verified offline in the
Rust core.

**Resolution order.** `QECTOR_LICENSE_KEY` ->
`QECTOR_LICENSE_FILE` -> `~/.qector/license.key`. A set-but-
unreadable `QECTOR_LICENSE_FILE` is invalid, not a silent
Community downgrade.

**Air-gapped by default.** All compute stays local via the MCP server (in-process guards, host egress rule for a hard guarantee). No
`.stim` / `.npy` / parity matrices leave the machine.
