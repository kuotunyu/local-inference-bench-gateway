# Public-Safe Hugging Face Space Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a CPU-only Docker Streamlit Space that exposes only deterministic in-memory Demo data and digest-verified committed benchmark evidence for `steven0226/local-inference-bench-gateway`.

**Architecture:** A dedicated `space/app.py` consumes pure dashboard presentation contracts, an in-memory fixture, and the existing evidence loader. A manifest-driven exporter copies only an exact public allowlist into a separate Space bundle; local verifiers reject runtime/live imports, network capabilities, secrets, private artifacts, evidence drift, unsafe Docker settings, and undeclared files. Remote collision checks remain read-only tooling and are never invoked by local CI.

**Tech Stack:** Python 3.12.13, Streamlit 1.61.1, pandas 3.0.5, Altair 6.2.2, pytest 9.1.1, Streamlit AppTest, httpx/respx, Ruff, Docker SDK Space on port 7860.

## Global Constraints

- Canonical Space ID is exactly `steven0226/local-inference-bench-gateway`.
- The complete zh-TW truth contract from the approved spec renders verbatim, except for line wrapping, before the first interactive control.
- Public application code never imports `gateway.*`, `dashboard.state`, `dashboard.data.live_status`, `dashboard.data.sqlite_repository`, `sqlite3`, `httpx`, `requests`, `urllib.request`, `socket`, or `subprocess`.
- Public application code never reads environment variables, credentials, arbitrary paths, backend URLs, local databases, or remote APIs.
- Demo data consists of exactly 60 request rows and three failover rows beginning at `2026-08-12T16:45:00Z`; its canonical digest is `44d6bb22d7bdfc59035ff8b4693ab7af73cba0568abdc7e31981ab264e4d2d16`.
- The local Operations Console retains its SQLite-backed Demo and Live behavior.
- The public evidence bundle contains all 12 declared artifacts plus `provenance.json` and `claims.json`; runtime rendering remains fail-closed.
- Docker metadata is `sdk: docker`, `app_port: 7860`; base image is `python:3.12.13-slim-bookworm`; runtime user is `10001:10001`.
- Direct Space dependencies are exactly `streamlit==1.61.1`, `pandas==3.0.5`, and `altair==6.2.2`, each matching `uv.lock`.
- Runtime works with outbound networking disabled; only the container-local Streamlit health probe is permitted.
- Browser request graphs are captured without blocking or interception; only loopback and
  same-origin runtime requests are permitted, and `data.streamlit.io`, Fivetran, or any other
  external origin is RED.
- Visual acceptance uses exact `1440x900` desktop and `390x844` mobile viewports.
- No task creates, uploads, modifies, deletes, or restarts a Hugging Face Space; pushes, PRs, merges, About edits, and visibility changes are forbidden.
- Every product or document correction follows observed RED, minimal GREEN, focused regression checks, and a new task-specific commit; Task 11 may commit adversarial tests after a first-run GREEN because it characterizes a contract implemented by Tasks 1–10, and Task 14 is verification-only.
- Stage reviewed file paths individually; never use `git add .`, `git add -A`, or a directory path.
- Any task that invokes `scripts/export_hf_space.py` first commits its focused GREEN changes, proves `git status --porcelain` is empty, and exports from that clean HEAD. Acceptance defects receive a new RED/GREEN corrective commit; never amend an already verified task commit or bypass the dirty-worktree guard.

---

## File Structure

### New runtime and presentation files

- `dashboard/data/public_demo.py` — pure deterministic snapshot, fixture presentation data, and canonical digest.
- `dashboard/windows.py` — pure observation-window slicing shared by local and public apps.
- `dashboard/data/operations_adapter.py` — local-only conversion from `GatewayStatus`/`Registry` to neutral presentation contracts; excluded from the Space bundle.
- `dashboard/data/public_evidence.py` — public integrity summary around `BenchmarkEvidence`.
- `space/app.py` — public Streamlit entrypoint with no Live, SQLite, health, environment, or network path.
- `space/README.md` — Space card and Docker SDK metadata.
- `space/Dockerfile` — non-root CPU-only Streamlit image.
- `space/requirements.txt` — three exact direct dependency pins.
- `space/.streamlit/config.toml` — theme and disabled Streamlit usage telemetry.
- `space/bundle-manifest.json` — exact source-to-destination public allowlist.

### New release tooling

- `release_checks/space_imports.py` — AST import-closure and capability denylist verifier.
- `release_checks/space_bundle.py` — manifest loader, deterministic exporter, and public artifact verifier.
- `release_checks/space_remote_gate.py` — authenticated GET-only owner/collision/eligibility preflight.
- `scripts/export_hf_space.py` — local CLI for exporting an empty destination from the current Git commit.
- `docs/HF_SPACE_RELEASE.md` — local validation, visual review, remote stop gates, and About ordering.

### Existing files modified

- `dashboard/models.py` — neutral immutable operations display contracts.
- `dashboard/data/demo_fixture.py` — write the local SQLite fixture from the pure snapshot.
- `dashboard/state.py` — import pure `slice_observation_window` while retaining its public symbol.
- `dashboard/views/overview.py` — consume `OperationsDisplay`, not runtime types.
- `dashboard/views/reliability.py` — consume `OperationsDisplay`, not runtime types.
- `dashboard/views/requests.py` — accept an explicit source note for the public in-memory fixture.
- `dashboard/app.py` — adapt local runtime state before rendering.
- `release_checks/cli.py` — run local Space source/bundle checks without contacting Hugging Face.
- `.github/workflows/ci.yml` — export, build, and smoke the Space image with runtime networking disabled.

### New test files

- `tests/dashboard/test_public_demo.py`
- `tests/dashboard/test_operations_adapter.py`
- `tests/dashboard/test_public_evidence.py`
- `tests/space/__init__.py`
- `tests/space/test_public_app.py`
- `tests/space/test_public_app_isolation.py`
- `tests/space/test_space_assets.py`
- `tests/space/test_exporter.py`
- `tests/space/test_import_boundary.py`
- `tests/space/test_bundle_verifier.py`
- `tests/space/test_remote_gate.py`
- `tests/space/test_ci_policy.py`
- `tests/space/test_release_runbook.py`

---

### Task 1: Extract the deterministic in-memory fixture and pure window slicing

**Files:**
- Create: `dashboard/data/public_demo.py`
- Create: `dashboard/windows.py`
- Create: `tests/dashboard/test_public_demo.py`
- Modify: `dashboard/data/demo_fixture.py`
- Modify: `dashboard/state.py`
- Modify: `tests/dashboard/test_app_state.py`
- Test: `tests/dashboard/test_demo_fixture.py`

**Interfaces:**
- Produces: `build_demo_snapshot() -> TelemetrySnapshot`
- Produces: `demo_snapshot_digest(snapshot: TelemetrySnapshot) -> str`
- Produces: `slice_observation_window(snapshot: TelemetrySnapshot, minutes: int | None, source_kind: Literal["demo", "live"]) -> TelemetrySnapshot`
- Preserves: `ensure_demo_database(directory: Path) -> Path`
- Preserves: `dashboard.state.slice_observation_window` as an imported compatibility symbol.

- [ ] **Step 1: Write the failing pure-fixture tests**

```python
from pathlib import Path

import pandas as pd

from dashboard.data.public_demo import build_demo_snapshot, demo_snapshot_digest

EXPECTED_DIGEST = "44d6bb22d7bdfc59035ff8b4693ab7af73cba0568abdc7e31981ab264e4d2d16"


def test_public_demo_snapshot_is_exact_stable_and_in_memory(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    first = build_demo_snapshot()
    second = build_demo_snapshot()

    pd.testing.assert_frame_equal(first.requests, second.requests)
    pd.testing.assert_frame_equal(first.failovers, second.failovers)
    assert len(first.requests) == 60
    assert len(first.failovers) == 3
    assert set(first.requests["alias"]) == {"fast", "smart"}
    assert set(first.requests["backend_name"].dropna()) == {
        "llamacpp",
        "ollama",
        "ollama-smart",
    }
    assert first.requests.sort_values("id").iloc[0]["timestamp"] == "2026-08-12T16:45:00+00:00"
    assert demo_snapshot_digest(first) == EXPECTED_DIGEST
    assert list(tmp_path.rglob("*.db")) == []
    assert list(tmp_path.rglob("*.sqlite*")) == []
```

Define `test_public_demo_matches_the_existing_local_fixture_contract` in the same file. It creates
the local database with `ensure_demo_database(tmp_path)`, loads it with `load_snapshot()`, and uses
`pd.testing.assert_frame_equal` on requests and failovers after sorting by `id` and resetting the
index. It separately asserts the in-memory `source_path == Path("deterministic-demo")`; no
DataFrame column is excluded, and the local database path is not compared with this fixed marker.

- [ ] **Step 2: Run the tests and observe RED**

Run:

```powershell
uv run --frozen pytest tests/dashboard/test_public_demo.py -v
```

Expected: collection fails with `ModuleNotFoundError: No module named 'dashboard.data.public_demo'`.

- [ ] **Step 3: Implement the pure snapshot and digest**

Use the existing 60-row loop and failover constants from `demo_fixture.py`. Build DataFrames with
the exact `REQUEST_COLUMNS` and `FAILOVER_COLUMNS` order, including deterministic IDs `1..60` and
`1..3`. Implement canonicalization without machine paths:

```python
def _canonical_records(frame: pd.DataFrame) -> list[dict[str, object]]:
    normalized = frame.sort_values("id").astype(object)
    normalized = normalized.where(pd.notna(normalized), None)
    return normalized.to_dict(orient="records")


def demo_snapshot_digest(snapshot: TelemetrySnapshot) -> str:
    payload = {
        "schema_version": snapshot.schema_version,
        "requests": _canonical_records(snapshot.requests),
        "failovers": _canonical_records(snapshot.failovers),
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
```

Set `source_path=Path("deterministic-demo")`. Change `ensure_demo_database()` to insert rows from
`build_demo_snapshot()` after dropping the DataFrame `id` columns. Move the existing pure window
function to `dashboard/windows.py`, then import it in `dashboard/state.py`.

- [ ] **Step 4: Run focused GREEN and local compatibility tests**

```powershell
uv run --frozen pytest tests/dashboard/test_public_demo.py tests/dashboard/test_demo_fixture.py tests/dashboard/test_app_state.py -v
```

Expected: all selected tests pass; no database appears outside pytest temporary directories.

