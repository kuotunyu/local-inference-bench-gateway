# Owner actions after public release

The Public GitHub Repository is available at
<https://github.com/kuotunyu/local-inference-bench-gateway>. The local `main` branch tracks
`origin/main`. No tag, hosted release, raw benchmark run, or model-registry update has been
published.

## Completed local verification

Docker verification was completed from the repository root on 2026-08-12 with Docker Engine
29.6.1, Docker Desktop 4.80.0, and Compose v5.3.0. The non-root production image built
successfully, retained `USER 10001:10001` and its health check, and the CPU-only Compose smoke
reported: `CPU Compose smoke passed: auth, alias routing, primary 503, fallback 200`. The smoke
command and the subsequent volume/orphan cleanup both exited with status 0; no project smoke
containers, network, or volumes remained afterward. No GPU, model server, or model download was
used.

## Remaining owner decisions

1. **Review licenses for future evidence updates.** Recheck the linked model and engine terms and preserve
   [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). The scoped MIT license covers only original
   code authored by kuotunyu.
2. **Decide whether raw benchmark runs will ever be public.** The release defaults to no. Any
   later raw-data publication needs a separate privacy, size, and provenance review plus a new
   evidence schema.

## Optional owner work

- Run a fresh GPU experiment only if a new dated benchmark release is desired. Never overwrite
  the pinned 2026-07-17 evidence silently.
- Add a real deployment example only after choosing authentication, TLS, secret storage,
  telemetry retention, and multi-worker admission-control architecture.
- Capture a short demo showing primary failure, fallback success, SQLite telemetry, and the
  dashboard; use mock backends if a model cannot be redistributed.
