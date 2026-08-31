from __future__ import annotations

import html
import re
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import pytest
from streamlit.testing.v1 import AppTest

from release_checks.space_bundle import _rendered_markdown

APP_PATH = Path(__file__).resolve().parents[2] / "space/app.py"
PUBLIC_PAGES = (
    "Demo 概覽",
    "Demo Routing 與可靠性",
    "Demo Request 紀錄",
    "Committed Benchmark Evidence",
)
TRUTH_CONTRACT = """\
公開證據示範（Demo Mode）
此 Space 僅呈現 deterministic illustrative fixture 與 2026-07-17 committed aggregate evidence。它不會、也無法連線到訪客的本機 Gateway、SQLite、inference backend 或 GPU；不是 live inference service，亦無 SLA。Space 可能休眠或 cold-start；其啟動狀態不代表 Gateway uptime。
Deterministic Demo data is illustrative and is not production or sampled traffic.
Benchmark evidence is a dated, hardware- and version-specific snapshot.
Request-level raw benchmark runs are not public.
This Space cannot connect to a visitor's local system.
This Space provides neither live inference nor an SLA.
Hosting sleep or cold start is not system uptime evidence.
"""
CANONICAL_EVIDENCE_LINKS = (
    (
        "GitHub source repository",
        "https://github.com/kuotunyu/local-inference-bench-gateway",
    ),
    (
        "Evaluation methodology (EVAL_REPORT.md)",
        "https://github.com/kuotunyu/local-inference-bench-gateway/blob/main/EVAL_REPORT.md",
    ),
    (
        "MIT License",
        "https://github.com/kuotunyu/local-inference-bench-gateway/blob/main/LICENSE",
    ),
    (
        "Third-party notices",
        "https://github.com/kuotunyu/local-inference-bench-gateway/blob/main/THIRD_PARTY_NOTICES.md",
    ),
)


def _normalize_html_whitespace(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", value)
    return " ".join(html.unescape(text).split())


def _semantic_markdown(app: AppTest) -> str:
    return " ".join(_normalize_html_whitespace(item.value) for item in app.markdown)


def _https_markdown_links(app: AppTest) -> list[tuple[str, str]]:
    links: list[tuple[str, str]] = []
    for item in app.markdown:
        rendered = _rendered_markdown(item.value)
        links.extend(
            (accessible_name, url)
            for accessible_name, url in re.findall(r"\[([^\]]+)\]\((https://[^)]+)\)", rendered)
        )
    return links


def _main_index(app: AppTest, element_type: str, containing: str | None = None) -> int:
    for index, element in enumerate(app.main):
        if element.type != element_type:
            continue
        if containing is None or containing in getattr(element, "value", ""):
            return index
    raise AssertionError(f"missing {element_type} element containing {containing!r}")


def test_truth_contract_is_first_and_no_live_control_exists() -> None:
    app = AppTest.from_file(str(APP_PATH)).run(timeout=20)

    assert not app.exception
    assert _normalize_html_whitespace(app.markdown[0].value) == _normalize_html_whitespace(
        TRUTH_CONTRACT
    )
    assert [item.label for item in app.selectbox] == ["觀測時間範圍"]
    assert not app.button
    assert all("Live 模式" not in item.value for item in app.markdown)
    assert all("GATEWAY_" not in item.value for item in app.markdown)

    truth_index = _main_index(app, "markdown", "公開證據示範（Demo Mode）")
    assert truth_index < _main_index(app, "radio")
    assert truth_index < _main_index(app, "selectbox")


@pytest.mark.parametrize("page", PUBLIC_PAGES)
def test_each_public_page_renders(page: str) -> None:
    app = AppTest.from_file(str(APP_PATH)).run(timeout=20)
    app.radio[0].set_value(page).run(timeout=20)

    assert not app.exception


def test_request_page_uses_only_the_deterministic_in_memory_fixture() -> None:
    app = AppTest.from_file(str(APP_PATH)).run(timeout=20)
    app.radio[0].set_value("Demo Request 紀錄").run(timeout=20)

    assert not app.exception
    assert "Deterministic in-memory Request fixture" in _semantic_markdown(app)
    assert len(app.dataframe) == 1
    assert len(app.dataframe[0].value) == 60


def test_public_app_truth_contract_and_control_surface() -> None:
    app = AppTest.from_file(str(APP_PATH)).run(timeout=20)

    assert not app.exception
    demo_markdown = _semantic_markdown(app)
    assert "公開證據示範（Demo Mode）" in demo_markdown
    assert "DETERMINISTIC DEMO · 非正式流量" in demo_markdown
    assert "Fixture backend state" in demo_markdown
    assert "This Space cannot connect to a visitor's local system." in demo_markdown
    assert "不是目前 reachability probe" in demo_markdown
    assert "This Space provides neither live inference nor an SLA." in demo_markdown
    assert "http://127.0.0.1:9000" not in demo_markdown
    assert "localhost:9000" not in demo_markdown
    assert not app.text_input
    assert not app.text_area
    assert not app.file_uploader
    assert not app.chat_input

    app.radio[0].set_value("Committed Benchmark Evidence").run(timeout=20)
    assert not app.exception
    evidence_markdown = _semantic_markdown(app)
    assert "COMMITTED EVIDENCE · aggregate only · raw runs unpublished" in evidence_markdown
    assert "2026-07-17" in evidence_markdown
    assert "NVIDIA GeForce RTX 4090" in evidence_markdown
    assert "Ministral-3-8B-Instruct-2512-Q4_K_M.gguf" in evidence_markdown
    assert "Request-level raw runs 未公開" in evidence_markdown
    assert "current gpu execution" not in evidence_markdown.lower()
    assert "目前 GPU 執行" not in evidence_markdown
    assert not app.selectbox


def test_evidence_first_screen_exposes_only_canonical_https_sources() -> None:
    app = AppTest.from_file(str(APP_PATH)).run(timeout=20)
    app.radio[0].set_value("Committed Benchmark Evidence").run(timeout=20)

    assert not app.exception
    assert _https_markdown_links(app) == list(CANONICAL_EVIDENCE_LINKS)
    source_links_index = _main_index(app, "markdown", "[GitHub source repository]")
    assert source_links_index < _main_index(app, "markdown", "Aggregate decode throughput")


def test_evidence_link_proof_ignores_comments_and_code_spans() -> None:
    app = cast(
        AppTest,
        SimpleNamespace(
            markdown=[
                SimpleNamespace(
                    value="""<!-- [Comment only](https://example.test/comment) -->
`[Code only](https://example.test/code)`
[Visible source](https://example.test/visible)
"""
                )
            ]
        ),
    )

    assert _https_markdown_links(app) == [("Visible source", "https://example.test/visible")]
