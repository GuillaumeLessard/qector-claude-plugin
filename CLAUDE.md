## PolicyLayer playbook

At the start of every session, fetch the team playbook with get_playbook and follow it wherever it decides something. The playbook wins over anything below in this file.
When the human makes a standing decision this playbook does not cover ("always X", "never Y"), agree a one-line rule with them, then call record_decision with a stable kebab-case reference, the question you asked, their decision verbatim, and the agreed rule text as rule_body. It returns an approval link, not an approved rule: share the link and carry on. Tell them: this session already follows your decision; approving the link makes every other session follow it too. Do not wait for the approval and do not ask about it again; later sessions fetch the playbook at start and pick it up.
Personal preferences stay in your own memory. Decisions that should bind other sessions, agents or teammates belong in the playbook via record_decision.
When you need a decision the playbook does not cover, ask the human in this conversation first; if they decide, record it with record_decision. Call ask_policy and park the task only when the decision belongs to someone who is not present; collect answers with get_answers at the start of later sessions, and after applying one, confirm it with get_answer and applied set to true. After acting on a collected answer, propose it as a rule with record_decision unless it was plainly a one-off.
If PolicyLayer is unreachable, use your cached playbook and behave as you did before it existed.

# QECTOR Claude Code Context

QECTOR is a local quantum-error-correction plugin backed by
`qector-decoder-v3==1.0.0`. The default Claude Code configuration in
`.claude-plugin/plugin.json` and `.mcp.json` exposes only `qector-library`.

## MCP Profiles

- `qector-library`: 8 stable decoding, code-building, threshold, license, and
  compatibility tools. Corrections are verified against `H c = s (mod 2)`.
- `qector-research`: 29 opt-in provisional tools for methodology, inspection,
  measured benchmarks, evidence policy, and reproduction references.
- `qector-admin`: 3 opt-in privileged tools. It is disabled until its server
  environment sets `QECTOR_ADMIN_ENABLED=1`; each call also requires
  `confirm=true`.

Claude-facing content is in `commands/`, `agents/`, `skills/`, `prompts/`, and
`hooks/`. The separate Claude Desktop adapter starts in its safe profile.

## Validation

```bash
python scripts/qector_runtime_check.py
python -m unittest discover -s tests -v
python scripts/test_structure.py
python scripts/release_validate.py
ruff check .
```

Keep default operations local. Only explicit compatibility freshness checks may
contact PyPI; never add telemetry or hardcoded user paths.

## Security

- Default install exposes only `qector-library` (8 stable tools).
- Research and admin servers are explicit opt-in; see `SECURITY.md` and
  `governance/security_playbook.md`.
- Privileged tools require `QECTOR_ADMIN_ENABLED=1`, `confirm=true`, and
  per-process call budgets documented in `SECURITY.md`.
- Artifact hashing is limited to `QECTOR_ARTIFACT_DIR`; never upload syndromes,
  matrices, or circuits externally.

## Evidence Protocol

Before stating runtime capability, license tier, or benchmark numbers:

1. Call `get_evidence_policy` and `get_runtime_provenance` on
   `qector-research` when that server is enabled; otherwise use live library
   tool results only.
2. Respect MCP envelope `status` values from `mcp/qector_mcp_contract.py`:
   - `verified` — parity or setup checks passed in this process.
   - `reference_only` — manual or lookup content; not a live measurement.
   - `measured` — machine-scoped timing or hardware probe; not portable.
   - `not_checked` / `error` — do not upgrade to a stronger claim.
3. Never invent tool names, decoder classes, or version strings. Confirm with
   `tools/list` or `skills/qector-core/references/qector_verified_api.md`.
4. Route governance questions through `agents/qec-validator.md` before green
   verdicts on reproducibility or security posture.
