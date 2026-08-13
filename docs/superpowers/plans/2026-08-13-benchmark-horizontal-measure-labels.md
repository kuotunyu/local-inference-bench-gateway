# Benchmark Horizontal Measure Labels Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove all six rotated quantitative Y-axis titles from the Benchmark Evidence page and replace them with the approved horizontal measure-label pattern.

**Architecture:** Promote the Overview-specific key into `dashboard.components.chart_measure_key_html()` so Overview and Benchmark render the same accessible mark/label system. Benchmark chart builders remove only their `y_title` values; render flow inserts a one-item key immediately before each successfully rendered chart, preserving missing-Artifact states and all quantitative encodings.

**Tech Stack:** Python 3.12, Streamlit, Altair, HTML/CSS theme tokens, pytest, Streamlit AppTest.

## Global Constraints

- Preserve all benchmark frames, derived values, fields, scales, zero baselines, heights, legends, marks, tooltips, captions, and Artifact guards.
- Every quantitative Benchmark Y-axis title must be `None`; numeric tick labels remain visible.
- Render `Throughput／tok/s`, `TTFT／ms`, `Median TTFT／s`, `Latency／ms`, `VRAM baseline／MiB`, and `P50 TTFT／ms` only when their charts render.
- A line or bar swatch must identify the chart mark type; engine and series legends remain unchanged.
- Labels must be HTML escaped; decorative swatches must use `aria-hidden="true"`; invalid mark or tone values raise `ValueError`.
- Keep the component flat, at least 15 px on mobile, and free of horizontal overflow.
- Do not add a dependency or alter backend, telemetry, or benchmark semantics.

---

### Task 1: Shared Horizontal Measure-Key Component

**Files:**
- Modify: `tests/dashboard/test_components.py`
- Modify: `tests/dashboard/test_theme.py`
- Modify: `tests/dashboard/test_view_models.py`
- Modify: `dashboard/components.py`
- Modify: `dashboard/theme.py`
- Modify: `dashboard/views/overview.py`

**Interfaces:**
- Produces: `ChartMeasure = tuple[str, str, str]` containing `(mark, tone, label)` and `chart_measure_key_html(measures: list[ChartMeasure]) -> str`.
- Valid marks: `bar`, `line`. Valid tones: `request`, `latency`, `neutral`.
- Consumed by: Overview and Benchmark view render paths.

- [ ] **Step 1: Write failing component and Overview compatibility tests**

Add component tests:

```python
def test_chart_measure_key_maps_marks_and_escapes_labels() -> None:
    markup = chart_measure_key_html(
        [("bar", "request", "Request <count>"), ("line", "latency", "P95 / ms")]
    )
    assert 'class="chart-measure-key chart-key-count-2"' in markup
    assert 'class="chart-key-bar" aria-hidden="true"' in markup
    assert 'class="chart-key-line" aria-hidden="true"' in markup
    assert "Request &lt;count&gt;" in markup
    assert "Request <count>" not in markup


def test_chart_measure_key_rejects_unknown_mark_or_tone() -> None:
    with pytest.raises(ValueError):
        chart_measure_key_html([("area", "neutral", "Throughput")])
    with pytest.raises(ValueError):
        chart_measure_key_html([("line", "danger", "Throughput")])
```

Update the theme test to require the generic `.chart-measure-key`, `.chart-key-item`,
`.chart-key-bar`, and `.chart-key-line` selectors, their one/two-column layout, `min-width:0`, flat
surface, and the exact mobile 15 px rule. Keep the existing Overview rendered labels and chart-spec
assertions unchanged.

- [ ] **Step 2: Run focused tests and verify RED**

Run:

```powershell
uv run pytest tests/dashboard/test_components.py tests/dashboard/test_theme.py tests/dashboard/test_view_models.py::test_overview_activity_chart_uses_full_operational_canvas tests/dashboard/test_dashboard_smoke.py::test_operational_views_use_zh_tw_first_copy -q
```

Expected: collection or assertion failure because the shared helper and generic theme selectors do not exist.

- [ ] **Step 3: Implement the shared component and preserve Overview rendering**

In `dashboard/components.py`, validate the finite mark/tone vocabulary, escape labels, add
`aria-hidden="true"`, and emit one flat key row. In `dashboard/theme.py`, rename the activity-only
selectors to generic chart-key selectors and provide:

