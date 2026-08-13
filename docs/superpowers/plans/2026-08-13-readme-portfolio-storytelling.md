# Portfolio README 與工程圖解 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 將 README 重構為正體中文優先、evidence-first 的作品集首頁，加入 Operations Console hero screenshot、System Context、Failover Sequence 與 Benchmark Evidence Pipeline 三張可驗證圖解。

**Architecture:** README 仍是 repository 的單一入口，不複製 DESIGN.md 與 EVAL_REPORT.md 的完整細節。圖解使用 GitHub-native Mermaid，各自負責 system structure、request-time failure semantics 與 evidence lineage；唯一 raster asset 是可重現的 Operations Console Demo Mode 截圖。

**Tech Stack:** GitHub Markdown、Mermaid、Streamlit、Playwright、Python 3.12、pytest、release checks、Ruff、GitHub Actions

## Global Constraints

- Primary language 必須是正體中文（zh-TW）；Gateway、Backend、Alias、Failover、Backpressure、Streaming、Telemetry、P50/P95、TTFT、Throughput、provenance 等技術詞保留原文。
- README 不得宣稱 enterprise-grade、production-ready、universal winner 或任何超出 single-process / single-workstation scope 的能力。
- Demo Mode、Live Mode、Benchmark Evidence 必須明確分開；Demo fixture 不得描述為 production traffic。
- canonical claims 必須逐字保留 `bench/results/claims.json` 的 `display` 字串，使 documentation verifier 可核驗。
- 三張 Mermaid 圖必須一圖一責任、具高對比 `classDef`，並在加入 README 後通過 renderer validation。
- Operations Console screenshot 必須顯示 `DEMO 資料` 標示、移除 browser chrome、寬 1440–1800 px、高 800–1100 px、檔案小於 1 MiB。
- 不修改 Gateway、Benchmark、Dashboard 或 release policy 的 runtime behavior。
- 不提交 runtime database、raw benchmark runs、browser cache、臨時 Mermaid render 或 Playwright automation 檔。

---

### Task 1: 建立可重現的 Operations Console hero asset

**Files:**
- Create: `tests/test_readme_portfolio.py`
- Create: `docs/assets/operations-console-overview.png`
- Verify: `dashboard/app.py`

**Interfaces:**
- Consumes: Streamlit Demo Mode at `dashboard/app.py`; publication limit `MAX_PUBLIC_FILE_BYTES` in `release_checks/publication.py`.
- Produces: `docs/assets/operations-console-overview.png`, which Task 2 embeds as README hero visual; `_png_dimensions(path: Path) -> tuple[int, int]` test helper.

- [ ] **Step 1: Write the failing asset contract**

Create `tests/test_readme_portfolio.py` with:

```python
from __future__ import annotations

import struct
from pathlib import Path

REPO_ROOT = Path(__file__).parents[1]
HERO_ASSET = REPO_ROOT / "docs" / "assets" / "operations-console-overview.png"


def _png_dimensions(path: Path) -> tuple[int, int]:
    header = path.read_bytes()[:24]
    assert header[:8] == b"\x89PNG\r\n\x1a\n"
    assert header[12:16] == b"IHDR"
    return struct.unpack(">II", header[16:24])


def test_operations_console_hero_is_readable_and_publication_safe():
    assert HERO_ASSET.is_file()
    width, height = _png_dimensions(HERO_ASSET)
    assert 1440 <= width <= 1800
    assert 800 <= height <= 1100
    assert HERO_ASSET.stat().st_size < 1024 * 1024
```

- [ ] **Step 2: Run the asset test and verify the intended failure**

Run:

```powershell
uv run --frozen pytest tests/test_readme_portfolio.py -q
```

Expected: FAIL because `docs/assets/operations-console-overview.png` does not exist.

- [ ] **Step 3: Inspect the Playwright helper contract before capture**

Run:

