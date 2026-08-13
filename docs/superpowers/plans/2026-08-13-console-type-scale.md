# Console Type Scale Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Raise undersized typography across the Operations Console by 2–4 px while preserving hierarchy and responsive density.

**Architecture:** Treat typography as named presentation roles. Update the shared CSS theme for UI,
metadata, DataFrame, and mobile roles; update the shared Altair theme for chart roles. Keep headings,
metric values, data, and application behavior unchanged.

**Tech Stack:** Streamlit, CSS, Altair, pytest, browser inspection.

## Global Constraints

- Desktop body remains 18 px; supporting UI text becomes 19 px.
- DataFrame headers and cells become 17 px.
- Chart axes and legends become 18 px.
- Mobile body becomes 18 px; mobile supporting text becomes 17 px.
- Do not change factual copy, metric values, data processing, chart encodings, or table interactions.
- Do not add a font family, container, border, radius, shadow, or dependency.

---

### Task 1: Raise Shared UI and Data Typography

**Files:**
- Modify: `tests/dashboard/test_theme.py`
- Modify: `dashboard/theme.py`

**Interfaces:**
- Consumes: `build_theme_css() -> str` and existing semantic selectors.
- Produces: 19 px desktop supporting roles, 17 px DataFrame roles, and 18/17 px mobile roles.

- [ ] Write failing assertions for every new CSS role floor and the Request ribbon overflow guard.
- [ ] Run the focused theme tests and confirm they fail on the old 15–17 px values.
- [ ] Update shared role sizes, inline code, DataFrame variables, mobile overrides, and Request-ribbon spacing/breakpoint without reducing type.
- [ ] Run focused tests and confirm they pass.

### Task 2: Raise Chart Typography

**Files:**
- Modify: `tests/dashboard/test_charts.py`
- Modify: `dashboard/charts.py`

**Interfaces:**
- Consumes: `chart_theme() -> dict`.
- Produces: 18 px axis labels/titles and legend labels/titles for every Altair chart.

- [ ] Write failing chart-theme assertions for the 18 px floor.
- [ ] Run the focused chart tests and confirm they fail on the old 15–16 px values.
- [ ] Update only shared chart typography tokens.
- [ ] Run focused tests and confirm they pass without changing chart data or encodings.

### Task 3: Render and Verify

**Files:**
- Modify: this plan to record completed steps.

**Interfaces:**
- Consumes: the shared Streamlit and Altair type roles from Tasks 1–2.
- Produces: a verified preview at `http://127.0.0.1:8501/`.

- [ ] Inspect Request, Benchmark, Overview, and Routing at wide and ordinary widths in one bounded browser pass.
- [ ] Confirm no horizontal overflow, clipping, split words, or Streamlit exceptions.
- [ ] Run full pytest, Ruff, release checks, detector, and `git diff --check`.
- [ ] Commit the scoped change and keep the verified Request page open for review.
