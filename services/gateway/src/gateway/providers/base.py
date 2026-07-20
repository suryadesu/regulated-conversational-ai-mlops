"""Provider contract and factory: the single abstraction over managed and self-hosted inference."""

from collections.abc import AsyncIterator
from typing import Protocol

from pydantic import BaseModel

from gateway.config import Settings


class Message(BaseModel):
    """A single chat message."""

    role: str  # one of: system | user | assistant
    content: str  # message text


class CompletionChunk(BaseModel):
    """A streamed increment of a completion."""

    delta: str  # incremental text for this chunk
    finish: bool  # True on the terminal chunk


class CompletionResult(BaseModel):
    """A full non-streaming completion with token accounting."""

    content: str  # assistant message content
    model: str  # model that produced the completion
    prompt_tokens: int  # tokens consumed by the prompt
    completion_tokens: int  # tokens produced in the completion


class ProviderClient(Protocol):
    """Structural contract implemented by every inference backend adapter."""

    async def complete(
        self, messages: list[Message], model: str, max_tokens: int, temperature: float
    ) -> CompletionResult:
        """Return a full completion for the given messages."""
        ...

    def stream(
        self, messages: list[Message], model: str, max_tokens: int, temperature: float
    ) -> AsyncIterator[CompletionChunk]:
        """Return an async iterator of completion chunks for the given messages."""
        ...


def make_provider(settings: Settings) -> ProviderClient:
    """Build the provider adapter selected by settings.provider.

    Adapters are imported lazily: they import this module's models, so a
    top-level import here would be circular.

    Args:
        settings: Settings — runtime configuration selecting and parameterizing the adapter.

    Returns:
        ProviderClient — an adapter satisfying the provider contract.
    """
    if settings.provider == "openai_compat":
        from gateway.providers.openai_compat import OpenAICompatProvider

        return OpenAICompatProvider(
            base_url=settings.provider_base_url,
            api_key=settings.provider_api_key,
            timeout_s=settings.request_timeout_s,
        )
    if settings.provider == "bedrock":
        from gateway.providers.bedrock import BedrockProvider

        return BedrockProvider(
            model_id=settings.bedrock_model_id,
            endpoint_url=settings.bedrock_endpoint_url,
            timeout_s=settings.request_timeout_s,
        )
    raise ValueError(f"unknown provider: {settings.provider}")
