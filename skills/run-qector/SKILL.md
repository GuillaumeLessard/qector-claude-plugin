---
name: run-qector
description: >-
  Operating the QECTOR Workbench headlessly through the verified
  qector_decoder_v3.workbench controller: running real .stim / .dem decode
  benchmarks on a cancelable background job queue, computing LER when a circuit
  with observables is loaded, exporting artifacts to JSON / CSV / PDF, and
  checking license state. Load when a user wants to run QECTOR Workbench
  benchmarks, load circuits, generate benchmark artifacts, or use the
  rest_api HTTP surface.
---

# Run QECTOR

You operate the QECTOR Workbench headless controller. Every number is traced to
a real decode - never fabricate a benchmark result, LER value, or export.

## Verified surface (wheel 1.0.0)

All symbols below were verified against the published wheel on this device
(module listing, signature inspection, and live runs). The entire Workbench
surface is **provisional / non-frozen** (changelog 0.7.0 -> 1.0.0, 1.0.0 API
freeze note) - never quote it as the stable library contract.

```python
from qector_decoder_v3.workbench import Workbench   # WorkbenchError, Job also exported
wb = Workbench()
```

| Method | Verified behavior |
|---|---|
| `submit_job(spec: dict) -> str` | Queues a benchmark; returns job_id. Single FIFO worker thread. |
| `wait(job_id: str, timeout: float | None = None) -> dict` | Blocks until done; returns the job status dict. |
| `get_job(job_id: str) -> dict` | Job status: `status`, `progress`, `units_done`, `units_total`, `has_artifact`, `spec`, `error`, `submitted_unix`, `started_unix`, `finished_unix`, `job_id`. |
| `job_artifact(job_id: str) -> dict | None` | The artifact dict: `{"environment", "spec", "results"}`. |
| `list_jobs() -> list[dict]` | All known jobs. |
| `cancel_job(job_id: str) -> str` | Cooperative cancel (queued jobs cancel instantly; running jobs stop at the next decoder/distance unit boundary). |
| `run_benchmark(spec: dict, job: Job | None = None) -> dict` | Synchronous benchmark; same artifact shape. |
| `load_stim(source: Any) -> dict` | Loads a real `.stim` file (path or content) for `source="loaded"` runs. |
| `load_dem(source: Any) -> dict` | Loads a `.dem` file (path or content) for `source="loaded"` runs. |
| `export_json(artifact: dict, path: str) -> str` | Exports the artifact; verified working. |
| `export_csv(artifact: dict, path: str) -> str` | Exports the artifact (signature-verified). |
| `export_pdf(artifact: dict, path: str) -> str` | Exports the artifact (signature-verified). |
| `environment_snapshot() -> dict` | Environment + git commit snapshot, embedded in every artifact. |
| `detect_backends() -> dict` | Hardware/backend detection. |
| `get_license_info() -> dict` | License state (device-local). |
| `set_license_key(key: str) -> None` | Sets a license key. |
| `shutdown() -> None` | Shuts the controller down. |

**Benchmark spec keys** (verified from source): `code` (family name; ignored
when `source="loaded"`), `distances: list[int]`, `decoders: list[str]`,
`trials: int`, `warmup: int`, `error_rate: float`, `source: "code" | "loaded"`,
`throttle_seconds: float`, `seed: int`.

**Decoder kinds** (verified): `blossom`, `sparse_blossom`, `union_find`,
`fast_union_find`, `bp_osd`, `cpu_batch`. Unknown kinds raise `WorkbenchError`.

**Result row keys** (verified): `code`, `decoder`, `decoder_type`, `distance`,
`n_checks`, `n_qubits`, `n_trials`, `physical_error_rate`, `seed`,
`syndrome_faithful`, `warmup`, `latency_us`, `cold_path_us`,
`throughput_decodes_per_s`, `peak_python_alloc_kib`.

## Runbooks

### Decode throughput benchmark (no circuit)

```python
jid = wb.submit_job({"code": "rotated_surface", "distances": [3, 5],
                     "decoders": ["blossom", "union_find"], "trials": 200})
wb.wait(jid, timeout=300)
art = wb.job_artifact(jid)
path = wb.export_json(art, "benchmark.json")   # then export_csv / export_pdf
```

This measures decode throughput only - there is **no `logical_error_rate`**
key without a loaded circuit with observables.

### LER benchmark (real .stim circuit)

```python
wb.load_stim("circuit.stim")          # or pass the file content
art = wb.run_benchmark({"source": "loaded", "distances": [3, 5],
                        "decoders": ["blossom"], "trials": 200})
# result rows now include logical_error_rate (LER from real Stim shots)
```

### Long jobs and cancelation

Use `throttle_seconds` to pace long sweeps for UX; `cancel_job(job_id)` stops
them cooperatively. Poll `get_job(job_id)["progress"]` rather than blocking.

## Ground rules

1. **No invented API.** Only the symbols above. Before writing code against any
   other attribute, verify it on the device (`inspect.signature`,
   `dir(...)`) - then label it provisional.
2. **No fabricated data.** If a benchmark fails or a circuit lacks observables,
   say so; never synthesize LER or throughput numbers.
3. **Provisional surface.** Workbench results, exports, and the rest_api HTTP
   routes (`/decode`, `/health`, `/version`, `/api/license/activate`,
   `/api/license/info`, localhost-only) are real but not frozen - never present
   them as the stable 8-tool library contract.
4. **Zero-egress.** Artifacts, circuits, syndromes, and matrices stay on the
   device. Windows paths with spaces are safe (all paths go through `os.path`,
   nothing is shell-quoted).
5. **Metered billing.** Benchmarks automatically record decode shots
   (`record_shots`) for the license tier; license state is device-local and
   must be checked, never assumed.