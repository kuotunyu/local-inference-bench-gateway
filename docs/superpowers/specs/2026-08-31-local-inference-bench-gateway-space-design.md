# Public-Safe Hugging Face Space Design

**Date:** 2026-08-31
**Status:** Approved by central coordinator on behalf of the owner
**Source repository:** `kuotunyu/local-inference-bench-gateway`
**Canonical Space identity:** `steven0226/local-inference-bench-gateway`

## 1. Objective

Publish a recruiter-friendly Hugging Face Space that demonstrates the repository's local
inference operations engineering without pretending that a public website can reach a visitor's
workstation. The Space presents exactly two evidence classes:

1. deterministic illustrative Demo Mode data; and
2. the repository's committed, digest-verified benchmark evidence.

The Space is not a hosted inference endpoint, a live gateway, a control plane, a GPU service, or
an availability claim. It must remain useful on CPU-only hardware without a model download,
backend engine, runtime database, credential, or network dependency.

This design implements Phase 1 priority 2 of the approved portfolio website strategy. It does not
authorize a Hugging Face mutation, deployment, GitHub About change, push, pull request, merge,
visibility change, or repository publication action.

## 2. Approved approach and rejected alternatives

### Selected: dedicated public-safe adapter plus allowlisted Docker Space bundle

A dedicated Streamlit entrypoint assembles immutable Demo data and committed evidence through
presentation-only contracts. A deterministic exporter constructs the separate Space repository
from an explicit source-to-destination allowlist. The bundle excludes the live application,
gateway runtime, SQLite readers, health client, secrets, and all local runtime state.

This is preferred because the public boundary is enforced by the import graph and deployment
payload, not only by hiding a control in the existing application.

### Rejected: environment switch in the existing Operations Console

Adding a `PUBLIC_SPACE` condition to `dashboard/app.py` would leave Live Mode, environment-driven
paths, SQLite access, gateway-health HTTP code, and gateway configuration inside the deployed
source tree. One missed branch could restore the wrong behavior. A visual toggle is not a security
or truth boundary.

### Rejected: static evidence-only page

A static page would minimize runtime surface but would remove the deterministic operational
walkthrough that demonstrates routing, failover, backpressure, request telemetry, and missing-data
semantics. It also would not implement the approved Streamlit direction. If a future account or
platform constraint prevents a Docker Streamlit Space, deployment stops for a new design decision;
it does not silently downgrade to this alternative.

## 3. Canonical identity and remote collision gate

The design target is the canonical Hub page:

`https://huggingface.co/spaces/steven0226/local-inference-bench-gateway`

The current authoritative evidence does not identify an existing or reserved Space for this
repository. That absence is not permanent authority to create or overwrite the name. Immediately
before any future remote creation, an authenticated preflight must perform all of the following:

1. Verify that the active Hugging Face identity is exactly `steven0226` and has permission to
   create a public Docker Space in that namespace.
2. Perform an exact authenticated lookup for the canonical Space ID, including objects that are
   private or protected to the authenticated owner.
3. List namespace Spaces with the authenticated identity and compare normalized IDs exactly; a
   public search result alone is insufficient.
4. Treat an existing object, reserved name, HTTP 401/403, network failure, incomplete response, or
   any other ambiguous result as a hard stop.
5. Never delete, repurpose, rename, transfer, force-push, reset, or overwrite a colliding Space.
6. Confirm that the account can create the required compute-backed Docker Space. If account or
   billing policy prevents creation, stop rather than substituting another SDK or identity.

Only a confirmed not-found result under the verified owner identity permits a separately approved
creation step. This gate must be implemented as a non-mutating command that completes before any
create or upload call. The check and the later create operation should be adjacent in the
deployment workflow to minimize time-of-check/time-of-use drift; a create-time conflict still
stops the workflow without retrying destructively.

## 4. Public truth contract

The following claim ceiling appears above the first interactive control on every fresh session:

> 公開證據示範（Demo Mode）
>
> 此 Space 僅呈現 deterministic illustrative fixture 與 2026-07-17 committed aggregate
> evidence。它不會、也無法連線到訪客的本機 Gateway、SQLite、inference backend 或 GPU；
> 不是 live inference service，亦無 SLA。Space 可能休眠或 cold-start；其啟動狀態不代表
> Gateway uptime。

The wording may be adjusted for line wrapping, but none of these meanings may be weakened. The
page must continue to state all of the following above the first control:

