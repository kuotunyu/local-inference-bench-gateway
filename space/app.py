"""Public evidence-only Streamlit experience.

Run: streamlit run space/app.py --server.address=0.0.0.0 --server.port=7860
"""

from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if sys.path[0] != str(PROJECT_ROOT):
    sys.path.insert(0, str(PROJECT_ROOT))

from dashboard.components import render_source_badge  # noqa: E402
from dashboard.data.public_demo import (  # noqa: E402
    build_demo_operations,
    build_demo_snapshot,
)
from dashboard.data.public_evidence import load_public_evidence  # noqa: E402
from dashboard.theme import apply_theme  # noqa: E402
from dashboard.views.evidence import render_evidence  # noqa: E402
from dashboard.views.overview import render_overview  # noqa: E402
from dashboard.views.reliability import render_reliability  # noqa: E402
from dashboard.views.requests import render_requests  # noqa: E402
from dashboard.windows import slice_observation_window  # noqa: E402

PAGES = (
    "Demo 概覽",
    "Demo Routing 與可靠性",
    "Demo Request 紀錄",
    "Committed Benchmark Evidence",
)
WINDOWS = {
    "15 分鐘": 15,
    "60 分鐘": 60,
    "6 小時": 360,
    "全部 Demo 資料": None,
}
DEMO_BADGE = "DETERMINISTIC DEMO · 非正式流量"
EVIDENCE_BADGE = "COMMITTED EVIDENCE · aggregate only · raw runs unpublished"
TRUTH_CONTRACT_HTML = """
<section class="truth-contract" aria-labelledby="truth-contract-title">
  <div id="truth-contract-title" class="truth-contract-title">公開證據示範（Demo Mode）</div>
  <p class="truth-contract-primary">此 Space 僅呈現 deterministic illustrative fixture 與 2026-07-17 committed aggregate evidence。它不會、也無法連線到訪客的本機 Gateway、SQLite、inference backend 或 GPU；不是 live inference service，亦無 SLA。Space 可能休眠或 cold-start；其啟動狀態不代表 Gateway uptime。</p>
  <p>Deterministic Demo data is illustrative and is not production or sampled traffic.</p>
  <p>Benchmark evidence is a dated, hardware- and version-specific snapshot.</p>
  <p>Request-level raw benchmark runs are not public.</p>
  <p>This Space cannot connect to a visitor's local system.</p>
  <p>This Space provides neither live inference nor an SLA.</p>
  <p>Hosting sleep or cold start is not system uptime evidence.</p>
</section>
"""


def render_truth_contract() -> None:
    """Render the immutable public claim ceiling as one semantic block."""
    st.markdown(TRUTH_CONTRACT_HTML, unsafe_allow_html=True)


def _render_demo_page(page: str) -> None:
    window_label = st.selectbox(
        "觀測時間範圍",
        list(WINDOWS),
        index=1,
        key="public_observation_window",
    )
    minutes = WINDOWS[window_label]
    snapshot = slice_observation_window(build_demo_snapshot(), minutes, "demo")
    operations = build_demo_operations()
    render_source_badge(
        "demo",
        "Deterministic illustrative fixture · 非 production 或 sampled traffic · 不是目前 reachability probe",
        label=DEMO_BADGE,
    )
    if page == "Demo 概覽":
        render_overview(snapshot, "demo", operations, observation_window_minutes=minutes)
    elif page == "Demo Routing 與可靠性":
        render_reliability(snapshot, "demo", operations)
    else:
        render_requests(
            snapshot,
            "demo",
            source_note="Deterministic in-memory Request fixture · 非 production traffic",
        )


def _render_evidence_page() -> None:
    state = load_public_evidence(PROJECT_ROOT / "bench/results")
    note = f"{state.verified_artifacts}/{state.declared_artifacts} declared artifacts verified"
    render_source_badge("evidence", note, label=EVIDENCE_BADGE)
    render_evidence(state.evidence)


def main() -> None:
    st.set_page_config(
        page_title="Local Inference Gateway · Public Evidence Demo",
        page_icon="◉",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    apply_theme()
    render_truth_contract()

    page = st.radio("頁面", PAGES, horizontal=True, label_visibility="collapsed")
    if page == "Committed Benchmark Evidence":
        _render_evidence_page()
    else:
        _render_demo_page(page)

    st.markdown('<div class="ops-rule" style="margin-top:2.4rem"></div>', unsafe_allow_html=True)
    st.caption("公開證據示範 · 無本機連線 · 無 hosted inference · 無 SLA")


if __name__ == "__main__":
    main()
