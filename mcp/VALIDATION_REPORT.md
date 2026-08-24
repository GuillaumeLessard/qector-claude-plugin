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
`mcp>=1.28.1,<2`, and a compatible `cryptography` release. A wheel outside the
reviewed `[1.0.0, 1.1.0)` window writes a stderr warning; set
`QECTOR_MCP_STRICT_VERSION=1` to refuse to start instead. Decode results
remain fail-closed against `H c = s (mod 2)` regardless.

Run the app-free self-check with:

```text
python scripts/qector_runtime_check.py
```

Run it with the system interpreter and with the selected virtual-environment
interpreter when both launch modes are supported. It validates the wheel, MCP
SDK, stable decoder imports, and one local syndrome-faithfulness path.

## Required Gates

Run the following on every target machine:

```text
python scripts/run_manual_math_validation.py
python -m unittest discover -s tests -t . -v
python scripts/run_threshold_sweep.py --family rotated_surface --distances 3 5 --error-rates 0.05 --trials 100 --seed 42
```

The math gate recalculates the reference-manual obligations and live decoder
contracts. It deliberately reports GPU and asymptotic obligations as out of
scope when the target machine cannot execute them. The sweep emits a fresh raw
artifact and SHA-256. The MCP tool uses `QECTOR_ARTIFACT_DIR` for relative
artifact paths; the standalone CLI uses `--out` or defaults to `artifacts/`
under its current working directory. Prefer an external directory such as
`..\qector-artifacts` so generated evidence never enters the plugin tree.

## MCP Gate

### 1. Library Server Gate (`qector-library` — 8 Tools)

Start `python mcp/mcp_server_library.py` through the MCP client and perform:

1. `initialize` with the client's negotiated protocol version.
2. `tools/list` and exact-name review before any tool call (8 tools).
3. `tools/call` for `list_code_families`, `list_decoders`, and `compat_report`.
4. One small `decode_syndrome` call and confirmation of `syndrome_valid`.
5. One invalid-input call and confirmation that the response is an MCP tool
   error, not a successful result.

### 2. Bench Server Gate (`qector-research` — 29 Tools)

Start `python mcp/mcp_server_qector_bench.py` through the MCP client and perform:

1. `initialize` and `tools/list` verification (29 tools; admin tools
   `system_setup`, `configure_claude_desktop`, and `workbench_probe` are
   filtered out of the public surface and require the separate
   `qector-admin` server, gated by `QECTOR_ADMIN_ENABLED=1` and
   `confirm=true`).
2. Call `get_capability_matrix` to verify the server's static capability
   inventory and the documented trust zones.
3. Call `reproduction_command_lookup(section="all")` to verify Appendix D reproduction maps.
4. Call `theorem_lookup(number=1)` and `glossary_lookup(term="syndrome faithfulness")`.
5. Call `wilson_ci(k=10, n=1000)` and verify interval `[0.00544, 0.01831]`.
6. Call `hot_path_microbench` and confirm the response includes a
   `measurement_scope` block (machine / OS / Python / CPU / RAM /
   backend / decoder_class / code_family / noise_model / seed /
   workload_hash).

The optional Workbench must be configured separately and probed with
`python scripts/probe_workbench_mcp.py --executable <target-workbench-executable>`.
Its tool names, hardware, license, and version must be negotiated on that device;
no bundled transcript is evidence.

## Claim Boundary

The reference manual at DOI `10.5281/zenodo.21941046` remains the mathematical
authority. A local run can validate the installed wheel and target hardware;
it cannot create a portable performance claim. Do not compare `code_capacity`
with `circuit_level`, and do not publish latency, throughput, GPU, threshold,
or license conclusions without the fresh device-local artifact and metadata.
