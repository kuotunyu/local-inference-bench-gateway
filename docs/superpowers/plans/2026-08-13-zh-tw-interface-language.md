# zh-TW Interface Language Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make all user-facing console copy zh-TW-first while preserving precise inference-engineering terminology and every data, layout, and behavior contract.

**Architecture:** Keep copy at its existing presentation boundary instead of introducing a localization framework. Update Streamlit smoke tests and Altair-spec assertions before changing the shell and four views; preserve internal data/schema identifiers and use the existing render functions unchanged.

**Tech Stack:** Python 3.12, Streamlit, Altair, pytest, Ruff.

## Global Constraints

- Use Traditional Chinese and Taiwan usage for navigation, actions, explanations, state, and ordinary labels.
- Retain original engineering terms listed in `docs/superpowers/specs/2026-08-13-zh-tw-interface-language-design.md`.
- Do not duplicate every term in Chinese and English.
- Do not translate table schema fields, data values, filenames, routes, commands, model/backend/alias names, or environment variables.
- Do not change layout, styling, telemetry, calculations, filtering semantics, routing, evidence verification, or fallback behavior.
- Preserve evidence uncertainty and scope limitations exactly.

---

### Task 1: Localize the Global Shell

**Files:**
- Modify: `tests/dashboard/test_dashboard_smoke.py`
- Modify: `tests/dashboard/test_components.py`
- Modify: `tests/dashboard/test_app_state.py`
- Modify: `dashboard/app.py`
- Modify: `dashboard/components.py`
- Modify: `dashboard/state.py`

**Interfaces:**
- Produces navigation values `系統總覽`, `Routing 與可靠性`, `Request 紀錄`, and `Benchmark 證據`.
- Produces mode values `Demo 模式` and `Live 模式`, while returning internal source kinds `demo` and `live`.
- Preserves `main()` dispatch to the same four render functions.

- [x] **Step 1: Update shell tests first**

Change the smoke-test page parameters to the four approved navigation values. Change the header
assertion from `Local inference gateway` to `本機推論 Gateway`. Change the unavailable-live test to
select `Live 模式` and expect `安全切換至 Demo 模式`. Add assertions that the two selectbox labels
are `Telemetry 資料源` and `觀測時間範圍`.

Update the component test input from `("REQUESTS", "<60>", "selected window")` to
`("REQUEST 數量", "<60>", "所選時間範圍")`. Update the state test to assert the localized fallback
sentence while retaining exact command and `GATEWAY_DB_PATH` assertions.

- [x] **Step 2: Run shell tests and verify RED**

Run:

```powershell
uv run pytest tests/dashboard/test_dashboard_smoke.py tests/dashboard/test_components.py tests/dashboard/test_app_state.py -q
```

Expected: failures mention old page values, subtitle, control labels, and mode copy.

- [x] **Step 3: Localize shell production strings**

Use these exact public values in `dashboard/app.py`:

```python
PAGES = ["系統總覽", "Routing 與可靠性", "Request 紀錄", "Benchmark 證據"]
```

Use `Telemetry 資料源`, `觀測時間範圍`, `Demo 模式`, and `Live 模式` in controls. Localize refresh
help, stale snapshot caption, registry warning title, and footer into Chinese sentence structure.
Update dispatch comparisons to the new navigation values without changing the called functions.

Change the brand subtitle in `dashboard/components.py` to `本機推論 Gateway`. In
`dashboard/state.py`, use `Live 模式暫時無法使用，已安全切換至 Demo 模式。` while preserving the
recovery command and environment variable.

- [x] **Step 4: Verify and commit Task 1**

Run the focused tests plus Ruff on the six files, then commit:

```powershell
git add dashboard/app.py dashboard/components.py dashboard/state.py tests/dashboard/test_dashboard_smoke.py tests/dashboard/test_components.py tests/dashboard/test_app_state.py
git commit -m "feat: localize console shell to zh-TW"
```

---

### Task 2: Localize Overview, Routing, and Request Records

**Files:**
- Modify: `tests/dashboard/test_view_models.py`
- Modify: `tests/dashboard/test_dashboard_smoke.py`
- Modify: `dashboard/views/overview.py`
- Modify: `dashboard/views/reliability.py`
- Modify: `dashboard/views/requests.py`

**Interfaces:**
- Preserves `build_activity_chart`, `build_error_chart`, `apply_request_filters`, and every view
  signature.
