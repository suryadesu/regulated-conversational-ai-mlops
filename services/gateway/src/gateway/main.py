"""Gateway application factory and lifespan."""

from collections.abc import AsyncIterator

from fastapi import FastAPI


def create_app() -> FastAPI:
    """Construct the FastAPI app with routes, middleware, metrics, and tracing wired in.

    Returns:
        FastAPI — the configured gateway application.
    """
    raise NotImplementedError


async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Init provider/metrics/tracing on startup; drain in-flight streams on shutdown.

    Args:
        app: FastAPI — the application whose state holds provider and drain handles.
    """
    raise NotImplementedError
    yield