- [ ] **Step 5: Run formatting and commit**

```powershell
uv run --frozen ruff check dashboard/data/public_demo.py dashboard/windows.py dashboard/data/demo_fixture.py dashboard/state.py tests/dashboard/test_public_demo.py tests/dashboard/test_app_state.py
uv run --frozen ruff format --check dashboard/data/public_demo.py dashboard/windows.py dashboard/data/demo_fixture.py dashboard/state.py tests/dashboard/test_public_demo.py tests/dashboard/test_app_state.py
git add dashboard/data/public_demo.py dashboard/windows.py dashboard/data/demo_fixture.py dashboard/state.py tests/dashboard/test_public_demo.py tests/dashboard/test_app_state.py
git commit -m "feat: add deterministic in-memory demo snapshot"
```

---

### Task 2: Add neutral operations presentation contracts and adapters

**Files:**
- Modify: `dashboard/models.py`
- Modify: `dashboard/data/public_demo.py`
- Create: `dashboard/data/operations_adapter.py`
- Create: `tests/dashboard/test_operations_adapter.py`

**Interfaces:**
- Produces: `BackendDisplay(name: str, healthy: bool | None, last_checked: str | None)`
- Produces: `RouteDisplay(alias: str, backend_names: tuple[str, ...], models: tuple[str, ...], max_concurrent: int | None)`
- Produces: `OperationsDisplay(mode: Literal["local-demo", "live", "public-demo"], source_note: str, overview_lede: str, reliability_lede: str, backend_heading: str, backend_state: Literal["rows", "offline", "unavailable", "fixture"], backend_message: str | None, backends: tuple[BackendDisplay, ...], routes: tuple[RouteDisplay, ...])`
- Produces: `operations_display_from_runtime(status: GatewayStatus, registry: Registry, *, source_kind: Literal["demo", "live"]) -> OperationsDisplay`
- Produces: `build_demo_operations() -> OperationsDisplay`

- [ ] **Step 1: Write failing contract and adapter tests**

```python
def test_public_demo_operations_have_no_urls_or_current_health_copy() -> None:
    display = build_demo_operations()

    assert display.mode == "public-demo"
    assert display.backend_heading == "Fixture backend state"
    assert display.backend_state == "fixture"
    assert [route.alias for route in display.routes] == ["fast", "smart"]
    assert display.routes[0].backend_names == ("llamacpp", "ollama")
    assert display.routes[0].models == ("bench-model", "bench-model-c")
    assert display.routes[0].max_concurrent == 4
    assert display.routes[1].backend_names == ("ollama-smart",)
    assert all("http" not in backend.name for backend in display.backends)
    assert "目前觀測" not in display.backend_heading
```

Define these exact cases with the existing test registry factory and `GatewayStatus`:

| Test | Input | Required result |
|---|---|---|
| `test_runtime_adapter_maps_reachable_backend_rows` | reachable status + Demo source | `backend_state == "rows"`; host labels and health flags match the current view |
| `test_runtime_adapter_maps_offline_status` | `reachable=False`, no detail | `backend_state == "offline"`; current offline copy remains unchanged |
| `test_runtime_adapter_maps_unavailable_detail_without_exposing_a_url` | unauthorized detail | `backend_state == "unavailable"`; detail is preserved; no backend label contains `http` |
| `test_runtime_adapter_marks_live_source` | reachable status + Live source | `mode == "live"`; source note equals the current Live note |
| `test_runtime_adapter_marks_local_demo_source` | reachable status + Demo source | `mode == "local-demo"`; source note equals the current local Demo note |

- [ ] **Step 2: Run the tests and observe RED**

```powershell
uv run --frozen pytest tests/dashboard/test_operations_adapter.py -v
```

Expected: import fails because `OperationsDisplay` and `operations_adapter.py` do not exist.

- [ ] **Step 3: Implement frozen contracts and both adapters**

Add the dataclasses to `dashboard/models.py` with tuple fields. In the local-only adapter, convert
URLs to display host labels exactly as the current views do, but keep all runtime imports inside
`dashboard/data/operations_adapter.py`. In `public_demo.py`, return fixed rows:

```python
def build_demo_operations() -> OperationsDisplay:
    return OperationsDisplay(
        mode="public-demo",
        source_note="Deterministic in-memory fixture · 非正式流量 · 無 endpoint probe",
        overview_lede="檢視固定 Demo scenario 的 Request、latency、routing、Failover 與 fixture backend state。",
        reliability_lede="檢視固定 Demo scenario 的 Alias Routing、Failover、Backpressure 與錯誤分類。",
        backend_heading="Fixture backend state",
        backend_state="fixture",
        backend_message="固定情境狀態；不是目前 reachability probe。",
        backends=(
            BackendDisplay("llamacpp", True, "2026-08-12T17:45:00+00:00"),
            BackendDisplay("ollama", True, "2026-08-12T17:45:00+00:00"),
            BackendDisplay("ollama-smart", True, "2026-08-12T17:45:00+00:00"),
        ),
        routes=(
            RouteDisplay("fast", ("llamacpp", "ollama"), ("bench-model", "bench-model-c"), 4),
            RouteDisplay("smart", ("ollama-smart",), ("qwen3:8b",), None),
        ),
    )
```

- [ ] **Step 4: Run focused GREEN**

```powershell
uv run --frozen pytest tests/dashboard/test_operations_adapter.py tests/dashboard/test_public_demo.py -v
```

Expected: all selected tests pass.

- [ ] **Step 5: Commit**

```powershell
uv run --frozen ruff check dashboard/models.py dashboard/data/public_demo.py dashboard/data/operations_adapter.py tests/dashboard/test_operations_adapter.py
uv run --frozen ruff format --check dashboard/models.py dashboard/data/public_demo.py dashboard/data/operations_adapter.py tests/dashboard/test_operations_adapter.py
git add dashboard/models.py dashboard/data/public_demo.py dashboard/data/operations_adapter.py tests/dashboard/test_operations_adapter.py
git commit -m "refactor: add neutral operations display contracts"
```

---

### Task 3: Decouple shared views from live Gateway and Registry types

**Files:**
- Modify: `dashboard/views/overview.py`
- Modify: `dashboard/views/reliability.py`
- Modify: `dashboard/views/requests.py`
- Modify: `dashboard/app.py`
- Modify: `tests/dashboard/test_dashboard_smoke.py`
- Modify: `tests/dashboard/test_view_models.py`
- Modify: `tests/dashboard/test_zh_tw_state_copy.py`

**Interfaces:**
- Consumes: `OperationsDisplay` and `operations_display_from_runtime()` from Task 2.
- Changes: `render_overview(snapshot: TelemetrySnapshot, source_kind: str, operations: OperationsDisplay, observation_window_minutes: int | None = None) -> None`
- Changes: `build_reliability_model(snapshot: TelemetrySnapshot, operations: OperationsDisplay) -> ReliabilityModel`
- Changes: `render_reliability(snapshot: TelemetrySnapshot, source_kind: str, operations: OperationsDisplay) -> None`
- Changes: `render_requests(snapshot: TelemetrySnapshot, source_kind: str, *, source_note: str | None = None) -> None`

- [ ] **Step 1: Write the failing import-boundary and rendering tests**

```python
@pytest.mark.parametrize(
    "module_path",
    [Path("dashboard/views/overview.py"), Path("dashboard/views/reliability.py")],
)
def test_shared_views_do_not_import_live_or_gateway_types(module_path: Path) -> None:
    source = module_path.read_text(encoding="utf-8")
    assert "dashboard.data.live_status" not in source
    assert "gateway.registry" not in source
```

Update every existing call site in `tests/dashboard/test_view_models.py` and
`tests/dashboard/test_dashboard_smoke.py` to pass an `OperationsDisplay`. Define
`test_overview_public_demo_uses_fixture_heading` and
`test_overview_local_runtime_preserves_observed_heading`; the first asserts rendered text contains
`Fixture backend state` and excludes `目前觀測`, while the second asserts rendered text contains
`Backend Health · 目前觀測`.

- [ ] **Step 2: Run the tests and observe RED**

```powershell
uv run --frozen pytest tests/dashboard/test_view_models.py tests/dashboard/test_dashboard_smoke.py -v
```

Expected: signature errors and import-boundary assertion failures.

- [ ] **Step 3: Refactor views and local app**

Delete runtime imports from both view modules. Render `operations.routes` and
`operations.backends`; branch only on `operations.backend_state`. Use
`operations.overview_lede`, `operations.reliability_lede`,
`operations.backend_heading`, and `operations.source_note` for copy. In `dashboard/app.py`, create
one `OperationsDisplay` after loading local status and registry:

```python
operations = operations_display_from_runtime(status, registry, source_kind=telemetry.source_kind)
```

Pass it to Overview and Reliability. Pass the existing local SQLite source note explicitly to
Requests. Preserve all existing local empty/degraded behavior.

- [ ] **Step 4: Run dashboard GREEN and full dashboard regression**

```powershell
uv run --frozen pytest tests/dashboard -q -p no:cacheprovider
```

Expected: all dashboard tests pass with no Streamlit exception.

- [ ] **Step 5: Commit**

```powershell
uv run --frozen ruff check dashboard tests/dashboard
uv run --frozen ruff format --check dashboard tests/dashboard
git add dashboard/views/overview.py dashboard/views/reliability.py dashboard/views/requests.py dashboard/app.py tests/dashboard/test_dashboard_smoke.py tests/dashboard/test_view_models.py tests/dashboard/test_zh_tw_state_copy.py
git commit -m "refactor: decouple dashboard views from gateway runtime"
```

---

### Task 4: Add a public evidence integrity state with fail-closed semantics

**Files:**
- Create: `dashboard/data/public_evidence.py`
- Create: `tests/dashboard/test_public_evidence.py`
- Test: `tests/dashboard/test_benchmark_repository.py`
- Test: `tests/dashboard/test_evidence_view.py`

**Interfaces:**
- Consumes: `load_benchmark_evidence(results_dir: Path) -> BenchmarkEvidence`.
- Produces: `PublicEvidenceState(evidence: BenchmarkEvidence, declared_artifacts: int, verified_artifacts: int, complete: bool)`.
- Produces: `load_public_evidence(results_dir: Path) -> PublicEvidenceState`.

- [ ] **Step 1: Write failing integrity-summary tests**

