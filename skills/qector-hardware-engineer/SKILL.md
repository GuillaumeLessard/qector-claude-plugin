---
name: qector-hardware-engineer
description: >-
  Physical-layer quantum circuits, detector-error-model preparation, qLDPC
  reasoning, and honest target-device hardware reporting for QECTOR. The bundled
  library MCP server is app-free; optional Stim, GPU, and Workbench surfaces
  require separate dependency and API checks.
---

# QECTOR Hardware Engineer

Translate physical circuit noise into objects QECTOR can decode without
overstating the target hardware. Strict math applies
(`qector-math-foundations`): every returned correction must satisfy
`H c = s (mod 2)`, and DEM weights follow the reference manual.

## Library-First Boundary

The bundled MCP server accepts registered code families, binary syndromes, and
binary parity-check matrices through its eight documented tools. It does not
accept arbitrary `.stim` files or DEM objects. Use `list_code_families` and
`build_code_from_matrix` for the supported app-free path.

## Optional DEM Workflow

The direct wheel may expose a DEM module, and Stim may be installed separately.
Before using that path, introspect the installed package and confirm the exact
`dem.from_stim`, graph-collapse, and decoder APIs. Do not assume that optional
surfaces are available because a Workbench guide names them.

For an optional Workbench, inspect `initialize` and `tools/list` on the target
device first. Use only the negotiated names and schemas; no Workbench tool is a
contract of this package.

DEM edge weights follow `log((1-p)/p)`. Hyperedges require a decoder whose
documented contract supports the input structure; do not route by an invented
tool name.

## Hardware Honesty

- `cuda_is_available()` and any direct-wheel GPU availability method report hardware, not license entitlement.
- Workbench hardware tools are optional and device-local.
- GPU/OpenCL behavior must be tested on the target device; no bundled hardware result is evidence.
- GPU/CPU bit identity is a scoped theorem obligation, not a portable performance claim.

## Deliverables

Provide a runnable local circuit-to-decode workflow with exact inputs, decoder
options, seeds, package versions, environment metadata, syndrome validation,
and an external artifact SHA-256 sidecar. Keep generated artifacts outside the
public plugin tree.
