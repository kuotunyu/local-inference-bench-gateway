# Activity Chart Mark Weight Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the Overview request Bars and P95 latency line visibly heavier while preserving responsive separation and all chart semantics.

**Architecture:** Keep the change inside the existing Altair chart builder in `dashboard/views/overview.py`. Lock the approved visual constants through generated-spec tests in `tests/dashboard/test_view_models.py`, including the existing 7-, 37-, and 145-bucket density cases.

**Tech Stack:** Python 3.12, Altair, pandas, pytest, Ruff, Streamlit.

## Global Constraints

- Raise the request Bar desktop maximum from 46 px to 54 px.
- Raise the responsive Bar density multiplier from 0.72 to 0.82.
- Raise the P95 latency line from 4 px to 5 px.
- Raise the P95 point area from 96 to 120 and retain its two-pixel stroke.
- Preserve colors, opacity, five-minute domain padding, adaptive ticks, independent Y scales, chart height, tooltips, telemetry, aggregation, and evidence semantics.
- Retain bucket-count-aware scaling for 6-hour and 24-hour series.

---

### Task 1: Increase Activity Mark Weight

**Files:**
- Modify: `tests/dashboard/test_view_models.py`
- Modify: `dashboard/views/overview.py`
- Modify: `docs/superpowers/plans/2026-08-13-chart-mark-weight.md`

**Interfaces:**
- Consumes: `build_activity_chart(series: pd.DataFrame) -> alt.Chart` and its valid bucket count.
- Produces: an Altair Bar mark sized by `min(54, width / bucket_slots * 0.82)` and a P95 line with five-pixel stroke and 120-area points.

- [ ] **Step 1: Update generated-spec expectations**

In `tests/dashboard/test_view_models.py`, change the seven-bucket expectation to:

```python
assert bar["mark"]["size"] == {"expr": "min(54, width / 9 * 0.82)"}
assert line["mark"]["strokeWidth"] == 5
assert line["mark"]["point"]["size"] == 120
```

Change the density expectations to:

```python
assert spec["layer"][0]["mark"]["size"] == {"expr": "min(54, width / 39 * 0.82)"}
assert spec["layer"][0]["mark"]["size"] == {"expr": "min(54, width / 147 * 0.82)"}
```

- [ ] **Step 2: Run the focused tests and verify RED**

Run:

```powershell
uv run pytest tests/dashboard/test_view_models.py -q
```

Expected: the chart mark assertions fail because production still emits a 46 px maximum, 0.72 density multiplier, four-pixel line, and 96-area points.

- [ ] **Step 3: Apply the approved Altair mark constants**

In `dashboard/views/overview.py`, update the Bar size expression and line mark:

```python
size=alt.ExprRef(expr=f"min(54, width / {bucket_slots} * 0.82)"),
```

```python
strokeWidth=5,
point=alt.OverlayMarkDef(color="#B56F45", size=120, filled=True, strokeWidth=2),
```

Do not change either mark's color, opacity, encoding, scales, axes, or tooltip.

- [ ] **Step 4: Run focused verification**

Run:

```powershell
uv run pytest tests/dashboard/test_view_models.py -q
uv run ruff check dashboard/views/overview.py tests/dashboard/test_view_models.py
uv run ruff format --check dashboard/views/overview.py tests/dashboard/test_view_models.py
```

Expected: all focused tests and Ruff checks pass.

- [ ] **Step 5: Run complete repository verification**

Run:

```powershell
uv run pytest tests/dashboard -q
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv run --frozen python -m release_checks.cli
```

Expected: dashboard and full tests, Ruff, and all publication/evidence/document/docker checks pass.

- [ ] **Step 6: Restart and inspect the branch preview once**

Restart Streamlit at `http://127.0.0.1:8502/`. Inspect Overview at desktop and 390 px. Confirm that Bars and the P95 line are visibly heavier, Bars remain separated, axes remain readable, no horizontal overflow appears, and no Streamlit exception is rendered.

- [ ] **Step 7: Record verification and commit**

Append the actual test counts and browser result under an `Execution Notes` heading in this plan, then run:

```powershell
git add dashboard/views/overview.py tests/dashboard/test_view_models.py docs/superpowers/plans/2026-08-13-chart-mark-weight.md
git commit -m "feat: strengthen activity chart marks"
git status --short
```

Expected: the commit succeeds and the worktree is clean.
