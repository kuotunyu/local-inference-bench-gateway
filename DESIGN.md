# Design

## System boundary

The repository joins two related but independently reviewable components:

1. A common async client, fixed workload matrix, and aggregate evidence for three local
   OpenAI-compatible inference frontends.
2. A small compatibility gateway for applications that should address stable model aliases
   instead of engine-specific URLs and model identifiers.

The gateway is intentionally a single-process reference implementation. Its purpose is to make
failure semantics, backpressure, and observability explicit without pretending to be a cluster
scheduler.

## Request path

```mermaid
sequenceDiagram
    participant C as Client
    participant G as Gateway
    participant P as Primary backend
    participant F as Fallback backend
    participant D as SQLite

    C->>G: POST /v1/chat/completions (alias)
    G->>G: auth, envelope, alias, capacity validation
    G->>P: backend model identifier
    alt primary returns retryable failure
        P-->>G: connection / timeout / malformed JSON / 5xx
        G->>D: safe failover category
        G->>F: same request, fallback model identifier
        F-->>G: OpenAI-compatible response
    else primary returns success or 4xx
        P-->>G: response
    end
    G->>D: metadata only; never request messages or API keys
    G-->>C: JSON or streamed SSE
```

## Compatibility decisions

- `/v1/models` exposes aliases, not backend model names.
- `/v1/chat/completions` rewrites only `model`; other request fields pass through.
- Structured upstream responses pass through with their status. Non-JSON or non-object success
  bodies are protocol failures and may trigger the next backend.
- A 4xx is not retried because it normally represents a request problem shared by every backend.
- A non-final 5xx, connection error, timeout, or protocol error advances the ordered chain.
- Public failures use an OpenAI-shaped `{"error": {...}}` envelope without exception text,
  private paths, addresses, or credentials.
- Streaming SSE is forwarded line by line. Usage-only chunks are requested for telemetry but are
  sent to the client only when it opted in.

## Capacity and streaming lifecycle

Each alias can define `max_concurrent`. Acquisition is atomic and excess work receives 429 plus
`Retry-After`; the gateway does not build an unbounded in-memory queue. A streaming request holds
its slot until the response iterator ends, fails, or is cancelled. `finally` releases the slot in
all cases. A mid-stream read error terminates the stream without fabricating `[DONE]` and records
only `stream_read_error`.

This limiter is process-local. Multiple Uvicorn workers would each enforce a separate counter, so
the deployment examples use one worker.

## Failover versus health checks

Background `/models` probes populate an authenticated topology view. They do not gate requests:
health state is stale as soon as it is sampled, and using it as a routing oracle can skip a newly
recovered backend. Each request therefore performs its own ordered attempts. Non-final backends
use a shorter read timeout so a hung primary cannot consume the fallback's entire latency budget.

## Telemetry boundary

SQLite stores timestamps, alias/backend/model identifiers, stream flag, status, success,
aggregate token counts, latency, and a controlled failure category. It does not store request
messages, authorization headers, raw upstream bodies, or exception strings. WAL mode, a busy
timeout, indexes, and schema version 1 make the local database predictable under modest
concurrency. A telemetry write failure emits a fixed local warning but never replaces a valid
completion or blocks failover.

## Shutdown behavior

The application lifespan owns the shared HTTP client and health-check task. Nested `finally`
blocks stop polling and close the client even when startup partially succeeds or the application
context exits with an exception.

## Security posture

When `GATEWAY_API_KEY` is configured, the topology, model list, and completion route require a
Bearer token and compare it with `secrets.compare_digest`. `/health` remains public so a local
container supervisor can check liveness without learning backend topology. TLS, user identities,
quotas, audit retention, and secret rotation are deployment responsibilities beyond this demo.

## Benchmark interpretation

The observed throughput, TTFT, and resident VRAM are measurements. Arithmetic ratios and charts
are derived. Explanations about an engine's internal scheduler or memory allocation are inferences
unless the public evidence contains a controlled observation. This distinction is enforced in the
claim manifest and carried into [EVAL_REPORT.md](EVAL_REPORT.md).
