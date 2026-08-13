# Operations Console Density & Readability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Operations Console denser at the page level and substantially more readable at the content and chart level.

**Architecture:** Preserve the existing data/view boundaries. Add one reusable Altair chart module for explicit typography and mark sizing, refine shared CSS tokens, then migrate each view from Streamlit convenience charts to the shared chart configuration while simplifying layout composition.

**Tech Stack:** Python 3.12, Streamlit, pandas, Altair, pytest, Ruff

## Global Constraints

- Page titles use a desktop range of 2–2.25 rem; mobile titles use 1.75–1.9 rem.
- Primary body copy is 17 px; supporting copy, source notes, KPI labels, captions, axes, and legends are at least 14 px.
- Primary charts use a full-width 380–420 px canvas; narrow-screen charts retain at least 320 px height.
- Preserve Traditional Chinese copy, original technical terms, current Morandi semantic colors, and all telemetry/evidence semantics.
- Do not add pages, navigation levels, unsupported operational claims, or decorative wrappers.

---

### Task 1: Shared typography and chart foundation

**Files:**
- Create: `dashboard/charts.py`
- Modify: `dashboard/theme.py`
- Test: `tests/dashboard/test_charts.py`
- Test: `tests/dashboard/test_theme.py`

**Interfaces:**
- Produces: `chart_theme() -> dict`, `line_chart(data, *, x, y, color, height, y_title, x_title=None, tooltip=None) -> alt.Chart`, and `bar_chart(data, *, x, y, color, height, x_title=None, y_title=None, tooltip=None) -> alt.Chart`.
- Consumes: pandas DataFrames and existing Morandi semantic colors.

- [ ] **Step 1: Write failing tests for chart typography and theme density**

```python
def test_chart_theme_has_readable_axes_and_legend() -> None:
    config = chart_theme()
    assert config["axis"]["labelFontSize"] >= 14
    assert config["axis"]["titleFontSize"] >= 15
    assert config["legend"]["labelFontSize"] >= 14


def test_theme_uses_compact_title_and_readable_body() -> None:
    css = build_theme_css()
    assert "font-size: 17px" in css
    assert "2.25rem" in css
    assert "3.55rem" not in css
```

- [ ] **Step 2: Run the focused tests and confirm they fail for missing chart helpers and old typography**

Run: `uv run --frozen pytest tests/dashboard/test_charts.py tests/dashboard/test_theme.py -q`

- [ ] **Step 3: Implement the shared Altair helpers and CSS density tokens**

Use 14 px axis/legend labels, 15 px axis titles, 2.75 px lines, 64 px points, 17 px body copy, 14 px support copy, a 2.65 rem title ceiling, a 1500 px canvas, and reduced shell/section/card spacing.

- [ ] **Step 4: Run focused tests and Ruff**

Run: `uv run --frozen pytest tests/dashboard/test_charts.py tests/dashboard/test_theme.py -q`

Run: `uv run --frozen ruff check dashboard/charts.py dashboard/theme.py tests/dashboard/test_charts.py tests/dashboard/test_theme.py`

- [ ] **Step 5: Commit the foundation**

```bash
git add dashboard/charts.py dashboard/theme.py tests/dashboard/test_charts.py tests/dashboard/test_theme.py
git commit -m "feat: add readable operations chart system"
```

### Task 2: Overview and reliability operational layout

**Files:**
- Modify: `dashboard/views/overview.py`
- Modify: `dashboard/views/reliability.py`
- Test: `tests/dashboard/test_dashboard_smoke.py`

**Interfaces:**
- Consumes: `dashboard.charts.line_chart` and `dashboard.charts.bar_chart`.
- Preserves: `build_overview_model`, `build_reliability_model`, telemetry semantics, and current health wording.

- [ ] **Step 1: Add smoke assertions for the expanded operational chart headings**

Assert that Overview renders a single `Request volume 與 P95 latency` section before health/routing content and Reliability renders `Error Categories` without exceptions.

- [ ] **Step 2: Run focused smoke tests and confirm the new layout assertions fail**

