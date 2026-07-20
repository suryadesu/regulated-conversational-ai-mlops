"""Deterministic OpenAI-compatible provider stub with runtime fault injection."""

from fastapi import FastAPI, Response

from provider_stub.faults import FaultConfig


def create_app() -> FastAPI:
    """Construct the stub app exposing /v1/chat/completions and the POST /__faults control endpoint.

    Returns:
        FastAPI — the configured stub application.
    """
    raise NotImplementedError


async def chat_completions(payload: dict) -> Response:
    """Return a deterministic OpenAI-compatible completion, honoring stream and injected faults.

    Args:
        payload: dict — OpenAI-style chat completion request body.

    Returns:
        Response — JSON completion, an SSE stream when stream=True, or an injected error.
    """
    raise NotImplementedError


async def set_faults(config: FaultConfig) -> dict[str, str]:
    """Update the active fault-injection configuration (POST /__faults).

    Args:
        config: FaultConfig — new fault-injection parameters.

    Returns:
        dict[str, str] — acknowledgement document.
    """
    raise NotImplementedError
