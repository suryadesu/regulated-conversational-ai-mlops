"""Liveness and readiness endpoints."""

from fastapi import Request, Response


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
