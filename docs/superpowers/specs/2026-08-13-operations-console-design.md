# Local Inference Operations Console — Design Specification

Date: 2026-08-13
Status: proposed for implementation
Primary language: 正體中文（zh-TW）；技術專有名詞保留原文

## 1. Purpose

Replace the current minimal Streamlit request table with an evidence-first Operations Console that makes the repository's inference engineering value legible within 30 seconds while remaining useful for local gateway diagnosis.

The console serves two audiences without pretending they share the same data source:

- GitHub visitors and reviewers can inspect a complete, explicitly labeled Demo Mode and the committed benchmark evidence without starting a model, GPU workload, gateway, or database.
- Local operators can switch to Live Mode to inspect the actual SQLite telemetry and current backend health available from their gateway.

This remains an observability surface for a single-workstation reference system. It is not represented as a production control plane, distributed scheduler, or Grafana replacement.

## 2. Success criteria

1. A first-time visitor sees meaningful content even when `data/gateway.db` does not exist.
2. Demo, live, and committed benchmark data are visually and textually distinguishable at all times.
3. The overview answers five questions immediately: Is the system healthy? How much traffic is present? How slow is it? Where is traffic routed? Did failover occur?
4. Every telemetry metric states its observation window and source.
5. Body text is comfortable to read and is not made artificially small to increase density.
6. Empty space supports hierarchy; it does not dominate the viewport or hide useful content below the fold.
7. The interface exposes engineering mechanisms and limitations, not merely attractive charts.

## 3. Product direction

### Selected approach: dual-mode Operations Console

The selected approach combines an operational view with a portfolio-ready evidence view:

- **Demo Mode** reads a deterministic mock SQLite fixture. It is the default only when a live database is unavailable. A persistent `DEMO DATA` badge, fixture time range, and explanatory note prevent confusion with production telemetry.
- **Live Mode** reads the configured local SQLite database. It is selected automatically when a compatible database exists and can also be selected manually.
- **Benchmark Evidence** always reads the committed aggregate artifacts in `bench/results`. It is neither demo data nor live telemetry.

Rejected alternatives:

- A dashboard-only refresh leaves the first-run experience empty and fails the portfolio goal.
- A portfolio landing page without operational depth makes the project look decorative and underuses the gateway telemetry.
- A separate frontend framework would increase build and maintenance surface without improving the core evidence story enough to justify it. Streamlit remains appropriate for this Python-first repository.

## 4. Information architecture

The primary navigation has four destinations. Secondary controls filter or anchor content instead of creating additional shallow pages.

### 4.1 Overview

The default view summarizes the active telemetry source and selected observation window.

Top-level metrics:

- Request volume and request rate
- Success rate with successful/total count
- P50 total latency
- P95 total latency
- Failover event count and failover/request ratio

Supporting panels:

- Request volume and P95 latency over time
- Current backend health, explicitly labeled as a current observation
- Alias routing chains and configured concurrency caps
- Recent failover events
- Data source, observation start/end, timezone, and last refresh

### 4.2 Routing & Reliability

This page explains runtime behavior rather than only reporting outcomes.

- Alias cards show ordered backends, resolved models, and `max_concurrent` configuration.
- Current backend health shows status and last check time where the live endpoint makes it available.
- Failover events show failed backend, next backend, reason, timestamp, and alias.
- Error categories aggregate sanitized `error_message` values and status codes.
- A concise explanatory note states that health polling is observational and request-time routing still walks the configured chain.
- Backpressure is represented through observed HTTP 429 / `concurrency_limit_exceeded` records. The UI must not infer current in-flight utilization because that field is not persisted.

### 4.3 Requests

This page provides a compact request explorer:

- Filters: observation window, alias, backend, success/failure, status code, streaming/non-streaming, and error category.
- Summary strip: filtered request count, success rate, P50/P95 latency, P50/P95 TTFT when available, prompt tokens, and completion tokens.
- Main table: timestamp, alias, backend, model, status, latency, TTFT, token counts, streaming, and sanitized error category.
- Default sort is newest first. Long tables are paginated or height-limited rather than expanding the entire page.
- Missing token and TTFT values render as an em dash with a short explanation, not as zero.

### 4.4 Benchmark Evidence

This page uses only committed aggregate artifacts and presents their evidence boundary.

