"""Evidence-first Streamlit Operations Console.

Run: uv run streamlit run dashboard/app.py --server.address 127.0.0.1
"""

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dashboard.components import render_state_message  # noqa: E402
from dashboard.data.benchmark_repository import load_benchmark_evidence  # noqa: E402
from dashboard.data.demo_fixture import select_default_mode  # noqa: E402
from dashboard.data.live_status import GatewayStatus, fetch_gateway_status  # noqa: E402
from dashboard.state import (  # noqa: E402
    AppTelemetryState,
    load_telemetry_state,
    slice_observation_window,
)
from dashboard.theme import apply_theme  # noqa: E402
from dashboard.views.evidence import render_evidence  # noqa: E402
from dashboard.views.overview import render_overview  # noqa: E402
from dashboard.views.reliability import render_reliability  # noqa: E402
from dashboard.views.requests import render_requests  # noqa: E402
from gateway.registry import Registry, RegistryConfigError, load_registry  # noqa: E402

PAGES = ["Overview", "Routing & Reliability", "Requests", "Benchmark Evidence"]
WINDOWS = {"15 分鐘": 15, "60 分鐘": 60, "6 小時": 360, "24 小時": 1440, "全部資料": None}


def _project_path(raw: str) -> Path:
    path = Path(raw)
    return path if path.is_absolute() else PROJECT_ROOT / path


def _demo_status() -> GatewayStatus:
    checked = datetime(2026, 8, 12, 17, 45, tzinfo=timezone.utc)
    return GatewayStatus(
        True,
        checked,
        {
            "http://127.0.0.1:8080/v1": {
                "healthy": True,
                "last_checked": checked.isoformat(),
            },
            "http://127.0.0.1:11434/v1": {
                "healthy": True,
                "last_checked": checked.isoformat(),
            },
        },
        "demo_fixture",
    )


def _header_controls(live_path: Path) -> tuple[str, str, int | None]:
    brand, controls = st.columns([1.1, 2.9], vertical_alignment="bottom")
    with brand:
        st.markdown(
            '<div class="ops-kicker" style="margin-bottom:.45rem">LOCAL INFERENCE / OPS</div>'
            '<div style="font-weight:820;font-size:1.08rem">Operations Console</div>',
            unsafe_allow_html=True,
        )
    with controls:
        source_col, window_col, refresh_col = st.columns([1, 1, 0.45], vertical_alignment="bottom")
        default = select_default_mode(live_path)
        with source_col:
            mode_label = st.selectbox(
                "Telemetry source",
                ["Demo Mode", "Live Mode"],
                index=1 if default == "live" else 0,
                key="telemetry_source",
            )
        with window_col:
            window_label = st.selectbox(
                "Observation window", list(WINDOWS), index=1, key="observation_window"
            )
        with refresh_col:
            st.button("重新整理", width="stretch", help="重新讀取 telemetry 與 current health")
    st.markdown('<div class="ops-rule" style="margin:.8rem 0"></div>', unsafe_allow_html=True)
    page = st.radio("View", PAGES, horizontal=True, label_visibility="collapsed")
    return ("live" if mode_label == "Live Mode" else "demo"), page, WINDOWS[window_label]


def main() -> None:
    st.set_page_config(
        page_title="Local Inference · Operations Console",
        page_icon="◉",
        layout="wide",
        initial_sidebar_state="collapsed",
    )
    apply_theme()
    live_path = _project_path(os.environ.get("GATEWAY_DB_PATH", "data/gateway.db"))
    mode, page, minutes = _header_controls(live_path)
    telemetry = load_telemetry_state(mode, live_path, PROJECT_ROOT / ".dashboard-cache")
    if mode == "live" and telemetry.source_kind == "live":
        st.session_state["last_live_snapshot"] = telemetry.snapshot
        st.session_state["last_live_refresh"] = datetime.now(timezone.utc)
    elif mode == "live" and "last_live_snapshot" in st.session_state:
        refreshed = st.session_state.get("last_live_refresh")
        stale_at = refreshed.isoformat() if isinstance(refreshed, datetime) else "unknown"
        telemetry = AppTelemetryState(
            st.session_state["last_live_snapshot"],
            "live",
            f"Live telemetry 暫時無法重新讀取；顯示 last-good stale snapshot（{stale_at}）。",
        )
    snapshot = slice_observation_window(telemetry.snapshot, minutes, telemetry.source_kind)
    if telemetry.notice:
        render_state_message("已切換至安全資料源", telemetry.notice, "warning")
    if mode == "live" and isinstance(st.session_state.get("last_live_refresh"), datetime):
        refreshed = st.session_state["last_live_refresh"].astimezone().strftime("%Y/%m/%d %H:%M:%S")
        st.caption(f"Last successful Live refresh · {refreshed}")

    registry_notice = None
    try:
        registry = load_registry(
            _project_path(os.environ.get("GATEWAY_MODELS_PATH", "gateway/models.yaml"))
        )
    except (OSError, RegistryConfigError) as exc:
        registry = Registry({})
        registry_notice = f"models.yaml 無法讀取：{exc}。Telemetry 與 Benchmark Evidence 仍可使用。"
    if registry_notice and page in {"Overview", "Routing & Reliability"}:
        render_state_message("Registry unavailable", registry_notice, "warning")

    if telemetry.source_kind == "demo":
        status = _demo_status()
    else:
        status = fetch_gateway_status(
            os.environ.get("GATEWAY_BASE_URL", "http://127.0.0.1:9000"),
            os.environ.get("GATEWAY_API_KEY") or None,
        )

    if page == "Overview":
        render_overview(
            snapshot,
            telemetry.source_kind,
            status,
            registry,
            observation_window_minutes=minutes,
        )
    elif page == "Routing & Reliability":
        render_reliability(snapshot, telemetry.source_kind, status, registry)
    elif page == "Requests":
        render_requests(snapshot, telemetry.source_kind)
    else:
        render_evidence(load_benchmark_evidence(PROJECT_ROOT / "bench/results"))

    st.markdown('<div class="ops-rule" style="margin-top:2.4rem"></div>', unsafe_allow_html=True)
    st.caption(
        "Single-workstation reference system · SQLite telemetry · aggregate benchmark evidence · loopback only"
    )


if __name__ == "__main__":
    main()
