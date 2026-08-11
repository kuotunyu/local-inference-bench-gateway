# Production scaling boundary

The current system is designed for one trusted workstation, one gateway process, loopback-bound
services, and a small number of local applications. It demonstrates the control points a larger
system needs, but it is not itself a production serving platform.

## What works at workstation scale

- Stable model aliases decouple clients from engine-specific model IDs.
- Ordered request-time failover handles local engine restarts and retryable failures.
- Per-alias rejection prevents an unbounded queue from hiding overload.
- SQLite provides a zero-service local audit trail and dashboard input.
- OpenAI-shaped errors and SSE pass-through make common SDK integration straightforward.

## What fails when scaled horizontally

| Current choice | Scaling limit | Production replacement |
|---|---|---|
| Process-local counter | Each worker admits its own limit | Distributed admission control or a single scheduling tier |
| SQLite WAL | One host and modest write concurrency | Managed relational store or telemetry pipeline |
| Ordered static registry | No load awareness or placement | Service discovery plus health/load-aware routing |
| In-memory health state | Lost at restart; host-local | Shared metrics and alerting |
| One API key | No user attribution or rotation | Identity provider, scoped credentials, quotas |
| Direct retry/failover | Can duplicate non-idempotent work | Request IDs, retry policy, cancellation, deduplication |
| Local logs | No retention or redaction governance | Central structured logging with explicit data policy |

## Practical evolution path

1. Keep the OpenAI-compatible edge and alias contract, but move admission control into a single
   scheduler or a distributed rate-limit service.
2. Replace SQLite writes with non-blocking structured telemetry and define retention, sampling,
   and prompt/privacy policy before collecting more fields.
3. Add request IDs, deadline propagation, cancellation, circuit breakers, and bounded retries.
4. Run inference behind a serving system designed for continuous batching and multi-GPU
   placement; treat this gateway as an edge adapter rather than a GPU scheduler.
5. Add TLS, network segmentation, user identity, quotas, secret rotation, and supply-chain
   scanning.
6. Load-test tail latency and failure recovery at the intended deployment topology. The recorded
   single-GPU benchmark cannot size a multi-host service.

## Why rejection is preferable to hidden queueing

The gateway returns 429 at the configured alias limit. A queue would make overload look like
success while TTFT grows without a bound and disconnected clients continue consuming capacity.
Production systems may use queues, but only with deadlines, cancellation, bounded depth,
observability, and explicit service-level objectives.

## Portfolio claim

This project should be presented as a tested local reference for benchmark hygiene, compatibility
boundaries, failure semantics, and backpressure. It should not be presented as Kubernetes-ready,
multi-tenant, or validated for hundreds of concurrent users.
