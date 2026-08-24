# QECTOR Verified API Reference

Source of truth: the QECTOR Decoder v3 reference manual v1.0.0 (DOI
`10.5281/zenodo.21941046`), the public library API, and device-local
validation runs. The reference manual is not
redistributed here. Do not treat unverified claims as fact.

## Library - qector_decoder_v3 (app-free)

### Stable decoders (manual 16.1)
```
import numpy as np
from qector_decoder_v3 import (
    UnionFindDecoder, FastUnionFindDecoder, BlossomDecoder,
    SparseBlossomDecoder, NativeAutoDecoder,
    generate_repetition_code_checks, generate_ring_code_checks,
    generate_surface_code_checks,
)
checks = [[0, 1], [1, 2], [2, 3], [3, 4]]        # repetition code, d = 5
syndrome = np.array([0, 1, 0, 0], dtype=np.uint8)
corr = BlossomDecoder(checks, n_qubits=5).decode(syndrome)   # H @ corr == s
```
Constructors: `(c2q, n_qubits=None, edge_weights=None)`; `decode(syndrome) ->
np.ndarray`. `generate_surface_code_checks(d)` is legacy toric-weight-4, NOT
graphlike - use `codes.rotated_surface_code(d)` for a graphlike surface code.

**Legacy generators return `(checks, n_qubits)` tuples** - unpack before use,
never pass the tuple as `c2q`. All three are verified to decode correctly on
the shipped wheel:

```
checks, n = generate_repetition_code_checks(5)   # (4 checks, weight 2, n = 5)
checks, n = generate_ring_code_checks(6)         # (36 checks, weight 2, n = 36)
checks, n = generate_surface_code_checks(3)      # (18 checks, weight 4, n = 9)
corr = BlossomDecoder(checks, n_qubits=n).decode(syndrome)
```

The legacy surface checks are toric-weight-4 (all checks weight 4, verified by
row-weight inspection), i.e. NOT graphlike.

