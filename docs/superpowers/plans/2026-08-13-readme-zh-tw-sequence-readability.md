# README zh-TW Diagrams and Sequence Readability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 將 README 圖解改為 zh-TW-first、使用理性 section heading，並讓 Request / Failover Sequence Diagram 在公開 GitHub 預設寬度下不開 zoom 即可閱讀。

**Architecture:** 保留 GitHub-native Mermaid 與現有三圖結構。System Context 與 Evidence Pipeline 只翻譯一般敘事文字；Sequence Diagram 精簡為 Client、Gateway、Primary Backend、Fallback Backend 四個 participant，Telemetry 改為 Gateway side effect，並以公開 GitHub render 決定是否啟用兩圖 fallback。

**Tech Stack:** Markdown、Mermaid、pytest、Python 3.12、Ruff、GitHub Actions、GitHub README renderer

## Global Constraints

- 正體中文（zh-TW）是主要敘事語言；Gateway、Backend、Alias、Failover、Streaming、Telemetry、provenance、claims 等 technical terms 保留原文。
- 不將 Gateway、Backend、Telemetry、nonce 等詞彙生硬翻譯。
- 不修改 Gateway、Benchmark、Dashboard、SQLite schema、canonical benchmark claims、Docker 或 release policy 行為。
- 不使用 Mermaid HTML `<br/>`；GitHub sanitizer 不得造成文字黏連。
- 保留 Demo、Live、aggregate evidence 與 unpublished raw runs 的 truth boundary。
- 預設維持三張 Mermaid；只有公開 GitHub 的四 participant Sequence Diagram 不達標時才拆成兩張。
- README 不新增外部圖床、固定 SVG、JavaScript widget、badge wall 或裝飾性層級。

---

## File Map

- `README.md`：更新 section heading、三張圖的 visible copy 與四 participant Sequence Diagram。
- `tests/test_readme_portfolio.py`：鎖定新 heading、zh-TW stage labels、四 participant sequence 與不可遺失的 request semantics。
- `docs/superpowers/specs/2026-08-13-readme-zh-tw-sequence-readability-design.md`：本計畫的核准需求來源，不修改。
- `docs/superpowers/plans/2026-08-13-readme-zh-tw-sequence-readability.md`：本執行計畫。

### Task 1: 建立 zh-TW heading 與 Mermaid contract

**Files:**
- Modify: `tests/test_readme_portfolio.py`
- Test: `tests/test_readme_portfolio.py`

**Interfaces:**
- Consumes: `_readme() -> str`、`_mermaid_blocks(text: str) -> list[str]`、`_level_two_headings(text: str) -> list[str]`、`_assert_high_contrast_class_defs(...)`。
- Produces: README structure、visible copy、participant 與 truth-boundary contract，供 Task 2 實作。

- [ ] **Step 1: 更新 heading order contract**

將 `PORTFOLIO_SECTION_ORDER` 改為：

```python
PORTFOLIO_SECTION_ORDER = (
    "工程能力與驗證範圍",
    "系統邊界",
    "Request 與 Failover 流程",
    "Benchmark 證據鏈",
    "量測結果與解讀邊界",
    "Operations Console",
    "Quickstart",
    "設計決策與誠實範圍",
    "Repository map 與延伸文件",
    "License",
)
```

在 `test_readme_has_zh_tw_portfolio_information_architecture` 加入舊 heading 不存在的 contract：

```python
for stale_heading in (
    "## 一眼看重點",
    "## 系統邊界（System Context）",
    "## Benchmark 證據鏈（Evidence Pipeline）",
):
    assert stale_heading not in text
```

- [ ] **Step 2: 更新 System Context visible-label contract**

保留 `flowchart TB`、必要 node、edge 與 high-contrast class assertions，將 subgraph contract 改為：

```python
for group in (
    'subgraph Entry["輸入端"]',
    'subgraph Execution["執行邊界"]',
    'subgraph Observability["執行期可觀測性"]',
    'subgraph Evidence["已發布證據"]',
):
    assert group in system_context
```

visible node contract 至少包含：