```powershell
uv run python C:/Users/3Hml/.codex/skills/webapp-testing/scripts/with_server.py --help
```

Use the documented argument order. Start the app with:

```powershell
uv run streamlit run dashboard/app.py --server.address 127.0.0.1 --server.port 8503 --server.headless true
```

Set `GATEWAY_DB_PATH` for that process to a deliberately missing temporary path so the screenshot always opens deterministic Demo Mode and never reads the owner's live database.

- [ ] **Step 4: Capture the hero screenshot with Playwright**

Use headless Chromium with this exact browser behavior in a temporary automation file:

```python
from pathlib import Path

from playwright.sync_api import sync_playwright

output = Path("docs/assets/operations-console-overview.png").resolve()
output.parent.mkdir(parents=True, exist_ok=True)

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1600, "height": 950}, device_scale_factor=1)
    page.goto("http://127.0.0.1:8503/", wait_until="networkidle")
    page.get_by_text("推論閘道運行概覽", exact=True).wait_for()
    page.get_by_text("DEMO 資料", exact=False).wait_for()
    page.screenshot(path=str(output), full_page=False)
    browser.close()
```

Delete the temporary automation file after capture. Do not crop or retouch metric values; Playwright output already excludes browser chrome.

- [ ] **Step 5: Visually inspect the screenshot**

Open `docs/assets/operations-console-overview.png` with the local image viewer. Confirm the title, Demo label, KPI ribbon and first chart are legible; confirm no browser chrome, user path, secret, debug panel or excessive blank margin is visible.

- [ ] **Step 6: Run the asset and publication tests**

Run:

```powershell
uv run --frozen pytest tests/test_readme_portfolio.py tests/test_publication.py -q
uv run --frozen python -m release_checks.cli
```

Expected: PASS; publication checks report no file-size, path or disclosure violation.

- [ ] **Step 7: Commit the hero asset contract**

```powershell
git add tests/test_readme_portfolio.py docs/assets/operations-console-overview.png
git commit -m "docs: add operations console hero"
```

---

### Task 2: 重構 README 敘事並加入三張 Mermaid 圖

**Files:**
- Modify: `README.md`
- Modify: `tests/test_readme_portfolio.py`
- Verify: `bench/results/claims.json`
- Verify: `DESIGN.md`
- Verify: `EVAL_REPORT.md`
- Verify: `SETUP.md`

**Interfaces:**
- Consumes: hero asset from Task 1; canonical claim strings from `bench/results/claims.json`; runtime semantics from `DESIGN.md` and source code.
- Produces: portfolio README with exactly three Mermaid blocks and stable section / source-boundary contracts.

- [ ] **Step 1: Add failing README structure tests**

Append to `tests/test_readme_portfolio.py`:

```python
import re

README = REPO_ROOT / "README.md"


def _readme() -> str:
    return README.read_text(encoding="utf-8")


def _mermaid_blocks(text: str) -> list[str]:
    return re.findall(r"```mermaid\s*\n(.*?)```", text, flags=re.DOTALL)


def test_readme_has_zh_tw_portfolio_information_architecture():
    text = _readme()
    for heading in (
        "## 一眼看重點",
        "## System Context",
        "## Request 與 Failover lifecycle",
        "## Benchmark evidence pipeline",
        "## 量測結果與解讀邊界",
        "## Operations Console",
        "## Quickstart",
        "## 設計決策與誠實範圍",
        "## Repository map 與延伸文件",
    ):
        assert heading in text
    assert "![Operations Console Demo Mode](docs/assets/operations-console-overview.png)" in text


def test_readme_uses_three_single_responsibility_diagrams():
    blocks = _mermaid_blocks(_readme())
    assert len(blocks) == 3
    assert blocks[0].lstrip().startswith("flowchart LR")
    assert blocks[1].lstrip().startswith("sequenceDiagram")
    assert blocks[2].lstrip().startswith(("flowchart LR", "flowchart TD"))
    assert "SQLite Telemetry" in blocks[0]
    assert "HTTP 429" in blocks[1]
    assert "finally" in blocks[1]
    assert "provenance.json" in blocks[2]
    assert "not public" in blocks[2]


def test_readme_keeps_data_sources_and_scope_distinct():
    text = _readme()
    for phrase in (
        "deterministic illustrative fixture",
        "metadata-only local telemetry",
        "aggregate evidence",
        "request-level raw runs 未公開",
        "single-process",
        "single-workstation",
    ):
        assert phrase in text
    lowered = text.lower()
    for overclaim in ("production-ready", "enterprise-grade", "universal winner"):
        assert overclaim not in lowered
```

