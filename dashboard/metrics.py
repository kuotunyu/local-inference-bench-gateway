"""Pure telemetry filtering and aggregation."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class OverviewMetrics:
    request_count: int
    success_rate_pct: float | None
    p50_latency_ms: float | None
    p95_latency_ms: float | None
    p50_ttft_ms: float | None
    p95_ttft_ms: float | None
    failover_count: int


def percentile_or_none(series: pd.Series, quantile: float) -> float | None:
    values = pd.to_numeric(series, errors="coerce").dropna()
    return None if values.empty else float(values.quantile(quantile))


def compute_overview(requests: pd.DataFrame, failovers: pd.DataFrame) -> OverviewMetrics:
    count = len(requests)
    success = pd.to_numeric(requests.get("success", pd.Series(dtype=float)), errors="coerce")
    success_rate = None if success.dropna().empty else float(success.mean() * 100)
    latency = requests.get("total_latency_ms", pd.Series(dtype=float))
    ttft = requests.get("ttft_ms", pd.Series(dtype=float))
    return OverviewMetrics(
        request_count=count,
        success_rate_pct=success_rate,
        p50_latency_ms=percentile_or_none(latency, 0.5),
        p95_latency_ms=percentile_or_none(latency, 0.95),
        p50_ttft_ms=percentile_or_none(ttft, 0.5),
        p95_ttft_ms=percentile_or_none(ttft, 0.95),
        failover_count=len(failovers),
    )


def categorize_error(raw: str | None, status_code: int | None) -> str | None:
    if raw is None and status_code is None:
        return None
    value = (raw or "").lower()
    if status_code == 429 or "429" in value or "concurrency_limit" in value:
        return "Backpressure"
    if "connection" in value:
        return "Connection"
    if "stream" in value:
        return "Streaming"
    if (status_code is not None and status_code >= 500) or "http 5" in value:
        return "Upstream 5xx"
    if "timeout" in value:
        return "Timeout"
    if "protocol" in value:
        return "Protocol"
    return "Other"


def with_error_categories(requests: pd.DataFrame) -> pd.DataFrame:
    result = requests.copy()
    result["error_category"] = [
        categorize_error(error, int(status) if pd.notna(status) else None)
        for error, status in zip(
            result.get("error_message", pd.Series([None] * len(result))),
            result.get("status_code", pd.Series([None] * len(result))),
            strict=False,
        )
    ]
    return result


def bucket_request_series(requests: pd.DataFrame, frequency: str = "10min") -> pd.DataFrame:
    if requests.empty:
        return pd.DataFrame(columns=["timestamp", "requests", "p95_latency_ms"])
    frame = requests.copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True, errors="coerce")
    frame = frame.dropna(subset=["timestamp"]).set_index("timestamp")
    if frame.empty:
        return pd.DataFrame(columns=["timestamp", "requests", "p95_latency_ms"])
    grouped = frame.resample(frequency).agg(
        requests=("id", "count"),
        p95_latency_ms=("total_latency_ms", lambda values: values.quantile(0.95)),
    )
    return grouped.reset_index()
