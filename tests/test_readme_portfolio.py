from __future__ import annotations

import re
import struct
from pathlib import Path

REPO_ROOT = Path(__file__).parents[1]
HERO_ASSET = REPO_ROOT / "docs" / "assets" / "operations-console-overview.png"
README = REPO_ROOT / "README.md"
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


def _readme() -> str:
    return README.read_text(encoding="utf-8")


def _mermaid_blocks(text: str) -> list[str]:
    return re.findall(r"```mermaid\s*\n(.*?)```", text, flags=re.DOTALL)


def _level_two_headings(text: str) -> list[str]:
    return re.findall(r"^## (.+)$", text, flags=re.MULTILINE)


def _class_definitions(block: str) -> dict[str, dict[str, str]]:
    definitions: dict[str, dict[str, str]] = {}
    for name, declaration in re.findall(r"^\s*classDef (\w+) (.+);$", block, flags=re.MULTILINE):
        definitions[name] = dict(
            property_.split(":", maxsplit=1) for property_ in declaration.split(",")
        )
    return definitions


def _assert_high_contrast_class_defs(block: str, expected_names: set[str]) -> None:
    definitions = _class_definitions(block)
    assert definitions.keys() == expected_names
    for properties in definitions.values():
        assert properties["stroke-width"] == "2px"
        colors = [properties[property_] for property_ in ("fill", "stroke", "color")]
        assert all(re.fullmatch(r"#[0-9A-Fa-f]{6}", color) for color in colors)
        assert len(set(colors)) == len(colors)


def test_readme_has_zh_tw_portfolio_information_architecture():
    text = _readme()
    assert _level_two_headings(text) == list(PORTFOLIO_SECTION_ORDER)
    assert _level_two_headings(text)[-1] == "License"
    for stale_heading in (
        "## 一眼看重點",
        "## 系統邊界（System Context）",
        "## Benchmark 證據鏈（Evidence Pipeline）",
    ):
        assert stale_heading not in text
    assert "一眼看重點 · System Context · Benchmark Evidence · Quickstart · 延伸文件" not in text
    assert "![Operations Console Demo Mode](docs/assets/operations-console-overview.png)" in text


def test_readme_diagrams_preserve_semantic_groups_and_rendering_contracts():
    blocks = _mermaid_blocks(_readme())
    assert len(blocks) == 3
    system_context, failover_lifecycle, evidence_pipeline = blocks

    assert "flowchart TB" in system_context
    for group in (
        'subgraph Entry["輸入端"]',
        'subgraph Execution["執行邊界"]',
        'subgraph Observability["執行期可觀測性"]',
        'subgraph Evidence["已發布證據"]',
        "direction LR",
    ):
        assert group in system_context
    for edge in ("HTTP / SSE", "read-only SQLite", "aggregate evidence"):
        assert edge in system_context
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
    _assert_high_contrast_class_defs(system_context, {"actor", "runtime", "data", "external"})

    assert "sequenceDiagram" in failover_lifecycle
    for participant in (
        "Client",
        "Gateway",
        "Primary as Primary Backend",
        "Fallback as Fallback Backend",
    ):
        assert f"participant {participant}" in failover_lifecycle
    for removed_participant in ("Telemetry", "Limiter"):
        assert f"participant {removed_participant}" not in failover_lifecycle
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
    assert '"fontSize": "20px"' in failover_lifecycle
    assert "<br" not in failover_lifecycle

    assert "flowchart TB" in evidence_pipeline
    for stage in (
        'subgraph Inputs["1 · 輸入"]',
        'subgraph Measurement["2 · 量測"]',
        'subgraph Boundary["3 · 發布邊界"]',
        'subgraph Verification["4 · 驗證"]',
        'subgraph Presentation["5 · 呈現"]',
    ):
        assert stage in evidence_pipeline
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
    _assert_high_contrast_class_defs(
        evidence_pipeline,
        {"input", "measurement", "artifact", "verification", "presentation", "unpublished"},
    )


def test_readme_cpu_verification_uses_frozen_quality_and_release_checks():
    text = _readme()
    verification_block = re.search(
        r"uv sync --frozen --all-extras\n(.*?)```", text, flags=re.DOTALL
    )
    assert verification_block is not None
    commands = verification_block.group(1)
    expected_commands = (
        "uv run --frozen ruff check .",
        "uv run --frozen ruff format --check .",
        "uv run --frozen pytest -q",
        "uv run --frozen python -m release_checks.cli",
    )
    assert all(command in commands for command in expected_commands)
    assert [commands.index(command) for command in expected_commands] == sorted(
        commands.index(command) for command in expected_commands
    )


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
