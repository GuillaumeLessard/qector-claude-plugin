---
name: qector-services
description: >-
  QECTOR service surfaces: REST (FastAPI / Flask), gRPC, MCP
  stdio, Prometheus metrics exporter (manual 17.4). Covers the
  Provisional status, the production checklist (manual 24.1), the
  request-size cap, the bearer-token check, the per-client rate
  limit, the strict decoder-type enum, the deployment modes
  (manual 24, Table 24.1), and the fact that the bundled local
  stdio wrapper is the supported service surface in this
  package. Load for any question about service hardening,
  deployment, REST, gRPC, metrics, or production posture.
---

# QECTOR Services

Source of authority: v1.0.0 reference manual, sections 17.4, 24.

## The four service surfaces (manual 17.4)

The engine ships four service surfaces, all **Provisional** under
the 1.0.0 API freeze note (manual 16.2, 17.4):

- **REST** (FastAPI or Flask), localhost-only by design.
- **gRPC** (under the `grpc` feature).
- **MCP stdio** (the bundled local wrapper, the supported service
  surface in this package).
- **Prometheus metrics exporter**.

They all sit on top of the same decoder contracts and apply the
same faithfulness gate (manual 26.5). None reimplements decoding;
they are thin transport layers, which is why the contracts of
chapters 4-13 transfer to them unchanged.

## Local REST surface (Provisional, manual 16.2 / 17.4)

Routes (from the verified wheel inspection):

| Method | Path                          | Notes                |
| ------ | ----------------------------- | -------------------- |
| GET    | `/`                           | root / health        |
| POST   | `/decode`                     | decode a syndrome    |
| GET    | `/health`                     | liveness probe       |
| GET    | `/version`                    | package version      |
| POST   | `/api/license/activate`       | activate a key       |
| GET    | `/api/license/info`           | live license info    |
| GET    | `/docs`                       | Swagger UI           |
| GET    | `/openapi.json`               | OpenAPI schema       |
| GET    | `/redoc`                      | ReDoc UI             |

`/decode` accepts a JSON body with the parity-check matrix, the
syndrome, and the decoder name. The 10 MB request cap and
per-client rate limit apply (manual 24.3).

## gRPC surface (Provisional)

The gRPC service is feature-gated under the `grpc` feature flag.
Verify the exact schema by introspecting the installed wheel; do
not assume any specific proto without a `pip show` plus
`grpc_tools.protoc` re-derivation. Path-shape validation runs
before the gRPC handler returns; binary syndromes are checked for
length.

## MCP stdio surface (the bundled wrapper)

The bundled local stdio wrapper is the **supported service
surface in this package** (manual 17.4). It is what
`qector-library` and `qector-research` (the two MCP servers this
plugin registers) implement.

Frame cap: `QECTOR_MCP_BENCH_MAX_DEM_BYTES` for the bench server
and the library server's frame cap by default. The strict
decoder-type enum rejects unknown names with a clear
`QECTORInputError`.

## Prometheus metrics exporter (Provisional)

`qector_decoder_v3.start_metrics_server(port=...)` is the entry
point on the verified wheel. Verify the exact metric names on the
target device; do not hard-code. Metrics include accumulated
shot count, decode latency quantiles (`get_latency_quantiles()`),
and license state.

## Production checklist (manual 24.1)

Before any customer-facing or network-accessible deployment:

1. Pin the git commit or release tag.
2. Record `Cargo.lock` and dependency versions.
3. Generate dependency inventories.
4. Disable unused optional services and GPU features.
5. Run local test and import smoke validation.
6. Run only the benchmark claims intended to be quoted.
7. Keep raw JSON / CSV artifacts and SHA-256 hashes.
8. Place any service behind TLS and a reverse proxy.
9. Restrict logs so benchmark inputs, customer data, and
   proprietary circuits are not leaked.
10. Document the operational owner, update path, and rollback
    path.

## Service hardening (manual 24.3)

- The REST layer enforces a 10 MB request cap, a per-client rate
  limit, and an optional bearer-token check.
- The MCP server enforces the same frame cap and a strict
  decoder-type enum.
- The gRPC path validates payload shapes and binary syndromes.
- These are necessary but not sufficient: authentication,
  authorization, TLS, rate limits, timeouts, audit logs, and
  resource quotas **must** be reviewed before production use.

## Deployment modes (manual 24, Table 24.1)

| Mode                          | Status                            | Guidance                                  |
| ----------------------------- | --------------------------------- | ----------------------------------------- |
| Local CPU library             | Supported public path             | Preferred for research and evaluation     |
| CUDA / OpenCL batch           | Optional local path               | Controlled driver / runtime setup only    |
| Docker REST server            | Demo / local service path          | Do not expose directly to the public internet |
| gRPC / MCP / metrics          | Optional feature-gated paths      | Experimental unless deployment-reviewed   |
| SaaS / hosted API             | Contact-only beta review          | Separate commercial agreement and hardening |
| OEM / embedded                | Contact-only partner validation    | Hardware / platform scope and support terms |

Network use, hosted API use, OEM integration, internal commercial
use, product integration, paid consulting, and commercial
benchmarking **require a written commercial license**.

## Common pitfalls

- **Exposing a Docker REST server directly to the internet** -> the
  service is demo / local; put it behind TLS and a reverse proxy.
- **Skipping the production checklist** -> manual 24.1 lists 10
  items; every one of them is a release blocker.
- **Hard-coding service endpoints** -> endpoints, ports, and
  config live in `QECTOR_DATA_DIR` and the runtime config; verify
  with the live probe.
- **Mixing service-tier claims with hardware-tier claims** -> the
  service tier (Community / Pro / Enterprise) is the
  license tier; the hardware probe is separate.

## How the bench server helps

- `qector-research.env_block` returns the chapter 22.3 environment
  block for a service artifact.
- `qector-research.hardware_probe` reports the live hardware state
  and license tier.
- `qector-research.license_active_check` reports the offline
  license tier and feature gates.
- `qector-research.artifact_metadata_check` generates the
  chapter 22.3 metadata block for a service benchmark.