```python
def test_complete_public_evidence_reports_twelve_verified_artifacts() -> None:
    state = load_public_evidence(Path("bench/results"))
    assert state.declared_artifacts == 12
    assert state.verified_artifacts == 12
    assert state.complete is True
    assert state.evidence.warnings == {}


def test_tampered_artifact_is_quarantined_without_hard_coded_metric(tmp_path: Path) -> None:
    copy_results(Path("bench/results"), tmp_path)
    (tmp_path / "concurrency_summary.csv").write_text("changed", encoding="utf-8")
    state = load_public_evidence(tmp_path)
    assert state.complete is False
    assert state.verified_artifacts == 11
    assert state.evidence.concurrency.empty
    assert state.evidence.overhead["overhead_ms"] > 0
    assert state.evidence.warnings["concurrency_summary.csv"] == "digest_mismatch"
```

Define `test_invalid_provenance_quarantines_every_artifact` and
`test_missing_provenance_quarantines_every_artifact`. In each case assert
`verified_artifacts == 0`, `complete is False`, every canonical evidence DataFrame is empty, and
every canonical evidence mapping is empty. For each object in `claims.json["claims"]`, assert its
`display` string occurs zero times in rendered Markdown.

- [ ] **Step 2: Run and observe RED**

```powershell
uv run --frozen pytest tests/dashboard/test_public_evidence.py -v
```

Expected: import fails because `dashboard.data.public_evidence` does not exist.

- [ ] **Step 3: Implement the integrity wrapper**

Use only `BenchmarkEvidence.provenance` and `warnings`; do not read a second source. When the
provenance manifest is invalid, return zero counts. Count an artifact as verified only when its
normalized `bench/results/...` path has no warning. Set `complete` only when the declared and
verified counts both equal 12 and the warnings mapping is empty.

```python
@dataclass(frozen=True)
class PublicEvidenceState:
    evidence: BenchmarkEvidence
    declared_artifacts: int
    verified_artifacts: int
    complete: bool
```

- [ ] **Step 4: Run evidence GREEN**

```powershell
uv run --frozen pytest tests/dashboard/test_public_evidence.py tests/dashboard/test_benchmark_repository.py tests/dashboard/test_evidence_view.py -v
```

Expected: all selected tests pass; tampered evidence keeps unaffected verified panels only.

- [ ] **Step 5: Commit**

```powershell
uv run --frozen ruff check dashboard/data/public_evidence.py tests/dashboard/test_public_evidence.py
uv run --frozen ruff format --check dashboard/data/public_evidence.py tests/dashboard/test_public_evidence.py
git add dashboard/data/public_evidence.py tests/dashboard/test_public_evidence.py
git commit -m "feat: add fail-closed public evidence state"
```

---

### Task 5: Build the public-only Streamlit entrypoint

**Files:**
- Create: `space/app.py`
- Create: `tests/space/__init__.py`
- Create: `tests/space/test_public_app.py`
- Modify: `dashboard/components.py`
- Modify: `dashboard/theme.py`

**Interfaces:**
- Consumes: `build_demo_snapshot()`, `build_demo_operations()`, `slice_observation_window()`, and `load_public_evidence()`.
- Produces: `TRUTH_CONTRACT_HTML: str`.
- Produces: `render_truth_contract() -> None`.
- Produces: `main() -> None`.
- Public pages: `("Demo 概覽", "Demo Routing 與可靠性", "Demo Request 紀錄", "Committed Benchmark Evidence")`.

- [ ] **Step 1: Write failing AppTest contracts**

```python
APP_PATH = Path(__file__).resolve().parents[2] / "space/app.py"


def test_truth_contract_is_first_and_no_live_control_exists() -> None:
    app = AppTest.from_file(str(APP_PATH)).run(timeout=20)
    assert not app.exception
    assert "公開證據示範（Demo Mode）" in app.markdown[0].value
    assert "不是 live inference service，亦無 SLA" in app.markdown[0].value
    assert [item.label for item in app.selectbox] == ["觀測時間範圍"]
    assert not app.button
    assert all("Live 模式" not in item.value for item in app.markdown)
    assert all("GATEWAY_" not in item.value for item in app.markdown)


@pytest.mark.parametrize(
    "page",
    ["Demo 概覽", "Demo Routing 與可靠性", "Demo Request 紀錄", "Committed Benchmark Evidence"],
)
def test_each_public_page_renders(page: str) -> None:
    app = AppTest.from_file(str(APP_PATH)).run(timeout=20)
    app.radio[0].set_value(page).run(timeout=20)
    assert not app.exception
```

In that test, normalize HTML whitespace and compare `app.markdown[0].value` with this complete
contract, not selected fragments:

```text
公開證據示範（Demo Mode）
此 Space 僅呈現 deterministic illustrative fixture 與 2026-07-17 committed aggregate evidence。它不會、也無法連線到訪客的本機 Gateway、SQLite、inference backend 或 GPU；不是 live inference service，亦無 SLA。Space 可能休眠或 cold-start；其啟動狀態不代表 Gateway uptime。
Deterministic Demo data is illustrative and is not production or sampled traffic.
Benchmark evidence is a dated, hardware- and version-specific snapshot.
Request-level raw benchmark runs are not public.
This Space cannot connect to a visitor's local system.
This Space provides neither live inference nor an SLA.
Hosting sleep or cold start is not system uptime evidence.
```

Iterate `app.main` and assert the truth-contract Markdown element precedes the radio and selectbox
elements. This establishes the first-viewport claim order independently of per-widget collections.

Define `test_public_app_truth_contract_and_control_surface` with these exact assertions: semantic
Markdown contains `公開證據示範（Demo Mode）`, `DETERMINISTIC DEMO · 非正式流量`,
`COMMITTED EVIDENCE · aggregate only · raw runs unpublished`, `Fixture backend state`, and the
no-local-backend/no-current-health/no-SLA disclosure; it contains neither
`http://127.0.0.1:9000` nor `localhost:9000`; `app.text_input`, `app.text_area`,
`app.file_uploader`, and `app.chat_input` are empty. On the evidence page, assert the verified
measurement scope identifies `2026-07-17`, `NVIDIA GeForce RTX 4090`, and the recorded model;
assert request-level raw runs are unpublished and no copy describes current GPU execution.

- [ ] **Step 2: Run and observe RED**

```powershell
uv run --frozen pytest tests/space/test_public_app.py -v
```

Expected: AppTest fails because `space/app.py` does not exist.

- [ ] **Step 3: Implement the minimal public app**

Set `PROJECT_ROOT = Path(__file__).resolve().parents[1]` and insert it at the front of `sys.path`.
Call `render_truth_contract()` immediately after page configuration and theme application, before
`st.radio` or `st.selectbox`. Use the pure snapshot and fixed presentation contracts. Evidence
loads only from `PROJECT_ROOT / "bench/results"`. Render these exact persistent badges:

```python
DEMO_BADGE = "DETERMINISTIC DEMO · 非正式流量"
EVIDENCE_BADGE = "COMMITTED EVIDENCE · aggregate only · raw runs unpublished"
```

Hide the observation-window selector on the evidence page. Do not import `os`, runtime adapters,
SQLite, health, Registry, HTTP, or gateway modules. The footer states
`公開證據示範 · 無本機連線 · 無 hosted inference · 無 SLA`.

- [ ] **Step 4: Run AppTest GREEN and dashboard regression**

```powershell
uv run --frozen pytest tests/space/test_public_app.py tests/dashboard -q -p no:cacheprovider
```

Expected: all tests pass and the local Console retains all four existing pages.

- [ ] **Step 5: Commit**

```powershell
uv run --frozen ruff check space/app.py dashboard/components.py dashboard/theme.py tests/space/test_public_app.py
uv run --frozen ruff format --check space/app.py dashboard/components.py dashboard/theme.py tests/space/test_public_app.py
git add space/app.py dashboard/components.py dashboard/theme.py tests/space/__init__.py tests/space/test_public_app.py
git commit -m "feat: add public-safe Streamlit Space app"
```

---

### Task 6: Add exact Space card, dependency, Streamlit, and Docker assets

**Files:**
- Create: `space/README.md`
- Create: `space/Dockerfile`
- Create: `space/requirements.txt`
- Create: `space/.streamlit/config.toml`
- Create: `tests/space/test_space_assets.py`

**Interfaces:**
- Produces Docker SDK metadata `sdk: docker`, `app_port: 7860`.
- Produces image command `streamlit run space/app.py --server.address=0.0.0.0 --server.port=7860 --server.headless=true`.
- Produces internal health endpoint `http://127.0.0.1:7860/_stcore/health`.

- [ ] **Step 1: Write failing source-asset tests**

```python
def test_space_assets_pin_public_runtime() -> None:
    card = Path("space/README.md").read_text(encoding="utf-8")
    dockerfile = Path("space/Dockerfile").read_text(encoding="utf-8")
    requirements = Path("space/requirements.txt").read_text(encoding="utf-8").splitlines()

    assert "sdk: docker" in card
    assert "app_port: 7860" in card
    assert requirements == [
        "streamlit==1.61.1",
        "pandas==3.0.5",
        "altair==6.2.2",
    ]
    assert "FROM python:3.12.13-slim-bookworm" in dockerfile
    assert "USER 10001:10001" in dockerfile
    assert "COPY . ." not in dockerfile
    assert "COPY .streamlit/config.toml /app/.streamlit/config.toml" in dockerfile
    assert "uvicorn" not in dockerfile.lower()
    assert "9000" not in dockerfile
```

Define `test_space_requirements_match_uv_lock_exactly`; parse `uv.lock` with `tomllib`, select
`streamlit`, `pandas`, and `altair`, and assert the resulting `name==version` set equals the three
lines in `space/requirements.txt`. Define `test_space_card_states_every_public_truth_boundary` and
assert the card contains the complete truth contract, aggregate/raw boundary, scoped license link,
third-party notices link, canonical GitHub repository, and sleep/cold-start statement; assert no
token matching `https://[^ ]+\.hf\.space` occurs.

- [ ] **Step 2: Run and observe RED**

```powershell
uv run --frozen pytest tests/space/test_space_assets.py -v
```

Expected: `FileNotFoundError` for `space/README.md`.

- [ ] **Step 3: Create minimal exact assets**

Use this Docker structure:

```dockerfile
FROM python:3.12.13-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 HOME=/tmp
WORKDIR /app
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt
COPY .streamlit/config.toml /app/.streamlit/config.toml
COPY space/app.py ./space/app.py
COPY dashboard ./dashboard
COPY bench/results ./bench/results
RUN groupadd --gid 10001 app && useradd --uid 10001 --gid 10001 --no-create-home app
EXPOSE 7860
USER 10001:10001
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=6 CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:7860/_stcore/health', timeout=2).read()"]
CMD ["streamlit", "run", "space/app.py", "--server.address=0.0.0.0", "--server.port=7860", "--server.headless=true"]
```

