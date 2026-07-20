"""Non-streaming chat completions endpoint and request/response models."""

import asyncio
import time
import uuid

from fastapi import Request
from pydantic import BaseModel

from gateway.observability.metrics import estimate_cost_usd, record_completion, track_inflight
from gateway.prompts.loader import render_system_prompt
from gateway.providers.base import Message
from gateway.providers.errors import ProviderTimeout
from gateway.providers.retry import with_retries

ROUTE = "/v1/chat/completions"


class ChatRequest(BaseModel):
    """Chat completion request accepted by the gateway."""

    messages: list[Message]  # ordered conversation turns
    intent: str | None = None  # routing hint selecting model/backend per intent
    stream: bool = False  # whether to return an SSE stream


class ChatResponse(BaseModel):
    """Non-streaming chat completion response returned by the gateway."""

    id: str  # gateway-assigned request id
    model: str  # model that produced the completion
    content: str  # assistant message content
    usage: dict[str, int]  # token accounting: prompt/completion/total


def build_messages(request: ChatRequest, http_request: Request) -> list[Message]:
    """Prepend the rendered pinned system prompt to the client's conversation turns."""
    system = render_system_prompt(http_request.app.state.prompt, {})
    return [Message(role="system", content=system), *request.messages]


async def chat_completions(request: ChatRequest, http_request: Request) -> ChatResponse:
    """Handle a non-streaming chat completion via the configured provider with retries.

    The whole retry loop runs under the total time budget
    (``settings.total_timeout_s``); exceeding it maps to ``ProviderTimeout``.

    Args:
        request: ChatRequest — validated chat completion request.
        http_request: Request — carries app.state (settings, provider, prompt, price table).

    Returns:
        ChatResponse — the completed assistant turn plus token usage.
    """
    state = http_request.app.state
    settings = state.settings
    messages = build_messages(request, http_request)
    start = time.monotonic()
    with track_inflight(ROUTE):
        try:
            async with asyncio.timeout(settings.total_timeout_s):
                result = await with_retries(
                    lambda: state.provider.complete(
                        messages,
                        model=settings.default_model,
                        max_tokens=settings.max_tokens,
                        temperature=settings.temperature,
                    ),
                    max_attempts=settings.max_retries,
                    base_delay_s=0.5,
                    max_delay_s=8.0,
                )
        except TimeoutError as exc:
            raise ProviderTimeout("total request budget exceeded") from exc
    latency_s = time.monotonic() - start
    cost = estimate_cost_usd(
        result.model, result.prompt_tokens, result.completion_tokens, state.price_table
    )
    record_completion(
        route=ROUTE,
        provider=settings.provider,
        model=result.model,
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
        latency_s=latency_s,
        ttft_s=None,
        cost_usd=cost,
        code="200",
    )
    return ChatResponse(
        id=str(uuid.uuid4()),
        model=result.model,
        content=result.content,
        usage={
            "prompt_tokens": result.prompt_tokens,
            "completion_tokens": result.completion_tokens,
            "total_tokens": result.prompt_tokens + result.completion_tokens,
        },
    )
