"""Non-streaming chat completions endpoint and request/response models."""

from pydantic import BaseModel

from gateway.providers.base import Message


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


async def chat_completions(request: ChatRequest) -> ChatResponse:
    """Handle a non-streaming chat completion via the configured provider with retries.

    Args:
        request: ChatRequest — validated chat completion request.

    Returns:
        ChatResponse — the completed assistant turn plus token usage.
    """
    raise NotImplementedError