- deterministic Demo data is illustrative and is not production or sampled traffic;
- benchmark evidence is a dated, hardware- and version-specific snapshot;
- request-level raw benchmark runs are not public;
- the Space cannot connect to a visitor's local system;
- the Space provides neither live inference nor an SLA; and
- hosting sleep or cold start is not system uptime evidence.

Every operational page also displays a persistent
`DETERMINISTIC DEMO · 非正式流量` source badge. The evidence page displays
`COMMITTED EVIDENCE · aggregate only · raw runs unpublished`. A badge cannot replace the claim
ceiling.

## 5. System boundary and data flow

```text
Hugging Face visitor
    -> public Streamlit entrypoint
        -> immutable public presentation contracts
            -> deterministic in-memory Demo snapshot
                -> Demo Overview / Routing / Requests
            -> read-only committed evidence loader
                -> SHA-256 and schema verification
                    -> Benchmark Evidence view
```

There is no data-flow edge to a gateway, local database, health endpoint, inference engine,
model, GPU, Space secret, user upload, or remote API.

### 5.1 Public entrypoint

The Space uses a dedicated public entrypoint rather than `dashboard/app.py`. It owns only page
configuration, the immutable truth-contract banner, public navigation, fixed Demo-window controls,
and assembly of the two approved sources.

It must not:

- offer a Demo/Live selector;
- read `GATEWAY_DB_PATH`, `GATEWAY_BASE_URL`, `GATEWAY_API_KEY`, or another credential/path
  override;
- discover local files from user-controlled environment variables;
- import or call the gateway application, registry loader, live-state assembler, SQLite
  repository, or health client;
- initiate HTTP, HTTPS, socket, subprocess, model download, or inference activity; or
- fall back to Live Mode under any error condition.

Browser-visible links to GitHub, the canonical Hub page, and source documentation are ordinary
navigation links. They do not authorize server-side fetching.

### 5.2 Deterministic Demo source

The public Demo source is a pure builder that returns a `TelemetrySnapshot`-shaped in-memory
object and immutable presentation models. It reuses the approved scenario semantics: at least two
aliases; multiple engine labels; successful streaming and non-streaming requests; nullable TTFT
and token fields; connection, timeout, upstream 5xx, and HTTP 429 examples; and failover events,
including an exhausted chain.

The builder has a fixed timestamp range and fixed rows. Observation windows anchor to the maximum
fixture timestamp, not the wall clock. Repeated construction must produce equal frames and a stable
canonical digest. The public path does not create, open, copy, or mutate a `.db`, `.sqlite`, or
`.sqlite3` file.

Demo backend presentation uses stable engine/backend labels, never endpoint URLs. A panel that
currently describes `Backend Health` must be presented in the Space as `Fixture backend state`
or an equivalent phrase that cannot be read as a current reachability check. The fixture state is
part of the scenario, not a probe.

The local Operations Console may retain its existing SQLite-backed Demo and Live behavior. Any
shared fixture refactor must preserve that local contract and its tests, while the public adapter
imports only the pure in-memory builder.

### 5.3 Presentation contracts

Shared views should depend on small dashboard-owned display contracts rather than runtime types
from `gateway.registry` or `dashboard.data.live_status`. The local Console adapter converts runtime
objects to those contracts. The public adapter constructs them from fixture constants.

This targeted separation is in scope because it makes the public import boundary enforceable. It
does not change gateway routing, health polling, SQLite schema, telemetry collection, failover,
capacity, authentication, or benchmark calculations.

### 5.4 Committed benchmark evidence

The evidence path reads the complete committed `bench/results` evidence set. The two control
manifests are `provenance.json` and `claims.json`; the 12 declared artifacts are validated against
the SHA-256 values in `provenance.json` using the repository's existing LF-normalization rule for
CSV/JSON and original bytes for PNG.

Evidence rendering is fail-closed:

- a missing or invalid provenance manifest invalidates the verified evidence context;
- an unsafe, duplicate, missing, or digest-mismatched artifact is quarantined;
- a panel must not display a canonical metric derived from an unavailable artifact;
- unaffected panels may remain available only when their required artifacts are independently
  verified under a valid manifest; and
- the UI must never replace a missing value with zero or a stale hard-coded claim.

The committed evidence is copied byte-for-byte into the Space bundle. It is not downloaded from
GitHub or Hugging Face at runtime and is not regenerated during Space startup.

## 6. Information architecture

The Space preserves four engineering views while eliminating source ambiguity:

1. **Deterministic Demo Overview** — request count/rate, success rate, latency, failover count,
   fixture activity, routing, and fixture backend state.
2. **Demo Routing and Reliability** — ordered alias chains, configured fixture capacity,
   failover examples, sanitized error classes, and observed fixture backpressure.
