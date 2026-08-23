# MCP API Contract

Every tool advertises JSON Schema 2020-12 input metadata, `outputSchema`, and
MCP behavioral annotations. Tool lists are deterministic within each server.

Every successful response exposes this structured envelope:

```json
{
  "status": "verified | reference_only | measured | not_checked | error",
  "claim_class": "runtime_verified | reference_only | machine_scoped_measurement | metadata_or_unverified",
  "provenance": {},
  "runtime": {},
  "scope": {},
  "verification": {"status": "verified", "checks": []},
  "artifact": null,
  "warnings": [],
  "result": {}
}
```

Errors return `status: "error"`, MCP `isError: true`, and a stable code such
as `INVALID_INPUT`, `RESOURCE_LIMIT`, `DEPENDENCY_MISSING`,
`BACKEND_UNAVAILABLE`, `VERIFICATION_FAILED`, `IO_ERROR`, or
`PERMISSION_DENIED`.

Clients must not interpret `not_checked`, `reference_only`, or `measured` as
runtime verification or universal performance evidence.