- [ ] **Step 2: Run the README tests and verify the intended failures**

Run:

```powershell
uv run --frozen pytest tests/test_readme_portfolio.py -q
```

Expected: the existing README fails the new zh-TW headings, hero reference and three-diagram contracts.

- [ ] **Step 3: Replace README with the approved information architecture**

Rewrite `README.md` in this exact order:

```markdown
# Local Inference Benchmark + OpenAI-Compatible Gateway

[![CI](https://github.com/kuotunyu/local-inference-bench-gateway/actions/workflows/ci.yml/badge.svg)](https://github.com/kuotunyu/local-inference-bench-gateway/actions/workflows/ci.yml)
![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
[![License: MIT](https://img.shields.io/badge/License-MIT-718B7A.svg)](LICENSE)

一個 evidence-first 的本機推論工程專案：以共同 workload 比較 llama.cpp、Ollama 與 LM Studio，並提供具備 Alias Routing、ordered Failover、Backpressure、Streaming pass-through 與 SQLite Telemetry 的 OpenAI-compatible FastAPI Gateway。

[一眼看重點](#一眼看重點) · [System Context](#system-context) · [Benchmark Evidence](#benchmark-evidence-pipeline) · [Quickstart](#quickstart) · [延伸文件](#repository-map-與延伸文件)

![Operations Console Demo Mode](docs/assets/operations-console-overview.png)

## 一眼看重點
## System Context
## Request 與 Failover lifecycle
## Benchmark evidence pipeline
## 量測結果與解讀邊界
## Operations Console
## Quickstart
## 設計決策與誠實範圍
## Repository map 與延伸文件
## License
```

Use no more than three badges. The opening two paragraphs must explain that the repository combines a common Benchmark client, an OpenAI-compatible FastAPI Gateway and an evidence-first Operations Console; explicitly state that Backend engines are external processes.

- [ ] **Step 4: Add the System Context Mermaid block**

Use `flowchart LR` with these exact semantic groups and edges:

```text
OpenAI SDK / HTTP Client
  -> FastAPI Gateway
  -> Model Registry + Alias Routing
  -> Capacity Limiter + Failover
  -> llama.cpp / Ollama / LM Studio

Gateway -> SQLite Telemetry -> Operations Console
Async Benchmark Client -> three engines -> Aggregate Artifacts
Aggregate Artifacts -> Digest + Claim Verifier -> README / EVAL_REPORT / Operations Console
```

Wrap repository-owned components in one subgraph and external Backend engines in another. Label HTTP / SSE, read-only SQLite and aggregate evidence edges. Use four high-contrast `classDef` groups: actor, runtime, data, external; every class must set `fill`, `stroke`, `stroke-width` and `color`.

- [ ] **Step 5: Add the Failover Sequence Mermaid block**

Use participants `Client`, `Gateway`, `Limiter`, `Primary`, `Fallback`, `Telemetry` and show:

```text
POST /v1/chat/completions with Alias
auth + envelope + Alias validation
try_acquire
alt no capacity -> HTTP 429 + Retry-After
else slot acquired -> resolve ordered Backend chain
  alt primary success or 4xx -> return without Failover
  else connection / timeout / protocol / non-final 5xx
    -> sanitized Failover event
    -> fallback attempt
  end
  opt Streaming SSE
    -> hold slot until stream end / failure / cancellation
  end
  -> metadata-only request telemetry
  -> release slot in finally
end
```

