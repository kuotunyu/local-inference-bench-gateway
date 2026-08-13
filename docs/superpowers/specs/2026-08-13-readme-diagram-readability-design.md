# README 圖解可讀性重構 — Design Specification

Date: 2026-08-13
Status: approved for planning
Primary language: 正體中文（zh-TW），技術專有名詞保留原文

## 1. 目的

改善公開 GitHub README 的圖解可讀性與閱讀節奏，不改變 Gateway、Benchmark、Dashboard、artifact 或 release policy 的功能與資料語意。

本次重構處理四個已確認問題：

1. 移除首段重複且沒有實際必要的頁內導覽列。
2. 解決 System Context 因單一路徑橫向展開而被 GitHub 等比例縮小的問題。
3. 將 Benchmark Evidence Pipeline 改成縱向主流程搭配橫向分組，讓字體與 publication boundary 清楚可讀。
4. 統一三張圖的資訊密度、語言、字級與視覺節奏，並減少圖前後重複敘述。

## 2. 現況證據

在公開 repository、1280 px browser viewport 下，GitHub README 的實際 article 寬度約為 823 px：

- System Context iframe 約 `823 × 188 px`。
- Request / Failover Sequence Diagram 約 `823 × 783 px`。
- Benchmark Evidence Pipeline 約 `823 × 180 px`。

兩張 `flowchart LR` 被壓成極扁的長條圖，node label 幾乎無法閱讀；Sequence Diagram 則過度縱長。這表示問題不能只靠增加 `fontSize` 解決，必須同時調整方向、node 數量、label 長度與分組方式。

## 3. 採用方案

採用 **GitHub-native Mermaid 混合方向重構**：外層以 `flowchart TB` 建立主閱讀方向，必要的同層元件再以 `subgraph` 搭配 `direction LR` 橫向排列。

不採用：

- **預先渲染 SVG 作為主要圖面**：字級控制最精確，但增加 asset 維護、dark mode 與 source review 成本。
- **拆成更多小圖**：單圖會更清楚，但 README 會變長，並削弱現有「三張圖、三個問題」的敘事結構。

## 4. README 結構調整

### 4.1 移除頂部頁內導覽

完整移除下列導覽列，不以其他 breadcrumb、目錄或 badge row 取代：

> 一眼看重點 · System Context · Benchmark Evidence · Quickstart · 延伸文件

保留各內容 section；本次移除的是重複導覽，不是刪除 Quickstart、文件連結或核心說明。

### 4.2 標題改為正體中文優先

三個圖解 section 採一致命名：

- `系統邊界（System Context）`
- `Request 與 Failover 流程`
- `Benchmark 證據鏈（Evidence Pipeline）`

Gateway、Backend、Alias、Failover、Backpressure、Streaming、Telemetry、provenance、claims 等保留原文。

### 4.3 文案節奏

- 每張圖前只保留一段「這張圖回答什麼」的短文。
- 圖後只保留圖上不適合承載的 truth boundary 或 failure semantics。
- 移除與 node label 逐句重複的說明。
- 不新增行銷式標題、icon wall、裝飾性 banner 或更多 badges。

## 5. System Context 設計

### 5.1 問題

目前圖面將 Client、Gateway internals、Backend、Telemetry、Benchmark、Verifier 與 presentation surface 串成一條橫向長鏈。GitHub 會縮小整張 SVG 以符合 article 寬度，導致所有文字失去可讀性。

### 5.2 新結構

外層使用 `flowchart TB`，分成三個閱讀層級：

1. **Entry points**（橫向）：OpenAI SDK / HTTP Client、Async Benchmark Client。
2. **Execution boundary**（橫向）：FastAPI Gateway、Gateway policy（Alias Routing / Capacity / Failover）、外部 Backend engines。
3. **Evidence & observability**（橫向分組）：SQLite Telemetry → Operations Console；Aggregate Artifacts → Digest + Claim Verifier → README / EVAL_REPORT / Operations Console。

Backend engines 必須明確位於 repository-owned boundary 之外。Operations Console 必須保持 read-only observability surface，不畫成會改寫 Gateway 設定的 control plane。

### 5.3 密度控制

- 主要 node 目標為 8–10 個。
- Gateway internals 合併為一個 policy node，不拆成三個平行小 node。
- node label 最多兩行，避免完整句子。
- edge label 僅保留 `HTTP / SSE`、`read-only SQLite`、`aggregate evidence` 等必要協定或 evidence boundary。

## 6. Request 與 Failover Sequence 設計

### 6.1 目標

保留 request-time semantics，但降低目前約 783 px 的圖高與 participant 寬度。

### 6.2 調整