The source Dockerfile uses explicit public directories; the exporter in Task 7 guarantees that
those directories contain only manifest entries. Configure `gatherUsageStats = false` and the
approved Morandi theme in `space/.streamlit/config.toml`, then copy that one file exactly to
`/app/.streamlit/config.toml`. A broad `COPY` or `CMD`-only hiding of telemetry is not an acceptable
substitute for the exact config copy.

- [ ] **Step 4: Run asset GREEN**

```powershell
uv run --frozen pytest tests/space/test_space_assets.py -v
```

Expected: all source-asset and lock-version tests pass.

- [ ] **Step 5: Commit**

```powershell
git add space/README.md space/Dockerfile space/requirements.txt space/.streamlit/config.toml tests/space/test_space_assets.py
git commit -m "build: add pinned Docker Space assets"
```

---

### Task 7: Implement the exact allowlisted bundle exporter

**Files:**
- Create: `space/bundle-manifest.json`
- Create: `release_checks/space_bundle.py`
- Create: `scripts/export_hf_space.py`
- Create: `tests/space/test_exporter.py`

**Interfaces:**
- Produces: `BundleEntry(source: PurePosixPath, destination: PurePosixPath)`.
- Produces: `load_bundle_manifest(repo_root: Path) -> tuple[BundleEntry, ...]`.
- Produces: `export_space_bundle(repo_root: Path, destination: Path, source_commit: str) -> Path` returning `destination / "deployment-manifest.json"`.
- CLI: `python scripts/export_hf_space.py --destination $bundle`, where `$bundle` is the nonexistent
  child path created by the concrete PowerShell sequence in Task 13.

- [ ] **Step 1: Write failing exporter tests**

```python
def test_export_is_exact_deterministic_and_refuses_nonempty_destination(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    export_space_bundle(Path.cwd(), first, "a" * 40)
    export_space_bundle(Path.cwd(), second, "a" * 40)

    assert relative_file_bytes(first) == relative_file_bytes(second)
    assert set(relative_file_bytes(first)) == expected_bundle_paths()

    occupied = tmp_path / "occupied"
    occupied.mkdir()
    (occupied / "keep.txt").write_text("preserve", encoding="utf-8")
    with pytest.raises(BundleExportError, match="destination must be empty"):
        export_space_bundle(Path.cwd(), occupied, "b" * 40)
    assert (occupied / "keep.txt").read_text(encoding="utf-8") == "preserve"
```

Define these exact tests:

| Test | Mutation | Required result |
|---|---|---|
| `test_manifest_rejects_source_traversal` | source `../secret` | raises `BundleManifestError("source escapes repository")` |
| `test_manifest_rejects_destination_traversal` | destination `../secret` | raises `BundleManifestError("destination escapes bundle")` |
| `test_manifest_rejects_duplicate_destination` | two entries target `README.md` | raises `BundleManifestError("duplicate destination")` |
| `test_export_rejects_missing_source` | allowlisted source absent | raises `BundleExportError("missing source")` before copying |
| `test_export_rejects_malformed_source_commit` | commit is not 40 lowercase hex characters | raises `BundleExportError("invalid source commit")` |
| `test_export_manifest_digest_uses_source_bytes` | LF then CRLF manifest bytes | each deployment digest equals `hashlib.sha256(raw_bytes).hexdigest()` and the two digests differ |

- [ ] **Step 2: Run and observe RED**

```powershell
uv run --frozen pytest tests/space/test_exporter.py -v
```

Expected: import fails because `release_checks.space_bundle` does not exist.

- [ ] **Step 3: Define the exact manifest and exporter**

The JSON manifest lists each file separately. Include only:

```text
README.md                         <- space/README.md
Dockerfile                       <- space/Dockerfile
requirements.txt                 <- space/requirements.txt
.streamlit/config.toml           <- space/.streamlit/config.toml
space/app.py                     <- space/app.py
bundle-manifest.json             <- space/bundle-manifest.json
dashboard/__init__.py
dashboard/models.py
dashboard/windows.py
dashboard/metrics.py
dashboard/components.py
dashboard/charts.py
dashboard/theme.py
dashboard/data/__init__.py
dashboard/data/public_demo.py
dashboard/data/public_evidence.py
dashboard/data/benchmark_repository.py
dashboard/views/__init__.py
dashboard/views/overview.py
dashboard/views/reliability.py
dashboard/views/requests.py
dashboard/views/evidence.py
bench/results/claims.json
bench/results/concurrency_summary.csv
bench/results/gateway_overhead.json
bench/results/lmstudio_concurrency_boundary_scan.json
bench/results/lmstudio_concurrency_boundary_scan_unified_kv_on.json
bench/results/lmstudio_unified_kv_cache_comparison.png
bench/results/prefill_summary.csv
bench/results/prefill_time_vs_prompt_length.png
bench/results/prompts/prompt_2000.json
bench/results/prompts/prompt_8000.json
bench/results/provenance.json
bench/results/throughput_vs_concurrency.png
bench/results/ttft_vs_concurrency.png
bench/results/vram_usage.png
EVAL_REPORT.md
LICENSE
THIRD_PARTY_NOTICES.md
```

Normalize and contain both paths under their roots. Copy bytes without transformation. Generate
`deployment-manifest.json` with exactly six keys: integer `schema_version` equal to `1`, string
`space_id` equal to `steven0226/local-inference-bench-gateway`, string `source_repository` equal to
`kuotunyu/local-inference-bench-gateway`, the validated 40-character lowercase-hex `source_commit`,
and lowercase-hex `export_manifest_sha256` and `evidence_manifest_sha256` values. The two SHA-256
values equal `hashlib.sha256(source_file.read_bytes()).hexdigest()` for
`space/bundle-manifest.json` and `bench/results/provenance.json`, respectively. The CLI obtains the
commit with `git rev-parse HEAD`, rejects a dirty worktree, and never deletes destination contents.

- [ ] **Step 4: Run exporter GREEN**

```powershell
uv run --frozen pytest tests/space/test_exporter.py -v
```

Expected: deterministic exports match byte-for-byte and unsafe destinations fail without mutation.

- [ ] **Step 5: Commit**

```powershell
uv run --frozen ruff check release_checks/space_bundle.py scripts/export_hf_space.py tests/space/test_exporter.py
uv run --frozen ruff format --check release_checks/space_bundle.py scripts/export_hf_space.py tests/space/test_exporter.py
git add space/bundle-manifest.json release_checks/space_bundle.py scripts/export_hf_space.py tests/space/test_exporter.py
git commit -m "build: add allowlisted Space exporter"
```

---

### Task 8: Enforce the transitive import and capability denylist

**Files:**
- Create: `release_checks/space_imports.py`
- Create: `tests/space/test_import_boundary.py`

**Interfaces:**
- Produces: `public_import_closure(bundle_root: Path, entrypoint: PurePosixPath = PurePosixPath("space/app.py")) -> tuple[PurePosixPath, ...]`.
- Produces: `verify_public_import_boundary(bundle_root: Path) -> list[str]`.

- [ ] **Step 1: Write failing denylist tests**

```python
@pytest.mark.parametrize(
    ("source", "message"),
    [
        ("import gateway.app\n", "forbidden import: gateway"),
        ("from dashboard import state\n", "forbidden import: dashboard.state"),
        ("import socket\n", "forbidden import: socket"),
        ("import subprocess\n", "forbidden import: subprocess"),
        ("import os\nVALUE = os.getenv('GATEWAY_API_KEY')\n", "environment read"),
        ("import importlib\nimportlib.import_module('gateway.app')\n", "dynamic import"),
        ("VALUE = __import__('socket')\n", "dynamic import"),
    ],
)
def test_import_boundary_rejects_capabilities(tmp_path: Path, source: str, message: str) -> None:
    write_minimal_bundle(tmp_path, source)
    assert any(message in item for item in verify_public_import_boundary(tmp_path))
```

Define these exact tests:

| Test | Input | Required result |
|---|---|---|
| `test_import_boundary_rejects_module_path_escape` | relative import resolving above bundle root | contains `import escapes bundle` |
| `test_import_boundary_rejects_unresolved_local_import` | `from dashboard import missing` | contains `unresolved local import` |
| `test_import_boundary_terminates_on_cycle` | two local modules importing one another | finishes with the violations from each module exactly once |
| `test_real_exported_bundle_has_zero_import_boundary_violations` | bundle produced by Task 7 | returns `[]` |
| `test_documentation_words_are_not_capability_violations` | Markdown containing `SQLite` and `HTTP` | returns `[]` because only Python AST is scanned |

- [ ] **Step 2: Run and observe RED**

```powershell
uv run --frozen pytest tests/space/test_import_boundary.py -v
```

Expected: import fails because `release_checks.space_imports` does not exist.

- [ ] **Step 3: Implement AST closure and capability checks**

Resolve only local `dashboard` and `space` modules inside the bundle. Reject these top-level or
qualified imports:

```python
FORBIDDEN_IMPORTS = {
    "gateway",
    "dashboard.state",
    "dashboard.data.live_status",
    "dashboard.data.sqlite_repository",
    "sqlite3",
    "httpx",
    "requests",
    "urllib.request",
    "socket",
    "subprocess",
}
```

Reject `os.getenv`, `os.environ`, `os.environ.get`, `__import__`, and
`importlib.import_module` anywhere in the application closure. Sort paths and violations for
deterministic output.

- [ ] **Step 4: Run denylist GREEN against fixtures and the real export**

```powershell
uv run --frozen pytest tests/space/test_import_boundary.py -v
```

Expected: malicious fixtures fail with exact categories and the real bundle has zero violations.

- [ ] **Step 5: Commit**

```powershell
uv run --frozen ruff check release_checks/space_imports.py tests/space/test_import_boundary.py
uv run --frozen ruff format --check release_checks/space_imports.py tests/space/test_import_boundary.py
git add release_checks/space_imports.py tests/space/test_import_boundary.py
git commit -m "test: enforce public Space import boundary"
```

---

### Task 9: Verify the exported Space artifact and integrate local release checks

**Files:**
- Modify: `release_checks/space_bundle.py`
- Modify: `release_checks/cli.py`
- Create: `tests/space/test_bundle_verifier.py`

