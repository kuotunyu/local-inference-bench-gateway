# Source-to-public audit

## Decision

The private source repository was treated as a read-only evidence library. Its Git history was not
copied, merged, rebased, or used as the ancestry of this repository. The public candidate began
from a new `main` branch and a file-by-file allowlist.

## Pinned source state

- Branch: `main`
- Commit: `f7b80d221460f1e1219a0ec5c7044465ea961dba`
- Remote configuration: none
- Worktree at audit and final comparison: clean
- CPU baseline from an archive-derived temporary copy: 28 tests passed

The two source commits used identities and message trailers that do not satisfy this release's
single-author policy. Rejecting the old lineage prevents those metadata from becoming public
history.

## Included by allowlist

- Gateway, benchmark, dashboard, and one local backpressure script
- Aggregate CSV/JSON results, calibrated synthetic prompt inputs, and derived PNG charts
- Existing CPU-only regression tests

## Explicitly excluded

- Git metadata and prior history
- Environment files, credentials, caches, virtual environments, logs, and runtime databases
- Model weights, inference-engine binaries, downloads, and generated raw request runs
- Private working notes, interview notes, and machine-specific helper scripts
- Source Docker and setup assets that had not passed the new publication boundary

No tracked source tree contained a model, engine binary, environment file, database, or raw result
directory. A history-wide secret-like scan and a local identity/path scan found no content match,
but the release still uses an allowlist rather than treating a negative scan as sufficient proof.

## Evidence preservation

The measured aggregate artifacts and charts were copied without altering their numerical content.
Their canonical LF or binary SHA-256 digests are recorded in
`bench/results/provenance.json`. The release does not claim to reproduce aggregates from raw runs,
because those raw runs are not public.

## Destination policy

All commits use only `kuotunyu <61350295+kuotunyu@users.noreply.github.com>`, contain no co-author
trailer, and remain local with no remote configured. Publication policy checks audit tracked and
non-ignored files plus commit metadata before the repository can be considered a release
candidate.
