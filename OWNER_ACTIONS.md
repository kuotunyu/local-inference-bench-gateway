# Owner actions before public release

No remote repository, push, tag, pull request, hosted release, or model-registry update was
created by this release preparation.

## Required owner decisions

1. **Run the Docker verification when the daemon is available.** On 2026-08-12 the installed
   Docker client reported version 29.6.1 and Compose v5.3.0, but the Linux daemon endpoint was
   unavailable because the `dockerDesktopLinuxEngine` named pipe did not exist. Docker Desktop was
   not started automatically. Run the build and CPU-only Compose smoke commands from
   [SETUP.md](SETUP.md), then record the successful output before publishing.
2. **Review the public-facing repository metadata.** Choose the final repository name,
   description, topics, visibility, branch protection, and vulnerability-reporting process.
3. **Create the remote and publish intentionally.** Confirm `git remote -v` is empty, inspect the
   complete local history, then create and push to the owner's chosen host. Do not import or merge
   the private source history.
4. **Review licenses at publication time.** Recheck the linked model and engine terms and preserve
   [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). The scoped MIT license covers only original
   code authored by kuotunyu.
5. **Decide whether raw benchmark runs will ever be public.** The release defaults to no. Any
   later raw-data publication needs a separate privacy, size, and provenance review plus a new
   evidence schema.

## Optional owner work

- Run a fresh GPU experiment only if a new dated benchmark release is desired. Never overwrite
  the pinned 2026-07-17 evidence silently.
- Add a real deployment example only after choosing authentication, TLS, secret storage,
  telemetry retention, and multi-worker admission-control architecture.
- Capture a short demo showing primary failure, fallback success, SQLite telemetry, and the
  dashboard; use mock backends if a model cannot be redistributed.