**Composition with `codes`-module codes:** the `c2q` constructor argument is
the check-to-qubits mapping (list of qubit indices per check). Pass
`Code.check_to_qubits` - never `Code.parity_check_matrix()`. Feeding the raw
H matrix raises an opaque `ValueError` ("The truth value of an array with more
than one element is ambiguous"):

```python
c = codes.rotated_surface_code(5)
dec = BlossomDecoder(c.check_to_qubits, n_qubits=c.n_qubits)  # NOT c.parity_check_matrix()
corr = dec.decode(syndrome)                                   # H @ corr == s (mod 2)
```

### codes module (verify on the target device)
```
>>> from qector_decoder_v3 import codes
>>> c = codes.rotated_surface_code(5)
>>> c.n_qubits
>>> c.n_checks
```
`Code` attributes: `check_to_qubits`, `description`, `distance`,
`n_checks`, `n_qubits`, `name`, `qubit_weights`, ... Methods (call with
parens): `H()`, `is_matching_graph()`, `parity_check_matrix()`,
`logicals_matrix()`, `random_error(p, rng=rng)`, `syndrome(error)`. `H()`
returns the same matrix as `parity_check_matrix()`; `H` itself is a bound
method, not a matrix. `seed=` is NOT valid; use
`rng=np.random.default_rng(seed)`.

**Matching-graph codes:** `rotated_surface_code(d)`, `unrotated_surface_code(d)`,
`toric_code(d)`, `heavy_hex_code(d)`, and `color_code(d)` return single-sector
matching-graph codes (`is_matching_graph()` is True) whose H is not
self-orthogonal: H H^T != 0 (e.g. `rotated_surface_code(5)` has a 12 x 25 H).
They use the arbitrary-matrix/logical-coset branch of Theorem 2, not the
self-orthogonal branch.

**Logicals are per-code - verify, never assume:** `num_logical_qubits` and
`logicals_matrix()` differ by family. `rotated_surface_code(d)` reports
`num_logical_qubits == 1` with an ndarray; `toric_code(d)` reports 2;
`color_code(d)` AND `unrotated_surface_code(d)` both report
`num_logical_qubits == 0` with `logicals_matrix() is None` (verified). When a
code provides no logicals matrix, the Theorem-2 logical-coset scoring needs an
explicitly constructed logical basis (or an explicit statement that it is
unavailable) - check per family, do not generalize from one code.

### DEM / routing / shims (manual 16.4-17, optional direct-wheel APIs)

These surfaces are outside the default eight-tool MCP contract. Install and
introspect their optional dependencies and APIs on the target device before
using them; no Stim/DEM package is required for the library MCP server.
- `pymatching_compat.Matching` drop-in (from_check_matrix,
  from_detector_error_model, add_edge, add_boundary_edge, decode,
  decode_batch, decode_to_edges_array).
- `qector_sinter_decoders()` -> qector_blossom, qector_belief,
  qector_unionfind, qector_bposd, qector_unionfind_unweighted.
- License: `set_license_key(key)` (raises on invalid), `get_license_info()`;
  metered telemetry `record_shots(n)` / `get_accumulated_shots()`; structured
  results `DecodeResult`. GPU: `CUDABatchDecoder.is_available()` is hardware;
  license tier is a separate gate. Wheels are CUDA-only; OpenCL = source build.

### Verified wheel surfaces outside the 8-tool contract (all provisional)

Real, present, and typed on the shipped wheel - verified by module listing,
`.pyi` inspection, and direct calls. None of these are part of the stable
8-tool MCP contract; they are provisional / non-frozen (1.0.0 API freeze note,
changelog 0.7.0 -> 1.0.0):

- `rest_api.py` - working FastAPI HTTP surface, localhost-only by design.
  Routes: `/decode`, `/health`, `/version`, `/api/license/activate`,
  `/api/license/info` (plus `/docs`, `/openapi.json`, `/redoc`).
- Top-level exports (.pyi-confirmed): `get_decoder`, `get_decoder_pool`,
  `clear_decoder_cache`, `decode_mmap`, `opencl_is_available`,
  `run_grpc_server`, `start_metrics_server`.
- Decoder caching: identity reuse and key discrimination both worked on the
  tested paths; an earlier suspected cache bug was not reproduced in those
  tests and could not be ruled out outside them - do not claim a cache bug.
- The Workbench MCP server (`QectorWorkbench-Portable.exe --mcp`) is real
  historical code (changelog 0.7.0 -> 1.0.0) but is absent from the shipped
  wheel (file listing, pip RECORD, `--mcp` grep, filename search, pip cache)
  and classified provisional / non-frozen in the 1.0.0 API freeze note.
- `workbench.py` is a headless application controller (benchmark job queue,
  JSON/CSV/PDF export); its docstring references a `run-qector` skill that is
  not part of this package.

## Workbench MCP (optional stdio extension, launch `--mcp`)

Handshake:
```json
{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"client","version":"1.0"}}}
{"jsonrpc":"2.0","method":"notifications/initialized"}
{"jsonrpc":"2.0","id":2,"method":"tools/list"}
{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"decode_single","arguments":{"family":"rotated_surface","distance":5,"decoder_name":"blossom","error_rate":0.05,"seed":42}}}
```
Result envelope: `content[0].text` holds a JSON payload; `isError` flags
tool-level failure. The exact Workbench tool list is device-local and must be
read from `tools/list`; no Workbench tool name is part of this package's
contract.

## Strict math ground truth (manual chapters 2, 3, 15, 22)

- Faithfulness gate: H c = s (mod 2) after every decode (Theorem 1).
- For self-orthogonal stabilizer/CSS checks (`H H^T = 0`), score the logical
  coset ker(H) / im(H^T), never raw correction equality (Theorem 2). Arbitrary
  matrices require code-provided logical and stabilizer spaces.
- Graphlike `codes` families (`rotated_surface_code`, `unrotated_surface_code`,
  `toric_code`, `heavy_hex_code`, `color_code`) are single-sector
  matching-graph codes with `H H^T != 0`: use the arbitrary-matrix/logical-coset
  branch of Theorem 2 (code-provided logical/stabilizer spaces), never the
  self-orthogonal branch.
- LER reports: Wilson 95% CI, z = 1.959963985; tag code_capacity vs
  circuit_level and refuse cross-model comparison (15.3).
- Every artifact carries the required metadata (22.3) + SHA-256.
- Safe wording (22.5): numbers are per machine/workload/artifact only.

## MCP SDK note

The production plugin pins `mcp>=1.28.1,<2` and uses the low-level
`mcp.server.Server` adapter, which gives the server explicit tool schemas and
error envelopes. Other SDK versions are unsupported until separately tested.
