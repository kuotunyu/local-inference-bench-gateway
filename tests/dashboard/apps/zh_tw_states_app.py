from __future__ import annotations

import os
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from dashboard.data.benchmark_repository import load_benchmark_evidence
from dashboard.data.live_status import GatewayStatus
from dashboard.data.operations_adapter import operations_display_from_runtime
from dashboard.data.public_demo import build_demo_operations, build_demo_snapshot
from dashboard.models import TelemetrySnapshot
from dashboard.views.evidence import render_evidence
from dashboard.views.overview import render_overview
from dashboard.views.reliability import render_reliability
from dashboard.views.requests import render_requests
from gateway.registry import Registry

state = os.environ["DASHBOARD_TEST_STATE"]

if state == "overview_empty":
    snapshot = TelemetrySnapshot(
        pd.DataFrame(columns=["timestamp"]), pd.DataFrame(), 1, Path("memory")
    )
    status = GatewayStatus(
        True,
        datetime.now(timezone.utc),
        {"http://127.0.0.1:8080/v1": {"healthy": True}},
    )
    operations = operations_display_from_runtime(status, Registry({}), source_kind="live")
    render_overview(snapshot, "live", operations)
elif state == "overview_public_demo":
    render_overview(build_demo_snapshot(), "demo", build_demo_operations())
elif state == "reliability_degraded":
    requests = pd.DataFrame({"error_message": [None], "status_code": [200]})
    snapshot = TelemetrySnapshot(requests, pd.DataFrame(), 1, Path("memory"))
    status = GatewayStatus(True, datetime.now(timezone.utc), {}, "backend_health_unauthorized")
    operations = operations_display_from_runtime(status, Registry({}), source_kind="live")
    render_reliability(snapshot, "live", operations)
elif state == "requests_filterable":
    requests = pd.DataFrame(
        [
            {
                "timestamp": "2026-08-13T00:00:00Z",
                "alias": "fast",
                "backend_name": "ollama",
                "model": "llama3",
                "status_code": 200,
                "success": 1,
                "total_latency_ms": 420,
                "ttft_ms": 110,
                "prompt_tokens": 12,
                "completion_tokens": 24,
                "stream": 1,
                "error_message": None,
            }
        ]
    )
    snapshot = TelemetrySnapshot(requests, pd.DataFrame(), 1, Path("memory"))
    render_requests(snapshot, "live", source_note="SQLite Request log")
elif state == "evidence_missing":
    render_evidence(load_benchmark_evidence(Path(os.environ["DASHBOARD_TEST_RESULTS_DIR"])))
elif state == "evidence_partial":
    evidence = load_benchmark_evidence(Path("bench/results"))
    render_evidence(replace(evidence, prefill=pd.DataFrame()))
