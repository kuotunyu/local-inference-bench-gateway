# Instrument Chart & Flat Surface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve the Overview activity chart's time scale and visual weight while replacing card-everywhere styling with a flatter scientific surface hierarchy.

**Architecture:** Keep chart-domain logic inside `dashboard/views/overview.py` as a deterministic presentation helper and keep reusable surface language inside `dashboard/theme.py`. Test chart behavior through generated Altair specs and direct time-guide values; test CSS contracts through the existing theme builder, then verify the rendered Streamlit app at desktop and mobile widths.

**Tech Stack:** Python 3.12, pandas, Altair, Streamlit, pytest, Ruff, embedded CSS.

## Global Constraints

- Preserve 10-minute aggregation buckets and all telemetry values.
- Add five minutes of temporal domain padding before and after the data.
- Select X-axis intervals from `10 min`, `30 min`, `1 h`, `2 h`, `4 h`, `6 h`, `12 h`, `1 d`, `2 d`, `7 d`, targeting approximately seven ticks.
- Use 46 px bars at 0.90 opacity with `#5F7F6B`; use a 4 px P95 line with `#B56F45`, 96 px points, and a 2 px point stroke.
- Preserve independent Y scales, the 400 px chart height, tooltips, observation-window behavior, and all data semantics.
- Keep boundaries only for inputs, buttons, data frames, expanders, source badges, and semantic state callouts.
- Preserve desktop and 390 px mobile layouts without horizontal overflow.

---

### Task 1: Deterministic activity-chart time guide and marks

**Files:**
- Modify: `tests/dashboard/test_view_models.py`
- Modify: `dashboard/views/overview.py`

**Interfaces:**
- Produces: `ActivityTimeGuide(domain: tuple[datetime, datetime], ticks: tuple[datetime, ...])`.
- Produces: `_activity_time_guide(frame: pd.DataFrame) -> ActivityTimeGuide`.
- Consumes: the current `timestamp`, `requests`, and `p95_latency_ms` series produced by `bucket_request_series`.

- [ ] **Step 1: Add failing tests for domain padding and adaptive ticks**

Add to `tests/dashboard/test_view_models.py`:

```python
from datetime import timedelta

import pandas as pd

from dashboard.views.overview import _activity_time_guide


def test_activity_time_guide_pads_half_a_bucket_and_uses_ten_minute_ticks() -> None:
    frame = pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-08-13T00:40:00Z", periods=7, freq="10min"),
            "requests": [5, 10, 10, 10, 10, 10, 5],
            "p95_latency_ms": [180, 280, 380, 460, 560, 650, 700],
        }
    )

    guide = _activity_time_guide(frame)

    assert guide.domain[0] == frame["timestamp"].iloc[0].to_pydatetime() - timedelta(minutes=5)
    assert guide.domain[1] == frame["timestamp"].iloc[-1].to_pydatetime() + timedelta(minutes=5)
    assert guide.ticks == tuple(frame["timestamp"].dt.to_pydatetime())


def test_activity_time_guide_uses_one_hour_ticks_for_six_hours() -> None:
    frame = pd.DataFrame(
        {
            "timestamp": pd.date_range("2026-08-13T00:10:00Z", periods=37, freq="10min"),
        }
    )

    guide = _activity_time_guide(frame)

    assert [tick.minute for tick in guide.ticks] == [0] * 6
    assert [tick.hour for tick in guide.ticks] == [1, 2, 3, 4, 5, 6]
```

- [ ] **Step 2: Strengthen the existing Altair-spec test**

Extend `test_overview_activity_chart_uses_full_operational_canvas` with:

```python
bar, line = spec["layer"]
assert bar["mark"]["size"] == 46
assert bar["mark"]["color"] == "#5F7F6B"
assert bar["mark"]["opacity"] == 0.9
assert line["mark"]["strokeWidth"] == 4
assert line["mark"]["color"] == "#B56F45"
assert line["mark"]["point"]["size"] == 96
assert line["mark"]["point"]["strokeWidth"] == 2
assert bar["encoding"]["x"]["scale"] == line["encoding"]["x"]["scale"]
assert bar["encoding"]["x"]["axis"]["tickSize"] == 6
assert bar["encoding"]["x"]["axis"]["labelOverlap"] == "greedy"
```

- [ ] **Step 3: Run the tests and verify RED**

Run:

```powershell
uv run pytest tests/dashboard/test_view_models.py -q
```

