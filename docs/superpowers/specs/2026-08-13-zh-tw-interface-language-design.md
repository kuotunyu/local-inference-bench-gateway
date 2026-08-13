# zh-TW Interface Language Design

## Goal

Make the Operations Console clearly zh-TW-first while retaining original English terms when they
are the precise, natural language of inference engineering, MLOps, HTTP, measurement, or the
repository's public data contract.

The result should read as a Taiwanese engineer's interface, not as translated English and not as a
bilingual glossary.

## Audience and Voice

The primary audience is a technical GitHub visitor evaluating an AI Engineer, MLOps, or Inference
Engineering portfolio project. Copy should be rational, concise, evidence-aware, and operational.

- Use Traditional Chinese characters and Taiwan usage throughout prose and controls.
- Prefer short declarative sentences over promotional language.
- Explain what is observed; do not imply causation, health history, or SLA evidence that the data
  does not establish.
- Use full-width Chinese punctuation in Chinese sentences. Preserve punctuation inside code,
  commands, filenames, paths, identifiers, and protocol values.

## Language Rule

Use Traditional Chinese for the sentence structure and the user's action. Retain a technical term
in its original form when translating it would be less recognizable, less precise, or awkward.

### Retain Original Terms

Retain these terms and their normal capitalization:

- Product and system concepts: `Operations Console`, `Gateway`, `Backend`, `Backend Health`,
  `Alias Routing`, `Telemetry`, `Benchmark`, `Failover`, `Backpressure`, `Request`
- Measurements: `P50`, `P95`, `latency`, `TTFT`, `throughput`, `VRAM`, `tokens`, `concurrency`
- Protocols and storage: `HTTP`, `SSE`, `SQLite`, `JSON`, `API`, `loopback`
- Evidence vocabulary: `Artifact`, `provenance`, `manifest`, `digest`, `raw runs`, `fixture`,
  `warmup`, `seed`
- Proper names and identifiers: `LM Studio`, `Ollama`, `llama.cpp`, model names, aliases,
  filenames, schema fields, routes, environment variables, commands, and error categories

Original terms participate in Chinese sentences without redundant bilingual expansion. For
example, use `目前沒有 Failover event` rather than `容錯移轉事件（Failover event）`.

### Translate Interface Language

Translate navigation, actions, state explanations, supporting labels, and ordinary measurement
descriptions:

| Current | Approved zh-TW-first treatment |
|---|---|
| `Telemetry source` | `Telemetry 資料源` |
| `Observation window` | `觀測時間範圍` |
| `Overview` | `系統總覽` |
| `Routing & Reliability` | `Routing 與可靠性` |
| `Requests` | `Request 紀錄` |
| `Benchmark Evidence` | `Benchmark 證據` |
| `Demo Mode` / `Live Mode` | `Demo 模式` / `Live 模式` |
| `REQUEST VOLUME` | `REQUEST 數量` |
| `SUCCESS RATE` | `成功率` |
| `FAILOVER EVENTS` | `FAILOVER 次數` |
| `selected window` | `所選時間範圍` |
| `successful` | `筆成功` |
| `total latency` | `端到端 latency` |
| `matching records` | `筆符合條件` |
| `filtered scope` | `目前篩選結果` |
| `when present` | `有資料時顯示` |
| `upstream usage incomplete` | `Upstream usage 不完整` |
| `illustrative fixture` | `示範 fixture` |
| `production traffic` | `正式流量` |
| `current probe` | `目前 probe` |
| `Recent Failover` | `近期 Failover` |
| `Error Categories` | `Error 分類` |
| `Failover Events` | `Failover event` |
| `Artifact unavailable` | `Artifact 無法使用` |
| `Method & Provenance` | `測量方法與 provenance` |

## Component Treatment

### Global Shell

- Keep `Operations Console` as the product name.
- Change its subtitle to `本機推論 Gateway`.
- Localize control labels, mode values, navigation, refresh help, stale-data notices, registry
  notices, and the footer.
- The browser title may retain `Local Inference · Operations Console` because it functions as a
  compact product identifier rather than body copy.

### Overview

- Keep the page title `推論閘道運行概覽`.
- Rewrite the lead and source note into natural Chinese sentence structure.
- Localize KPI labels and supporting details while preserving `Request`, `latency`, and `Failover`.
- Keep chart measurements and technical headings precise; translate ordinary nouns such as
  `時間`, `數量`, and `端到端` where they improve comprehension.
- Use `正常` and `降級` for visible Backend status values, while keeping `Backend Health` as the
  section concept.

### Routing and Reliability

- Use Chinese sentence structure for invariants, capacity notes, empty states, and recovery copy.
- Preserve `Alias Routing`, `Backend Health`, `Backpressure`, `HTTP 429`, `queue`,
  `max_concurrent`, and schema field names.
- Localize chart axis and tooltip descriptors such as `觀測到的 failure`, `分類`, and `數量`.

### Request Records

- Localize filter labels and selectable outcomes where they are interface concepts.
- Preserve data values and table schema field names so the UI stays aligned with SQLite telemetry
  and code-level evidence.
- Localize KPI labels, helper text, empty states, and missing-data explanations.
- Preserve `Streaming`, `Non-streaming`, `Status code`, and error category values.

### Benchmark Evidence

- Localize headings, verification states, KPI descriptions, captions, and method labels.
- Preserve engine names, measurement abbreviations, `concurrency`, `throughput`, `Artifact`,
  `provenance`, `manifest`, `digest`, file names, and chart series identifiers.
- Replace English-only direction text such as `higher is better`, `lower is better`, and
  `unavailable` with concise zh-TW explanations or `—` when availability is unknown.
- Preserve every scope limitation and evidence warning; this language pass must not strengthen any
  claim.

## Non-Goals

- Do not translate database columns, filenames, route paths, environment variables, commands,
  model names, backend names, aliases, or error-category data values.
- Do not add a language switcher, localization framework, glossary panel, tooltip dictionary, or
  duplicated Chinese-and-English labels.
- Do not change layout, typography, colors, chart values, metric calculations, filtering,
  routing, telemetry, evidence verification, or fallback behavior.

## Verification

- Update copy-focused tests before production strings and observe expected failures.
- Add a shell/navigation contract covering the approved primary labels.
- Update view copy tests for KPI labels, explanations, statuses, and evidence warnings.
- Run dashboard and complete repository tests, Ruff, and release checks.
- Inspect all four views at desktop and 390 px. Confirm natural line wrapping, no horizontal
  overflow, no rendered Streamlit exception, and no accidental translation of identifiers or data
  fields.