**Interfaces:**
- Produces: `verify_space_bundle(repo_root: Path, bundle_root: Path) -> list[str]`.
- Produces: `verify_space_source(repo_root: Path) -> list[str]`, which exports into a temporary directory and runs bundle plus import checks.
- Extends local CLI output with `[space] OK` or `[space] FAIL`; it never calls `space_remote_gate`.

- [ ] **Step 1: Write failing mutation-matrix tests**

```python
@pytest.mark.parametrize(
    ("mutation", "expected"),
    [
        (add_unlisted_file, "undeclared bundle file"),
        (add_environment_file, "environment file"),
        (add_database_file, "runtime database"),
        (add_raw_jsonl, "raw result"),
        (add_model_weight, "model weight"),
        (add_large_file, "file is at least 5 MiB"),
        (add_secret_token, "secret-like token"),
        (remove_license, "missing required bundle file: LICENSE"),
        (tamper_evidence, "evidence byte mismatch"),
        (make_root_user, "Space runtime user must be 10001:10001"),
        (add_broad_copy, "broad Docker COPY"),
        (add_gpu_term, "GPU configuration"),
        (add_gateway_port, "gateway port 9000"),
    ],
)
def test_bundle_verifier_rejects_public_boundary_violation(
    tmp_path: Path, mutation, expected
) -> None:
    bundle = export_valid_bundle(tmp_path)
    mutation(bundle)
    assert any(expected in item for item in verify_space_bundle(Path.cwd(), bundle))
```

Define `test_valid_exported_bundle_passes_every_policy` and assert `verify_space_bundle(...) == []`.
Before that final assertion, compare the actual relative-path set with `expected_bundle_paths()`,
recompute both deployment-manifest digests from source bytes, assert the three dependency pins equal
Task 6, assert the card links scoped license and third-party notices, assert the canonical Space ID
and source revision, and assert each of the 14 evidence/control paths from the allowlist exists.

- [ ] **Step 2: Run and observe RED**

```powershell
uv run --frozen pytest tests/space/test_bundle_verifier.py -v
```

Expected: tests fail because `verify_space_bundle` and `verify_space_source` are absent.

- [ ] **Step 3: Implement artifact verification and local CLI integration**

Reuse `release_checks.publication` concepts without weakening its existing policy. Verify the exact
manifest destination set, a 5 MiB exclusive ceiling, known secret patterns, forbidden suffixes and
directories, LF-normalized evidence digests, byte equality with the source commit checkout, Docker
tokens, dependency pins, and deployment-manifest digests. Call
`verify_public_import_boundary(bundle_root)` and append its violations.

Add this local-only CLI entry:

```python
("space", lambda: verify_space_source(repo_root))
```

Do not import or invoke `space_remote_gate` from `release_checks/cli.py`.

- [ ] **Step 4: Run GREEN and all release checks**

```powershell
uv run --frozen pytest tests/space/test_bundle_verifier.py tests/test_publication.py tests/test_evidence.py -v
uv run --frozen python -m release_checks.cli
```

Expected: mutation tests reject exact violations; CLI prints `[space] OK` and `release checks passed`.

- [ ] **Step 5: Commit**

```powershell
uv run --frozen ruff check release_checks/space_bundle.py release_checks/cli.py tests/space/test_bundle_verifier.py
uv run --frozen ruff format --check release_checks/space_bundle.py release_checks/cli.py tests/space/test_bundle_verifier.py
git add release_checks/space_bundle.py release_checks/cli.py tests/space/test_bundle_verifier.py
git commit -m "test: verify exported Space artifact"
```

---

### Task 10: Implement the authenticated GET-only remote identity gate

**Files:**
- Create: `release_checks/space_remote_gate.py`
- Create: `tests/space/test_remote_gate.py`

**Interfaces:**
- Produces: `RemoteGateError(reason: Literal["owner_mismatch", "docker_ineligible", "exact_identity_exists", "namespace_collision", "authentication_failed", "rate_limited", "remote_error", "malformed_response", "timeout", "pagination_incomplete"])`.
- Produces: `RemoteGateDecision(space_id: str, owner: str, available: bool, docker_eligible: bool)`.
- Produces: `check_remote_gate(client: httpx.Client, token: str) -> RemoteGateDecision`.
- CLI: `python -m release_checks.space_remote_gate`; reads `HF_TOKEN`, emits no token value, performs GET requests only.

- [ ] **Step 1: Write failing mocked remote-gate tests**

```python
@respx.mock
def test_remote_gate_accepts_only_verified_owner_clear_name_and_pro_account() -> None:
    respx.get("https://huggingface.co/api/whoami-v2").mock(
        return_value=httpx.Response(200, json={"name": "steven0226", "isPro": True})
    )
    respx.get("https://huggingface.co/api/spaces/steven0226/local-inference-bench-gateway").mock(
        return_value=httpx.Response(404)
    )
    respx.get("https://huggingface.co/api/spaces").mock(return_value=httpx.Response(200, json=[]))

    decision = check_remote_gate(httpx.Client(), "secret-test-token")
    assert decision.available is True
    assert decision.docker_eligible is True
    assert {call.request.method for call in respx.calls} == {"GET"}
```

Define the following parameterized cases, each requiring `pytest.raises(RemoteGateError)` and an
exact stable `.reason`: `owner_mismatch`, `docker_ineligible`, `exact_identity_exists`, `namespace_collision`,
`authentication_failed`, `rate_limited`, `remote_error`, `malformed_response`, `timeout`, and
`pagination_incomplete`. Map wrong owner to `owner_mismatch`; false or missing `isPro` to
`docker_ineligible`; exact Space 200 to `exact_identity_exists`; a matching namespace-list item to
`namespace_collision`; 401/403, 429, 5xx, invalid JSON, `httpx.TimeoutException`, and a page with a
continuation cursor that cannot be completed to the remaining reason codes in order. In every case,
capture stdout/stderr and assert the supplied token occurs zero times.

- [ ] **Step 2: Run and observe RED**

```powershell
uv run --frozen pytest tests/space/test_remote_gate.py -v
```

Expected: import fails because `release_checks.space_remote_gate` does not exist.

- [ ] **Step 3: Implement strict read-only decisions**

Use bearer authentication and fixed URLs. Require exact `name == "steven0226"` and
`isPro is True`. Treat every result other than authenticated owner + exact 404 + collision-free
complete namespace listing as `RemoteGateError`. Inspect `response.next`/pagination metadata and
continue GET pages until complete. Reject every redirect to a non-Hugging Face host. Define no
POST, PUT, PATCH, DELETE, upload, create, or repository mutation function in this module.

- [ ] **Step 4: Run remote-gate GREEN without real network**

```powershell
uv run --frozen pytest tests/space/test_remote_gate.py -v
```

Expected: all mocked cases pass; test logs prove all calls are GET and no secret is printed.

- [ ] **Step 5: Commit**

```powershell
uv run --frozen ruff check release_checks/space_remote_gate.py tests/space/test_remote_gate.py
uv run --frozen ruff format --check release_checks/space_remote_gate.py tests/space/test_remote_gate.py
git add release_checks/space_remote_gate.py tests/space/test_remote_gate.py
git commit -m "feat: add read-only Space identity gate"
```

---

### Task 11: Characterize AppTest runtime isolation and evidence degradation adversarially

**Files:**
- Create: `tests/space/test_public_app_isolation.py`
- Modify: `tests/space/test_public_app.py`
- Modify: `tests/dashboard/test_public_evidence.py`
- Correct only after an observed product-contract RED: `space/app.py`
- Correct only after an observed product-contract RED: `dashboard/data/public_demo.py`
- Correct only after an observed product-contract RED: `dashboard/data/public_evidence.py`
- Correct only after an observed product-contract RED: `dashboard/views/evidence.py`

**Interfaces:**
- Consumes the public app and evidence boundary produced by Tasks 1–10.
- Produces test helper `semantic_app_snapshot(app: AppTest) -> tuple[str, ...]` inside the test module.
- Treats a first-run GREEN as valid characterization evidence, not as a reason to damage working product code.

- [ ] **Step 1: Write the adversarial characterization tests**

```python
def test_public_app_ignores_hostile_environment_and_never_opens_socket(monkeypatch) -> None:
    clean = AppTest.from_file(str(APP_PATH)).run(timeout=20)
    clean_snapshot = semantic_app_snapshot(clean)

    for key in (
        "GATEWAY_DB_PATH",
        "GATEWAY_BASE_URL",
        "GATEWAY_API_KEY",
        "HF_TOKEN",
        "HUGGING_FACE_HUB_TOKEN",
        "HF_HOME",
        "DATABASE_URL",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "NO_PROXY",
    ):
        monkeypatch.setenv(key, "http://attacker.invalid/secret")

    def reject_connection(*args, **kwargs):
        raise AssertionError("public app attempted a network connection")

    monkeypatch.setattr(socket, "create_connection", reject_connection)
    monkeypatch.setattr(socket.socket, "connect", reject_connection)
    monkeypatch.setattr(urllib.request, "urlopen", reject_connection)
    monkeypatch.setattr(httpx.Client, "request", reject_connection)
    hostile = AppTest.from_file(str(APP_PATH)).run(timeout=20)
    assert not hostile.exception
    assert semantic_app_snapshot(hostile) == clean_snapshot
```

Define `test_every_public_page_runs_with_network_guard` over the four Task 5 page labels and require
no exception. Define `test_public_app_creates_no_runtime_or_model_artifacts`; run from `tmp_path`
and require no files matching `*.db`, `*.sqlite*`, `*.gguf`, `*.safetensors`, `*.onnx`, or `*.jsonl`.
Define `test_evidence_panel_suppresses_unverified_values` over missing provenance, invalid
provenance, and one tampered artifact; require the affected panel to show `Unavailable — evidence
integrity check failed` and require every canonical value belonging to that panel to be absent from
rendered Markdown.

- [ ] **Step 2: Run once and classify the characterization result**

```powershell
uv run --frozen pytest tests/space/test_public_app_isolation.py tests/dashboard/test_public_evidence.py -v
```

There are exactly three outcomes:

1. Exit 0: record `first-run GREEN — Tasks 1–10 already satisfy the adversarial contract`; do not
   edit a source file and continue to Step 4.
2. A contract assertion or blocked-network sentinel fails: retain that failing test as the observed
   RED and continue to Step 3.
3. Test collection or fixture setup fails before exercising the product contract: correct only the
   three declared test files, rerun this step, and classify the resulting product-contract outcome.

