# Developer Onboarding

## Slide 1: Library-First MCP

QECTOR Decoder v3 has its own app-free local MCP server in
`mcp/mcp_server_library.py`. The library path is the default supported surface;
QECTOR Workbench is optional and separate.

Install with:

```text
python -m pip install -r requirements.txt
python scripts/qector_runtime_check.py
```

## Slide 2: Exact Library Tool Surface

The library server exposes exactly:

`list_code_families`, `list_decoders`, `get_license_info`, `decode_syndrome`,
`decode_single`, `threshold_sweep`, `build_code_from_matrix`, and
`compat_report`.

Always run `initialize` and `tools/list` before use.

## Slide 3: Interpreter Selection

System Python and a virtual environment are both supported. Use the same
interpreter for installation, runtime checks, and the MCP server:

```text
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python scripts/qector_runtime_check.py
python mcp/mcp_server_library.py
```

## Slide 4: Strict Math

Every correction must satisfy `H c = s (mod 2)`. LER is logical-coset scored
and carries a Wilson 95% interval. Hardware, performance, GPU, and threshold
claims are device-local and require fresh artifacts.

## Slide 5: Optional Circuit Workflows

Stim and DEM workflows are optional direct-wheel surfaces and require their own
dependencies and API checks. Workbench tool names must be discovered from the
target device's `tools/list`; they are not part of the library MCP contract.
