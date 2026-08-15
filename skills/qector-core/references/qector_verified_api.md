# QECTOR Verified API Reference

Source of truth: the QECTOR Decoder v3 reference manual v1.0.0 (DOI
`10.5281/zenodo.21941046`), the public library API, and the device-local
validation protocol in `mcp/VALIDATION_REPORT.md`. The reference manual is not
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

### codes module (verify on the target device)
```
>>> from qector_decoder_v3 import codes
>>> c = codes.rotated_surface_code(5)
>>> c.n_qubits
>>> c.n_checks
```
`Code` attributes: `H`, `check_to_qubits`, `description`, `distance`,
`n_checks`, `n_qubits`, `name`, `qubit_weights`, ... Methods (call with
parens): `parity_check_matrix()`, `logicals_matrix()`,
`random_error(p, rng=rng)`, `syndrome(error)`. `seed=` is NOT valid; use
`rng=np.random.default_rng(seed)`.

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
- LER reports: Wilson 95% CI, z = 1.959963985; tag code_capacity vs
  circuit_level and refuse cross-model comparison (15.3).
- Every artifact carries the required metadata (22.3) + SHA-256.
- Safe wording (22.5): numbers are per machine/workload/artifact only.

## MCP SDK note

The production plugin pins `mcp==1.26.0` and uses the low-level
`mcp.server.Server` adapter, which gives the server explicit tool schemas and
error envelopes. Other SDK versions are unsupported until separately tested.
