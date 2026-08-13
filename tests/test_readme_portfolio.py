from __future__ import annotations

import re
import struct
from pathlib import Path

REPO_ROOT = Path(__file__).parents[1]
HERO_ASSET = REPO_ROOT / "docs" / "assets" / "operations-console-overview.png"
README = REPO_ROOT / "README.md"
PORTFOLIO_SECTION_ORDER = (
    "一眼看重點",
    "System Context",
    "Request 與 Failover lifecycle",
    "Benchmark evidence pipeline",
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
    assert "![Operations Console Demo Mode](docs/assets/operations-console-overview.png)" in text


def test_readme_diagrams_preserve_semantic_groups_and_rendering_contracts():
    blocks = _mermaid_blocks(_readme())
    assert len(blocks) == 3
    system_context, failover_lifecycle, evidence_pipeline = blocks

    assert system_context.lstrip().startswith("flowchart LR")
    for group in ("subgraph Repo", "subgraph External"):
        assert group in system_context
    for edge in ("HTTP / SSE", "read-only SQLite", "aggregate evidence"):
        assert edge in system_context
    for semantic_group in (
        "OpenAI SDK / HTTP Client",
        "FastAPI Gateway",
        "SQLite Telemetry",
        "llama.cpp / Ollama / LM Studio",
        "Async Benchmark Client",
        "Aggregate Artifacts",
        "Digest + Claim Verifier",
    ):
        assert semantic_group in system_context
    _assert_high_contrast_class_defs(system_context, {"actor", "runtime", "data", "external"})

    assert failover_lifecycle.lstrip().startswith("sequenceDiagram")
    for participant in (
        "Client",
        "Gateway",
        "Limiter",
        "Primary",
        "Fallback",
        "Telemetry",
    ):
        assert f"participant {participant}" in failover_lifecycle
    for lifecycle_boundary in (
        "HTTP 429 + Retry-After",
        "return without Failover",
        "sanitized Failover event",
        "Streaming SSE",
        "hold slot until stream end / failure / cancellation",
        "release slot in finally",
    ):
        assert lifecycle_boundary in failover_lifecycle

    assert evidence_pipeline.lstrip().startswith(("flowchart LR", "flowchart TD"))
    for semantic_group in (
        "Synthetic calibrated prompts + workload matrix",
        "random 8-character nonce",
        "request-level raw runs (not public)",
        "aggregate CSV + controlled JSON + derived charts",
        "provenance.json",
        "claims.json + release checks",
        "README + EVAL_REPORT + Operations Console",
    ):
        assert semantic_group in evidence_pipeline
    assert "-. publication boundary .->" in evidence_pipeline
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
