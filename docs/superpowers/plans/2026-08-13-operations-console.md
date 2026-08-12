# Local Inference Operations Console Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a polished, evidence-first Streamlit Operations Console with honest Demo/Live telemetry modes and a committed Benchmark Evidence view.

**Architecture:** Keep Streamlit as the delivery surface, but separate read-only data repositories, deterministic fixture generation, pure metric calculations, and page renderers. The UI selects a telemetry source once, passes shaped data into view functions, and treats committed benchmark artifacts as a separate evidence source.

**Tech Stack:** Python 3.12–3.14, Streamlit 1.40–1.x, pandas 2.2–3.x, SQLite, httpx, PyYAML, pytest, Ruff.

## Global Constraints

- Primary UI language is 正體中文（zh-TW）; established technical terms remain in English.
- Body text must target 16 px minimum; supporting metadata may use 13–14 px only with strong contrast.
- Use the approved Morandi instrumentation palette and never rely on color alone for status.
- Demo, Live, and Benchmark Evidence sources must remain visibly distinct on every relevant page.
- SQLite access from the console is read-only; demo generation must never write to `GATEWAY_DB_PATH`.
- Missing values remain missing and render as an em dash, never zero.
- Do not infer GPU metrics, queue depth, current in-flight requests, uptime, or SLA from existing data.
- Benchmark claims remain hardware-, version-, and workload-specific.
- Dashboard binds to loopback by default and does not mutate gateway configuration.
- Do not commit runtime databases, fixture databases, raw benchmark requests, secrets, or generated UI caches.

## Planned file structure

- `dashboard/app.py`: Streamlit entry point, source selection, navigation, and page dispatch.
- `dashboard/models.py`: shared dataclasses and typed telemetry/evidence result shapes.
- `dashboard/data/sqlite_repository.py`: read-only schema validation and telemetry queries.
- `dashboard/data/demo_fixture.py`: deterministic SQLite fixture construction in a temporary/cache path.
- `dashboard/data/benchmark_repository.py`: committed CSV/JSON/provenance loading.
- `dashboard/data/live_status.py`: safe, time-bounded gateway and backend-health reads.
- `dashboard/metrics.py`: pure filtering, percentile, time-bucket, and category calculations.
- `dashboard/theme.py`: CSS tokens, Streamlit chrome adjustments, and formatting helpers.
- `dashboard/components.py`: shared source badge, metric card, state message, and provenance UI.
- `dashboard/views/overview.py`: overview renderer.
- `dashboard/views/reliability.py`: routing, health, failover, and backpressure renderer.
- `dashboard/views/requests.py`: request explorer renderer.
- `dashboard/views/evidence.py`: benchmark evidence renderer.
- `tests/dashboard/`: isolated repository, metric, fixture, evidence, status, and smoke tests.
- `SETUP.md` and `README.md`: console launch and mode documentation.

---

### Task 1: Establish telemetry contracts and read-only SQLite access

**Files:**
- Create: `dashboard/__init__.py`
- Create: `dashboard/data/__init__.py`
- Create: `dashboard/models.py`
- Create: `dashboard/data/sqlite_repository.py`
- Create: `tests/dashboard/__init__.py`
- Create: `tests/dashboard/test_sqlite_repository.py`

**Interfaces:**
- Produces: `TelemetrySnapshot(requests: pd.DataFrame, failovers: pd.DataFrame, schema_version: int, source_path: Path)`.
- Produces: `SchemaStatus(compatible: bool, detected_version: int | None, reason: str | None)`.
- Produces: `inspect_schema(path: Path) -> SchemaStatus` and `load_snapshot(path: Path) -> TelemetrySnapshot`.
- `load_snapshot` opens SQLite with URI `mode=ro`, never creates a file, and raises `TelemetryUnavailable` or `IncompatibleSchema` with safe messages.

- [ ] **Step 1: Write failing repository tests**

