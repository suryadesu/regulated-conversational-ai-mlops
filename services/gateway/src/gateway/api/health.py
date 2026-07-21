"""Liveness and readiness endpoints."""

from fastapi import Request, Response

from gateway.observability.metrics import CANARY_PROBE_SUCCESS


async def healthz() -> dict[str, str]:
    """Liveness probe: 200 while the process is alive, even while draining.

    Returns:
        dict[str, str] — a static status document.
    """
    return {"status": "ok"}


async def readyz(http_request: Request) -> Response:
    """Readiness probe: 200 when serving, 503 once draining so the pod leaves endpoints.

    Args:
        http_request: Request — carries app.state.drain (shared drain-state handle).

    Returns:
        Response — 200 or 503 depending on drain state.
    """
    drain = http_request.app.state.drain
    if drain.is_draining:
        return Response(
            status_code=503, content='{"status":"draining"}', media_type="application/json"
        )
    return Response(status_code=200, content='{"status":"ready"}', media_type="application/json")


async def canary_probe_result(payload: dict) -> dict[str, str]:
    """Record the canary prober's eval outcome on the gateway_canary_probe_success gauge.

    The prober Job POSTs here instead of pushing through a Prometheus
    Pushgateway — one fewer piece of infrastructure for the same signal.

    Args:
        payload: dict — {"success": bool} from the canary-prober Job.

    Returns:
        dict[str, str] — acknowledgement document.
    """
    CANARY_PROBE_SUCCESS.set(1.0 if payload.get("success") else 0.0)
    return {"status": "recorded"}
