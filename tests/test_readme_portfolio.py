from __future__ import annotations

import re
import struct
from pathlib import Path

REPO_ROOT = Path(__file__).parents[1]
HERO_ASSET = REPO_ROOT / "docs" / "assets" / "operations-console-overview.png"
README = REPO_ROOT / "README.md"


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