- Changes only visible labels, helper text, headings, status strings, chart titles, and tooltips.

- [x] **Step 1: Add failing operational-copy assertions**

In `test_view_models.py`, assert that the Overview chart Y titles are `每 bucket Request 數` and
`P95 latency / ms`, the Request tooltip title is `Request 數`, and the reliability failure-axis title
is `觀測到的 failure` with tooltip titles `分類` and `數量`.

In `test_dashboard_smoke.py`, add a parameterized zh-TW-first copy check:

```python
[
    ("系統總覽", ["REQUEST 數量", "成功率", "FAILOVER 次數", "近期 Failover"]),
    ("Routing 與可靠性", ["Error 分類", "觀測到的 HTTP 429", "Failover event"]),
    ("Request 紀錄", ["篩選後 REQUEST", "成功率", "TOKEN 數量"]),
]
```

Render each page and assert every expected fragment appears in combined Markdown or metric output.

- [x] **Step 2: Run operational tests and verify RED**

Run:

```powershell
uv run pytest tests/dashboard/test_view_models.py tests/dashboard/test_dashboard_smoke.py -q
```

Expected: generated chart specs and rendered copy still contain the previous English labels.

- [x] **Step 3: Localize Overview**

In `dashboard/views/overview.py`:

- use `觀測時間範圍` in `_time_note`;
- use `每 bucket Request 數` and tooltip `Request 數`;
- use `Gateway 離線`, `Gateway 可連線`, `正常`, `降級`, and `目前 probe`;
- rewrite the lead with Chinese structure while retaining `Request throughput`, `latency`,
  `routing`, `Failover`, and `Backend Health`;
- use `示範 fixture，非正式流量`;
- use KPI labels/details `REQUEST 數量`, `所選時間範圍`, `成功率`, `筆成功`, `端到端 latency`, and
  `FAILOVER 次數`;
- use heading `Request 數量與 P95 latency`, a fully Chinese chart explanation, `無上限`,
  `近期 Failover`, and a Chinese empty-state sentence.

- [x] **Step 4: Localize Routing and Requests**

In `dashboard/views/reliability.py`, localize the lead, fixture note, routing invariant, capacity and
resolved-model descriptions, health states, `Error 分類`, chart descriptors, `觀測到的 HTTP 429`,
and `Failover event`; retain the approved original terms and schema values.

In `dashboard/views/requests.py`, localize filter labels to `結果`, `Error 分類`, and
`傳輸方式` while retaining selectable values `Success`, `Failure`, `Streaming`, and
`Non-streaming`. Use page lead and source copy with Chinese structure. Use KPI labels/details
`篩選後 REQUEST`, `筆符合條件`, `成功率`, `目前篩選結果`, `端到端 latency`, `有資料時顯示`,
`Streaming 有資料時顯示`, `TOKEN 數量`, and `Upstream usage 不完整`.

- [x] **Step 5: Verify and commit Task 2**

Run focused tests and Ruff, then commit:

```powershell
git add dashboard/views/overview.py dashboard/views/reliability.py dashboard/views/requests.py tests/dashboard/test_view_models.py tests/dashboard/test_dashboard_smoke.py
git commit -m "feat: localize operational views to zh-TW"
```

---

### Task 3: Localize Benchmark Evidence

**Files:**
- Modify: `tests/dashboard/test_dashboard_smoke.py`
- Modify: `tests/dashboard/test_evidence.py`
- Modify: `dashboard/views/evidence.py`

**Interfaces:**
- Preserves all benchmark data frames, series fields, chart builders, validation, warnings, and
  artifact boundaries.
- Localizes display-only headings, captions, KPI labels/details, chart titles, and method labels.

- [x] **Step 1: Add failing evidence-copy assertions**

Add rendered smoke assertions for `C16 最高 THROUGHPUT`, `GATEWAY 額外成本`, `測量日期`,
`PUBLIC RAW RUNS`, `測量方法與 provenance`, and `Artifact 無法使用` where the fixture permits.

Extend evidence spec tests so the throughput X title remains `Concurrency`, while captions and
display headings are covered by the rendered smoke path. Retain all existing digest/wrong-shape
tests unchanged.

- [x] **Step 2: Run evidence tests and verify RED**

Run:

```powershell
uv run pytest tests/dashboard/test_evidence.py tests/dashboard/test_dashboard_smoke.py -q
```

Expected: English-only KPI labels and method headings fail the new rendered-copy contract.

