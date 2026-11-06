---
description: Generate a Sinter task template for a QECTOR decoder and report which Sinter shims this build exposes.
argument-hint: "--family rotated_surface --size 5 --decoder blossom --shots 100000"
---

Generate a Sinter task template for benchmarking QECTOR against community harnesses (Reference Manual chapter 17.2).

Arguments: `$ARGUMENTS` (e.g. `--family rotated_surface --size 5 --decoder blossom --shots 100000`).

Both tools are on the research profile (`qector-secure --profile research`).

1. **Sinter discovery**
   - Call `sinter_decoder_list()` and report exactly what it returns: `sinter_exposed` and `sinter_decoders`. On `qector-decoder-v3 1.0.0` without the `sinter` package installed the answer is `sinter_exposed: false` with an empty list and a note; say that, and do not list shim names that the tool did not return. Installing `sinter` is a network action and is outside the air-gapped default.

2. **Generate the task configuration**
   - Call `sinter_task_template(family=..., size=..., decoder_name=..., shots=..., error_rate=..., seed=...)`. Only `family` is required; argument names are exactly these (there is no `circuit_path`, `decoder` or `max_shots`).
   - Present the returned `task_template` and the runner notes verbatim; the template names a QECTOR decoder shim only if step 1 exposed it.
   - Remind the user that logical-error-rate samples must be reported with the noise model and a Wilson 95 % interval (`/qec-wilson`).
