"""OpenAI-compatible HTTP provider adapter (local stub, self-hosted server, or managed API)."""

from collections.abc import AsyncIterator

from gateway.providers.base import CompletionChunk, CompletionResult, Message


class OpenAICompatProvider:
    """Provider adapter speaking the OpenAI chat-completions wire format over HTTP."""

    def __init__(self, base_url: str, api_key: str, timeout_s: float) -> None:
        """Create an OpenAI-compatible client.

        Args:
            base_url: str — root URL of the OpenAI-compatible API.
            api_key: str — bearer token sent as the Authorization header.
            timeout_s: float — per-attempt request timeout in seconds.
        """
        raise NotImplementedError

    async def complete(
        self, messages: list[Message], model: str, max_tokens: int, temperature: float
    ) -> CompletionResult:
        """Return a full completion via POST /chat/completions.

        Args:
            messages: list[Message] — conversation turns.
            model: str — model identifier.
            max_tokens: int — maximum tokens to generate.
            temperature: float — sampling temperature.

        Returns:
            CompletionResult — completion content and token usage.
        """
        raise NotImplementedError

    def stream(
        self, messages: list[Message], model: str, max_tokens: int, temperature: float
    ) -> AsyncIterator[CompletionChunk]:
        """Return an async iterator of completion chunks via streaming POST /chat/completions.

        Args:
            messages: list[Message] — conversation turns.
            model: str — model identifier.
            max_tokens: int — maximum tokens to generate.
            temperature: float — sampling temperature.
        """
        raise NotImplementedError