```python
def test_missing_database_is_unavailable_without_creating_file(tmp_path):
    path = tmp_path / "missing.db"
    with pytest.raises(TelemetryUnavailable, match="找不到 Live telemetry"):
        load_snapshot(path)
    assert not path.exists()


def test_load_snapshot_reads_gateway_schema(tmp_path):
    path = tmp_path / "gateway.db"
    init_db(path)
    snapshot = load_snapshot(path)
    assert snapshot.schema_version == 1
    assert list(snapshot.requests.columns) == REQUEST_COLUMNS
    assert list(snapshot.failovers.columns) == FAILOVER_COLUMNS
```

- [ ] **Step 2: Run the tests and verify the import failure**

Run: `uv run --frozen pytest tests/dashboard/test_sqlite_repository.py -q`

Expected: FAIL because `dashboard.models` and `dashboard.data.sqlite_repository` do not exist.

- [ ] **Step 3: Implement contracts and URI read-only queries**

```python
@dataclass(frozen=True)
class TelemetrySnapshot:
    requests: pd.DataFrame
    failovers: pd.DataFrame
    schema_version: int
    source_path: Path


def _connect_read_only(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise TelemetryUnavailable(f"找不到 Live telemetry：{path}")
    uri = f"file:{path.resolve().as_posix()}?mode=ro"
    return sqlite3.connect(uri, uri=True, timeout=2.0)
```

Validate `PRAGMA user_version == 1` and the exact required column subsets before querying. Return empty DataFrames with stable columns for an initialized empty database.

- [ ] **Step 4: Run repository tests**

Run: `uv run --frozen pytest tests/dashboard/test_sqlite_repository.py -q`

Expected: PASS.

- [ ] **Step 5: Run formatting and commit**

Run: `uv run --frozen ruff check dashboard/models.py dashboard/data/sqlite_repository.py tests/dashboard/test_sqlite_repository.py`

Commit:

```bash
git add dashboard tests/dashboard
git commit -m "feat: add read-only dashboard telemetry repository"
```

### Task 2: Add pure telemetry metrics and filtering

**Files:**
- Create: `dashboard/metrics.py`
- Create: `tests/dashboard/test_metrics.py`

**Interfaces:**
- Consumes: request and failover DataFrames from `TelemetrySnapshot`.
- Produces: `RequestFilters`, `OverviewMetrics`, `filter_requests`, `compute_overview`, `bucket_request_series`, and `categorize_error`.

- [ ] **Step 1: Write failing calculation tests**

```python
def test_compute_overview_uses_window_and_preserves_missing_ttft():
    rows = request_frame([
        {"timestamp": "2026-08-13T00:00:00+00:00", "success": 1,
         "total_latency_ms": 100.0, "ttft_ms": None},
        {"timestamp": "2026-08-13T00:01:00+00:00", "success": 0,
         "total_latency_ms": 900.0, "ttft_ms": None},
    ])
    result = compute_overview(rows, failover_frame([]))
    assert result.request_count == 2
    assert result.success_rate_pct == 50.0
    assert result.p50_latency_ms == 500.0
    assert result.p50_ttft_ms is None


@pytest.mark.parametrize(("raw", "expected"), [
    ("connection_error", "Connection"),
    ("stream_read_error", "Streaming"),
    ("HTTP 429", "Backpressure"),
    ("HTTP 503", "Upstream 5xx"),
])
def test_categorize_error(raw, expected):
    assert categorize_error(raw, status_code=None) == expected
```

- [ ] **Step 2: Verify failures**

Run: `uv run --frozen pytest tests/dashboard/test_metrics.py -q`

Expected: FAIL because the metrics API is missing.

- [ ] **Step 3: Implement pure calculations**

Use dataclasses with `float | None` percentile fields. Convert timestamps with `pd.to_datetime(..., utc=True, errors="coerce")`; exclude invalid timestamps from windowed series but keep the original records available to the request table. Calculate P50/P95 only from non-null numeric values. Define backpressure as status 429 or sanitized category `concurrency_limit_exceeded`.

```python
def percentile_or_none(series: pd.Series, q: float) -> float | None:
    values = pd.to_numeric(series, errors="coerce").dropna()
    return None if values.empty else float(values.quantile(q))
```

- [ ] **Step 4: Run metric and repository tests**

Run: `uv run --frozen pytest tests/dashboard/test_metrics.py tests/dashboard/test_sqlite_repository.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add dashboard/metrics.py tests/dashboard/test_metrics.py
git commit -m "feat: derive honest gateway telemetry metrics"
```

