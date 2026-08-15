# QECTOR Validation Protocol

This file is a device-local validation protocol. It intentionally contains no
captured test results, benchmark numbers, hardware status, or portable pass
count. Every user must run the checks on the target device and retain any
result outside the plugin if it is needed as evidence.

## Runtime

Install the pinned runtime from the workspace root:

```text
python -m pip install -r requirements.txt
```

The production library path requires `qector-decoder-v3==1.0.0`,
`mcp==1.26.0`, and a compatible `cryptography` release. The server rejects a
different QECTOR wheel version at startup rather than silently running against
an unreviewed API.

Run the app-free self-check with:

```text
python bin/qector_runtime_check.py
```

Run it with the system interpreter and with the selected virtual-environment
interpreter when both launch modes are supported. It validates the wheel, MCP
SDK, stable decoder imports, and one local syndrome-faithfulness path.

## Required Gates

Run the following on every target machine:

```text
python bin/run_manual_math_validation.py
python -m unittest discover -s tests -v
python bin/run_threshold_sweep.py --family rotated_surface --distances 3 5 --error-rates 0.05 --trials 100 --seed 42
```

The math gate recalculates the reference-manual obligations and live decoder
contracts. It deliberately reports GPU and asymptotic obligations as out of
scope when the target machine cannot execute them. The sweep emits a fresh raw
artifact and SHA-256. The MCP tool uses `QECTOR_ARTIFACT_DIR` for relative
artifact paths; the standalone CLI uses `--out` or defaults to `artifacts/`
under its current working directory. Prefer an external directory such as
`..\qector-artifacts` so generated evidence never enters the plugin tree.

## MCP Gate

Start `python mcp/mcp_server_library.py` through the MCP client and perform:

1. `initialize` with the client's negotiated protocol version.
2. `tools/list` and exact-name review before any tool call.
3. `tools/call` for `list_code_families`, `list_decoders`, and `compat_report`.
4. One small `decode_syndrome` call and confirmation of `syndrome_valid`.
5. One invalid-input call and confirmation that the response is an MCP tool
   error, not a successful result.

The optional Workbench must be configured separately and probed with
`python bin/probe_workbench_mcp.py --executable <target-workbench-executable>`.
Its tool names, hardware, license, and
version must be negotiated on that device; no bundled transcript is evidence.

## Claim Boundary

The reference manual at DOI `10.5281/zenodo.21941046` remains the mathematical
authority. A local run can validate the installed wheel and target hardware;
it cannot create a portable performance claim. Do not compare `code_capacity`
with `circuit_level`, and do not publish latency, throughput, GPU, threshold,
or license conclusions without the fresh device-local artifact and metadata.
