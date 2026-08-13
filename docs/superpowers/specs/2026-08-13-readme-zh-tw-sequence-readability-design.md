# README zh-TW 圖解與時序圖可讀性 — Design Specification

Date: 2026-08-13
Status: approved for planning
Primary language: 正體中文（zh-TW），技術專有名詞保留原文

## 1. 目的

延續 README 圖解的縱向分層方向，進一步修正圖中文字語言不一致、時序圖字體過小與 section heading 過度口語或中英重複的問題。

本次只調整 README、Mermaid source 與相關 contract tests，不改變 Gateway、Benchmark、Dashboard、artifact、canonical claims 或 release policy 的功能與資料語意。

## 2. 已確認問題

1. System Context 與 Evidence Pipeline 仍有大量一般敘事文字使用英文，與 README 的 zh-TW-first 原則不一致。
2. Request / Failover Sequence Diagram 在 GitHub 約 838 px 的 article 寬度中同時容納 5 個 participant、兩層 `alt` 與多段長英文，導致 actor、branch 與 message text 過小。
3. `一眼看重點` 偏口語與媒體式標題，不符合專案理性、科學、evidence-first 的語氣。
4. `系統邊界（System Context）` 同時使用中文與英文，造成不必要的資訊重複。

## 3. 採用方案

採用 **單張精簡時序圖＋全面 zh-TW 圖面敘事**：

- 保留一張 Sequence Diagram，避免 README 增長與情境重複。
- participant 從 5 個精簡為 4 個：Client、Gateway、Primary Backend、Fallback Backend。
- Telemetry 不再占用獨立 lifeline；改以 Gateway note 表達受控、去敏的 telemetry side effect。
- 將 branch label、note 與 message 的一般敘事改為正體中文，技術詞與協定保留原文。
- 縮短 message，降低 Mermaid natural width，並提高 sequence typography tokens。

若公開 GitHub 實際 render 仍無法達到不開 zoom 即可閱讀，才啟用 fallback：拆成「容量控制」與「受控 Failover」兩張 Sequence Diagram。只有實際 render 證據不達標時才採用 fallback，不預先增加第四張圖。

不採用一般 flowchart 取代 Sequence Diagram，因為那會失去 participant、時間順序與 Failover 互動關係。

## 4. Section heading

### 4.1 能力摘要

`一眼看重點` 改為：

> 工程能力與驗證範圍

此 heading 同時涵蓋 Gateway 能力、Benchmark evidence、Operations Console truth boundary 與 CPU-only reviewer path，比「重點」更精確且更符合工程文件語氣。

### 4.2 系統圖

`系統邊界（System Context）` 改為：

> 系統邊界

中文已能完整表達概念，不再重複英文。其他 heading 仍可保留必要 technical term，例如 `Request 與 Failover 流程`、`Benchmark 證據鏈`。

### 4.3 Evidence Pipeline heading

`Benchmark 證據鏈（Evidence Pipeline）` 改為：

> Benchmark 證據鏈

`Benchmark` 是專案領域核心名詞，保留原文；`Evidence Pipeline` 與「證據鏈」語意重複，因此移除。

## 5. 圖解語言原則

### 5.1 翻譯一般敘事

以下可自然翻譯且不損失工程語意的圖面文字使用正體中文：

| Current label | New label |
|---|---|
| Entry points | 輸入端 |
| Execution boundary | 執行邊界 |
| Runtime observability | 執行期可觀測性 |
| Published evidence | 已發布證據 |
| Inputs | 輸入 |
| Measurement | 量測 |
| Publication boundary | 發布邊界 |
| Verification | 驗證 |
| Presentation | 呈現 |
| Outside the public repository | 不在公開 repository 中 |
| not published | 未發布 |
| aggregate only | 僅發布 aggregate |

### 5.2 保留原文的 technical terms

下列名詞保持原文，必要時嵌入中文句子：

- OpenAI SDK、HTTP Client、Async Benchmark Client
- FastAPI Gateway、Backend、Alias、Failover、Capacity、Streaming、SSE
- SQLite Telemetry、Operations Console
- aggregate artifacts、Digest、Claim Verifier
- workload matrix、prompt、nonce、warmup、GPU
- `provenance.json`、`claims.json`、release checks、README、EVAL_REPORT
- HTTP status、`Retry-After`、connection、timeout、protocol、5xx、4xx、`finally`

### 5.3 不做生硬翻譯

不把 Gateway 翻成「閘道器」、Backend 翻成「後端端點」、Telemetry 翻成「遙測資料」、nonce 翻成「一次性隨機數」。以正體中文句法承載原文 technical terms，避免看似中文但降低辨識性。

## 6. System Context 圖面

保留目前 `flowchart TB` 與四層結構，只調整 visible labels：

1. `輸入端`
2. `執行邊界`
3. `執行期可觀測性`
4. `已發布證據`

Node 建議文案：

- `OpenAI SDK／HTTP Client`
- `Async Benchmark Client`
- `FastAPI Gateway · Alias Routing／Capacity／Failover`
- `外部 Backend engines · llama.cpp／Ollama／LM Studio`
- `SQLite Telemetry`
- `Operations Console`
- `Aggregate artifacts`
- `Digest／Claim Verifier`
- `README／EVAL_REPORT／Operations Console`

Edge label 建議文案：

- `OpenAI-compatible HTTP`
- `HTTP／SSE`
- `read-only SQLite`
- `aggregate evidence`

上述 edge labels 屬協定或 evidence terminology，不強制翻譯。

## 7. Request 與 Failover Sequence Diagram

### 7.1 Participants

僅保留：

