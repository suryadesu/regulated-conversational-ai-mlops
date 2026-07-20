"""Liveness and readiness endpoints."""

from fastapi import Response

from gateway.draining import DrainState


async def healthz() -> dict[str, str]:
    """Liveness probe: 200 while the process is alive, even while draining.

    Returns:
        dict[str, str] — a static status document.
    """
    raise NotImplementedError


async def readyz(drain: DrainState) -> Response:
    """Readiness probe: 200 when serving, 503 once draining so the pod leaves endpoints.

    Args:
        drain: DrainState — shared drain-state handle.

    Returns:
        Response — 200 or 503 depending on drain state.
    """
    raise NotImplementedError