Run: `uv run --frozen pytest tests/dashboard/test_dashboard_smoke.py -q`

- [ ] **Step 3: Recompose Overview**

Render request volume and P95 latency as one layered full-width Altair chart at 400 px. Move Backend Health and Alias Routing into the following row and retain Recent Failover as the paired operational detail. Keep five KPI cards but reduce their visual height through shared CSS.

- [ ] **Step 4: Recompose Reliability**

Keep routing and health paired. Render Error Categories as a 360 px horizontal Altair bar chart with Backpressure in a narrower adjacent column and retain the full-width failover table.

- [ ] **Step 5: Run view tests and commit**

Run: `uv run --frozen pytest tests/dashboard/test_view_models.py tests/dashboard/test_dashboard_smoke.py -q`

```bash
git add dashboard/views/overview.py dashboard/views/reliability.py tests/dashboard/test_dashboard_smoke.py
git commit -m "feat: expand operational overview charts"
```

### Task 3: Requests and benchmark evidence readability

**Files:**
- Modify: `dashboard/views/requests.py`
- Modify: `dashboard/views/evidence.py`
- Test: `tests/dashboard/test_requests_view.py`
- Test: `tests/dashboard/test_evidence_view.py`

**Interfaces:**
- Consumes: shared Altair chart helpers and the existing filtered request/evidence DataFrames.
- Preserves: filters, evidence verification warnings, KPI definitions, provenance disclosure, and unavailable-artifact states.

- [ ] **Step 1: Add regression tests for empty/degraded chart states**

Extend the existing tests so missing request/evidence frames still render without exceptions after the Altair migration.

- [ ] **Step 2: Run focused tests before migration**

Run: `uv run --frozen pytest tests/dashboard/test_requests_view.py tests/dashboard/test_evidence_view.py -q`

- [ ] **Step 3: Tighten Requests composition**

Keep filters in two compact rows, reduce summary spacing, increase the request table height to 540 px, and retain 14 px-or-larger table/support text through shared CSS.

- [ ] **Step 4: Expand Benchmark Evidence charts**

Render throughput and P50/P95 TTFT as separate 400 px full-width charts. Render Prefill, Gateway Cost, VRAM, and Unified KV Cache as 340–360 px secondary charts using explicit 14/15 px chart typography and visible marks.

- [ ] **Step 5: Run focused tests and commit**

Run: `uv run --frozen pytest tests/dashboard/test_requests_view.py tests/dashboard/test_evidence_view.py -q`

```bash
git add dashboard/views/requests.py dashboard/views/evidence.py tests/dashboard/test_requests_view.py tests/dashboard/test_evidence_view.py
git commit -m "feat: enlarge request and evidence canvases"
```

### Task 4: Full verification and bounded visual QA

**Files:**
- Verify: `dashboard/app.py`
- Verify: all files changed in Tasks 1–3

**Interfaces:**
- Consumes: the completed Streamlit application at `http://127.0.0.1:8501/`.
- Produces: a clean merged working tree with tested desktop and mobile layouts.

- [ ] **Step 1: Run the full automated verification gate**

Run: `git diff --check`

Run: `uv run --frozen ruff format --check .`

Run: `uv run --frozen ruff check .`

Run: `uv run --frozen pytest -q`

Run: `uv run --frozen python -m release_checks.cli`

- [ ] **Step 2: Run the Impeccable mechanical detector once**

Run: `node "$env:USERPROFILE\.codex\skills\impeccable\scripts\detect.mjs" --json dashboard/app.py dashboard/theme.py dashboard/charts.py dashboard/views`

- [ ] **Step 3: Perform one batched browser inspection**

At 1440×900 and 390×844, inspect all four views. Confirm readable typography, expanded chart canvases, no horizontal overflow, no application exception, and no new console errors.

- [ ] **Step 4: Fix all findings in one batch and run one confirmation pass**

Do not begin open-ended polishing. Re-run the relevant automated tests plus one desktop/mobile confirmation.

- [ ] **Step 5: Commit final refinements**

```bash
git add dashboard tests/dashboard
git commit -m "fix: polish console density and chart legibility"
```