- [ ] **Step 3: Apply a source correction only for an observed product-contract RED**

For a RED from Step 2, remove the identified environment read, runtime import, endpoint-derived
copy, non-deterministic timestamp, or evidence leak in the smallest matching declared source file.
Do not add exception handling that hides a connection attempt. Do not edit product code when Step 2
is first-run GREEN. If the fix requires a source path outside the four declared correction files,
stop this task and revise the plan before editing that path.

- [ ] **Step 4: Run the complete adversarial GREEN gate**

```powershell
uv run --frozen pytest tests/space/test_public_app.py tests/space/test_public_app_isolation.py tests/space/test_import_boundary.py tests/dashboard/test_public_evidence.py -v
```

Expected: all pages render identically under hostile environment and blocked sockets; degraded
evidence suppresses affected canonical values.

- [ ] **Step 5: Review exact paths and create a new task commit**

```powershell
git status --short
git diff --check
git diff -- tests/space/test_public_app_isolation.py tests/space/test_public_app.py tests/dashboard/test_public_evidence.py space/app.py dashboard/data/public_demo.py dashboard/data/public_evidence.py dashboard/views/evidence.py
uv run --frozen ruff check tests/space/test_public_app_isolation.py tests/space/test_public_app.py tests/dashboard/test_public_evidence.py space/app.py dashboard/data/public_demo.py dashboard/data/public_evidence.py dashboard/views/evidence.py
uv run --frozen ruff format --check tests/space/test_public_app_isolation.py tests/space/test_public_app.py tests/dashboard/test_public_evidence.py space/app.py dashboard/data/public_demo.py dashboard/data/public_evidence.py dashboard/views/evidence.py
git add -- tests/space/test_public_app_isolation.py tests/space/test_public_app.py tests/dashboard/test_public_evidence.py
```

When Step 2 was first-run GREEN, confirm `git diff --cached --name-only` lists only the three test
paths, then commit with `git commit -m "test: characterize public Space runtime isolation"`.

When Step 3 corrected source, inspect each changed source with `git diff --` and run only the
matching command below for every reviewed source path reported by `git status`; do not run a command
for an unchanged path:

```powershell
git add -- space/app.py
git add -- dashboard/data/public_demo.py
git add -- dashboard/data/public_evidence.py
git add -- dashboard/views/evidence.py
git diff --cached --name-only
git commit -m "fix: enforce public Space runtime isolation"
```

Do not amend a prior task commit in either branch.

---

### Task 12: Add Docker no-network smoke to CI and accept it from a clean HEAD

**Files:**
- Modify: `.github/workflows/ci.yml`
- Create: `tests/space/test_ci_policy.py`

**Interfaces:**
- Consumes: `scripts/export_hf_space.py` and exported Docker context.
- Produces CI image tag `local-inference-bench-gateway-space:rc`.
- Produces CI container name `local-inference-space-smoke`.
- Uses at most 45 one-second polling intervals with a 55-second hard deadline.

- [ ] **Step 1: Write failing CI policy tests**

```python
def test_ci_builds_non_root_space_and_runs_without_network() -> None:
    workflow = Path(".github/workflows/ci.yml").read_text(encoding="utf-8")
    assert "scripts/export_hf_space.py" in workflow
    assert "local-inference-bench-gateway-space:rc" in workflow
    assert "--network none" in workflow
    assert "local-inference-space-smoke" in workflow
    assert "Config.User" in workflow
    assert 'test "$runtime_user" = "10001:10001"' in workflow
    assert "for attempt in $(seq 1 45)" in workflow
    assert "deadline=$((SECONDS + 55))" in workflow
    assert "sleep 1" in workflow
    assert "http://127.0.0.1:7860/_stcore/health" in workflow
    assert "docker logs local-inference-space-smoke" in workflow
    assert "space_remote_gate" not in workflow
    assert "docker rm -f local-inference-space-smoke" in workflow
```

Define `test_ci_contains_no_network_space_smoke` to assert the workflow's `/app` scan names each of
`.db`, `.sqlite`, `.gguf`, `.safetensors`, `.onnx`, and `.jsonl`; the timeout branch prints container
logs and exits nonzero; and cleanup contains both `if: always()` and
`docker rm -f local-inference-space-smoke`.

- [ ] **Step 2: Run and observe RED**

```powershell
uv run --frozen pytest tests/space/test_ci_policy.py -v
```

Expected: assertions fail because Space export/build/bounded-smoke steps are absent.

- [ ] **Step 3: Add exact bounded CI steps**

After frozen tests and release checks, export into `${{ runner.temp }}/hf-space`, build the image,
inspect `.Config.User`, start with `--network none`, and implement this bounded health logic in the
workflow shell:

```bash
runtime_user="$(docker inspect --format '{{.Config.User}}' local-inference-space-smoke)"
test "$runtime_user" = "10001:10001"
healthy=0
deadline=$((SECONDS + 55))
for attempt in $(seq 1 45); do
  if docker exec local-inference-space-smoke python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:7860/_stcore/health', timeout=0.2).read()"; then
    healthy=1
    break
  fi
  if [ "$SECONDS" -ge "$deadline" ]; then break; fi
  sleep 1
done
if [ "$healthy" -ne 1 ]; then
  docker logs local-inference-space-smoke >&2
  exit 1
fi
```

Then inspect `/app` for forbidden generated files. Add unconditional log capture and cleanup. Do not
expose a host port in the no-network smoke and do not execute the remote gate.

- [ ] **Step 4: Run focused policy GREEN without exporting**

```powershell
uv run --frozen pytest tests/space/test_ci_policy.py tests/test_ci_policy.py -v
git diff --check
```

Expected: all selected tests pass. Do not call the exporter while these changes are uncommitted.

- [ ] **Step 5: Commit the exact focused changes and prove the HEAD is clean**

```powershell
git status --short
git diff -- .github/workflows/ci.yml tests/space/test_ci_policy.py
git add -- .github/workflows/ci.yml tests/space/test_ci_policy.py
git diff --cached --check
git commit -m "ci: smoke public Space without network"
$dirty = git status --porcelain
if ($dirty) { throw "Task 12 requires a clean HEAD before export: $dirty" }
$sourceCommit = (git rev-parse HEAD).Trim()
```

- [ ] **Step 6: Export from the clean HEAD and run the bounded local Docker acceptance**

```powershell
$smokeRoot = New-Item -ItemType Directory -Path (Join-Path ([System.IO.Path]::GetTempPath()) ([guid]::NewGuid().ToString()))
$bundle = Join-Path $smokeRoot.FullName 'hf-space'
if (Test-Path -LiteralPath $bundle) { throw "Expected a nonexistent bundle path: $bundle" }
$existing = docker ps -a --filter "name=^/local-inference-space-smoke$" --format '{{.Names}}'
if ($existing) { throw "Container name is already in use: local-inference-space-smoke" }
uv run --frozen python scripts/export_hf_space.py --destination $bundle
if ($LASTEXITCODE -ne 0) { throw "Clean-HEAD export failed" }
$manifest = Get-Content -Raw -LiteralPath (Join-Path $bundle 'deployment-manifest.json') | ConvertFrom-Json
if ($manifest.source_commit -cne $sourceCommit) { throw "Exported source commit does not match HEAD" }
docker build -t local-inference-bench-gateway-space:rc $bundle
if ($LASTEXITCODE -ne 0) { throw "Docker build failed" }
$containerStarted = $false
try {
    docker run -d --name local-inference-space-smoke --network none local-inference-bench-gateway-space:rc
    if ($LASTEXITCODE -ne 0) { throw "Container start failed" }
    $containerStarted = $true
    $runtimeUser = (docker inspect --format '{{.Config.User}}' local-inference-space-smoke).Trim()
    if ($runtimeUser -cne '10001:10001') { throw "Unexpected runtime user: $runtimeUser" }
    $healthy = $false
    $deadline = [DateTimeOffset]::UtcNow.AddSeconds(55)
    for ($attempt = 1; $attempt -le 45 -and [DateTimeOffset]::UtcNow -lt $deadline; $attempt++) {
        docker exec local-inference-space-smoke python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:7860/_stcore/health', timeout=0.2).read()"
        if ($LASTEXITCODE -eq 0) { $healthy = $true; break }
        Start-Sleep -Seconds 1
    }
    if (-not $healthy) {
        docker logs local-inference-space-smoke
        throw "Streamlit health did not pass within 45 attempts and 55 seconds"
    }
    docker exec local-inference-space-smoke sh -c "! find /app -type f \( -name '*.db' -o -name '*.sqlite*' -o -name '*.gguf' -o -name '*.safetensors' -o -name '*.onnx' -o -name '*.jsonl' \) | grep ."
    if ($LASTEXITCODE -ne 0) { throw "Forbidden runtime artifact found" }
} finally {
    if ($containerStarted) { docker rm -f local-inference-space-smoke }
}
```

Expected: export records the clean `$sourceCommit`; runtime user equals `10001:10001`; health passes
within both bounds; forbidden-file scan exits 0; cleanup exits 0. Retain `$smokeRoot` for review and
report its exact path; this step performs no recursive deletion.

- [ ] **Step 7: Handle acceptance defects with a new corrective commit**

If Step 6 passes, make no further Task 12 commit. If it fails, do not amend the Task 12 commit. Add
one failing regression test according to this exact ownership table, run that test to record RED,
make the minimal listed source correction, and run the same test plus Step 4 to GREEN:

| Failed invariant | Regression test file | Permitted correction file |
|---|---|---|
| workflow ordering, polling, logs, or cleanup | `tests/space/test_ci_policy.py` | `.github/workflows/ci.yml` |
| image user, command, port, or health metadata | `tests/space/test_space_assets.py` | `space/Dockerfile` |
| export path, commit, or manifest mismatch | `tests/space/test_exporter.py` | `release_checks/space_bundle.py` or `scripts/export_hf_space.py` |
| startup or forbidden runtime write | `tests/space/test_public_app_isolation.py` | `space/app.py`, `dashboard/data/public_demo.py`, or `dashboard/data/public_evidence.py` |

Review `git status --short`, `git diff --check`, and `git diff --` for the exact row's paths. Stage
only those reviewed file paths, commit with `git commit -m "fix: correct Docker Space smoke defect"`,
prove the new HEAD clean, and repeat Step 6 from that new HEAD. A failure requiring a path outside
the table stops the task for a plan revision.

---