3. **Demo Request Records** — filters and exact illustrative metadata rows, with missing values
   retained as missing.
4. **Committed Benchmark Evidence** — throughput, TTFT, prefill, gateway overhead, VRAM, controlled
   Unified KV Cache comparison, provenance, method, and publication boundary.

The header has no telemetry-source selector and no live refresh control. Observation-window
controls appear only where they filter the fixed Demo snapshot. The evidence view always uses the
full committed snapshot and does not imply that it changes with page refresh.

The evidence first screen identifies the measurement date, RTX 4090 environment, recorded model,
digest status, aggregate-only boundary, and the statement that results are not a universal engine
ranking. It links to the GitHub repository, `EVAL_REPORT.md`, scoped MIT license, and
`THIRD_PARTY_NOTICES.md`.

No view accepts prompts, files, backend addresses, database paths, API keys, or inference
parameters. There is no chat box, upload control, run-benchmark button, health refresh, or gateway
configuration control.

## 7. Repository and deployment-bundle design

The GitHub repository remains the reviewable source of truth. A `space/` source directory holds
Space-specific card/runtime assets, while public adapter and reusable dashboard modules remain in
their normal Python packages. A deterministic export step creates a separate temporary Space
checkout from an explicit manifest; it does not mirror the entire GitHub repository.

### 7.1 Required source-to-bundle allowlist

The export manifest enumerates both source and destination path. At minimum, it includes:

- Space card `README.md` with `sdk: docker` and `app_port: 7860` metadata;
- a Space-only `Dockerfile`;
- a minimal, exactly pinned Space dependency file;
- a Space-specific `.streamlit/config.toml` containing theme and telemetry settings but no
  loopback-only server address;
- the dedicated public entrypoint;
- the pure public Demo builder and neutral presentation contracts;
- only the dashboard components, metrics, charts, theme, evidence loader, and views used by the
  public entrypoint;
- all 12 evidence artifacts plus `provenance.json` and `claims.json`;
- `EVAL_REPORT.md`, `LICENSE`, and `THIRD_PARTY_NOTICES.md`; and
- a generated deployment manifest recording the exact GitHub source commit, export-manifest
  digest, evidence-manifest digest, and intended canonical Space ID.

The deployment manifest is provenance for the bundle, not benchmark evidence. It may be generated
at export time, must be committed with the future Space revision, and must not alter evidence
files.

### 7.2 Path denylist

The exporter and bundle verifier reject these paths and classes even if an implementation later
adds them to a broad source pattern:

- `gateway/`;
- local `dashboard/app.py` and `dashboard/state.py`;
- `dashboard/data/live_status.py` and `dashboard/data/sqlite_repository.py`;
- `.env` files other than no environment template is needed in the Space bundle;
- `compose*.yaml`, the gateway production Dockerfile, and `docker/smoke/`;
- `gateway/models*.yaml`, `data/`, `.dashboard-cache/`, `.superpowers/`, `.worktrees/`, logs, and
  runtime databases;
- benchmark runners, raw results, JSONL logs, calibrated-run staging directories, and local helper
  scripts;
- model weights, inference engines, native binaries, archives, and Git metadata; and
- any file not explicitly named by the export manifest.

The final clause makes the bundle an allowlist even as the repository evolves.

### 7.3 Import and capability denylist

Static inspection of the public entrypoint's transitive application import graph must reject:

- `gateway.*`;
- `dashboard.state`;
- `dashboard.data.live_status` and `dashboard.data.sqlite_repository`;
- `sqlite3`, `httpx`, `requests`, `urllib.request`, raw `socket`, and process-spawning modules in
  public application code;
- reads of any `GATEWAY_*`, Hugging Face secret, credential, arbitrary file-path, or backend URL
  environment variable; and
- dynamically constructed imports that bypass the check.

Documentation may truthfully discuss SQLite, HTTP, and the local gateway. The denylist applies to
shipped application paths and executable imports, not to honest explanatory text.

## 8. Docker Space runtime

Hugging Face deprecated its built-in Streamlit SDK in favor of running Streamlit with the Docker
SDK. The Space therefore declares `sdk: docker` and `app_port: 7860` and starts Streamlit on
`0.0.0.0:7860`.

Runtime requirements:

