# Portfolio README 與工程圖解 — Design Specification

Date: 2026-08-13
Status: proposed for implementation
Primary language: 正體中文（zh-TW），技術專有名詞保留原文

## 1. 目的

將目前偏技術摘要型的 README，重構為一份能在 30 秒內讓 GitHub 訪客理解專案價值、在 3 分鐘內看懂核心工程設計、並能進一步核驗 Benchmark evidence 的作品集首頁。

README 不以華麗術語或大量 badge 製造聲量，而是用清楚的資訊層級、真實的 Operations Console 畫面、三張互不重複的工程圖，以及可追溯的量測證據，呈現 AI Engineer、MLOps 與 Inference Engineering 能力。

## 2. 目標讀者

主要讀者依序為：

1. 第一次進入 repository 的招募者或工程主管，需要快速判斷專案深度。
2. AI / MLOps / Backend 工程師，需要理解 routing、failover、backpressure、streaming lifecycle 與 telemetry 邊界。
3. 想在本機執行或核驗結果的 reviewer，需要 CPU-only 的明確入口。
4. 本機 operator，需要知道 Operations Console 與 Live telemetry 如何啟動。

## 3. 成功標準

1. 首個 viewport 能回答：這是什麼、解決什麼問題、有哪些可驗證成果、如何看 Demo。
2. 訪客不讀 source code，也能分辨 Benchmark client、Gateway、Inference engine、SQLite telemetry 與 Operations Console 的責任。
3. 三張圖分別回答「系統裡有誰」、「一次 request 如何處理失敗」、「Benchmark evidence 如何產生與驗證」。
4. 正體中文是主要敘事語言；Gateway、Backend、Alias、Failover、Backpressure、Streaming、Telemetry、P50/P95、TTFT、Throughput、provenance 等保留原文。
5. 所有數字與能力宣告都可由 repository 中的 code、artifact、test 或文件核驗。
6. Demo data、Live telemetry、aggregate Benchmark evidence 三者不混用。
7. README 保持適合 GitHub light / dark mode，不依賴外部圖床或自訂 JavaScript。

## 4. 敘事策略

### 4.1 核心定位

首頁主敘事為：

> 一個 evidence-first 的本機推論工程專案：以共同 workload 比較三種 OpenAI-compatible inference frontend，並提供具備 Alias Routing、ordered Failover、Backpressure、Streaming pass-through 與 SQLite Telemetry 的 FastAPI Gateway。

這段定位應立即說明專案不是單純 Benchmark script，也不是只有 UI 的 Dashboard；它是一個把「量測、執行路徑、故障處理與可觀測性」放在同一個可審查 repository 的完整系統。

### 4.2 語氣

- 理性、精確、證據優先。
- 避免「企業級」、「production-ready」、「最快」等無法由目前範圍證明的字眼。
- 將限制放在適當位置，不把它藏在 README 最底部。
- 使用短段落、表格和圖解降低閱讀負擔，不堆疊大量行銷式標題。

### 4.3 與其他 portfolio repository 的一致性

延續 owner 其他 repository 的有效模式：

- 首屏快速定位與導覽。
- 「一眼看重點」先提供成果，再進入細節。
- Demo / visual evidence 先於長篇 setup。
- 架構、方法、結果與 limitation 形成完整證據鏈。
- Quickstart、project map、license 維持清楚可掃讀。

## 5. README 資訊架構

README 採以下固定順序：

1. **Title、定位句與精簡導覽**
   專案名稱、兩行定位、CI / Python / License 等不超過三個必要 badge，以及 Overview、Architecture、Evidence、Quickstart、Docs 的頁內連結。
2. **Operations Console hero**
   一張目前完成版 UI 的寬幅截圖，附一句說明 Demo Mode 可在無 GPU、無 model、無 gateway process 下直接檢視。
3. **一眼看重點**
   使用四至六個高訊息密度項目呈現：三個 engine、OpenAI-compatible Gateway、ordered Failover、per-alias Backpressure、SQLite Telemetry、CPU-only reviewer path。量測數字另以 evidence snapshot 呈現，不與產品能力混在一起。
4. **System Context**
   第一張 Mermaid 圖，建立系統邊界與元件責任。