- [x] **Step 3: Localize evidence production strings**

In `dashboard/views/evidence.py`:

- rewrite the lead, digest status, source note, and verification warning into Chinese sentence
  structure while retaining `Artifact`, `digest`, and filenames;
- use KPI labels `C16 最高 THROUGHPUT`, `GATEWAY 額外成本`, `測量日期`, `PUBLIC RAW RUNS`;
- use values/details `是`, `否`, `manifest 無法使用`, and `僅提供 aggregate evidence`;
- localize headings and captions, including `Aggregate decode throughput`,
  `依 concurrency 比較 P50 / P95 TTFT`, `Prefill · 校準後 prompt`, `Gateway 成本`,
  `測量方法與 provenance`, and `數值越高／越低越好`;
- use `Artifact 無法使用` and `Controlled scan 無法使用` for degraded states;
- localize method labels to `模型`, `測量日期`, `測量方法`, `Engine 隔離`, and
  `Prefix-cache 控制`, without modifying provenance values;
- replace display fallbacks `unavailable` with `無法使用` and retain scope limitations.

- [x] **Step 4: Verify and commit Task 3**

Run evidence tests, dashboard tests, and Ruff, then commit:

```powershell
git add dashboard/views/evidence.py tests/dashboard/test_evidence.py tests/dashboard/test_dashboard_smoke.py
git commit -m "feat: localize benchmark evidence to zh-TW"
```

---

### Task 4: Full Verification and Browser Review

**Files:**
- Modify: `docs/superpowers/plans/2026-08-13-zh-tw-interface-language.md`

**Interfaces:**
- Consumes the completed four-view interface.
- Produces recorded automated and rendered verification evidence.

- [x] **Step 1: Run complete automated verification**

Run:

```powershell
uv run pytest tests/dashboard -q
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv run --frozen python -m release_checks.cli
```

Expected: every command passes.

- [x] **Step 2: Run the Impeccable detector once**

Run the detector on `dashboard/app.py`, `dashboard/components.py`, `dashboard/state.py`, and the four
view files. Expected: no unexplained finding.

- [x] **Step 3: Inspect all views in one browser batch**

Restart `http://127.0.0.1:8502/`. Inspect all four views at desktop and 390 px. Verify navigation,
controls, KPI labels, headings, helper text, error/empty states visible in the fixture, chart labels,
and evidence captions. Confirm no horizontal overflow, rendered Streamlit exception, accidental
translation of identifiers/data fields, or awkward Chinese line break.

- [x] **Step 4: Apply at most one correction and confirm once**

If defects appear, add the smallest failing regression test, fix the copy in one batch, rerun the
focused and complete checks, restart Streamlit, and perform one confirmation pass.

- [x] **Step 5: Record execution notes and commit**

Append actual test counts, browser widths, and any justified term retained in original form, then:

```powershell
git add docs/superpowers/plans/2026-08-13-zh-tw-interface-language.md
git commit -m "docs: record zh-TW interface verification"
git status --short
```

Expected: the worktree is clean and the branch preview remains available for further UI iteration.

## Execution Notes

- TDD RED was observed for the shell, operational-view, evidence, and final consistency copy
  contracts before production strings changed.
- The evidence tests live in `tests/dashboard/test_evidence_view.py`; the plan's original
  `test_evidence.py` filename was corrected during execution without changing scope.
- Automated verification passed with 73 dashboard tests and 161 full repository tests, plus Ruff
  lint/format and publication/evidence/document/docker release checks.
- The Impeccable detector returned no findings for the shell, state, components, or four views.
- Desktop 1280 px and mobile 390 px browser passes covered all four views with no horizontal
  overflow or rendered Streamlit exception. One bounded correction localized the source badges,
  Failover ratio detail, and `SQLite Telemetry` capitalization; the confirmation pass passed.
- Schema fields, aliases, Backend and model names, filenames, routes, environment variables,
  `P50`, `P95`, `TTFT`, `VRAM`, `concurrency`, `Artifact`, `provenance`, and `digest`
  remain in original form by design.
- Final copy review aligned `Routing 原則`, `Backend Health`, `Request`, `Failover`, and
  `證據驗證警告` across normal and degraded states. Four state-specific AppTests were added;
  final verification passed with 77 dashboard tests and 165 full repository tests. The 734 px
  handoff viewport rendered all four views without horizontal overflow or Streamlit exceptions.
