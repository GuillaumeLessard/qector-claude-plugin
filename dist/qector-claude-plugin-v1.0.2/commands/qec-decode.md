---
description: Execute single-shot syndrome decoding and verify syndrome faithfulness H c = s (mod 2) on a quantum code family.
---

Perform a validated single-shot error generation and decoding execution using the QECTOR decoding engine.

Arguments: `$ARGUMENTS` (e.g. `--family rotated_surface --distance 5 --decoder blossom --p 0.05 --seed 42`).
Defaults: family `rotated_surface`, distance `3`, decoder `blossom`, p `0.05`, seed `42`.

1. **Step 1 - Call MCP Tool**:
   - Call MCP tool `decode_single(family=..., distance=..., decoder_name=..., error_rate=..., seed=...)` on `qector-library` or `qector-bench`.
   - Or call `decode_syndrome(family=..., distance=..., syndrome=..., decoder_name=...)` with an explicit binary syndrome vector.

2. **Step 2 - Verify Strict Math Obligations**:
   - Confirm `syndrome_valid: true`, asserting Theorem 1 ($H c \equiv s \pmod 2$).
   - Check `logically_correct` status scored over the logical coset (Theorem 2).
   - Display the error weight $|e|$, correction weight $|c|$, and execution duration.