1. `Client`
2. `Gateway`
3. `Primary Backend`
4. `Fallback Backend`

移除 `Telemetry` participant。Telemetry 是此圖的 side effect，不是 Failover 時序的主要互動角色；移除後可降低約 20% 的水平跨度。

### 7.2 Message 與 branch copy

使用以下精簡語意，不塞入完整句子：

- `POST /v1/chat/completions · Alias`
- `auth · Alias validation · acquire slot`
- `容量已滿 · 不排隊`
- `HTTP 429 + Retry-After`
- `已取得 slot`
- `解析 Alias · 嘗試 Primary`
- `Primary 成功或 4xx`
- `成功或 4xx · 不 Failover`
- `可重試的 upstream failure`
- `connection／timeout／protocol／non-final 5xx`
- `記錄去敏 Failover event`
- `嘗試 Fallback Backend`
- `response`
- `JSON response／Streaming SSE`
- `Streaming：持有 slot 至結束／失敗／取消`
- `記錄 metadata-only request telemetry`
- `finally 釋放 slot`

### 7.3 Telemetry side effect

使用 Gateway 自身 note 或 self-message 表達：

- Failover 時記錄去敏 `Failover event`。
- response 結束時記錄 `metadata-only request telemetry`。

不顯示 request prompt、Authorization header、raw upstream body 或 exception string。

### 7.4 Typography 與密度

- Mermaid `themeVariables.fontSize` 目標為 20 px。
- `actorFontSize`、`messageFontSize` 目標為 19–20 px；`noteFontSize` 不低於 18 px。
- `messageMargin` 維持足以分辨 arrow 與 label，但不以增加無效高度換取可讀性。
- 使用最少必要的 `alt` fragment；保留 capacity 與 retryable failure 兩個決策，移除重複說明。
- 不使用 HTML `<br/>`，避免 GitHub Mermaid sanitizer 移除 tag 後文字黏連。

## 8. Benchmark 證據鏈

保留五階段 mixed-direction layout，visible stage title 改為：

1. `1 · 輸入`
2. `2 · 量測`
3. `3 · 發布邊界`
4. `4 · 驗證`
5. `5 · 呈現`

主要 node copy：

- `合成校準 prompts／workload matrix`
- `random 8-character nonce`
- `Async Benchmark Client · warmup 3 次 · 計時 5 次`
- `每次僅一個受測 engine 常駐 GPU`
- `request-level raw runs · 未公開`
- `aggregate CSV／controlled JSON／derived charts`
- `不在公開 repository 中`
- `provenance.json · versions · method · artifact class · SHA-256`
- `claims.json · canonical claims`
- `release checks`
- `README`、`EVAL_REPORT`、`Operations Console`

## 9. Contract tests

更新 `tests/test_readme_portfolio.py`：

- 鎖定新 heading order：`工程能力與驗證範圍`、`系統邊界`、`Request 與 Failover 流程`、`Benchmark 證據鏈`。
- 斷言舊 heading 不存在。
- 鎖定 System Context 與 Evidence Pipeline 的 zh-TW stage labels。
- Sequence Diagram 必須只有 4 個 participant；`Telemetry` 與 `Limiter` 不得成為 participant。
- 鎖定 HTTP 429、4xx no-Failover、retryable failure、sanitized event、Streaming slot lifecycle、metadata-only telemetry 與 `finally` release。
- 保留 high-contrast `classDef`、Demo / Live / Evidence 與 publication boundary tests。

## 10. 驗證標準

### 10.1 Local verification

- 三張 Mermaid 由 pinned `@mermaid-js/mermaid-cli@11.12.0` 成功 render。
- PNG 視覺檢查沒有 overlap、clipping、文字黏連或過長 note。
- `uv run --frozen ruff check .`
- `uv run --frozen ruff format --check .`
- `uv run --frozen pytest -q`
- `uv run --frozen python -m release_checks.cli`
- `git diff --check`

### 10.2 Public GitHub verification

在公開 GitHub README、約 1440 px browser viewport（article 約 838 px）驗證：

- 三張 Mermaid 均為 rendered output，沒有 syntax error。
- Sequence Diagram 不使用 zoom controls 即可辨識 participant、branch label 與主要 message。
- actor 與主要 message 的視覺字級不得明顯小於目前版本；目標至少接近 14–15 CSS px 的可讀體感。
- System Context 與 Evidence Pipeline 的一般敘事以正體中文呈現。
- 沒有 `<br/>` 被移除造成的文字黏連。
- article 與 document 均無 horizontal overflow。
- 另以約 760 px viewport 檢查 heading、圖面主結構與整頁 overflow。

若單張四 participant Sequence Diagram仍不達標，實作必須停下單圖方案，改用兩張 scenario-focused Sequence Diagram，再重跑全部 contract 與公開 render 驗收。

## 11. 範圍外事項

- 不改寫 README 首段定位、hero screenshot、canonical benchmark 數字或 Quickstart commands。
- 不修改 Gateway、Benchmark、Dashboard、SQLite schema、Docker 或 CI 行為。
- 不將所有 technical terms 強制翻成中文。
- 不新增外部圖床、固定 SVG、JavaScript widget 或 Mermaid 以外的圖解框架。

## 12. 完成定義

1. README section heading 理性且沒有中英重複。
2. 圖面一般敘事為 zh-TW，technical terms 保持工程辨識度。
3. Sequence Diagram 在公開 GitHub 預設寬度下不開 zoom 即可閱讀。
4. Failover、Backpressure、Streaming 與 telemetry truth boundary 沒有因精簡而遺失。
5. Mermaid render、README contract、完整 tests、release checks、desktop / narrow GitHub render 全部通過。
