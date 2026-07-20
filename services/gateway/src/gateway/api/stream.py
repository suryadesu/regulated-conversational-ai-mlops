"""Streaming (SSE) chat completions endpoint."""

from collections.abc import AsyncIterator

from sse_starlette.sse import EventSourceResponse

from gateway.api.chat import ChatRequest
from gateway.providers.base import CompletionChunk


async def chat_completions_stream(request: ChatRequest) -> EventSourceResponse:
    """Stream a chat completion as Server-Sent Events, draining safely on shutdown.

    Args:
        request: ChatRequest — validated chat completion request with stream=True.

    Returns:
        EventSourceResponse — SSE response yielding completion chunks then [DONE].
    """
    raise NotImplementedError


async def sse_event_generator(
    chunks: AsyncIterator[CompletionChunk], request_id: str
) -> AsyncIterator[str]:
    """Serialize completion chunks to SSE frames; record TTFT on the first chunk, emit [DONE].

    Args:
        chunks: AsyncIterator[CompletionChunk] — upstream provider chunk stream.
        request_id: str — correlation id echoed in each SSE frame.
    """
    raise NotImplementedError
    yield ""
