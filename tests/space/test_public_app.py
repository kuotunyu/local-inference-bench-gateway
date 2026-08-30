from __future__ import annotations

import html
import re
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

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


def _normalize_html_whitespace(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", value)
    return " ".join(html.unescape(text).split())


def _semantic_markdown(app: AppTest) -> str:
    return " ".join(_normalize_html_whitespace(item.value) for item in app.markdown)


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
    assert "current GPU execution" not in evidence_markdown.lower()
    assert "目前 GPU 執行" not in evidence_markdown
    assert not app.selectbox