### Task 13: Add release gates, then visually accept valid and NEVER_DEPLOY bundles

**Files:**
- Create: `docs/HF_SPACE_RELEASE.md`
- Create: `tests/space/test_release_runbook.py`
- Correct only after an observed request-graph RED: `tests/space/test_space_assets.py`
- Correct only after an observed request-graph RED: `space/Dockerfile`
- Correct only after an observed visual RED: `tests/space/test_public_app.py`
- Correct only after an observed visual RED: `tests/space/test_public_app_isolation.py`
- Correct only after an observed visual RED: `tests/dashboard/test_public_evidence.py`
- Correct only after an observed visual RED: `tests/dashboard/test_theme.py`
- Correct only after an observed visual RED: `space/app.py`
- Correct only after an observed visual RED: `dashboard/data/public_evidence.py`
- Correct only after an observed visual RED: `dashboard/views/evidence.py`
- Correct only after an observed visual RED: `dashboard/theme.py`

**Interfaces:**
- Documents local checks, exact visual viewports, read-only remote gate, create/upload stop point,
  canonical Hub verification, and post-deployment About approval order.
- Does not add the planned Space URL to the GitHub About field or repository README.
- Uses a verified valid bundle for the four-page visual gate and a separate disposable
  `NEVER_DEPLOY-hf-space-tampered` copy for one-artifact fail-closed review.

- [ ] **Step 1: Write failing runbook-order tests**

```python
def test_runbook_preserves_remote_and_about_gates() -> None:
    text = Path("docs/HF_SPACE_RELEASE.md").read_text(encoding="utf-8")
    ordered = [
        "Authenticated collision preflight",
        "STOP — separate owner authorization required for Space creation",
        "Public Space cold-start and mobile/desktop review",
        "STOP — separate owner authorization required for GitHub About",
        "https://huggingface.co/spaces/steven0226/local-inference-bench-gateway",
    ]
    positions = [text.index(item) for item in ordered]
    assert positions == sorted(positions)
    assert "steven0226-local-inference-bench-gateway.hf.space" not in text
    assert "1440x900" in text
    assert "390x844" in text
    assert "No SLA" in text
    assert "NEVER_DEPLOY-hf-space-tampered" in text
```

Define `test_release_runbook_contains_every_claim_and_visual_gate`. Assert it contains the exact
truth-contract copy, a valid-bundle `12/12` evidence-status check, valid-bundle degraded-warning
absence check, endpoint-URL absence check, Live-selector absence check,
model/GPU-current-execution claim absence check, browser-console error check, horizontal-overflow
check, license and notices checks, Space sleep/cold-start check, and the separate tampered-bundle
warning/value-suppression check. Also assert that both valid and tampered gates record the original
full URL, resource type, and initiator metadata for every non-loopback origin without blocking or
interception; permit only loopback and same-origin runtime requests and make
`data.streamlit.io`, Fivetran, or any other external origin RED. Define
`test_release_runbook_keeps_remote_writes_behind_stops`;
assert the first write-capable operation is after the creation authorization stop, the About
mutation is after its separate authorization stop, and final About API readback follows the mutation.

- [ ] **Step 2: Run and observe RED**

```powershell
uv run --frozen pytest tests/space/test_release_runbook.py -v
```

Expected: `FileNotFoundError` for `docs/HF_SPACE_RELEASE.md`.

- [ ] **Step 3: Write the exact runbook without executing its export command**

Document these future release commands in order:

```powershell
# RUNBOOK CONTENT ONLY — DO NOT EXECUTE DURING STEP 3
uv sync --frozen --all-extras
uv run --frozen ruff check .
uv run --frozen ruff format --check .
uv run --frozen pytest -q -p no:cacheprovider
uv run --frozen python -m release_checks.cli
$dirty = git status --porcelain
if ($dirty) { throw "Release export requires a clean HEAD: $dirty" }
$reviewRoot = New-Item -ItemType Directory -Path (Join-Path ([System.IO.Path]::GetTempPath()) ([guid]::NewGuid().ToString()))
$bundle = Join-Path $reviewRoot.FullName 'hf-space'
uv run --frozen python scripts/export_hf_space.py --destination $bundle
```

The runbook requires the operator to verify `$bundle` is the nonexistent child of the new
GUID-named directory. Place the real remote-gate command after all local checks and immediately
before the explicit creation stop. State that the gate performs GET only and that implementation
agents never execute it without owner credentials and authority. State that paths containing
`NEVER_DEPLOY` are prohibited inputs to every remote command. The local runbook also requires an
unintercepted CDP or Playwright request graph for each visual gate, with original URLs, resource
types, and initiators retained as evidence and zero non-loopback or cross-origin runtime requests.

- [ ] **Step 4: Run focused runbook GREEN**

```powershell
uv run --frozen pytest tests/space/test_release_runbook.py -v
git diff --check
```

Expected: gate-order, claim-boundary, valid-bundle, and tampered-bundle instructions pass. Do not
call the exporter while the runbook and test are uncommitted.

- [ ] **Step 5: Commit the exact runbook changes and prove the HEAD is clean**

```powershell
git status --short
git diff -- docs/HF_SPACE_RELEASE.md tests/space/test_release_runbook.py
git add -- docs/HF_SPACE_RELEASE.md tests/space/test_release_runbook.py
git diff --cached --check
git commit -m "docs: add public Space release gates"
$dirty = git status --porcelain
if ($dirty) { throw "Task 13 requires a clean HEAD before export: $dirty" }
$sourceCommit = (git rev-parse HEAD).Trim()
```

- [ ] **Step 6: Export the valid clean-HEAD bundle and run its full visual gate**

```powershell
$reviewRoot = New-Item -ItemType Directory -Path (Join-Path ([System.IO.Path]::GetTempPath()) ([guid]::NewGuid().ToString()))
$bundle = Join-Path $reviewRoot.FullName 'hf-space-valid'
if (Test-Path -LiteralPath $bundle) { throw "Expected a nonexistent valid bundle path: $bundle" }
$existing = docker ps -a --filter "name=^/local-inference-space-visual-valid$" --format '{{.Names}}'
if ($existing) { throw "Container name is already in use: local-inference-space-visual-valid" }
function Wait-SpaceContainerHealth([string]$ContainerName) {
    $healthy = $false
    $deadline = [DateTimeOffset]::UtcNow.AddSeconds(55)
    for ($attempt = 1; $attempt -le 45 -and [DateTimeOffset]::UtcNow -lt $deadline; $attempt++) {
        docker exec $ContainerName python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:7860/_stcore/health', timeout=0.2).read()"
        if ($LASTEXITCODE -eq 0) { $healthy = $true; break }
        Start-Sleep -Seconds 1
    }
    if (-not $healthy) {
        docker logs $ContainerName
        throw "Streamlit health did not pass within 45 attempts and 55 seconds: $ContainerName"
    }
}
uv run --frozen python scripts/export_hf_space.py --destination $bundle
if ($LASTEXITCODE -ne 0) { throw "Clean-HEAD visual export failed" }
$manifest = Get-Content -Raw -LiteralPath (Join-Path $bundle 'deployment-manifest.json') | ConvertFrom-Json
if ($manifest.source_commit -cne $sourceCommit) { throw "Visual bundle source commit does not match HEAD" }
uv run --frozen python -c "import sys; from pathlib import Path; from release_checks.space_bundle import verify_space_bundle; assert verify_space_bundle(Path.cwd(), Path(sys.argv[1])) == []" $bundle
if ($LASTEXITCODE -ne 0) { throw "Valid bundle verification failed" }
docker build -t local-inference-bench-gateway-space:visual-valid $bundle
if ($LASTEXITCODE -ne 0) { throw "Valid visual image build failed" }
docker run -d --name local-inference-space-visual-valid -p 127.0.0.1:7860:7860 local-inference-bench-gateway-space:visual-valid
if ($LASTEXITCODE -ne 0) { throw "Valid visual container start failed" }
Wait-SpaceContainerHealth 'local-inference-space-visual-valid'
```

At both `1440x900` and `390x844`, inspect all four views and require:

1. The truth contract is visible before the first control.
2. `document.documentElement.scrollWidth === document.documentElement.clientWidth` is `true`.
3. The correct persistent source badge is visible and cannot be confused with Live data.
4. No local URL, health endpoint, prompt input, upload, current GPU runtime, or SLA claim appears.
5. Charts, legends, tooltips, table columns, and navigation are readable.
6. The evidence page reports `12/12` verified artifacts and displays no degraded-evidence warning.
7. Browser console and Streamlit exception counts are both zero.
8. At each viewport, record every request made while visiting all four views. Preserve the original
   full URL, resource type, and initiator metadata for each non-loopback origin. Do not block,
   intercept, rewrite, or fulfill a request. Require zero non-loopback or cross-origin runtime
   requests; `data.streamlit.io`, Fivetran, and every other external origin are RED.

Save optional screenshots only under ignored `.dashboard-cache/space-visual/valid/`. Then run
`docker rm -f local-inference-space-visual-valid`, require exit 0, and do not remove `$reviewRoot`
yet. If an inspection fails, remove that exact container before entering Step 8.

- [ ] **Step 7: Build a disposable NEVER_DEPLOY copy and inspect fail-closed degradation**