Expected: collection fails because `ActivityTimeGuide` and `_activity_time_guide` do not exist, or
the existing chart-spec assertions fail against 34 px bars and a 3 px line.

- [ ] **Step 4: Implement the time guide**

Add to `dashboard/views/overview.py`:

```python
ACTIVITY_INTERVALS = tuple(
    pd.Timedelta(value)
    for value in (
        "10min",
        "30min",
        "1h",
        "2h",
        "4h",
        "6h",
        "12h",
        "1d",
        "2d",
        "7d",
    )
)
ACTIVITY_DOMAIN_PADDING = pd.Timedelta(minutes=5)


@dataclass(frozen=True)
class ActivityTimeGuide:
    domain: tuple[datetime, datetime]
    ticks: tuple[datetime, ...]


def _activity_time_guide(frame: pd.DataFrame) -> ActivityTimeGuide:
    timestamps = pd.to_datetime(frame.get("timestamp"), utc=True, errors="coerce").dropna()
    if timestamps.empty:
        raise ValueError("activity chart requires a valid timestamp")
    start = timestamps.min()
    end = timestamps.max()
    target = max((end - start) / 6, ACTIVITY_INTERVALS[0])
    interval = next(
        (candidate for candidate in ACTIVITY_INTERVALS if candidate >= target),
        ACTIVITY_INTERVALS[-1],
    )
    tick_start = start.ceil(interval)
    ticks = tuple(pd.date_range(tick_start, end, freq=interval).to_pydatetime())
    if not ticks:
        ticks = (start.to_pydatetime(),)
    return ActivityTimeGuide(
        domain=(
            (start - ACTIVITY_DOMAIN_PADDING).to_pydatetime(),
            (end + ACTIVITY_DOMAIN_PADDING).to_pydatetime(),
        ),
        ticks=ticks,
    )
```

- [ ] **Step 5: Apply one synchronized X encoding and stronger marks**

Inside `build_activity_chart`, drop invalid timestamps and build one `ActivityTimeGuide`. Apply its
domain with `alt.Scale(domain=list(guide.domain), nice=False)` to both layers. Configure both X axes
with `format="%H:%M"`, `labelAngle=0`, `labelOverlap="greedy"`, `tickSize=6`,
`tickWidth=1.25`, and `values=list(guide.ticks)`. Use the exact bar, line, and point values from the
Global Constraints.

- [ ] **Step 6: Run focused verification and commit**

Run:

```powershell
uv run pytest tests/dashboard/test_view_models.py -q
uv run ruff check dashboard/views/overview.py tests/dashboard/test_view_models.py
uv run ruff format --check dashboard/views/overview.py tests/dashboard/test_view_models.py
git add dashboard/views/overview.py tests/dashboard/test_view_models.py
git commit -m "feat: refine activity chart time scale"
```

Expected: focused tests and Ruff pass.

---

### Task 2: Flat scientific surface hierarchy

**Files:**
- Modify: `tests/dashboard/test_theme.py`
- Modify: `dashboard/theme.py`

**Interfaces:**
- Consumes: existing `.metric-grid`, `.metric-card`, `.status-card`, `.callout`, Streamlit radio,
  data-frame, expander, button, and BaseWeb select selectors.
- Produces: one KPI instrument rail, flat status rows, borderless navigation, and reduced retained
  radii.

- [ ] **Step 1: Add failing theme-contract assertions**

Add a separate test to `tests/dashboard/test_theme.py`:

```python
def test_theme_uses_flat_instrument_surfaces() -> None:
    css = build_theme_css()

    assert ".metric-grid" in css and "border-top:1px solid var(--border)" in css
    assert "border-bottom:1px solid var(--border)" in css
    assert ".metric-card" in css and "border-radius:0" in css
    assert "box-shadow:none" in css
    assert ".status-card" in css and "background:transparent" in css
    assert 'div[role="radiogroup"]' in css and "border:0" in css
    assert '[data-testid="stDataFrame"]' in css and "border-radius:4px" in css
    assert '[data-testid="stExpander"]' in css and "border-radius:4px" in css
    assert ".stButton button" in css and "border-radius:6px" in css
```

- [ ] **Step 2: Run the test and verify RED**

Run:

```powershell
uv run pytest tests/dashboard/test_theme.py::test_theme_uses_flat_instrument_surfaces -q
```

Expected: FAIL because the current KPI, status, and navigation containers use 13--14 px radii,
borders, surfaces, and shadows.

