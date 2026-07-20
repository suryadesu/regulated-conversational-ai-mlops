"""AWS Bedrock provider adapter using the Converse / ConverseStream APIs (boto3)."""

from collections.abc import AsyncIterator

from gateway.providers.base import CompletionChunk, CompletionResult, Message


class BedrockProvider:
    """Provider adapter calling Bedrock Runtime Converse; endpoint_url points at floci locally."""

    def __init__(self, model_id: str, endpoint_url: str | None, timeout_s: float) -> None:
        """Create a Bedrock Converse client.

        Args:
            model_id: str — Bedrock model identifier for Converse.
            endpoint_url: str | None — floci endpoint locally; None uses real AWS.
            timeout_s: float — per-attempt request timeout in seconds.
        """
        raise NotImplementedError

    async def complete(
        self, messages: list[Message], model: str, max_tokens: int, temperature: float
    ) -> CompletionResult:
        """Return a full completion via the Bedrock Converse API.

        Args:
            messages: list[Message] — conversation turns.
            model: str — model identifier (overrides the constructor default).
            max_tokens: int — maximum tokens to generate.
            temperature: float — sampling temperature.

        Returns:
            CompletionResult — completion content and token usage.
        """
        raise NotImplementedError

    def stream(
        self, messages: list[Message], model: str, max_tokens: int, temperature: float
    ) -> AsyncIterator[CompletionChunk]:
        """Return an async iterator of completion chunks via the Bedrock ConverseStream API.

        Args:
            messages: list[Message] — conversation turns.
            model: str — model identifier (overrides the constructor default).
            max_tokens: int — maximum tokens to generate.
            temperature: float — sampling temperature.
        """
        raise NotImplementedError