```python
for label in (
    "OpenAI SDK／HTTP Client",
    "Async Benchmark Client",
    "FastAPI Gateway · Alias Routing／Capacity／Failover",
    "外部 Backend engines · llama.cpp／Ollama／LM Studio",
    "SQLite Telemetry",
    "Operations Console",
    "Aggregate artifacts",
    "Digest／Claim Verifier",
):
    assert label in system_context
```

- [ ] **Step 3: 更新四 participant Sequence contract**

將 participant contract 改為：

```python
for participant in ("Client", "Gateway", "Primary as Primary Backend", "Fallback as Fallback Backend"):
    assert f"participant {participant}" in failover_lifecycle
for removed_participant in ("Telemetry", "Limiter"):
    assert f"participant {removed_participant}" not in failover_lifecycle
```

鎖定精簡後的必要語意：

```python
for lifecycle_boundary in (
    "容量已滿 · 不排隊",
    "HTTP 429 + Retry-After",
    "成功或 4xx · 不 Failover",
    "connection／timeout／protocol／non-final 5xx",
    "記錄去敏 Failover event",
    "嘗試 Fallback Backend",
    "Streaming：持有 slot 至結束／失敗／取消",
    "記錄 metadata-only request telemetry",
    "finally 釋放 slot",
):
    assert lifecycle_boundary in failover_lifecycle
```

另加入：

```python
assert '"fontSize": "20px"' in failover_lifecycle
assert "<br" not in failover_lifecycle
```

- [ ] **Step 4: 更新 Evidence Pipeline zh-TW stage contract**

將五個 stage 斷言改為：

```python
for stage in (
    'subgraph Inputs["1 · 輸入"]',
    'subgraph Measurement["2 · 量測"]',
    'subgraph Boundary["3 · 發布邊界"]',
    'subgraph Verification["4 · 驗證"]',
    'subgraph Presentation["5 · 呈現"]',
):
    assert stage in evidence_pipeline
```

visible semantics 改為：

```python
for label in (
    "合成校準 prompts／workload matrix",
    "random 8-character nonce",
    "warmup 3 次 · 計時 5 次",
    "每次僅一個受測 engine 常駐 GPU",
    "request-level raw runs · 未公開",
    "aggregate CSV／controlled JSON／derived charts",
    "不在公開 repository 中",
    "provenance.json",
    "claims.json · canonical claims",
    "release checks",
):
    assert label in evidence_pipeline
assert "-. 未發布 .->" in evidence_pipeline
```

- [ ] **Step 5: 執行 focused test，確認 RED**

Run:

```powershell
uv run --frozen pytest tests/test_readme_portfolio.py -q
```

Expected: structure / Mermaid contract tests FAIL，原因為舊 heading、英文 stage labels、5 participant Sequence Diagram 與舊 message copy 尚未修改；hero、CPU verification 與 source-boundary tests 仍 PASS。

### Task 2: 實作 zh-TW 圖解與四 participant Sequence Diagram

**Files:**
- Modify: `README.md`
- Test: `tests/test_readme_portfolio.py`

**Interfaces:**
- Consumes: Task 1 的 exact heading、visible label、participant 與 lifecycle contract。
- Produces: 三張 GitHub-native Mermaid，其中 System Context / Evidence Pipeline 為 zh-TW-first，Sequence Diagram 為四 participant 單圖版本。

- [ ] **Step 1: 更新 README headings**

使用：

```markdown
## 工程能力與驗證範圍
## 系統邊界
## Request 與 Failover 流程
## Benchmark 證據鏈
```

其他 level-2 heading 保持原順序與文字。

- [ ] **Step 2: 翻譯 System Context 一般敘事 labels**

保留現有 `flowchart TB`、edge direction 與 classDef，使用 Task 1 的 exact labels。保留 `OpenAI-compatible HTTP`、`HTTP／SSE`、`read-only SQLite` 與 `aggregate evidence` 為 technical edge labels。

禁止加入 `<br/>`。Node label 使用 `·`、`／` 與 Mermaid 自動換行。

- [ ] **Step 3: 實作四 participant Sequence Diagram**

Sequence initialization 使用：

```mermaid
%%{init: {"themeVariables": {"fontSize": "20px"}, "sequence": {"actorFontSize": 20, "messageFontSize": 19, "noteFontSize": 18, "messageMargin": 22, "noteMargin": 8, "mirrorActors": false}}}%%
```

participant 使用：

