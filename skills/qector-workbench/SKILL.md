---
name: qector-workbench
description: >-
  The optional QECTOR Workbench desktop application (manual 17.5,
  20). Covers the device-local stdio MCP integration, the
  historical changelog (0.7.0 -> 1.0.0), the explicit
  provisional / non-frozen classification, the fact that the
  Workbench is absent from the shipped wheel, the headless
  application controller (workbench.py), the benchmark job
  queue, the JSON / CSV / PDF export, the environment snapshot,
  the git commit, and the qector-admin.workbench_probe tool.
  Load for any question about the Workbench, the optional app,
  or how to probe a target device.
---

# QECTOR Workbench (Optional Desktop App)

Source of authority: v1.0.0 reference manual, section 17.5; the
1.0.0 API freeze note; the device-local Workbench handler.

## What the Workbench is

The Workbench is an **optional desktop application** that exposes
real `.stim` / `.dem` loading, a cancelable benchmark job queue,
and JSON / CSV / PDF export. Every number is traced to a real
decode, with an environment snapshot and git commit.

It is real historical code (changelog `0.7.0 -> 1.0.0`) but it is
**absent from the shipped `qector-decoder-v3` wheel** (file
listing, pip RECORD, `--mcp` grep, filename search, pip cache).
Its exact tools, version, license, and hardware status are
**device-local** and must be negotiated with `initialize` and
`tools/list` on the target machine.

## The class hierarchy

- **`QectorWorkbench-Portable.exe --mcp`** is the launch command
  on Windows. The executable is a portable app; it starts an
  stdio MCP server.
- **`workbench.py`** in the library is a headless application
  controller (benchmark job queue, JSON/CSV/PDF export). Its
  docstring references a `run-qector` skill that is not part of
  this package.
- The optional direct-wheel `qector_decoder_v3.workbench` module
  is not shipped in 1.0.0.

## How to probe the Workbench

`qector-admin.workbench_probe` runs a local stdio probe of an
approved Workbench executable. The admin server must be enabled
with `QECTOR_ADMIN_ENABLED=1`, the binary must sit inside
`QECTOR_WORKBENCH_DIR`, and the call must include `confirm=true`
plus `expected_sha256`.

The tool:

1. Spawns the executable with `--mcp`.
2. Sends `initialize` + `notifications/initialized` + (optionally)
   `tools/list` or `mcp_status`.
3. Returns the live JSON-RPC responses.
4. Closes the subprocess and waits for it to exit.

No transcript is bundled by the admin probe; the result is
fresh for every call.

## What the Workbench tools are

The exact list is **device-local**. Common patterns:

- `mcp_status` - health / version / license probe.
- `tools/list` - returns the actual tool names on the target.
- `get_license_info` - same shape as the library tool.
- `get_hardware_info` - returns CUDA / OpenCL / RAM / CPU.
- `verify_license_token` - Ed25519 token validation.
- `decode_single` / `decode_batch` - dev-friendly decode
  wrappers.
- `run_benchmark` - cancelable benchmark job.

Never assume any specific Workbench tool name. **Always** run
`tools/list` on the target before using any name. The
`probe_workbench_mcp.py` script in `scripts/` does the same thing
from the command line:

```bash
python scripts/probe_workbench_mcp.py --executable "C:\\path\\to\\QectorWorkbench-Portable.exe"
python scripts/probe_workbench_mcp.py --executable "..." --tools --limit 5
```

## What the Workbench is NOT

- It is not part of the stable library contract.
- It is not part of the 8-tool MCP library surface.
- It is not bundled in `qector-decoder-v3 1.0.0`.
- It is not the supported service surface for a research
  deployment; the bundled local stdio wrapper is.

## When to use the Workbench

Use the Workbench when:

- The user has the desktop app installed locally.
- The use case is dev / interactive benchmarking.
- The required tools (e.g. `get_hardware_info`,
  `run_benchmark`) are negotiated via `tools/list` and are
  necessary.

Do not use the Workbench when:

- The use case is a library-only research workflow.
- The user is on a server with no display.
- The user is running headless CI / scheduled jobs.

## Common pitfalls

- **Quoting Workbench tool names that were not negotiated on the
  target device** -> always run `tools/list` first.
- **Assuming the Workbench is bundled with the wheel** -> it is
  not; the wheel ships only the library, the library MCP server,
  and the headless controller.
- **Comparing Workbench and library results without flagging the
  source** -> the Workbench runs the same Rust core, but the
  pipeline (DEM loading, batch dispatch) is a different layer.
- **Publishing a Workbench-based artifact without the
  chapter 22.3 metadata** -> manual 24.1 lists 10 production
  items; every artifact must include the metadata.

## How the research server helps

- `qector-admin.workbench_probe` is the live probe.
- `qector-research.env_block` returns the chapter 22.3 environment
  block for a Workbench artifact.
- `qector-research.hardware_probe` returns the live hardware state
  via the library probe.
- `qector-research.license_active_check` reports the offline
  license tier.
