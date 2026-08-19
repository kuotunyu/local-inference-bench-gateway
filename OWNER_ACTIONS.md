# Release closure record and owner actions

## v0.1.0 release criteria

The intended formal tag for this source line is `v0.1.0`. Publication status is deliberately not
asserted in this document. The authoritative sources are the repository's
[`v0.1.0` tag](https://github.com/kuotunyu/local-inference-bench-gateway/tree/v0.1.0) and
[GitHub Releases](https://github.com/kuotunyu/local-inference-bench-gateway/releases); their
presence and target determine whether the release has actually been published.

A source commit qualifies for `v0.1.0` only when all of the following are true:

- `pyproject.toml` and `uv.lock` identify version `0.1.0`.
- Frozen dependency sync, Ruff lint and format checks, the complete CPU test suite, and
  `python -m release_checks.cli` pass from a clean worktree.
- The exact source commit passes the GitHub Actions `verify` job, including the non-root image
  build and CPU-only Compose smoke.
- `main` is protected by the existing `verify` check, uses linear history, and forbids force
  pushes and deletion.
- The annotated `v0.1.0` tag points exactly to that validated `main` commit.
- Release notes preserve the evidence and deployment boundaries below.

No GPU rerun is required for release closure. A new GPU run would be a new dated experiment and
must not silently replace the committed 2026-07-17 evidence.

## Validated evidence and publication boundaries

- The benchmark is a dated 2026-07-17 snapshot for the recorded NVIDIA GeForce RTX 4090,
  driver, model, engine versions, flags, and workload. It is not a cross-hardware or
  cross-version engine ranking.
- Request-level raw benchmark runs are not public. Public aggregate artifacts can verify
  integrity and canonical claims, but cannot independently recreate the aggregation from the
  unpublished requests.
- The Gateway is a single-process, single-workstation reference implementation, not a
  multi-worker or distributed serving control plane.
- Operations Console Demo, Live, and Benchmark Evidence modes have separate truth boundaries:
  deterministic illustrative fixture, metadata-only local telemetry, and committed aggregate
  evidence respectively.
- The scoped MIT license covers only original source code authored by kuotunyu. Model weights,
  inference engines, third-party packages, trademarks, third-party content, and benchmark facts
  are not relicensed; see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).

## Completed local verification baseline

Docker verification was completed from the repository root on 2026-08-12 with Docker Engine
29.6.1, Docker Desktop 4.80.0, and Compose v5.3.0. The non-root production image built
successfully, retained `USER 10001:10001` and its health check, and the CPU-only Compose smoke
reported: `CPU Compose smoke passed: auth, alias routing, primary 503, fallback 200`. The smoke
command and the subsequent volume/orphan cleanup both exited with status 0; no project smoke
containers, network, or volumes remained afterward. No GPU, model server, or model download was
used.

## Remaining owner decisions

1. **Review licenses for future evidence updates.** Recheck the linked model and engine terms and
   preserve [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
2. **Decide whether raw benchmark runs will ever be public.** The default is no. Any later
   raw-data publication needs a separate privacy, size, and provenance review plus a new evidence
   schema.

## Optional owner work

- Run a fresh GPU experiment only if a new dated benchmark release is desired. Never overwrite
  the pinned 2026-07-17 evidence silently.
- Add a real deployment example only after choosing authentication, TLS, secret storage,
  telemetry retention, and multi-worker admission-control architecture.
- Capture a short demo showing primary failure, fallback success, SQLite telemetry, and the
  dashboard; use mock backends if a model cannot be redistributed.
