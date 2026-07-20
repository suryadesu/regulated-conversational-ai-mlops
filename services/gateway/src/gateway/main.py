"""Gateway application factory and lifespan."""

import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from gateway.api.chat import ChatRequest, chat_completions
from gateway.api.health import healthz, readyz
from gateway.api.stream import chat_completions_stream
from gateway.config import Settings, get_settings
from gateway.draining import DrainState
from gateway.observability.metrics import load_price_table, setup_metrics
from gateway.observability.tracing import setup_tracing
from gateway.prompts.loader import load_prompt
from gateway.providers.base import make_provider
from gateway.providers.errors import ProviderError, to_error_response


async def _chat_dispatcher(request: ChatRequest, http_request: Request):
    """Single documented endpoint: dispatch on the request's stream flag."""
    if request.stream:
        return await chat_completions_stream(request, http_request)
    return await chat_completions(request, http_request)


def _provider_error_handler(request: Request, exc: Exception) -> JSONResponse:
    return to_error_response(exc, request_id=str(uuid.uuid4()))


def create_app(settings: Settings | None = None) -> FastAPI:
    """Construct the FastAPI app with routes, middleware, metrics, and tracing wired in.

    Args:
        settings: Settings | None — test-injection override; production omits it
            and the lifespan reads the environment via get_settings().

    Returns:
        FastAPI — the configured gateway application.
    """
    app = FastAPI(title="gateway", lifespan=lifespan)
    app.state._settings_override = settings
    app.post("/v1/chat/completions", response_model=None)(_chat_dispatcher)
    app.get("/healthz")(healthz)
    app.get("/readyz")(readyz)
    app.add_exception_handler(ProviderError, _provider_error_handler)
    app.add_exception_handler(RequestValidationError, _provider_error_handler)
    return app


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Init provider/metrics/tracing on startup; drain in-flight streams on shutdown.

    Args:
        app: FastAPI — the application whose state holds provider and drain handles.
    """
    settings = getattr(app.state, "_settings_override", None) or get_settings()
    app.state.settings = settings
    app.state.provider = make_provider(settings)
    app.state.drain = DrainState()
    app.state.prompt = load_prompt(
        settings.prompt_dir, settings.prompt_name, settings.prompt_version
    )
    app.state.price_table = load_price_table(settings.price_table_path)
    setup_metrics(app)
    if settings.otlp_endpoint:
        setup_tracing(app, settings.otlp_endpoint, "gateway")
    yield
    app.state.drain.begin_drain()
    await app.state.drain.wait_for_drain(settings.drain_timeout_s)
