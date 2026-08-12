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
            headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
            try:
                health = client.get(
                    f"{base_url.rstrip('/')}/health/backends",
                    headers=headers,
                )
                if health.status_code == 200:
                    content = health.json()
                    if isinstance(content, dict):
                        backends = {
                            str(url): entry
                            for url, entry in content.items()
                            if isinstance(entry, dict)
                        }
                        if len(backends) != len(content):
                            reason = "backend_health_protocol_error"
                    else:
                        reason = "backend_health_protocol_error"
                elif health.status_code in {401, 403}:
                    reason = "backend_health_unauthorized"
                else:
                    reason = "backend_health_unavailable"
            except httpx.TimeoutException:
                reason = "backend_health_timeout"
            except (httpx.HTTPError, ValueError):
                reason = "backend_health_unavailable"
            return GatewayStatus(True, checked_at, backends, reason)
    except httpx.TimeoutException:
        return GatewayStatus(False, checked_at, {}, "timeout")
    except (httpx.HTTPError, ValueError):
        return GatewayStatus(False, checked_at, {}, "offline")