- [ ] **Step 3: Implement the desktop surface hierarchy**

Update `dashboard/theme.py`:

```css
.metric-grid {
  gap:0;
  border-top:1px solid var(--border);
  border-bottom:1px solid var(--border);
}
.metric-card {
  border:0;
  border-left:1px solid var(--border);
  border-radius:0;
  background:transparent;
  box-shadow:none;
}
.metric-card:first-child { border-left:0; }
.status-card {
  padding:.75rem .15rem;
  border:0;
  border-bottom:1px solid var(--border);
  border-radius:0;
  background:transparent;
}
div[role="radiogroup"] { border:0; border-radius:0; background:transparent; padding:0; }
div[role="radiogroup"] label { border-radius:0; border-bottom:2px solid transparent; }
div[role="radiogroup"] label:has(input:checked) {
  background:rgba(113,139,122,.10);
  border-bottom-color:var(--healthy);
}
.callout { border-radius:4px; }
[data-testid="stDataFrame"], [data-testid="stExpander"] { border-radius:4px; }
.stButton button, .stDownloadButton button { border-radius:6px; }
div[data-baseweb="select"] > div { border-radius:6px; }
```

Do not change source-badge pills, status-dot circles, semantic callout colors, data-frame borders,
expander borders, focus outlines, or minimum control heights.

- [ ] **Step 4: Implement mobile separator logic**

Inside the existing `max-width:760px` media query, keep two KPI columns but set `gap:0`. Remove
left borders from odd children, retain left borders on even children, and add a top border to every
card after the first row:

```css
.metric-card:nth-child(odd) { border-left:0; }
.metric-card:nth-child(even) { border-left:1px solid var(--border); }
.metric-card:nth-child(n+3) { border-top:1px solid var(--border); }
```

- [ ] **Step 5: Run focused verification and commit**

Run:

```powershell
uv run pytest tests/dashboard/test_theme.py -q
uv run ruff check dashboard/theme.py tests/dashboard/test_theme.py
uv run ruff format --check dashboard/theme.py tests/dashboard/test_theme.py
git add dashboard/theme.py tests/dashboard/test_theme.py
git commit -m "feat: flatten console surface hierarchy"
```

Expected: focused tests and Ruff pass.

---

### Task 3: Full verification and bounded browser inspection

**Files:**
- Modify: `docs/superpowers/plans/2026-08-13-instrument-chart-surface.md`

**Interfaces:**
- Consumes: Tasks 1 and 2 as one rendered Streamlit surface.
- Produces: verified desktop/mobile behavior and a clean integration branch.

- [ ] **Step 1: Run complete automated verification**

Run:

```powershell
uv run pytest tests/dashboard -q
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv run --frozen python -m release_checks.cli
```

Expected: all dashboard and repository tests, Ruff checks, and publication/evidence/document/docker
checks pass.

- [ ] **Step 2: Run the Impeccable detector once**

Run:

```powershell
node C:\Users\3Hml\.codex\skills\impeccable\scripts\detect.mjs --json dashboard/theme.py dashboard/views/overview.py
```

Expected: no unexplained findings.

- [ ] **Step 3: Inspect all views in one browser pass**

Restart the branch Streamlit process so imported Python modules are fresh. Inspect Overview,
Routing & Reliability, Requests, and Benchmark Evidence at desktop width and 390 px mobile. Verify:

- first and last bars have visible half-bucket plot padding;
- the 60-minute view displays 10-minute tick marks and readable labels;
- bars, line, and points are visibly stronger without obscuring grid or tooltips;
- KPI metrics read as one rail, not five cards;
- navigation and status rows are flat while controls, callouts, tables, and expanders retain useful
  boundaries;
- page `scrollWidth == clientWidth`, no Streamlit exception appears, and no new console error is
  introduced.

- [ ] **Step 4: Apply at most one batched correction and confirm once**

If the inspection exposes defects, write the smallest failing regression test, implement one
batched correction, rerun the focused and complete checks, restart Streamlit, and perform one
confirmation pass. Do not enter an open-ended polish loop.

- [ ] **Step 5: Document execution notes and commit**

Record any justified plan deviation or known pre-existing browser warning in this plan, then run:

```powershell
git add docs/superpowers/plans/2026-08-13-instrument-chart-surface.md
git commit -m "docs: record instrument surface verification"
git status --short
```

Expected: commit succeeds and the worktree is clean.
