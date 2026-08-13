# Scientific Console Density Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the existing Operations Console into a rational, scientific interface with larger supporting text and more deliberate use of wide-screen space.

**Architecture:** Keep the existing Streamlit view and data boundaries intact. Centralize visual changes in `dashboard/theme.py`, move the header brand markup into the testable presentation helpers in `dashboard/components.py`, update only view-heading copy in the four view modules, and raise the shared Altair typography tokens in `dashboard/charts.py`.

**Tech Stack:** Python 3.12, Streamlit, Altair, pytest, Ruff, CSS embedded through `st.markdown`.

## Global Constraints

- Use an 18 px desktop root and body size; use 17 px for supporting UI text.
- Keep the mobile root at 16 px and supporting text at 15 px or larger.
- Use 15 px chart tick/legend labels and 16 px chart axis titles.
- Use the approved neutral view names exactly as written in the design spec.
- Preserve the current Morandi palette and all telemetry, routing, failover, Benchmark, provenance, Demo/Live, and last-good snapshot behavior.
- Preserve the enlarged chart canvases and avoid new pages, filters, navigation levels, wrappers, sidebars, or decorative visuals.

---

### Task 1: Scientific layout primitives

**Files:**
- Modify: `tests/dashboard/test_components.py`
- Modify: `tests/dashboard/test_theme.py`
- Modify: `dashboard/components.py`
- Modify: `dashboard/theme.py`

**Interfaces:**
- Consumes: existing `escape_html(value: object) -> str` and Streamlit-safe HTML rendering.
- Produces: `brand_block_html() -> str`, two-column `page_heading_html(...) -> str`, and compact internal KPI grid markup governed by CSS areas `label`, `detail`, and `value`.

- [ ] **Step 1: Write failing component tests**

Add the following tests to `tests/dashboard/test_components.py`:

```python
from dashboard.components import brand_block_html, metric_grid_html, page_heading_html


def test_brand_block_uses_both_header_rows() -> None:
    markup = brand_block_html()
    assert 'class="brand-block"' in markup
    assert 'class="brand-title"' in markup
    assert 'class="brand-subtitle"' in markup
    assert "Operations Console" in markup
    assert "Local inference gateway" in markup


def test_page_heading_uses_scientific_two_column_structure() -> None:
    markup = page_heading_html("IGNORED", "推論閘道運行概覽", "Selected-window evidence")
    assert 'class="ops-heading"' in markup
    assert 'class="ops-title"' in markup
    assert 'class="ops-lede"' in markup
    assert "推論閘道運行概覽" in markup
    assert "Selected-window evidence" in markup


def test_metric_grid_exposes_compact_internal_regions() -> None:
    markup = metric_grid_html([("REQUEST VOLUME", "60", "1.0 req/min")])
    assert 'class="metric-label"' in markup
    assert 'class="metric-detail"' in markup
    assert 'class="metric-value"' in markup
```

- [ ] **Step 2: Write failing theme assertions**

Update `test_theme_contains_accessible_type_and_semantic_tokens` in
`tests/dashboard/test_theme.py` with these exact checks:

```python
assert "html { font-size: 18px; }" in css
assert ".ops-heading" in css
assert "grid-template-columns:minmax(0,38fr) minmax(0,62fr)" in css
assert "grid-template-areas:" in css
assert "min-height:88px" in css
assert "font-size:17px" in css
assert "font-size: 16px" in css
```

- [ ] **Step 3: Run the focused tests and verify failure**

Run:

```powershell
uv run pytest tests/dashboard/test_components.py tests/dashboard/test_theme.py -q
```

Expected: FAIL because `brand_block_html`, `.ops-heading`, the 18 px root, and KPI grid areas do not yet exist.

- [ ] **Step 4: Implement the presentation helpers**

Add to `dashboard/components.py`:

```python
def brand_block_html() -> str:
    return (
        '<div class="brand-block">'
        '<div class="brand-title">Operations Console</div>'
        '<div class="brand-subtitle">Local inference gateway</div>'
        "</div>"
    )
```

Change `page_heading_html` to emit one `ops-heading` wrapper containing the title and lede, followed
by the existing rule. Keep `escape_html` on both values and continue discarding the redundant
`kicker` argument so callers remain compatible.

- [ ] **Step 5: Implement the density and typography tokens**

Update `dashboard/theme.py` so the generated CSS includes:

```css
html { font-size: 18px; }
.block-container { max-width: 1500px; padding: .75rem 1.5rem 2rem; }
p, label, [data-testid="stMarkdownContainer"] { font-size: 18px; line-height: 1.5; }
.brand-block { min-height:3.55rem; display:flex; flex-direction:column; justify-content:flex-end; }
.brand-title { font-size:1.08rem; font-weight:820; line-height:1.2; }
.brand-subtitle { color:var(--ink-muted); font-size:.944rem; line-height:1.35; }
.ops-heading { display:grid; grid-template-columns:minmax(0,38fr) minmax(0,62fr); gap:1.5rem; align-items:end; }
.ops-title { font-size:clamp(1.75rem,2vw,2.05rem); }
.ops-lede { max-width:none; font-size:1rem; }
.source-note, .metric-label, .metric-detail, .callout-copy,
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p,
.status-card small { font-size:17px !important; }
.metric-card { min-height:88px; display:grid; grid-template-columns:minmax(0,1fr) auto;
  grid-template-areas:"label value" "detail value"; column-gap:.8rem; align-items:center; }
.metric-label { grid-area:label; }
.metric-value { grid-area:value; margin:0; }
.metric-detail { grid-area:detail; }
```

At `max-width: 860px`, stack `.ops-heading`. At `max-width: 760px`, keep `html` at 16 px, set the
supporting selectors to at least 15 px, and return `.metric-card` to `display:block` so narrow cards
remain readable.

- [ ] **Step 6: Run focused tests and commit**

Run:

```powershell
uv run pytest tests/dashboard/test_components.py tests/dashboard/test_theme.py -q
uv run ruff check dashboard/components.py dashboard/theme.py tests/dashboard/test_components.py tests/dashboard/test_theme.py
git add dashboard/components.py dashboard/theme.py tests/dashboard/test_components.py tests/dashboard/test_theme.py
git commit -m "feat: add scientific console layout primitives"
```

Expected: all focused tests and Ruff checks pass.

---

### Task 2: Compact header and scientific view copy

**Files:**
- Modify: `tests/dashboard/test_app_state.py`
- Create: `tests/dashboard/test_view_copy.py`
- Modify: `dashboard/app.py`
- Modify: `dashboard/views/overview.py`
- Modify: `dashboard/views/reliability.py`
- Modify: `dashboard/views/requests.py`
- Modify: `dashboard/views/evidence.py`

**Interfaces:**
- Consumes: `brand_block_html() -> str` from Task 1 and existing `render_page_heading` calls.
- Produces: one compact four-column desktop control row and exact neutral titles for all four views.

- [ ] **Step 1: Write failing copy and header tests**

Create `tests/dashboard/test_view_copy.py`:

```python
from pathlib import Path


def test_views_use_neutral_scientific_titles() -> None:
    expected = {
        "overview.py": "推論閘道運行概覽",
        "reliability.py": "路由與可靠性分析",
        "requests.py": "請求遙測檢視",
        "evidence.py": "Benchmark 測量證據",
    }
    root = Path("dashboard/views")
    for filename, title in expected.items():
        source = (root / filename).read_text(encoding="utf-8")
        assert title in source


def test_editorial_headlines_are_removed() -> None:
    source = "".join(path.read_text(encoding="utf-8") for path in Path("dashboard/views").glob("*.py"))
    for headline in (
        "推論系統，一眼掌握。",
        "不是漂亮圖表，是可追溯的行為。",
        "每一筆請求，都能回到證據。",
        "快，不夠。還要知道為什麼可信。",
    ):
        assert headline not in source
```

Add to `tests/dashboard/test_app_state.py`:

```python
def test_header_uses_testable_brand_block() -> None:
    source = Path("dashboard/app.py").read_text(encoding="utf-8")
    assert "brand_block_html" in source
    assert "st.columns([1.2, 0.85, 0.85, 0.42]" in source
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```powershell
uv run pytest tests/dashboard/test_app_state.py tests/dashboard/test_view_copy.py -q
```

Expected: FAIL because the current app has nested brand/controls columns and all four editorial
headlines remain.

- [ ] **Step 3: Implement the compact header**

In `dashboard/app.py`, import `brand_block_html`. Replace the nested `[1.1, 2.9]` layout with:

```python
brand, source_col, window_col, refresh_col = st.columns(
    [1.2, 0.85, 0.85, 0.42], vertical_alignment="bottom"
)
with brand:
    st.markdown(brand_block_html(), unsafe_allow_html=True)