5. **Request / Failover lifecycle**
   第二張 Mermaid 圖，解釋一次 chat completion 的 request-time 行為。
6. **Benchmark evidence pipeline**
   第三張 Mermaid 圖，解釋從 calibrated workload 到可公開、可核驗 artifact 的鏈路。
7. **量測結果與解讀邊界**
   保留現有 Throughput chart、C16 三個 engine 數字、Gateway median TTFT overhead、硬體與日期，並鄰接 caveat。
8. **Operations Console 能看什麼**
   簡述 Overview、Routing & Reliability、Request 記錄、Benchmark 證據四個頁面及 Demo / Live / Evidence source 的差異。
9. **Quickstart**
   分為「先看 UI」、「啟動 Gateway」、「完整 CPU verification」三條最短路徑。
10. **設計決策與誠實範圍**
    簡要列出 no queue、health poller observational、stream slot lifecycle、metadata-only telemetry、single-process boundary。
11. **Repository map、延伸文件與 License**
    以表格連結更深入的 DESIGN、EVAL_REPORT、SETUP、PRODUCTION_SCALING、SOURCE_AUDIT 與 RELEASE_DESIGN。

## 6. 圖解組合

只採用三張圖。每張圖有單一責任，避免同一 routing path 在 architecture、flowchart、sequence 中重複三次。

### 6.1 System Context Diagram —「系統裡有誰」

**形式：** Mermaid `flowchart LR`，以 C4 Context / Container 的抽象方式表達，但不使用可能在 GitHub renderer 相容性較差的 C4 專用語法。

**必須包含：**

- Actor：OpenAI SDK / HTTP Client。
- 系統邊界：Local Inference Bench Gateway repository。
- Runtime path：FastAPI Gateway、Model Registry / Alias Routing、Capacity Limiter、Failover orchestration。
- External inference frontends：llama.cpp、Ollama、LM Studio，明確標示為既有 OpenAI-compatible Backend，不由 repository 安裝或啟動。
- Evidence / observability path：SQLite Telemetry、Streamlit Operations Console。
- Benchmark path：Async Benchmark Client、aggregate CSV / controlled JSON / charts、digest + claim verifier。
- 主要協定或資料流：HTTP / SSE、read-only SQLite、aggregate artifact verification。

**不得包含：**

- Kubernetes、cloud service、load balancer、distributed scheduler 等目前不存在的部署元件。
- 把 Operations Console 畫成控制 Gateway 設定的 control plane；它是 read-only observability surface。
- 把 health poller 畫成 routing oracle；request-time routing 不依賴可能過期的 health snapshot。

### 6.2 Failover Sequence Diagram —「一次 request 如何安全失敗」

**形式：** Mermaid `sequenceDiagram`。

**參與者：** Client、FastAPI Gateway、Capacity Limiter、Primary Backend、Fallback Backend、SQLite Telemetry。

**主路徑：**

1. Client 送出 `POST /v1/chat/completions`，model 欄位使用 Alias。
2. Gateway 驗證 API key、request envelope、Alias 與 stream options。
3. Capacity Limiter 嘗試取得 alias slot。
4. 無 slot 時直接回傳 HTTP 429 + `Retry-After`，不建立無界 queue。
5. 有 slot 時將 Alias 解析為 ordered Backend chain，僅改寫 model identifier。
6. Primary 成功或回傳 4xx 時不 Failover；結果直接回到 Client。
7. Primary 發生 connection、timeout、protocol error 或非最終 5xx 時，記錄 sanitized Failover event，再嘗試 Fallback。
8. JSON response 完成時記錄 metadata-only telemetry 並釋放 slot。
9. Streaming response 使用 SSE pass-through，slot 持有到 stream 結束、失敗或取消，再於 `finally` 釋放。

**圖面控制：**

- 以一張圖呈現主路徑與兩個必要分支：Backpressure、retryable Failover。
- Streaming lifecycle 以簡短 `opt` 或 note 呈現，不把每個 chunk 畫成獨立節點。
- 不顯示 request prompt、Authorization header、raw response body 或 exception string，呼應 telemetry privacy boundary。

