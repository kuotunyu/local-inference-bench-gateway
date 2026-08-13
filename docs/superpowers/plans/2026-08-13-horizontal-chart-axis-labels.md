# Horizontal Chart Axis Labels Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace both rotated Y-axis titles in the Overview activity chart with a readable horizontal measure key while preserving its independent numeric axes.

**Architecture:** Keep `build_activity_chart()` responsible for quantitative encodings and remove only its axis-title strings. Add one small presentation helper in the same Overview view for the horizontal key, styled by existing theme tokens so its green bar and orange line correspond to the chart marks without introducing another container.

**Tech Stack:** Python 3.12, Streamlit, Altair, HTML/CSS theme tokens, pytest, Streamlit AppTest.

## Global Constraints

- Preserve all telemetry queries, aggregation, bucketing, domains, ticks, scales, tooltips, mark weights, and observation-window behavior.
- Keep left numeric ticks for Request volume and right numeric ticks for P95 latency.
- Do not render either measure as a rotated Y-axis title.
- Render `Request 數量／bucket` on the left and `P95 latency／ms` on the right with both color and mark-shape cues.
- Do not add a bordered card, rounded container, dependency, or JavaScript.
- Keep the key legible and free of horizontal overflow at 734 px and 390 px.

---

### Task 1: Replace Rotated Titles With a Horizontal Measure Key

**Files:**
- Modify: `tests/dashboard/test_view_models.py`
- Modify: `tests/dashboard/test_dashboard_smoke.py`
- Modify: `tests/dashboard/test_theme.py`
- Modify: `dashboard/views/overview.py`
- Modify: `dashboard/theme.py`

**Interfaces:**
- Consumes: `build_activity_chart(series: pd.DataFrame) -> alt.Chart`, existing Overview render flow, and CSS tokens `--healthy`, `--warning`, and `--ink-muted`.
- Produces: `activity_measure_key_html() -> str`, an HTML row rendered immediately before the Altair chart; the chart continues returning the same layered Altair object with independent Y scales.

- [ ] **Step 1: Write failing chart and render-contract tests**

Update the existing activity-chart test to require horizontal-only axis labeling:

```python
assert bar["encoding"]["y"]["title"] is None
assert line["encoding"]["y"]["title"] is None
assert line["encoding"]["y"]["axis"]["orient"] == "right"
```

Add the rendered labels to the Overview smoke expectations:

```python
"Request 數量／bucket",
"P95 latency／ms",
```

Add a theme contract asserting `.activity-measure-key`, `.activity-key-bar`, and
`.activity-key-line` exist, and that the key uses two flexible columns rather than a container
border.

- [ ] **Step 2: Run focused tests and verify RED**

Run:

```powershell
uv run pytest tests/dashboard/test_view_models.py::test_overview_activity_chart_uses_full_operational_canvas tests/dashboard/test_dashboard_smoke.py::test_operational_views_use_zh_tw_first_copy tests/dashboard/test_theme.py::test_theme_uses_flat_instrument_surfaces -q
```

Expected: the chart assertions fail because both Y-axis titles still contain text, and the rendered/CSS assertions fail because the horizontal key does not exist.

- [ ] **Step 3: Add the minimal horizontal key and remove axis titles**

In `dashboard/views/overview.py`, add:

```python
def activity_measure_key_html() -> str:
    return (
        '<div class="activity-measure-key">'
        '<span class="activity-key-item request"><i class="activity-key-bar"></i>'
        "Request 數量／bucket</span>"
        '<span class="activity-key-item latency"><i class="activity-key-line"></i>'
        "P95 latency／ms</span>"
        "</div>"
    )
```

Set both `alt.Y(..., title=None, ...)` values, retaining the right-axis orientation on latency.
Render the key with `st.markdown(activity_measure_key_html(), unsafe_allow_html=True)` immediately
before `st.altair_chart(...)`.

In `dashboard/theme.py`, add a flat flex/grid row using the existing chart colors `#5F7F6B` and
`#B56F45`. Use a rectangular bar swatch and a horizontal line swatch; align the latency item to the
right, allow text wrapping, and keep at least 15 px type on mobile.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run the focused command from Step 2.

Expected: PASS with both numeric axes intact, no axis titles, both labels rendered, and theme rules present.

- [ ] **Step 5: Run full automated verification**

Run:

```powershell
uv run pytest tests/dashboard -q
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv run --frozen python -m release_checks.cli
git diff --check
```

Expected: every command exits 0.

- [ ] **Step 6: Inspect the rendered result in one bounded browser pass**

Restart the branch preview at `http://127.0.0.1:8502/`. At 734 px and 390 px verify:

- neither rotated Y-axis title is present;
- the green bar label appears above the left scale and the orange line label above the right scale;
- numeric ticks, Bar, line, points, tooltip interaction, and X-axis spacing remain visible;
- no horizontal overflow, clipping, or Streamlit exception occurs.

Apply at most one bounded correction, then confirm once.

- [ ] **Step 7: Run the Impeccable detector and commit**

Run once after UI changes are complete:

```powershell
node C:\Users\3Hml\.codex\skills\impeccable\scripts\detect.mjs --json dashboard/views/overview.py dashboard/theme.py
```

Resolve any relevant finding, rerun the affected tests, then commit:

```powershell
git add dashboard/views/overview.py dashboard/theme.py tests/dashboard/test_view_models.py tests/dashboard/test_dashboard_smoke.py tests/dashboard/test_theme.py docs/superpowers/plans/2026-08-13-horizontal-chart-axis-labels.md
git commit -m "fix: replace rotated chart labels"
```

Leave the verified `8502` preview open on `系統總覽` for the next UI review.