```css
.chart-measure-key { display:grid; grid-template-columns:repeat(var(--chart-key-columns),minmax(0,1fr)); }
.chart-key-count-1 { --chart-key-columns:1; }
.chart-key-count-2 { --chart-key-columns:2; }
.chart-key-item { display:flex; align-items:center; min-width:0; }
.chart-key-count-2 .chart-key-item:last-child { justify-content:flex-end; text-align:right; }
```

Retain the existing green/orange Overview tones, add a neutral evidence tone using `--ink-muted`,
and keep the existing bar/line swatch geometry. Import and render the shared helper in Overview;
delete its local `activity_measure_key_html()`.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run the command from Step 2. Expected: PASS with Overview visually and semantically unchanged.

- [ ] **Step 5: Commit the shared component**

```powershell
git add dashboard/components.py dashboard/theme.py dashboard/views/overview.py tests/dashboard/test_components.py tests/dashboard/test_theme.py tests/dashboard/test_view_models.py tests/dashboard/test_dashboard_smoke.py
git commit -m "refactor: share chart measure keys"
```

---

### Task 2: Benchmark Horizontal Labels

**Files:**
- Modify: `tests/dashboard/test_evidence_view.py`
- Modify: `tests/dashboard/test_dashboard_smoke.py`
- Modify: `tests/dashboard/test_zh_tw_state_copy.py`
- Modify: `dashboard/views/evidence.py`
- Modify: `docs/superpowers/plans/2026-08-13-benchmark-horizontal-measure-labels.md`

**Interfaces:**
- Consumes: `chart_measure_key_html(measures: list[ChartMeasure]) -> str`.
- Preserves: all six existing Benchmark chart-builder function signatures and return types.

- [ ] **Step 1: Write failing chart-spec and rendered-state tests**

For all six builders, assert `spec["encoding"]["y"]["title"] is None` while retaining the existing
height, field, legend, and zero-scale assertions. Add all six horizontal labels to the normal
Benchmark smoke expectations. In the missing-evidence AppTest, assert none of those labels appears,
proving labels follow chart availability rather than headings alone.

- [ ] **Step 2: Run focused tests and verify RED**

Run:

```powershell
uv run pytest tests/dashboard/test_evidence_view.py tests/dashboard/test_dashboard_smoke.py::test_benchmark_evidence_uses_zh_tw_first_copy tests/dashboard/test_zh_tw_state_copy.py::test_missing_evidence_uses_zh_tw_warning_heading -q
```

Expected: chart specs still expose six Y-axis titles and normal rendering lacks the six horizontal labels.

- [ ] **Step 3: Remove Y-axis titles and render keys only beside available charts**

Pass `y_title=None` in every Benchmark chart builder. Immediately before each `st.altair_chart`,
render the matching one-item neutral key:

```python
st.markdown(
    chart_measure_key_html([("line", "neutral", "Throughput／tok/s")]),
    unsafe_allow_html=True,
)
```

Use `bar` for Prefill, Gateway cost, and VRAM; use `line` for Throughput, TTFT, and KV control.
Keep each key inside the same availability branch as its chart.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run the command from Step 2. Expected: PASS with six title-free quantitative axes, six labels in the valid fixture, and no orphaned labels in the missing fixture.

- [ ] **Step 5: Run complete automated verification**

```powershell
uv run pytest tests/dashboard -q
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv run --frozen python -m release_checks.cli
git diff --check
```

Expected: every command exits 0.

- [ ] **Step 6: Inspect Benchmark Evidence in one bounded browser pass**

Restart `http://127.0.0.1:8502/`, open `Benchmark 證據`, and inspect the full page. Verify every
rendered plot has a horizontal label and no rotated quantitative title, legends remain distinct,
numeric ticks remain visible, and no overflow, clipping, or Streamlit exception appears. Apply at
most one correction and confirm once.

- [ ] **Step 7: Run the Impeccable detector and commit**

```powershell
node "$env:USERPROFILE\.codex\skills\impeccable\scripts\detect.mjs" --json dashboard/components.py dashboard/theme.py dashboard/views/overview.py dashboard/views/evidence.py
git add dashboard/views/evidence.py tests/dashboard/test_evidence_view.py tests/dashboard/test_dashboard_smoke.py tests/dashboard/test_zh_tw_state_copy.py docs/superpowers/plans/2026-08-13-benchmark-horizontal-measure-labels.md
git commit -m "fix: replace benchmark axis titles"
```

Leave the verified `8502` preview open on `Benchmark 證據` for continued UI review.