```mermaid
participant Client
participant Gateway
participant Primary as Primary Backend
participant Fallback as Fallback Backend
```

主流程保留兩個 `alt`：

```mermaid
Client->>Gateway: POST /v1/chat/completions · Alias
Gateway->>Gateway: auth · Alias validation · acquire slot
alt 容量已滿 · 不排隊
    Gateway-->>Client: HTTP 429 + Retry-After
else 已取得 slot
    Gateway->>Primary: 解析 Alias · 嘗試 Primary
    alt Primary 成功或 4xx
        Primary-->>Gateway: 成功或 4xx · 不 Failover
    else 可重試的 upstream failure
        Primary--xGateway: connection／timeout／protocol／non-final 5xx
        Gateway->>Gateway: 記錄去敏 Failover event
        Gateway->>Fallback: 嘗試 Fallback Backend
        Fallback-->>Gateway: response
    end
    Gateway-->>Client: JSON response／Streaming SSE
    Note over Gateway,Primary: Streaming：持有 slot 至結束／失敗／取消
    Gateway->>Gateway: 記錄 metadata-only request telemetry
    Gateway->>Gateway: finally 釋放 slot
end
```

- [ ] **Step 4: 翻譯 Evidence Pipeline 一般敘事 labels**

保留 `flowchart TB` 與五階段混合方向。使用 Task 1 的 exact zh-TW stage / node labels，並將 publication edge 改為：

```mermaid
Raw -->|"僅發布 aggregate"| Aggregate
Raw -. 未發布 .-> Private
```

- [ ] **Step 5: 執行 focused tests，確認 GREEN**

Run:

```powershell
uv run --frozen ruff format tests/test_readme_portfolio.py
uv run --frozen pytest tests/test_readme_portfolio.py -q
uv run --frozen ruff check tests/test_readme_portfolio.py
uv run --frozen ruff format --check tests/test_readme_portfolio.py
git diff --check
```

Expected: focused tests、Ruff、format、diff check 全部 PASS。

- [ ] **Step 6: Commit implementation**

```powershell
git add -- README.md tests/test_readme_portfolio.py
git diff --cached --check
git commit -m "docs: localize README diagrams"
```

### Task 3: Mermaid render 與單圖可讀性決策

**Files:**
- Modify if visual review finds a defect: `README.md`
- Modify if contract follows justified visual change: `tests/test_readme_portfolio.py`
- Temporary outputs only: `$env:TEMP/local-inference-readme-zh-tw-diagrams-*`

**Interfaces:**
- Consumes: Task 2 的三個 Mermaid blocks。
- Produces: parser-valid renders，以及「保留四 participant 單圖」或「啟用兩圖 fallback」的 evidence-backed 決策。

- [ ] **Step 1: Extract Mermaid blocks**

```powershell
$diagramTemp = Join-Path $env:TEMP ('local-inference-readme-zh-tw-diagrams-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $diagramTemp | Out-Null
$env:PYTHONIOENCODING = 'utf-8'
uv run --frozen python "$env:USERPROFILE/.agents/skills/design-doc-mermaid/scripts/extract_mermaid.py" README.md --output-dir $diagramTemp --prefix readme
```

Expected: exactly three `.mmd` files。

- [ ] **Step 2: Render with pinned Mermaid CLI**

```powershell
$env:PUPPETEER_EXECUTABLE_PATH = Join-Path $env:ProgramFiles 'Google/Chrome/Application/chrome.exe'
Get-ChildItem -LiteralPath $diagramTemp -Filter '*.mmd' | ForEach-Object {
    $renderPath = [System.IO.Path]::ChangeExtension($_.FullName, '.png')
    npx --yes @mermaid-js/mermaid-cli@11.12.0 -i $_.FullName -o $renderPath -b transparent -w 1050
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
```

Expected: exit 0，exactly three non-empty PNG files。

- [ ] **Step 3: Visual review**

逐張檢查：

- zh-TW stage labels 沒有缺字、亂碼、黏字或 awkward wrap。
- System Context / Evidence Pipeline 的 technical terms 仍易辨識。
- Sequence participant、branch label、message、note 沒有 overlap 或 clipping。
- Sequence actor / message 在 1050 px render 中明顯大於舊版。
- 四 participant 單圖只保留 capacity 與 retryable failure 兩個必要 fragment。