Do not include request prompt, API key, raw response body or exception text.

- [ ] **Step 6: Add the Evidence Pipeline Mermaid block**

Use `flowchart LR` or `flowchart TD` with:

```text
Synthetic calibrated prompts + workload matrix
  -> random 8-character nonce
  -> Async Benchmark Client: 3 warmups + 5 timed runs
  -> one measured engine resident on GPU at a time
  -> request-level raw runs (not public)
  -> aggregate CSV + controlled JSON + derived charts
  -> provenance.json: versions, method, artifact class, SHA-256
  -> claims.json + release checks
  -> README + EVAL_REPORT + Operations Console
```

Render the `not public` branch with a dashed edge and neutral gray class. Use separate high-contrast classes for input, measurement, artifact, verification and presentation.

- [ ] **Step 7: Preserve exact canonical claims and adjacent caveats**

Include these exact strings without translation or punctuation changes:

```text
llama.cpp: 625.55 tok/s at concurrency 16
Ollama: 704.98 tok/s at concurrency 16
LM Studio: 686.72 tok/s at concurrency 16
Gateway median TTFT overhead: 1.66 ms
```

Immediately identify RTX 4090, measurement date 2026-07-17 and the hardware- / version-specific scope. Embed `bench/results/throughput_vs_concurrency.png` and link `EVAL_REPORT.md` for full conditions.

- [ ] **Step 8: Add the Demo / Live / Evidence source table and three Quickstart paths**

The source table must contain these truth boundaries verbatim:

```text
Demo Mode — deterministic illustrative fixture，非 production traffic
Live Mode — metadata-only local telemetry
Benchmark Evidence — aggregate evidence；request-level raw runs 未公開
```

Quickstart A starts Streamlit loopback, B starts Uvicorn loopback after registry configuration, and C runs frozen CPU verification. State that the repository does not install or start a Backend engine.

- [ ] **Step 9: Run targeted documentation checks**

Run:

```powershell
uv run --frozen pytest tests/test_readme_portfolio.py tests/test_documents.py tests/test_evidence.py -q
uv run --frozen python -m release_checks.evidence
uv run --frozen python -m release_checks.cli
git diff --check
```

Expected: all pass; every canonical claim remains discoverable and every local link target exists.

- [ ] **Step 10: Commit the README rewrite**

```powershell
git add README.md tests/test_readme_portfolio.py
git commit -m "docs: rebuild portfolio README"
```

---

### Task 3: 驗證 Mermaid render、README 視覺與完整 repository

**Files:**
- Verify: `README.md`
- Verify: `docs/assets/operations-console-overview.png`
- Verify: `tests/test_readme_portfolio.py`
- Temporary only: operating-system temp directory for `.mmd` and rendered `.png` files

**Interfaces:**
- Consumes: final README and hero asset from Tasks 1–2.
- Produces: validated diagrams, visual audit evidence and a clean, release-safe commit history; no new permanent artifact unless a concrete defect requires a README/test correction.

- [ ] **Step 1: Inspect the Mermaid extraction helper contract**

Run:

```powershell
uv run python C:/Users/3Hml/.agents/skills/design-doc-mermaid/scripts/extract_mermaid.py --help
```

Then extract all README Mermaid blocks into a fresh temporary directory outside the repository. Confirm exactly three `.mmd` files exist.

Use:

```powershell
$renderDir = Join-Path ([System.IO.Path]::GetTempPath()) ("local-inference-readme-mermaid-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $renderDir | Out-Null
uv run python C:/Users/3Hml/.agents/skills/design-doc-mermaid/scripts/extract_mermaid.py README.md --output-dir $renderDir --prefix readme
if ((Get-ChildItem -LiteralPath $renderDir -Filter '*.mmd').Count -ne 3) { throw 'expected exactly three Mermaid diagrams' }
```