### 6.3 Evidence Pipeline Flowchart —「數字如何成為證據」

**形式：** Mermaid `flowchart LR` 或 `flowchart TD`，依實際 GitHub 寬度選擇可讀性較高者。

**流程：**

1. Synthetic calibrated prompts（2k / 8k）與固定 workload matrix。
2. 每個 measured user prompt 前置 random 8-character nonce，避免 prefix-cache 污染。
3. Async Benchmark Client 以 3 warmups + 5 timed runs 執行。
4. llama.cpp、Ollama、LM Studio 一次只讓一個 measured engine resident on GPU。
5. 產生 request-level raw runs，但明確標示為 **not public**。
6. 公開 aggregate CSV、controlled JSON 與 derived charts。
7. `provenance.json` 記錄硬體、版本、model、方法、artifact class 與 SHA-256 digest policy。
8. `claims.json` + release checks 重算 README / EVAL_REPORT 的 canonical claims。
9. 經核驗的 evidence 供 README、EVAL_REPORT 與 Operations Console 使用。

**視覺語意：**

- Input、measurement、public artifact、verification、presentation 使用不同但克制的高對比色。
- `not public` raw runs 使用灰色虛線分支，避免誤解為 repository 內可下載資料。
- Verification 是流程必要關卡，不只是旁邊的裝飾節點。

## 7. Mermaid 視覺與相容性規則

1. 圖解直接使用 GitHub-native Mermaid code block，讓 source 可閱讀且不依賴外部服務。
2. 每張圖最多約 12–15 個主要 node / participant；過多細節改由文字或 DESIGN.md 承接。
3. Node label 以正體中文敘事，技術名詞保留原文；標點或括號存在時以雙引號包住 label。
4. 每個 `classDef` 必須明確設定 `fill`、`stroke` 與 `color`，確保文字對比。
5. 配色採低飽和 sage、dusty blue、clay amber 與 neutral gray，但前景文字需達清楚可讀的深淺對比。
6. 不依賴 emoji 或系統可能缺字的 icon；必要語意以文字與節點形狀表達。
7. Link label 保持短句；不在箭頭上塞入完整規格說明。
8. 所有圖在加入 README 前，必須以 Mermaid CLI 或等價 renderer 驗證並產生可檢視輸出。
9. 實作時保留 Mermaid source；若 GitHub render 對字級或深色模式表現不穩定，再提供同內容的 SVG fallback，但 README 預設仍以 native Mermaid 為主。

## 8. Screenshot 規格

Operations Console 截圖是 README 的唯一 hero visual，不再額外製作裝飾性 banner。

- 顯示「系統總覽」頁與最具辨識度的 KPI / chart / routing context。
- 使用 1440–1600 px 寬的桌面 viewport，裁掉 browser chrome 與無效空白。
- Demo Mode 標籤必須可見，避免畫面被誤認為 production traffic。
- 字體需清楚到 GitHub README 內容寬度下仍可辨認。
- 儲存於 repository 內的 `docs/assets/`，使用 PNG 或 WebP，目標低於 1 MiB，硬上限不得碰觸 publication policy 的 5 MiB 限制。
- 截圖只展示既有 UI，不含人工偽造數字或後製功能。

## 9. 可公開數字與宣告

README 可突出但不得改寫意義的現有 canonical claims：

- llama.cpp：625.55 tok/s at concurrency 16。
- Ollama：704.98 tok/s at concurrency 16。
- LM Studio：686.72 tok/s at concurrency 16。
- Gateway median TTFT overhead：1.66 ms。

這些數字必須鄰近以下限定：RTX 4090、2026-07-17、pinned engine / model environment、hardware- and version-specific、不是通用 engine ranking。

測試數量若呈現，應由最後一次完整 verification 的實際輸出決定，不在規格中固定為永久數值。CI badge 可呈現 workflow 狀態，但不取代本機 verification command。

## 10. Demo、Live 與 Evidence 的區隔

README 應以短表格清楚區分：