```powershell
$tamperRoot = New-Item -ItemType Directory -Path (Join-Path ([System.IO.Path]::GetTempPath()) ([guid]::NewGuid().ToString()))
$tamperedBundle = Join-Path $tamperRoot.FullName 'NEVER_DEPLOY-hf-space-tampered'
if (Test-Path -LiteralPath $tamperedBundle) { throw "Expected a nonexistent tampered bundle path" }
Copy-Item -LiteralPath $bundle -Destination $tamperedBundle -Recurse
Set-Content -LiteralPath (Join-Path $tamperRoot.FullName 'NEVER_DEPLOY.txt') -Encoding utf8 -Value 'LOCAL FAIL-CLOSED VISUAL FIXTURE ONLY. NEVER DEPLOY OR UPLOAD.'
$tamperedArtifact = Join-Path $tamperedBundle 'bench\results\gateway_overhead.json'
[System.IO.File]::AppendAllText($tamperedArtifact, "`n", [System.Text.UTF8Encoding]::new($false))
uv run --frozen python -c "import sys; from pathlib import Path; from release_checks.space_bundle import verify_space_bundle; v=verify_space_bundle(Path.cwd(), Path(sys.argv[1])); assert len(v) == 1 and 'evidence byte mismatch' in v[0], v" $tamperedBundle
$existing = docker ps -a --filter "name=^/local-inference-space-visual-tampered$" --format '{{.Names}}'
if ($existing) { throw "Container name is already in use: local-inference-space-visual-tampered" }
docker build -t local-inference-bench-gateway-space:never-deploy $tamperedBundle
if ($LASTEXITCODE -ne 0) { throw "NEVER_DEPLOY visual image build failed" }
docker run -d --name local-inference-space-visual-tampered -p 127.0.0.1:7861:7860 local-inference-bench-gateway-space:never-deploy
if ($LASTEXITCODE -ne 0) { throw "NEVER_DEPLOY visual container start failed" }
Wait-SpaceContainerHealth 'local-inference-space-visual-tampered'
```

Inspect only the evidence view at `http://127.0.0.1:7861` using `1440x900` and `390x844`. Require
`Unavailable — evidence integrity check failed`,
require the canonical `Gateway median TTFT overhead: 1.66 ms` claim to be absent, require unaffected
verified panels to remain readable, and require zero console or Streamlit exceptions. At each
viewport, capture the unintercepted request graph with original full URLs, resource types, and
initiator metadata; require zero non-loopback or cross-origin runtime requests, treating
`data.streamlit.io`, Fivetran, or any other external origin as RED. Save optional
screenshots only under ignored `.dashboard-cache/space-visual/NEVER_DEPLOY/`. Never pass
`$tamperedBundle`, its image tag, or its container to a remote command.

After inspection, remove the exact tampered container. Resolve and validate both task-owned roots
before recursive cleanup:

```powershell
function Remove-TaskOwnedTempRoot([string]$Path) {
    $resolved = [System.IO.Path]::GetFullPath($Path).TrimEnd('\', '/')
    $temp = [System.IO.Path]::GetFullPath([System.IO.Path]::GetTempPath()).TrimEnd('\', '/')
    $parent = [System.IO.Path]::GetDirectoryName($resolved)
    $leaf = [System.IO.Path]::GetFileName($resolved)
    $parsed = [Guid]::Empty
    if (-not [string]::Equals($parent, $temp, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing cleanup outside the OS temp directory: $resolved"
    }
    if (-not [Guid]::TryParseExact($leaf, 'D', [ref]$parsed)) {
        throw "Refusing cleanup of a non-GUID task root: $resolved"
    }
    Remove-Item -LiteralPath $resolved -Recurse -Force
}

docker rm -f local-inference-space-visual-tampered
Remove-TaskOwnedTempRoot $tamperRoot.FullName
Remove-TaskOwnedTempRoot $reviewRoot.FullName
```

- [ ] **Step 8: Correct any visual defect with a new RED/GREEN commit**

If Steps 6 and 7 pass, create no additional Task 13 commit. If either gate fails, clean up its
task-owned container and temp roots first; do not amend the runbook commit. Add one failing
regression according to this table, run it to record RED, make the minimal listed correction, and
run the same test plus Steps 4, 6, and 7 to GREEN:

| Visual defect | Regression test file | Permitted correction file |
|---|---|---|
| truth contract, badge, controls, or page semantics | `tests/space/test_public_app.py` | `space/app.py` |
| fail-closed warning or canonical value leak | `tests/space/test_public_app_isolation.py` or `tests/dashboard/test_public_evidence.py` | `dashboard/data/public_evidence.py` or `dashboard/views/evidence.py` |
| desktop/mobile overflow or unreadable responsive rule | `tests/dashboard/test_theme.py` | `dashboard/theme.py` |
| runbook claim or ordering defect | `tests/space/test_release_runbook.py` | `docs/HF_SPACE_RELEASE.md` |
| browser request graph contains a non-loopback or cross-origin request | `tests/space/test_space_assets.py` and `tests/space/test_release_runbook.py` | `space/Dockerfile` and `docs/HF_SPACE_RELEASE.md` |

Review `git status --short`, `git diff --check`, and `git diff --` for the exact row's paths. Stage
only the reviewed test and correction paths and commit with
`git commit -m "fix: correct public Space visual acceptance defect"`. Prove the corrective HEAD is
clean before re-exporting. A required path outside the table stops the task for a plan revision.

For the observed Streamlit/Fivetran request-graph RED, preserve the pre-fix graph with every
external original URL, resource type, and initiator. Do not fake GREEN by blocking, intercepting,
rewriting, or fulfilling the requests. Before any product, test, or runbook correction, commit only
the governing design and plan update and obtain a fresh review of that docs-only commit.

After fresh review, add regressions in exactly `tests/space/test_space_assets.py` and
`tests/space/test_release_runbook.py`. The asset regression requires the literal
`COPY .streamlit/config.toml /app/.streamlit/config.toml`, rejects broad-copy instructions, and
rejects `CMD`-only hiding of telemetry. The runbook regression requires unintercepted valid and
tampered request graphs with zero non-loopback or cross-origin requests. Run both focused tests and
record RED before changing exactly `space/Dockerfile` and `docs/HF_SPACE_RELEASE.md`; then run both
focused tests to GREEN. Review and stage exactly those four paths and create a new corrective commit
without amending the existing `docs: add public Space release gates` commit. From that clean new
HEAD, re-run Step 4, re-export rather than altering the retained bundle, and re-run all of Steps 6
and 7. Both visual gates must preserve the request-graph evidence, report zero external requests at
both viewports, pass their visual assertions, remove only preflight-proven task-owned containers,
images, and temporary copies, and finish with a clean HEAD.

---

### Task 14: Run final local acceptance and hand off without remote mutation

**Files:**
- Verify only; no repository file creation or modification. New GUID-named OS temporary roots are
  permitted for exported acceptance bundles and are removed only after the path-containment check.

**Interfaces:**
- Consumes every prior task deliverable.
- Produces a clean branch, exact verification evidence, and no remote side effect.

- [ ] **Step 1: Run the complete frozen verification suite**

```powershell
uv sync --frozen --all-extras
uv run --frozen ruff check .
uv run --frozen ruff format --check .
uv run --frozen pytest -q -p no:cacheprovider
uv run --frozen python -m release_checks.cli
```

Expected: every command exits 0; pytest reports zero failures; release checks include `[space] OK`.

- [ ] **Step 2: Re-export and verify deterministic bytes**

Export twice into two newly created empty temporary paths using the same HEAD. Compare every
relative path and byte sequence. Require identical outputs, including `deployment-manifest.json`.
Run `verify_space_bundle()` and `verify_public_import_boundary()` on both and require empty
violation lists.

- [ ] **Step 3: Re-run final Docker and browser acceptance from the clean HEAD**

Build one of Step 2's verified bundles. Start it as `local-inference-space-final-networkless` with
`--network none` and no host-port mapping. Store
`docker inspect --format '{{.Config.User}}' local-inference-space-final-networkless` in a variable
and require exact equality with `10001:10001`. Poll the container-local
`http://127.0.0.1:7860/_stcore/health` at most 45 times, sleep one second between attempts, and stop
at a 55-second deadline. On timeout, print the exact container logs and fail. Require the `/app`
scan to find no `.db`, `.sqlite*`, `.gguf`, `.safetensors`, `.onnx`, or `.jsonl` file, then remove
that exact container.

Start the same verified bundle as `local-inference-space-final-visual` with
`127.0.0.1:7860:7860`. Apply the identical 45-attempt/55-second health bounds. At `1440x900` and
`390x844`, visit all four views; require the truth contract before controls, correct badges,
`12/12` verified evidence without a degraded warning, zero horizontal overflow, zero browser-console
errors, zero Streamlit exceptions, and an unintercepted request graph with zero non-loopback or
cross-origin runtime requests. Preserve original full URLs, resource types, and initiators for any
failure. Create a separate `NEVER_DEPLOY-hf-space-tampered` copy,
append one LF byte only to `bench/results/gateway_overhead.json`, and require the verifier to report
exactly one evidence-byte mismatch. Run that copy only as
`local-inference-space-final-tampered` on `127.0.0.1:7861:7860`; require the fail-closed warning and
absence of `Gateway median TTFT overhead: 1.66 ms` at both viewports. Remove both exact containers.
Capture the same unintercepted request graph for the tampered gate at both viewports and require
zero non-loopback or cross-origin runtime requests. Never block or intercept telemetry to satisfy
either request-graph gate.
Before recursively removing the task-created temporary roots, resolve each absolute path, require
its parent to equal the OS temp directory, and require its leaf to parse as a GUID.

- [ ] **Step 4: Prove remote boundaries and clean state**

```powershell
git status --short --branch
git diff --check
git log --oneline --decorate -15
git remote -v
```

Expected: worktree is clean on the implementation branch. Report that no push, PR, merge, Space
mutation, About edit, visibility change, or real remote-gate call occurred. Do not create an empty
verification commit.

---

## Spec Coverage Matrix

| Spec section | Implemented and verified by |
|---|---|
| 1. Objective | Tasks 5, 6, 13, 14 |
| 2. Approved approach | Tasks 3, 5, 7, 8, 9 |
| 3. Canonical identity and collision gate | Tasks 10, 13, 14 |
| 4. Public truth contract | Tasks 5, 6, 11, 13 |
| 5. System boundary and data flow | Tasks 1–5, 8, 11 |
| 6. Information architecture | Tasks 3, 5, 11, 13 |
| 7. Repository and bundle design | Tasks 6–9 |
| 8. Docker runtime | Tasks 6, 9, 12, 14 |
| 9. Runtime network isolation | Tasks 8, 11, 12, 14 |
| 10. Error and degraded states | Tasks 4, 5, 10, 11 |
| 11. Verification strategy | Tasks 1–14 |
| 12. Deployment and About gates | Tasks 10, 13, 14 |
| 13. Success criteria | Tasks 11–14 |
| 14. Implementation-plan scope | Tasks 1–14; remote operations remain excluded |
| 15. Non-goals | Global Constraints, Tasks 8–14 |
| 16. Authoritative references | Global Constraints and `docs/HF_SPACE_RELEASE.md` in Task 13 |

## Execution Handoff

Plan complete and saved to
`docs/superpowers/plans/2026-08-31-local-inference-bench-gateway-space.md`.

Two execution options:

1. **Subagent-Driven (recommended)** — dispatch a fresh subagent per task with two-stage review
   between tasks.
2. **Inline Execution** — execute tasks in this session with `superpowers:executing-plans` and
   explicit batch checkpoints.

No execution begins until the owner or central coordinator chooses one option in writing.