- Concurrency comparison: aggregate decode throughput and P50/P95 TTFT across llama.cpp, Ollama, and LM Studio.
- Prefill comparison: calibrated 2k and 8k prompt results.
- Gateway overhead: direct versus via-gateway TTFT and total latency, highlighting the measured median overhead.
- VRAM summary and LM Studio Unified KV Cache controlled comparison.
- Method panel: measurement date, GPU, model file, quantization, engine versions, warmups, timed runs, seed, nonce policy, and engine isolation.
- Evidence panel: artifact class, public aggregation boundary, provenance digest policy, and link/path to `EVAL_REPORT.md`.
- Claims remain hardware- and version-specific. The UI does not declare a universal engine winner.

## 5. Visual system

### 5.1 Direction

Use a restrained “Morandi instrumentation” aesthetic: warm off-white surfaces, muted sage for healthy/active states, dusty blue for neutral evidence, clay amber for degraded states, and desaturated red only for failures.

Suggested semantic palette:

- Canvas: `#F1EFE8`
- Raised surface: `#FFFDF9`
- Primary text: `#26322C`
- Secondary text: `#66716B`
- Border: `#D9D6CC`
- Healthy / active: `#718B7A`
- Evidence / neutral: `#78909A`
- Warning / degraded: `#B1815F`
- Failure: `#A45F5F`

Color never acts as the only status signal; pair it with text and icons.

### 5.2 Typography and density

- UI copy is primarily zh-TW; industry terms such as Gateway, Backend Health, Alias Routing, P50/P95, TTFT, Failover, Throughput, Backpressure, Live, Demo, and Evidence remain in English.
- Prefer a system-compatible sans stack with `Noto Sans TC` when available.
- Body text target: 16 px minimum. Supporting metadata may use 13–14 px only when contrast remains strong.
- Main page title: approximately 30–36 px on desktop; section titles: 20–24 px.
- Metric values use tabular numerals where supported.
- Use an approximately 8 px spacing system. Typical panel gaps are 12–16 px and section gaps 20–28 px.
- Avoid nested cards when a divider or aligned grid communicates the grouping.
- Desktop overview should place key metrics and the first operational panels above or near the first fold at a typical 1440×900 viewport.

### 5.3 Streamlit chrome

- Hide or minimize nonessential Streamlit branding and deployment controls through supported configuration/CSS where practical.
- Keep application controls visually separate from Streamlit framework controls.
- Use a responsive main width rather than an excessively narrow centered column.

## 6. Data architecture

The current single `dashboard/app.py` is split into units with clear boundaries:

- `dashboard/app.py`: application entry point, page configuration, navigation, and mode selection.
- `dashboard/data/sqlite_repository.py`: read-only SQLite queries and schema compatibility checks.
- `dashboard/data/benchmark_repository.py`: parsing of committed CSV/JSON evidence and provenance.
- `dashboard/data/demo_fixture.py`: creation or loading of a deterministic, read-only demo database in a temporary/cache location. It must never overwrite `data/gateway.db`.
- `dashboard/metrics.py`: pure aggregation functions for percentiles, rates, time buckets, error categories, and filtered summaries.
- `dashboard/views/`: page renderers and reusable presentational components.
- `dashboard/theme.py` or a static CSS asset: centralized design tokens and Streamlit-specific styling.

Views receive typed or consistently shaped data frames/results. They do not open SQLite connections or parse evidence files directly.

### 6.1 Telemetry source selection

1. Inspect the configured `GATEWAY_DB_PATH`.
2. If a compatible database exists, default to Live Mode.
3. Otherwise default to Demo Mode and show a prominent but nonblocking explanation.
4. The user can switch modes explicitly.
5. Benchmark Evidence remains available in either mode because it has a separate committed source.

### 6.2 Observation windows

Preset windows: 15 minutes, 60 minutes, 6 hours, 24 hours, and All available data. Demo data uses a fixed clock-relative fixture or a fixed published fixture window, but the UI must state which policy is used. Aggregations are computed only from records within the selected window.

SQLite timestamps are stored as UTC ISO 8601. Display defaults to Asia/Taipei (`UTC+8`) while preserving the original timestamp semantics.

## 7. Data truthfulness and limitations

The following rules are non-negotiable:

- A demo fixture is never described as live, sampled, or production traffic.
- Current backend health is not converted into historical uptime or SLA.
- Queue depth, GPU utilization, GPU temperature, current in-flight requests, and capacity saturation are not displayed unless future telemetry explicitly records them.
- Backpressure is reported only from observed rejection records and configuration, not inferred from latency.
- Missing values remain missing and are explained; they are not coerced to zero.
- Benchmark results identify the measurement date, RTX 4090 environment, engine versions, model, and aggregate-only publication boundary.
- The console does not rank engines outside the measured workload and concurrency.

## 8. Empty, degraded, and error states

- **No live database:** retain the full console in Demo Mode and provide the exact command/path needed to start Live Mode.
- **Empty compatible database:** show live health/configuration where available and an informative request-empty state; do not stop the entire application.
- **Incompatible schema:** show the detected schema version, expected version, and a safe recovery instruction. Do not mutate the database.
- **SQLite temporarily locked:** keep the last successful view when possible, mark it stale, and offer refresh.
- **Gateway offline:** show telemetry from the database with a clear `Gateway offline / last observed` state; do not equate process reachability with backend health.
- **Benchmark artifact missing or digest mismatch:** isolate the affected panel, label the evidence unavailable/unverified, and leave other pages functional.
- **No rows after filtering:** preserve filters and summary context with a concise empty result message.

## 9. Interaction behavior

- Manual refresh is always available and reports the last successful refresh time.
- Optional auto-refresh is off by default to avoid surprising reruns; if enabled, use a conservative interval and keep filters stable.
- Filters use explicit labels and sensible defaults. Do not hide essential controls behind hover-only affordances.
- Charts include units, accessible legends, and tooltips. Tables retain exact values for auditability.
- Clicking or selecting an alias/backend narrows related panels where Streamlit can support it reliably; this is enhancement, not a prerequisite for the first release.

## 10. Demo fixture

The deterministic fixture should exercise real schema and meaningful operational cases:

- At least two aliases and three backends matching the example registry shape.
- A realistic spread of successful streaming and non-streaming requests.
- Enough timestamps for time-window and time-bucket behavior.
- P50 and P95 values that visibly differ.
- Several sanitized error categories, including timeout, connection, upstream 5xx, and concurrency-limit rejection.
- Multiple failover events, including one with no next backend.
- Nullable TTFT/token fields to verify honest missing-value rendering.

Fixture values are illustrative and must not reuse or imply unpublished raw benchmark runs.

## 11. Verification strategy

### Unit tests

- Percentile, rate, time-window, timezone, and error-category calculations.
- Empty and nullable datasets.
- Demo fixture determinism and schema compatibility.
- Benchmark artifact parsing and expected provenance fields.
- Live/Demo default-selection rules.

### Integration tests

- Read an initialized empty gateway database without stopping the entire UI data flow.
- Read a populated temporary database and verify overview summaries.
- Reject or explain an incompatible schema without mutation.
- Confirm the demo fixture never writes to the configured live database path.

### UI and smoke verification

- Streamlit starts headlessly without errors in Demo Mode and Live Mode.
- Rendered desktop view is visually checked near 1440×900 and at a narrow/mobile width.
- Primary body text, contrast, status labeling, and above-the-fold density are reviewed manually.
- Demo/Live/Evidence labels remain visible on every relevant page.

### Repository verification

- Existing Ruff, pytest, release checks, and evidence checks remain passing.
- No model weights, raw request benchmark runs, secrets, runtime database, or generated demo database are committed.

## 12. Scope boundaries

Included in the first implementation:

- Four-view Streamlit console
- Deterministic demo fixture
- Live SQLite telemetry
- Current backend health/configuration when safely available
- Committed benchmark evidence
- Responsive and accessible visual system
- Automated aggregation/data-source tests and startup smoke coverage

Deferred unless future telemetry warrants it:

- Authentication or remote deployment of the dashboard
- Persisted health history and uptime/SLA calculations
- Live GPU metrics
- Distributed/multi-worker aggregation
- Alerting, notification delivery, or incident acknowledgment
- Mutating gateway configuration from the UI
- React or another standalone frontend stack

## 13. Implementation constraints

- The dashboard remains loopback-only by default.
- SQLite access is read-only from the console.
- The design must preserve the repository's evidence/publication boundary.
- Existing user changes, if any, must be preserved.
- Implementation begins only after this design specification is reviewed and approved.