### Task 3: Build deterministic Demo Mode and source selection

**Files:**
- Create: `dashboard/data/demo_fixture.py`
- Create: `dashboard/data/live_status.py`
- Create: `tests/dashboard/test_demo_fixture.py`
- Create: `tests/dashboard/test_live_status.py`
- Modify: `.gitignore`

**Interfaces:**
- Consumes: gateway schema version 1 and `load_snapshot`.
- Produces: `ensure_demo_database(directory: Path) -> Path`.
- Produces: `select_default_mode(live_path: Path) -> Literal["live", "demo"]`.
- Produces: `GatewayStatus(reachable: bool, checked_at: datetime, backends: dict[str, dict], reason: str | None)` and `fetch_gateway_status(base_url: str, api_key: str | None, timeout_s: float = 1.0) -> GatewayStatus`.

- [ ] **Step 1: Write failing fixture truthfulness tests**

```python
def test_demo_fixture_is_deterministic_and_never_touches_live_path(tmp_path):
    live = tmp_path / "live.db"
    demo = ensure_demo_database(tmp_path / "demo")
    first = load_snapshot(demo)
    demo.unlink()
    second = load_snapshot(ensure_demo_database(tmp_path / "demo"))
    pd.testing.assert_frame_equal(first.requests, second.requests)
    assert not live.exists()
    assert len(first.requests) >= 48
    assert {"connection_error", "HTTP 503", "HTTP 429"} <= set(
        first.requests["error_message"].dropna()
    )
```

Add status tests using `respx` for reachable, 401 backend-health, timeout, and offline responses. A public `/health` success with unauthorized `/health/backends` is represented as gateway reachable with backend details unavailable.

- [ ] **Step 2: Verify test failures**

Run: `uv run --frozen pytest tests/dashboard/test_demo_fixture.py tests/dashboard/test_live_status.py -q`

Expected: FAIL because fixture and status modules are missing.

- [ ] **Step 3: Implement the deterministic fixture**

Seed fixed rows across `2026-08-12T16:45:00+00:00` through `2026-08-12T17:45:00+00:00`, aliases `fast` and `smart`, and backends `llamacpp`, `ollama`, and `ollama-smart`. Include successful/failed, streaming/non-streaming, nullable TTFT/token values, HTTP 429, HTTP 503, connection, timeout, and failover-without-next-backend cases.

Create the fixture only inside `directory`; write a temporary sibling and atomically rename it to `demo-gateway-v1.db`. Add `.dashboard-cache/` to `.gitignore`; the app uses that directory by default while tests use `tmp_path`.

- [ ] **Step 4: Implement safe live status reads**

Use `httpx.Client(timeout=timeout_s)` against `/health`, then `/health/backends` only when an API key is configured. Sanitize exception details to `offline`, `timeout`, or `backend_health_unauthorized`; do not display raw URLs containing credentials.

- [ ] **Step 5: Run tests and commit**

Run: `uv run --frozen pytest tests/dashboard/test_demo_fixture.py tests/dashboard/test_live_status.py -q`

Commit:

```bash
git add .gitignore dashboard/data tests/dashboard
git commit -m "feat: add truthful demo and live status modes"
```

### Task 4: Load and validate committed benchmark evidence

**Files:**
- Create: `dashboard/data/benchmark_repository.py`
- Create: `tests/dashboard/test_benchmark_repository.py`

**Interfaces:**
- Produces: `BenchmarkEvidence(concurrency, prefill, overhead, provenance, claims, warnings)`.
- Produces: `load_benchmark_evidence(results_dir: Path) -> BenchmarkEvidence`.
- Produces: warnings keyed by artifact path when a file is missing or its provenance digest does not match.

- [ ] **Step 1: Write failing evidence tests**

