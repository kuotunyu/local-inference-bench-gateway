"""Safe, short-lived gateway reachability and current-health reads."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import httpx


@dataclass(frozen=True)
class GatewayStatus:
    reachable: bool
    checked_at: datetime
    backends: dict[str, dict]
    reason: str | None = None


def fetch_gateway_status(
    base_url: str, api_key: str | None, timeout_s: float = 1.0
) -> GatewayStatus:
    checked_at = datetime.now(timezone.utc)
    try:
        with httpx.Client(timeout=timeout_s) as client:
            response = client.get(f"{base_url.rstrip('/')}/health")
            response.raise_for_status()
            backends: dict[str, dict] = {}
            reason = None
            if api_key:
                health = client.get(
                    f"{base_url.rstrip('/')}/health/backends",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                if health.status_code == 200 and isinstance(health.json(), dict):
                    backends = health.json()
                elif health.status_code in {401, 403}:
                    reason = "backend_health_unauthorized"
            return GatewayStatus(True, checked_at, backends, reason)
    except httpx.TimeoutException:
        return GatewayStatus(False, checked_at, {}, "timeout")
    except (httpx.HTTPError, ValueError):
        return GatewayStatus(False, checked_at, {}, "offline")