```

Keep the existing selectbox keys, values, mode selection, window mapping, refresh semantics, radio
navigation, accessibility labels, and return tuple unchanged. Tighten only the divider margin.

- [ ] **Step 4: Replace the four view titles and ledes**

Use these exact titles and neutral descriptions:

```text
推論閘道運行概覽
彙整 request throughput、latency、routing、failover 與 Backend Health，呈現所選 observation window 的可追溯運行狀態。

路由與可靠性分析
對照 Alias routing、request-time failover、Backend Health 與 Backpressure，檢視路由決策及其失效處理。

請求遙測檢視
依 Alias、Backend、Outcome 與 Error category 篩選 request telemetry；缺失值維持未知，不以 0 取代。

Benchmark 測量證據
並列聚合結果、控制條件、測量環境與 provenance，界定 performance measurement 的適用範圍。
```

- [ ] **Step 5: Run focused tests and commit**

Run:

```powershell
uv run pytest tests/dashboard/test_app_state.py tests/dashboard/test_view_copy.py -q
uv run ruff check dashboard/app.py dashboard/views tests/dashboard/test_app_state.py tests/dashboard/test_view_copy.py
git add dashboard/app.py dashboard/views tests/dashboard/test_app_state.py tests/dashboard/test_view_copy.py
git commit -m "feat: adopt scientific console copy and header"
```

Expected: focused tests and Ruff pass; all view titles are neutral and no editorial headline remains.

---

### Task 3: Chart typography and bounded visual verification

**Files:**
- Modify: `tests/dashboard/test_charts.py`
- Modify: `dashboard/charts.py`
- Modify: `docs/superpowers/plans/2026-08-13-scientific-console-density.md`

**Interfaces:**
- Consumes: existing `chart_theme() -> dict` and all chart helpers using `style_chart`.
- Produces: 15 px tick/legend labels and 16 px axis titles across every shared Altair chart.

- [ ] **Step 1: Raise the failing chart assertions**

Update `test_chart_theme_has_readable_axes_and_legend`:

```python
assert config["axis"]["labelFontSize"] >= 15
assert config["axis"]["titleFontSize"] >= 16
assert config["legend"]["labelFontSize"] >= 15
assert config["legend"]["titleFontSize"] >= 15
```

Update the final line-chart assertion to require `labelFontSize >= 15`.

- [ ] **Step 2: Run the chart tests and verify failure**

Run:

```powershell
uv run pytest tests/dashboard/test_charts.py -q
```

Expected: FAIL because the current shared chart theme uses 14 px labels and 15 px axis titles.

- [ ] **Step 3: Implement the shared chart type floor**

In `dashboard/charts.py`, set axis `labelFontSize` to `15`, axis `titleFontSize` to `16`, legend
`labelFontSize` to `15`, and legend `titleFontSize` to `15`. Do not alter chart heights, marks,
scales, colors, or data encodings.

- [ ] **Step 4: Run automated verification**

Run:

```powershell
uv run pytest tests/dashboard -q
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv run python scripts/check_publication.py
uv run python scripts/check_evidence.py
uv run python scripts/check_documents.py
uv run python scripts/check_docker_release.py
```

Expected: all dashboard tests, full repository tests, Ruff checks, and release checks pass.

- [ ] **Step 5: Perform one bounded browser inspection**

Open the local Streamlit app at `http://127.0.0.1:8501/`. Inspect all four views at desktop width
and 390 px mobile width in one pass. Verify:

- the brand block has no empty top row;
- page title and lede occupy both sides of the desktop heading row;
- Overview KPI cards use left/right space and are 88 px tall;
- supporting text and chart labels are comfortably readable;
- charts retain their enlarged canvases;
- no horizontal overflow, Streamlit exception, or browser console error appears.

Apply one batched correction if the inspection exposes defects, then perform one confirmation pass.
Do not start an open-ended polish loop.

- [ ] **Step 6: Commit verified implementation**

Mark completed plan checkboxes, then run:

```powershell
git add dashboard/charts.py tests/dashboard/test_charts.py docs/superpowers/plans/2026-08-13-scientific-console-density.md
git commit -m "fix: improve scientific console legibility"
git status --short
```

Expected: commit succeeds and the worktree is clean.