```python
def test_repository_loads_committed_aggregate_evidence():
    evidence = load_benchmark_evidence(Path("bench/results"))
    assert set(evidence.concurrency["engine"]) == {"llamacpp", "ollama", "lmstudio"}
    assert evidence.overhead["overhead_ms"] == pytest.approx(1.656700020248536)
    assert evidence.provenance["measurement"]["public_raw_request_runs"] is False
    assert evidence.warnings == {}


def test_digest_mismatch_isolated_to_affected_artifact(tmp_path):
    copy_evidence_tree(tmp_path)
    (tmp_path / "concurrency_summary.csv").write_text("changed", encoding="utf-8")
    evidence = load_benchmark_evidence(tmp_path)
    assert "concurrency_summary.csv" in evidence.warnings
    assert evidence.overhead
```

- [ ] **Step 2: Verify failures**

Run: `uv run --frozen pytest tests/dashboard/test_benchmark_repository.py -q`

Expected: FAIL because the repository is missing.

- [ ] **Step 3: Implement parsing and digest verification**

Reuse the repository's documented digest policy: SHA-256 over PNG bytes and SHA-256 after CRLF-to-LF normalization for CSV/JSON. Do not reimplement claim semantics already covered by `release_checks`; the dashboard loader reports verification state and parses available aggregate content.

- [ ] **Step 4: Run evidence tests and existing release evidence tests**

Run: `uv run --frozen pytest tests/dashboard/test_benchmark_repository.py tests/test_evidence.py tests/test_publication.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add dashboard/data/benchmark_repository.py tests/dashboard/test_benchmark_repository.py
git commit -m "feat: expose verified benchmark evidence to dashboard"
```

### Task 5: Create the visual system, application shell, and reusable components

**Files:**
- Create: `dashboard/theme.py`
- Create: `dashboard/components.py`
- Create: `dashboard/views/__init__.py`
- Create: `tests/dashboard/test_theme.py`
- Replace: `dashboard/app.py`
- Modify: `.streamlit/config.toml` if present; otherwise create it.

**Interfaces:**
- Consumes: mode selection, telemetry snapshot, gateway status, and evidence repository.
- Produces: `apply_theme()`, `render_source_badge(...)`, `render_metric_card(...)`, `render_state_message(...)`, and four-page dispatch.

- [ ] **Step 1: Write failing theme contract tests**

```python
def test_theme_contains_accessible_type_and_semantic_tokens():
    css = build_theme_css()
    assert "--canvas: #F1EFE8" in css
    assert "--healthy: #718B7A" in css
    assert "font-size: 16px" in css
    assert "prefers-reduced-motion" in css
```

Add an import smoke test that stubs Streamlit and verifies `dashboard.app` does not open or mutate a database at import time. App execution lives in `main()` guarded by `if __name__ == "__main__": main()`.

- [ ] **Step 2: Verify failures**

Run: `uv run --frozen pytest tests/dashboard/test_theme.py -q`

Expected: FAIL because theme and app shell contracts are missing.

- [ ] **Step 3: Implement theme and components**

Centralize the approved colors as CSS variables. Use `clamp()` for headings, 16 px body copy, visible focus rings, WCAG-conscious contrast, `font-variant-numeric: tabular-nums`, reduced-motion support, 12–16 px card gaps, and 20–28 px section gaps. Minimize Streamlit's deploy/header chrome without hiding functional keyboard focus.

Format missing numeric values with:

```python
def format_metric(value: float | int | None, suffix: str = "") -> str:
    return "—" if value is None or pd.isna(value) else f"{value:,.1f}{suffix}"
```

- [ ] **Step 4: Implement app shell and source selector**

Use a single top navigation control for `Overview`, `Routing & Reliability`, `Requests`, and `Benchmark Evidence`. Show mode/source, observation window, timezone, and last refresh in a compact utility row. Store filters in `st.session_state` so reruns preserve them.

- [ ] **Step 5: Configure Streamlit and run tests**

Set theme base/light colors and `browser.gatherUsageStats = false`. Run:

