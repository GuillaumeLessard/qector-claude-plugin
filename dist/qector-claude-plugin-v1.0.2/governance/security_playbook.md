# QECTOR Security And Data Handling

This public policy defines the safe default for the QECTOR Claude plugin.

## Local Data

- The bundled library MCP server runs locally over stdio.
- Never send `.stim`, `.npy`, syndrome buffers, parity-check matrices, or
  proprietary circuits to external services.
- Network transports are not exposed by the bundled server.
- Keep generated artifacts outside the plugin directory and protect them using
  the target system's normal access controls.

## Tool Verification

- Call `initialize` and `tools/list` before relying on any MCP tool name.
- The library server's contract is limited to its eight documented tools.
- Optional Workbench names and schemas must be negotiated on the target device.
- Do not invent unsupported decoders or write unverified replacement backends.

## Supply Chain

- Install only from the pinned `requirements.txt` or an independently reviewed
  dependency source.
- Confirm package name, version, maintainer metadata, and the reference manual
  DOI before execution.
- After installation, inspect the live package API instead of trusting stale
  integration examples.
- Keep credentials, license keys, and generated artifacts out of source control.

## Claims And Evidence

- Verify `H c = s (mod 2)` before logical scoring.
- Tag LER artifacts as `code_capacity` or `circuit_level`; never compare the two.
- Record exact environment, command, seed, and decoder mode in fresh artifacts.
- Store the raw artifact and an external `.sha256` sidecar outside the public
  plugin tree.
- Treat performance, GPU, hardware, threshold, and license state as
  device-local unless independently reproduced.