| Source | 用途 | 是否需要 Gateway / GPU | 真實性邊界 |
|---|---|---|---|
| Demo Mode | 初次檢視 UI / UX 與操作案例 | 否 | deterministic illustrative fixture，非 production traffic |
| Live Mode | 讀取本機 Gateway SQLite telemetry | 需要 Gateway database；不必因看歷史資料而啟動 GPU | metadata-only local telemetry |
| Benchmark Evidence | 檢視 committed aggregate 結果與 provenance | 否 | aggregate evidence；request-level raw runs 未公開 |

這個表格只出現一次；其他段落以連結回指，不重複長篇解釋。

## 11. Quickstart 設計

採三個清楚入口，不把所有 command 混成一段：

### A. 先看 Operations Console（推薦）

安裝 dashboard extra，於 loopback 啟動 Streamlit。說明沒有 compatible database 時會自動進入 Demo Mode。

### B. 啟動 Gateway

連結 SETUP.md，保留最短的 `.env`、registry 設定與 Uvicorn loopback command。明確說明 Backend 需由使用者自行啟動。

### C. CPU-only verification

列出 frozen sync、Ruff、pytest、release checks 與 evidence-only verifier。GPU benchmark reproduction 保留在 SETUP / EVAL_REPORT，不放進第一層 Quickstart。

## 12. 範圍與非目標

本次只重構 README 與其必要的 visual asset，不修改 Gateway、Benchmark、Dashboard 或 release policy 行為。

不加入：

- Deployment Diagram：目前主要是 single-workstation reference system，加入雲端或叢集圖會造成 production deployment 的錯誤期待。
- ER Diagram：SQLite schema 不是訪客理解專案價值的最高優先資訊，欄位細節由 code / DESIGN.md 承接。
- 獨立 Routing Flowchart：其內容會與 Failover Sequence Diagram 重複。
- 自動播放 GIF、video 或外部 analytics：增加負擔且無助於 evidence-first 敘事。
- 大量彩色 badge、visitor counter、skill icon wall：會稀釋核心工程內容。

## 13. 實作檔案

預計修改：

- `README.md`：完整資訊架構、zh-TW 文案與三張 Mermaid 圖。
- `docs/assets/operations-console-overview.png` 或 `.webp`：裁切後的 hero screenshot。

若沒有現成的 Mermaid validation 工具，可在臨時目錄安裝或使用技能附帶 renderer 驗證；驗證輸出不一定需要 commit。不得將 cache、runtime database、raw benchmark runs 或工具產物誤加入 repository。

## 14. 驗證標準

### 14.1 內容核驗

- 所有 route、failure category、capacity、stream lifecycle 與 telemetry boundary 均對照 source code / DESIGN.md。
- 所有 Benchmark claim 均通過 `release_checks.evidence` 與完整 release checks。
- 所有相對連結、圖片路徑、anchor 與 command 都可用。
- 搜尋並移除 TODO、TBD、placeholder、production-ready 與未經證明的 superlative。

### 14.2 圖解核驗

- 三張 Mermaid diagram 分別通過 parser / renderer validation。
- GitHub light / dark mode 下文字與線條皆清楚。
- 1440 px desktop 與約 760 px narrow layout 下可讀；窄螢幕允許 GitHub 水平捲動，但不得因過多 node 變成不可理解的縮圖。
- 每張圖只回答其指定問題，沒有互相複製同一套 node 與箭頭。

### 14.3 Repository verification

- `uv run --frozen ruff check .`
- `uv run --frozen ruff format --check .`
- `uv run --frozen pytest -q`
- `uv run --frozen python -m release_checks.cli`
- 以本機 Markdown preview 或 GitHub 實際頁面檢查首屏、截圖、表格與 Mermaid render。

## 15. 完成定義

當以下條件同時成立，README 重構才算完成：

1. 新訪客能從首屏理解專案定位並看到 Operations Console。
2. 三張圖通過驗證且各有單一責任。
3. 量測結果與 limitation 鄰接呈現，沒有誇大推論。
4. Demo / Live / Evidence 三種 data source 不會混淆。
5. Quickstart 可複製執行，所有連結有效。
6. 完整 test、lint、format、evidence 與 publication checks 通過。
7. README 的視覺與語氣和 owner 其他 portfolio repository 一致，但保留此專案 evidence-first 的獨特性。