`uv run --frozen pytest tests/dashboard/test_theme.py -q`

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add .streamlit dashboard tests/dashboard/test_theme.py
git commit -m "feat: establish operations console visual system"
```

### Task 6: Implement Overview and Routing & Reliability views

**Files:**
- Create: `dashboard/views/overview.py`
- Create: `dashboard/views/reliability.py`
- Create: `tests/dashboard/test_view_models.py`
- Modify: `dashboard/app.py`

**Interfaces:**
- Consumes: `TelemetrySnapshot`, `OverviewMetrics`, `GatewayStatus`, registry data from `gateway.registry.load_registry`, and selected observation window.
- Produces: render-only `render_overview(...)` and `render_reliability(...)` functions plus pure view-model builders for testability.

- [ ] **Step 1: Write failing view-model tests**

```python
def test_overview_model_discloses_demo_source_and_time_range(demo_snapshot):
    model = build_overview_model(demo_snapshot, source_kind="demo")
    assert model.source_label == "DEMO DATA"
    assert model.observed_from is not None
    assert model.observed_to is not None


def test_health_is_current_observation_not_uptime():
    model = build_reliability_model(snapshot(), gateway_status(), registry())
    assert model.health_heading == "Backend Health · 目前觀測"
    assert not hasattr(model, "uptime_pct")
```

- [ ] **Step 2: Verify failures**

Run: `uv run --frozen pytest tests/dashboard/test_view_models.py -q`

Expected: FAIL because view models are missing.

- [ ] **Step 3: Implement Overview**

Render five KPI cards, a time-bucket request/P95 chart, current backend status, alias chains, and recent failovers. Use chart units and legends. Keep source badge and observation window visible without scrolling at a 1440×900 viewport.

- [ ] **Step 4: Implement Routing & Reliability**

Render ordered backend chains, configured `max_concurrent`, current health, failover reasons, sanitized error categories, and observed HTTP 429 backpressure. Include the explicit note that health polling is observational and request-time failover always walks the ordered chain.

- [ ] **Step 5: Run tests and commit**

Run: `uv run --frozen pytest tests/dashboard/test_view_models.py tests/dashboard/test_metrics.py -q`

Commit:

```bash
git add dashboard/app.py dashboard/views tests/dashboard/test_view_models.py
git commit -m "feat: add gateway overview and reliability views"
```

### Task 7: Implement Requests and Benchmark Evidence views

**Files:**
- Create: `dashboard/views/requests.py`
- Create: `dashboard/views/evidence.py`
- Create: `tests/dashboard/test_requests_view.py`
- Create: `tests/dashboard/test_evidence_view.py`
- Modify: `dashboard/app.py`

**Interfaces:**
- Consumes: filtered request DataFrame and `BenchmarkEvidence`.
- Produces: `build_request_table`, `build_benchmark_charts`, `render_requests`, and `render_evidence`.

- [ ] **Step 1: Write failing request table tests**

```python
def test_request_table_preserves_missing_values_and_newest_first(requests):
    table = build_request_table(requests)
    assert table.iloc[0]["timestamp"] >= table.iloc[1]["timestamp"]
    assert table.loc[table["ttft_ms"].isna(), "ttft_display"].eq("—").all()
```

Test combined filters for alias, backend, success, status, stream, error category, and time window.

- [ ] **Step 2: Write failing evidence presentation tests**

```python
def test_benchmark_model_includes_scope_and_environment(evidence):
    model = build_evidence_view_model(evidence)
    assert model.measurement_date == "2026-07-17"
    assert model.gpu == "NVIDIA GeForce RTX 4090"
    assert "hardware- and version-specific" in model.scope_note
    assert model.public_raw_runs is False