- [ ] **Step 4: Apply render-driven refinements**

若有視覺缺陷，只可調整 label 長度、`·` / `／` 分隔、participant alias、font tokens、message margin 或 note 位置；禁止縮小到低於 spec 字級。每次修改後重跑 Task 2 focused verification 與 Task 3 render。

- [ ] **Step 5: Commit render refinements（有差異時）**

```powershell
git add -- README.md tests/test_readme_portfolio.py
git diff --cached --check
git commit -m "docs: refine zh-TW Mermaid layout"
```

若 source 沒有修改，略過此 commit。

### Task 4: 完整驗證、發布與公開 GitHub render gate

**Files:**
- No expected source changes before public render
- Modify only if public render exposes GitHub-specific issue: `README.md`、`tests/test_readme_portfolio.py`

**Interfaces:**
- Consumes: focused tests 與 local Mermaid render 通過的 commits。
- Produces: clean main、green CI、public desktop / narrow README evidence，以及單圖或 fallback 的最終版本。

- [ ] **Step 1: Run full local verification**

```powershell
uv run --frozen ruff check .
uv run --frozen ruff format --check .
uv run --frozen pytest -q
uv run --frozen python -m release_checks.cli
git diff --check
git status --short
```

Expected: all commands PASS，working tree clean。

- [ ] **Step 2: Integrate verified branch**

依 `finishing-a-development-branch` 執行使用者核准的 integration choice。若選 local merge，必須使用 fast-forward / non-destructive merge 並在合併後的 main 重跑 Step 1。

- [ ] **Step 3: Publication ancestry gate and non-force push**

```powershell
git fetch origin main
git merge-base --is-ancestor origin/main HEAD
git log --oneline origin/main..HEAD
git push origin HEAD:main
```

Expected: ancestry exit 0；push 不使用 force。

- [ ] **Step 4: Wait for exact GitHub Actions run**

找出 `headSha == git rev-parse HEAD` 的 CI run，等待 verify job success。Locked dependencies、Ruff、format、CPU tests、release policy、non-root image build 與 Compose smoke 必須全部通過。

- [ ] **Step 5: Desktop public render audit**

在約 1440 × 1000 viewport 驗證：

- 新 headings 正確，舊 headings 不存在。
- 三張 Mermaid 正常 rendered，沒有 syntax error。
- System Context / Evidence Pipeline visible copy 為 zh-TW-first。
- Sequence participant / branch / main messages 不開 zoom 即可閱讀。
- `Telemetry` 不再是 participant，但 telemetry side-effect text 存在。
- `article.scrollWidth <= article.clientWidth` 且 document 無 horizontal overflow。

若能存取 iframe computed style，記錄 actor / message text 的 font size；若受 cross-origin 限制，使用 screenshot 進行同 viewport 的 before / after visual comparison。

- [ ] **Step 6: Execute fallback only if desktop gate fails**

若四 participant 單圖仍不可直接閱讀，將 Request / Failover section 拆為兩張 Sequence Diagram：

1. `容量控制`：Client、Gateway，顯示 acquire slot、429、no queue。
2. `受控 Failover`：Client、Gateway、Primary Backend、Fallback Backend，顯示 retryable failure、Fallback、Streaming、telemetry side effects、finally release。

同步更新 tests 將 Mermaid block count 改為 4、鎖定兩張 sequence 的單一情境責任；重新執行 Task 3、Task 4 Step 1–5，另 commit：

```powershell
git add -- README.md tests/test_readme_portfolio.py
git diff --cached --check
git commit -m "docs: split request sequence scenarios"
```

- [ ] **Step 7: Narrow public render audit**

在約 760 × 900 viewport 驗證 headings、Mermaid 主結構、code blocks、tables 與 document horizontal overflow。Narrow view 可使用 Mermaid pan / zoom controls，但初始畫面仍須可辨識 diagram purpose 與主要 participants。

- [ ] **Step 8: Final evidence**

```powershell
git fetch origin main
git rev-parse HEAD
git rev-parse origin/main
git status --short
git log -5 --oneline --decorate
```

Expected: `HEAD == origin/main`，working tree clean。Final report 包含 test count、release checks、CI URL、public repository URL，以及是否啟用 fallback。