- participant 縮減為 Client、Gateway、Primary、Fallback、Telemetry。
- Capacity Limiter 改為 Gateway 內部動作與 note，不再占用獨立 lifeline。
- 短化 message label，但保留以下不可刪除語意：
  - capacity exhausted → `HTTP 429 + Retry-After`
  - primary success 或 4xx 不 Failover
  - connection / timeout / protocol / non-final 5xx 才進入受控 Failover
  - sanitized Failover event
  - Streaming 持有 slot 到 stream end / failure / cancellation
  - metadata-only telemetry
  - slot 在 `finally` 釋放
- 不呈現 prompt、Authorization header、raw upstream body 或 exception string。

## 7. Benchmark 證據鏈設計

### 7.1 主方向

外層使用 `flowchart TB`，建立五個縱向 stage；每個 stage 內的同層元件使用 `direction LR`：

1. **Inputs**：Synthetic calibrated prompts / workload matrix → random nonce。
2. **Measurement**：Async Benchmark Client → one measured engine resident on GPU。
3. **Publication boundary**：request-level raw runs（not public）→ aggregate CSV / controlled JSON / derived charts（public）。
4. **Verification**：`provenance.json` 與 `claims.json` 並列 → release checks。
5. **Presentation**：README、EVAL_REPORT、Operations Console 並列。

### 7.2 Truth boundary

- Raw runs 必須使用 neutral gray，並以虛線或 `not public` edge 清楚標示未發布。
- Aggregate artifact 是主要公開路徑，不能讓讀者誤以為 repository 含 request-level raw runs。
- `provenance.json` 與 `claims.json` 是互補證據，不合併成含糊的 verification node。
- Release checks 必須位於公開 presentation 之前，表示驗證是必要關卡。

## 8. Mermaid 視覺規則

1. 保留 GitHub-native Mermaid code block。
2. 使用 GitHub 支援的 Mermaid initialization 設定提高基準字級；目標 desktop node text 約 17–18 px、Sequence text 約 16–17 px。
3. 外層 `TB`、內層 `LR`，避免單一超寬 row。
4. 每個 `classDef` 明確設定 `fill`、`stroke`、`stroke-width` 與 `color`。
5. 配色維持低飽和 dusty blue、sage、clay amber、muted violet 與 neutral gray，但文字與底色必須有清楚對比。
6. 不靠 emoji、外部 icon、HTML/CSS 或 JavaScript 表達語意。
7. 圖解需同時檢查 GitHub light / dark mode；線條、箭頭、edge label 與 subgraph title 均須可辨認。
8. 任何 source、claim 或 boundary 不因版面精簡而改變語意。

## 9. 額外改善

- 保留現有 hero screenshot、量測結果、Quickstart 與延伸文件；它們已有清楚用途。
- 統一 heading 大小寫與中英文間距，移除 `Benchmark evidence pipeline` 等不一致形式。
- 不再增加 README 長度；圖解重構後，README 總行數應大致持平或下降。
- 更新 README contract tests，鎖定 section 順序、三張圖方向、必要 truth boundary、participant 精簡與頂部導覽移除。

## 10. 驗證標準

### 10.1 Mermaid

- 三張 Mermaid 均通過 parser / renderer validation。
- 逐張檢視渲染輸出，沒有 node overlap、edge label clipping、截字或錯誤換行。
- 公開 GitHub article 寬度約 823 px 時：
  - System Context 與 Evidence Pipeline 不再呈現約 180 px 高的扁平長條。
  - node label 不需使用 Mermaid zoom controls 即可辨讀。
  - Sequence Diagram 明顯短於目前約 783 px，同時保留必要分支。
- 以 desktop 與窄版 GitHub render 檢查，不出現 README 水平 overflow。

### 10.2 內容與 repository

- 頂部舊導覽列不存在。
- 正體中文為主，技術專有名詞保留原文。
- README 仍明確區分 Demo、Live、aggregate evidence 與 unpublished raw runs。
- `uv run --frozen ruff check .`
- `uv run --frozen ruff format --check .`
- `uv run --frozen pytest -q`
- `uv run --frozen python -m release_checks.cli`
- `git diff --check`

## 11. 範圍外事項

- 不修改 Gateway、Benchmark、Dashboard、SQLite schema 或 release policy。
- 不重跑 GPU benchmark，不更改 canonical claims。
- 不新增外部託管圖片、JavaScript widget、animation 或 analytics。
- 不新增第四張工程圖，也不把 README 改成完整 DESIGN.md 的替代品。

## 12. 完成定義

1. 頂部冗餘導覽已移除。
2. System Context 與 Benchmark Evidence Pipeline 在公開 GitHub 預設寬度下可直接閱讀。
3. Evidence Pipeline 同時使用縱向主流程與橫向 stage，publication boundary 清楚。
4. Sequence Diagram 更精簡，但 request、Backpressure、Failover、Streaming 與 telemetry semantics 完整。
5. README 文案更短、更一致，沒有增加無效層級。
6. Mermaid render、README contract、完整 tests、release checks 與 GitHub 實際 render 全部通過。