```

- [ ] **Step 3: Verify failures**

Run: `uv run --frozen pytest tests/dashboard/test_requests_view.py tests/dashboard/test_evidence_view.py -q`

Expected: FAIL because both views are missing.

- [ ] **Step 4: Implement Requests**

Render filters above a height-limited table and a summary strip for filtered results. Show exact values in the table, explain missing TTFT/tokens, and keep an empty filtered result inside the page shell rather than calling `st.stop()`.

- [ ] **Step 5: Implement Benchmark Evidence**

Render throughput and P50/P95 TTFT by concurrency, prefill comparison, gateway overhead, VRAM summary, and Unified KV Cache controlled comparison. Add method/provenance panels and per-artifact verification warnings. Do not name a universal winner; label all metrics with units.

- [ ] **Step 6: Run tests and commit**

Run: `uv run --frozen pytest tests/dashboard/test_requests_view.py tests/dashboard/test_evidence_view.py -q`

Commit:

```bash
git add dashboard/app.py dashboard/views tests/dashboard
git commit -m "feat: add request explorer and benchmark evidence views"
```

### Task 8: Harden degraded states, documentation, and full verification

**Files:**
- Create: `tests/dashboard/test_dashboard_smoke.py`
- Modify: `dashboard/app.py`
- Modify: `README.md`
- Modify: `SETUP.md`

**Interfaces:**
- Consumes: all prior components.
- Produces: documented commands and verified graceful states for missing, empty, locked, incompatible, offline, and unverified inputs.

- [ ] **Step 1: Add failing degraded-state tests**

Cover:

```python
@pytest.mark.parametrize("condition", [
    "missing_live_db", "empty_live_db", "incompatible_schema",
    "sqlite_locked", "gateway_offline", "evidence_digest_mismatch",
])
def test_dashboard_state_is_nonfatal(condition, scenario_factory):
    state = build_app_state(**scenario_factory(condition))
    assert state.fatal_error is None
    assert state.notice is not None
```

Add a subprocess smoke test that launches Streamlit headlessly on an unused loopback port with a temporary `GATEWAY_DB_PATH`, polls `/_stcore/health`, and terminates the process in `finally`.

- [ ] **Step 2: Verify failures**

Run: `uv run --frozen pytest tests/dashboard/test_dashboard_smoke.py -q`

Expected: FAIL until `build_app_state` and all nonfatal fallbacks are wired.

- [ ] **Step 3: Implement degraded-state orchestration**

Build the complete app state before page rendering. Use cached last-good data only within the Streamlit session, mark it stale, and preserve navigation/filter controls. Replace all data-dependent `st.stop()` calls with scoped state components.

- [ ] **Step 4: Update user documentation**

Document:

- `uv sync --frozen --extra dashboard`
- `uv run streamlit run dashboard/app.py --server.address 127.0.0.1`
- Demo/Live selection behavior
- `GATEWAY_DB_PATH`, gateway base URL, and optional API-key behavior
- The committed Benchmark Evidence source and aggregate-only boundary
- A screenshot only if generated deterministically and publication policy permits it

- [ ] **Step 5: Run targeted dashboard verification**

```bash
uv run --frozen pytest tests/dashboard -q
uv run --frozen ruff check dashboard tests/dashboard
uv run --frozen ruff format --check dashboard tests/dashboard
```

Expected: all commands exit 0.

- [ ] **Step 6: Run the complete repository verification**

```bash
uv run --frozen pytest -q
uv run --frozen ruff check .
uv run --frozen ruff format --check .
uv run --frozen python -m release_checks.cli
```

Expected: all commands exit 0; release checks continue to confirm the publication/evidence boundary.

- [ ] **Step 7: Perform visual verification**

Start the app in Demo Mode and inspect at approximately 1440×900 and a narrow/mobile viewport. Confirm:

- The source badge and observation window are above the fold.
- Body copy remains comfortably readable.
- No horizontal overflow appears.
- Overview space is dense but not cramped.
- Healthy, warning, and failed states have text labels in addition to color.
- Streamlit framework chrome does not dominate the product UI.
- All four views remain usable with the sidebar collapsed.

- [ ] **Step 8: Commit the completed console**

```bash
git add dashboard tests/dashboard README.md SETUP.md .streamlit .gitignore
git commit -m "feat: complete inference operations console"
```

## Final acceptance checklist

- [ ] First launch without a live database opens a complete, labeled Demo Mode.
- [ ] Live Mode uses read-only SQLite and never creates a missing database.
- [ ] Empty live telemetry does not stop the app.
- [ ] Overview answers health, volume, latency, routing, and failover questions.
- [ ] Routing page explains health polling, failover, and observed backpressure honestly.
- [ ] Requests filters and missing values behave correctly.
- [ ] Benchmark Evidence exposes measurement scope and provenance.
- [ ] No unmeasured operational metric is invented.
- [ ] zh-TW copy, font sizing, density, palette, responsive layout, and accessibility match the approved design.
- [ ] Dashboard and full repository verification suites pass.