- fixed Python 3.12 base compatible with the source project;
- CPU-only image with no CUDA, GPU, model-serving, or inference dependencies;
- non-root runtime user with a stable numeric UID/GID such as `10001:10001`;
- explicit `COPY` instructions rather than `COPY . .`;
- minimal directly used packages pinned to exact versions and checked against `uv.lock`;
- `gatherUsageStats = false`;
- no declared Space secrets, variables, model preload, persistent storage, or GPU hardware;
- no application-owned writes outside ephemeral framework/cache paths; and
- a container health check that probes only the Streamlit process inside the container.

The self-health probe is hosting process liveness. It must not be displayed as gateway/backend
health, historical uptime, or an SLA. The image must not expose the gateway's port 9000 or start
Uvicorn.

The Space card states that free/default compute may sleep and cold-start. A future operator must
not select paid always-on hardware to create an implied availability guarantee without a separate
owner decision.

## 9. Runtime network isolation

The public application is network-independent after the image is built. Dependency installation
during image build is distinct from runtime behavior.

Network controls and verification must establish that:

- startup and all four views work when outbound network access is denied;
- no code path resolves or contacts loopback gateway ports, LAN addresses, Hugging Face APIs,
  GitHub, model repositories, telemetry endpoints, or inference backends;
- poisoned `GATEWAY_*` and proxy environment variables do not alter rendered data or cause a
  connection attempt;
- all benchmark and Demo data come from the bundle; and
- user clicks on documentation links are browser navigation, not server fetches.

A container smoke run with no outbound network must start Streamlit and pass its internal local
process-health probe. A separate normal-network browser smoke may expose port 7860 solely for UI
inspection. Neither smoke may start or contact the gateway.

## 10. Error and degraded states

- **Demo construction failure:** show a public Demo unavailable state and retain the truth-contract
  banner. Do not discover a database or fall back to Live Mode.
- **Evidence manifest missing or invalid:** state that evidence verification is unavailable and
  suppress canonical evidence metrics.
- **Individual artifact failure:** isolate the affected panel under the valid-manifest rules in
  Section 5.4; do not render cached or hard-coded values.
- **Unexpected environment configuration:** ignore it, log no secret value, and preserve the same
  deterministic output.
- **Runtime network denial:** remain functional; a connection error is a test failure, not a
  user-facing operating mode.
- **Cold start or sleep:** rely on the Hub lifecycle screen, then render the same deterministic
  application after startup. Never translate host availability into project uptime.
- **Canonical name or permission ambiguity:** stop before mutation and report the exact gate that
  could not be proven.

Errors must not expose filesystem paths, environment values, credentials, exception strings,
internal URLs, or stack traces in the public UI.

## 11. Verification strategy

### 11.1 Unit and contract tests

- The pure Demo builder produces equal snapshots and a stable digest across repeated runs.
- Demo observation windows anchor to the fixture maximum timestamp.
- No public builder operation creates or opens a database file.
- Neutral presentation contracts preserve existing local Console semantics.
- Evidence parsing, schema checks, artifact path containment, and SHA-256 mismatch handling retain
  their existing tests.
- Exact Space dependency pins match the corresponding versions resolved in `uv.lock`.
- The bundle allowlist includes every runtime import and rejects every non-allowlisted path.
- Static transitive-import inspection enforces the import/capability denylist in Section 7.3.

### 11.2 Streamlit AppTest

AppTest renders all four public views and verifies:

- the complete truth-contract banner occurs before the first interactive control;
- no source selector, Live Mode label, refresh-health control, inference input, local endpoint,
  database path, or credential control exists;
- operational pages always show the deterministic Demo badge;
- the evidence page always shows the aggregate/raw-run boundary and measurement scope;
- fixture filtering is deterministic;
- missing values remain em dashes rather than zero; and
- missing/tampered evidence fails closed without breaking unrelated navigation.

An isolation test blocks socket creation and common HTTP clients, sets hostile values for every
known `GATEWAY_*`, proxy, and credential-like environment key, and renders every page. The render
must complete without a connection attempt and must match the clean-environment semantic output.

### 11.3 Repository and bundle policy

Run the full frozen repository suite, Ruff lint/format checks, and release checks. Add a Space
bundle verifier that rejects:

- secrets or secret-like tokens;
- environment files, databases, raw runs, model weights, engine binaries, archives, and runtime
  state;
- Windows user paths or private source paths;
- files at least 5 MiB;
- broad Docker copies, root runtime, GPU configuration, gateway ports, and unpinned direct
  dependencies;
- a missing scoped license, third-party notices, or source revision manifest; and
- evidence bytes or digests that differ from the source commit.

### 11.4 Docker and runtime smoke

