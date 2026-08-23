---
description: Generate Sinter task templates and configure community benchmark harnesses for QECTOR decoders.
---

Generate configuration templates and runner scripts for benchmarking QECTOR against standard QEC tools via Sinter (Chapter 17.2).

Arguments: `$ARGUMENTS` (e.g. `--circuit circuit.stim --decoder qector_blossom --max_shots 100_000`).

1. **Step 1 - Sinter Discovery**:
   - Call MCP tool `sinter_decoder_list()` on `qector-research` to inspect available registered Sinter decoder shims:
     - `qector_blossom`: Exact MWPM Blossom decoder.
     - `qector_unionfind`: Fast Union-Find decoder with weighted clustering.
     - `qector_bposd`: BP-OSD combination decoder.
     - `qector_unionfind_unweighted`: Unweighted graph traversal decoder.
     - `qector_belief`: Belief propagation standalone decoder.

2. **Step 2 - Generate Task Configuration**:
   - Call `sinter_task_template(circuit_path=..., decoder=..., max_shots=...)`.
   - Output runnable Python script importing `sinter` and `qector_sinter_decoders()`.
   - Ensure resulting LER samples are tagged with exact noise models and Wilson 95% intervals.
