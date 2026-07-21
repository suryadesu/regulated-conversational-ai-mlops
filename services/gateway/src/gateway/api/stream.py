"""Streaming (SSE) chat completions endpoint."""

import json
import time
import uuid
from collections.abc import AsyncIterator

from fastapi import Request
from sse_starlette.sse import EventSourceResponse

from gateway.api.chat import ROUTE, ChatRequest, build_messages, upstream_label
from gateway.observability.metrics import (
    TTFT,
    estimate_cost_usd,
    record_completion,
    track_inflight,
    track_upstream_inflight,
)
from gateway.providers.base import CompletionChunk


async def chat_completions_stream(
    request: ChatRequest, http_request: Request
) -> EventSourceResponse:
    """Stream a chat completion as Server-Sent Events, draining safely on shutdown.

    The first chunk is pulled eagerly BEFORE the SSE response starts, so a
    provider failure surfaces as the standard JSON error envelope; once bytes
    have been sent there is no retry and no remapping (a partial stream must
    never be replayed).

    Args:
        request: ChatRequest — validated chat completion request with stream=True.
        http_request: Request — carries app.state (settings, provider, drain, price table).

    Returns:
        EventSourceResponse — SSE response yielding completion chunks then [DONE].
    """
    state = http_request.app.state
    settings = state.settings
    messages = build_messages(request, http_request)
    model = settings.default_model
    request_id = str(uuid.uuid4())

    chunks = state.provider.stream(
        messages,
        model=model,
        max_tokens=settings.max_tokens,
        temperature=settings.temperature,
    )
    iterator = chunks.__aiter__()
    # Eager first pull: ProviderError raised here propagates to the JSON envelope
    # handler because no response bytes have been written yet.
    first_chunk = await anext(iterator, None)

    async def replayed() -> AsyncIterator[CompletionChunk]:
        if first_chunk is not None:
            yield first_chunk
        async for chunk in iterator:
            yield chunk

    async def tracked() -> AsyncIterator[str]:
        start = time.monotonic()
        deltas: list[str] = []

        async def counted() -> AsyncIterator[CompletionChunk]:
            async for chunk in replayed():
                deltas.append(chunk.delta)
                yield chunk

        with track_inflight(ROUTE), track_upstream_inflight(upstream_label(settings)):
            async with state.drain.track_request():
                async for frame in sse_event_generator(counted(), request_id, model):
                    yield frame
        completion_text = "".join(deltas)
        prompt_estimate = sum(len(m.content.split()) for m in messages)
        completion_estimate = len(completion_text.split())
        record_completion(
            route=ROUTE,
            provider=settings.provider,
            model=model,
            prompt_tokens=prompt_estimate,
            completion_tokens=completion_estimate,
            latency_s=time.monotonic() - start,
            ttft_s=None,  # TTFT observed inside sse_event_generator; None avoids double-count
            cost_usd=estimate_cost_usd(
                model, prompt_estimate, completion_estimate, state.price_table
            ),
            code="200",
        )

    return EventSourceResponse(tracked(), ping=15)


async def sse_event_generator(
    chunks: AsyncIterator[CompletionChunk], request_id: str, model: str
) -> AsyncIterator[str]:
    """Serialize completion chunks to SSE frames; record TTFT on the first chunk, emit [DONE].

    Args:
        chunks: AsyncIterator[CompletionChunk] — upstream provider chunk stream.
        request_id: str — correlation id echoed in each SSE frame.
        model: str — model label for the TTFT histogram.
    """
    start = time.monotonic()
    first = True
    async for chunk in chunks:
        if first:
            TTFT.labels(route="chat_stream", model=model).observe(time.monotonic() - start)
            first = False
        yield json.dumps({"request_id": request_id, "delta": chunk.delta, "finish": chunk.finish})
    yield "[DONE]"