- [ ] **Step 2: Render all three diagrams with a pinned temporary CLI**

Render every extracted `.mmd` with:

```powershell
Get-ChildItem -LiteralPath $renderDir -Filter '*.mmd' | ForEach-Object {
    $outputPath = [System.IO.Path]::ChangeExtension($_.FullName, '.png')
    npx --yes @mermaid-js/mermaid-cli@11.12.0 -i $_.FullName -o $outputPath -b transparent
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $outputPath)) { throw "Mermaid render failed: $($_.Name)" }
}
```

Expected: exit code 0 and a non-empty PNG for every diagram. Renderer output remains in the temporary directory and is not staged.

- [ ] **Step 3: Visually inspect rendered diagrams**

Open each rendered PNG with the local image viewer. Confirm:

- System Context has a clear system boundary and does not imply Operations Console can mutate Gateway configuration.
- Failover Sequence remains readable at README width and makes 429, retryable failure, telemetry and `finally` release visible.
- Evidence Pipeline makes the `not public` raw branch and verification gate visually distinct.
- Text has sufficient contrast; no node label is clipped; no diagram duplicates another diagram's purpose.

If a visual defect exists, edit only the affected Mermaid block and add a regression assertion to `tests/test_readme_portfolio.py` when the defect has a stable textual contract. Re-render before continuing.

- [ ] **Step 4: Run complete local verification**

Run:

```powershell
uv run --frozen ruff check .
uv run --frozen ruff format --check .
uv run --frozen pytest -q
uv run --frozen python -m release_checks.cli
git diff --check
git status --short
```

Expected: all tests and release checks pass; Ruff reports no issues; working tree is clean except an intentional, reviewed diagram correction waiting to be committed.

- [ ] **Step 5: Commit any validation-driven correction**

Only if Step 3 or Step 4 required changes:

```powershell
git add README.md tests/test_readme_portfolio.py
git commit -m "docs: polish README diagrams"
```

Re-run Step 4 after the commit and require a clean working tree.

---

### Task 4: 發布並檢查 GitHub 實際 render

**Files:**
- Verify remotely: `README.md`
- Verify remotely: `docs/assets/operations-console-overview.png`
- Verify remotely: GitHub Actions workflow `.github/workflows/ci.yml`

**Interfaces:**
- Consumes: clean local `main` with all Task 1–3 commits and passing release checks.
- Produces: updated public repository homepage and a verified passing CI run.

- [ ] **Step 1: Confirm safe publication state**

Run:

```powershell
git status --short
git log --oneline --decorate -5
uv run --frozen python -m release_checks.cli
```

Expected: clean tree, intended README/spec/asset commits only, all release checks pass.

- [ ] **Step 2: Push the current main branch**

```powershell
git push origin main
```

Expected: `origin/main` advances to the local verified commit without force push.

- [ ] **Step 3: Inspect the public GitHub README**

Open `https://github.com/kuotunyu/local-inference-bench-gateway` and verify at desktop width:

- hero screenshot appears before long technical detail and is sharp;
- zh-TW content and retained English terms read naturally;
- all three Mermaid diagrams render without GitHub error panels;
- source table, Throughput chart, Quickstart code blocks and local links render correctly;
- no horizontal overflow makes the primary text unreadable.

- [ ] **Step 4: Verify CI completion**

Inspect the newly triggered `CI` workflow and wait for the `verify` job to complete. Expected: checkout with full history, locked dependency sync, lint / format, CPU tests, release checks, image build and Compose smoke all pass.

- [ ] **Step 5: Fix only concrete render or CI defects**

If GitHub rendering or CI reveals a defect, reproduce it locally, make the smallest correction, run the complete Task 3 Step 4 verification, commit with a specific message, push normally, and re-check the replacement CI run. Do not weaken publication, evidence or history checks to obtain a green workflow.
