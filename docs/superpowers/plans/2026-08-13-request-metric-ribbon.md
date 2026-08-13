# Request Metric Ribbon Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the seven-metric Request summary into a compact, readable instrumentation ribbon.

**Architecture:** Keep the shared metric HTML unchanged and use its existing `metric-count-7` class as
the scope. Add count-specific layout rules in the theme so other pages retain their approved metric
structure.

**Tech Stack:** Streamlit HTML, CSS, pytest, browser inspection.

## Global Constraints

- Keep all seven values and supporting details unchanged.
- Keep desktop supporting text at 17 px and mobile supporting text at 15 px.
- Add no new container, shadow, radius, dependency, or data transformation.

---

### Task 1: Compact Seven-Metric Ribbon

**Files:**
- Modify: `dashboard/theme.py`
- Modify: `tests/dashboard/test_theme.py`

**Interfaces:**
- Consumes: `.metric-grid.metric-count-7` and its `.metric-card`, `.metric-label`, `.metric-value`, and `.metric-detail` descendants.
- Produces: a vertical seven-cell ribbon at desktop, four-plus-three below 1320 px, and two columns below 760 px.

- [x] **Step 1: Write a failing theme contract test**

Assert that `.metric-count-7 .metric-card` uses a single-column grid, compact minimum height, and
that its labels use `white-space:nowrap` without any `word-break` rule.

- [x] **Step 2: Verify RED**

Run `uv run pytest tests/dashboard/test_theme.py::test_seven_metric_ribbon_uses_vertical_density -q`.
Expected: FAIL because the count-specific layout does not exist.

- [x] **Step 3: Implement the count-specific CSS**

Add a vertical grid-area override for `.metric-count-7 .metric-card`, tighten row spacing, prevent
intra-word label wrapping, and add responsive height overrides inside the existing media queries.

- [x] **Step 4: Verify GREEN and the rendered page**

Run the focused test, then inspect Request records at `http://127.0.0.1:8501/`. Confirm all seven
values are visible, the ribbon is materially shorter, labels do not split, and the table begins
immediately after the summary.

- [x] **Step 5: Run full verification and commit**

Run `uv run pytest -q`, Ruff lint/format, release checks, detector, and `git diff --check`, then commit
the scoped files.
