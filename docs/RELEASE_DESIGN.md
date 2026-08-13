# Release design

## Objective

Provide a public, reviewable single-workstation inference benchmark and OpenAI-compatible gateway
whose evidence and CPU behavior can be verified without a GPU, model download, paid API, or
access to another repository.

## Selected approach

The repository uses a new Git lineage and a file-by-file source allowlist. Aggregate measurements,
calibrated synthetic prompts, and charts are retained as evidence. Source history, raw runs,
runtime state, machine-local files, model weights, engine binaries, credentials, and private work
notes are excluded.

The alternatives were less suitable:

- Copying a complete working tree and deleting files later creates an avoidable disclosure risk.
- Rewriting every component from scratch would sever the relationship between the exercised code
  and the retained benchmark artifacts.

## Evidence model

Every public artifact is classified as a measured summary, measured control, calibrated input, or
derived chart. `provenance.json` pins artifacts and the recorded environment; `claims.json` maps
display claims to selectors that recompute them from public data. Documentation separates measured
facts, deterministic derivations, hardware-specific scope, and unproven interpretations.

The publication boundary is explicit: request-level raw runs are absent, so this release verifies
aggregate integrity but does not claim independent raw-to-summary re-aggregation.

## Gateway model

The gateway preserves a small module boundary around registry loading, backend I/O, ordered
failover, capacity admission, authentication, and SQLite telemetry. Hardening focuses on observed
failure boundaries: malformed envelopes, unsafe exception disclosure, logging failure, streaming
cleanup, invalid configuration, schema initialization, and application teardown.

The normal `/health` endpoint remains public. Topology and OpenAI routes share the optional API-key
boundary. Streaming remains line-oriented SSE pass-through, and a failure after headers terminates
without invented model output.

## Reviewer model

The primary review path is frozen dependency installation, static checks, CPU-only tests, evidence
verification, and publication-policy checks. A separate Compose topology uses two deterministic
mock backends to test auth, primary failure, fallback success, and cleanup. The production image
contains no benchmark evidence or mocks and runs without root privileges.

## Release boundary

The public repository uses `main`, one approved author identity, and a clean lineage that excludes
the private source history. A configured Git remote is expected after publication and is not itself
a disclosure violation; publication checks continue to audit reachable history, tracked and
non-ignored files, evidence, documents, and Docker policy. Tags, hosted releases, raw benchmark
runs, and model-registry updates remain separate, intentional owner actions.