- Build the Space image from the exported bundle on CPU-only CI.
- Inspect the final user and fail if it is root.
- Confirm only the Streamlit app is started and port 7860 is used.
- Start with outbound networking disabled and check internal Streamlit process health.
- Run a browser smoke against an exposed local port and visit all four views.
- Confirm no model download, gateway process, SQLite database, or external request appears in logs
  or filesystem outputs.

### 11.5 Visual and claim gates

Perform bounded visual review at approximately 1440x900 and 390px widths:

- the claim ceiling is visible before the first control without scrolling;
- navigation, badges, charts, tooltips, legends, tables, and error states remain readable;
- no horizontal overflow or clipped disclosure occurs;
- no Streamlit exception or browser-console error is present;
- fixture state cannot be mistaken for current backend health; and
- the four views retain the existing restrained scientific-console design.

Every displayed benchmark number must resolve from a verified committed artifact or an existing
canonical claim selector. The review rejects universal engine-winner language, production-ready
claims, current GPU/queue/health claims, uptime/SLA claims, and any suggestion that the Space is
running the recorded model. Demo values may be fixed only when the Demo badge and illustrative
scope remain visible.

## 12. Deployment and About gates

No deployment is authorized by this spec. A future, separately approved deployment proceeds in
this order:

1. Re-run the authenticated identity/collision gate in Section 3.
2. Build the allowlisted bundle from a clean, approved GitHub source commit.
3. Run all unit, AppTest, policy, evidence, Docker, network-isolation, and visual preflight checks.
4. Create the exact new public Space only if the gate proves the name is available and the account
   is eligible.
5. Upload the exact reviewed bundle without altering evidence.
6. Verify the public canonical Hub page, source identity, public/not-disabled state, cold start,
   desktop/mobile rendering, license, links, claim ceiling, and runtime logs.
7. Record the Space commit and its GitHub source revision in the portfolio control ledger.
8. Request a separate owner approval for the GitHub About Website update.
9. Only after that approval, set About to the canonical Hub page, never the `*.hf.space` runtime
   subdomain, and read the GitHub API back to verify the exact URL.

A planned, building, private, disabled, broken, or unreviewed Space is never placed in GitHub
About. A successful Space deployment does not itself authorize the About mutation.

## 13. Success criteria

The design is successfully implemented only when all of the following are true:

1. A first-time visitor understands within the first viewport that the site is deterministic Demo
   plus committed evidence, not live inference.
2. The shipped application has no import or bundle path to gateway runtime, local SQLite, health
   polling, credentials, model downloads, or inference backends.
3. The Demo remains deterministic, in memory, clearly labeled, and useful across all three
   operational views.
4. Every benchmark claim is derived from verified committed evidence and fails closed when its
   source is unavailable.
5. The Docker Space is CPU-only, non-root, network-independent at runtime, and honest about sleep
   and cold start.
6. The exported payload passes secret, size, license, artifact, source-revision, and denylist
   checks.
7. Desktop and mobile review preserves the truth contract and scientific-console readability.
8. Remote collision, Space deployment, and GitHub About remain separate explicit gates.

## 14. Non-goals

- Hosting the FastAPI gateway or an OpenAI-compatible inference endpoint.
- Connecting the Space to a visitor's localhost, LAN, VPN, tunnel, database, GPU, or backend.
- Loading the recorded GGUF or any model weight.
- Re-running, updating, or replacing the 2026-07-17 benchmark.
- Publishing request-level raw runs.
- Presenting fixture state as live telemetry, current health, production traffic, or an SLA.
- Adding authentication, uploads, prompts, remote configuration, persistence, analytics, alerts,
  control-plane actions, or a paid always-on availability promise.
- Refactoring gateway behavior or changing the local Console beyond the narrow presentation-contract
  separation needed for safe reuse.
- Creating or modifying a Space, pushing, opening a PR, merging, changing visibility, or editing
  GitHub About as part of the design-document phase.

## 15. Authoritative references

- Portfolio strategy:
  `../_portfolio_control/docs/superpowers/specs/2026-08-30-github-about-website-strategy-design.md`
- Repository evidence boundary: `README.md`, `EVAL_REPORT.md`, and
  `bench/results/provenance.json`
- Existing Operations Console design:
  `docs/superpowers/specs/2026-08-13-operations-console-design.md`
- Hugging Face Spaces changelog, including Streamlit SDK deprecation:
  <https://huggingface.co/docs/hub/spaces-changelog>
- Hugging Face Docker Spaces configuration:
  <https://huggingface.co/docs/hub/spaces-sdks-docker>
- Hugging Face Spaces lifecycle and visibility:
  <https://huggingface.co/docs/hub/spaces-overview>
