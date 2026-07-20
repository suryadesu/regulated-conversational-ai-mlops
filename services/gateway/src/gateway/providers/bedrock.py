"""AWS Bedrock provider adapter using the Converse / ConverseStream APIs (boto3)."""

import asyncio
import os
from collections.abc import AsyncIterator

import boto3
import botocore.config
import botocore.exceptions

from gateway.providers.base import CompletionChunk, CompletionResult, Message
from gateway.providers.errors import ProviderRateLimited, ProviderTimeout, ProviderUnavailable


def _map_client_error(exc: botocore.exceptions.ClientError) -> Exception:
    code = exc.response.get("Error", {}).get("Code", "")
    if code == "ThrottlingException":
        return ProviderRateLimited(f"bedrock throttled: {code}")
    if code == "ModelTimeoutException":
        return ProviderTimeout(f"bedrock model timeout: {code}")
    return ProviderUnavailable(str(exc), retryable=True)


class BedrockProvider:
    """Provider adapter calling Bedrock Runtime Converse; endpoint_url points at floci locally."""

    def __init__(self, model_id: str, endpoint_url: str | None, timeout_s: float) -> None:
        """Create a Bedrock Converse client.

        The region falls back to us-east-1 when no AWS region is configured, so
        construction never depends on ambient AWS CLI config (CI runners have none).

        Args:
            model_id: str — Bedrock model identifier for Converse.
            endpoint_url: str | None — floci endpoint locally; None uses real AWS.
            timeout_s: float — per-attempt request timeout in seconds.
        """
        self.model_id = model_id
        region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "us-east-1"
        self._client = boto3.client(
            "bedrock-runtime",
            endpoint_url=endpoint_url,
            region_name=region,
            config=botocore.config.Config(read_timeout=timeout_s, connect_timeout=timeout_s),
        )

    @staticmethod
    def _converse_kwargs(
        model_id: str, messages: list[Message], max_tokens: int, temperature: float
    ) -> dict:
        return {
            "modelId": model_id,
            "messages": [{"role": m.role, "content": [{"text": m.content}]} for m in messages],
            "inferenceConfig": {"maxTokens": max_tokens, "temperature": temperature},
        }

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
        model_id = model or self.model_id
        kwargs = self._converse_kwargs(model_id, messages, max_tokens, temperature)
        try:
            response = await asyncio.to_thread(lambda: self._client.converse(**kwargs))
        except botocore.exceptions.ClientError as exc:
            raise _map_client_error(exc) from exc
        return CompletionResult(
            content=response["output"]["message"]["content"][0]["text"],
            model=model_id,
            prompt_tokens=response["usage"]["inputTokens"],
            completion_tokens=response["usage"]["outputTokens"],
        )

    def stream(
        self, messages: list[Message], model: str, max_tokens: int, temperature: float
    ) -> AsyncIterator[CompletionChunk]:
        """Return an async iterator of completion chunks via the Bedrock ConverseStream API.

        The blocking EventStream is drained inside the offloaded thread (Bedrock
        responses are bounded token streams) rather than bridging a sync iterator
        across the event loop live.

        Args:
            messages: list[Message] — conversation turns.
            model: str — model identifier (overrides the constructor default).
            max_tokens: int — maximum tokens to generate.
            temperature: float — sampling temperature.
        """
        model_id = model or self.model_id
        kwargs = self._converse_kwargs(model_id, messages, max_tokens, temperature)

        def drain() -> list[dict]:
            response = self._client.converse_stream(**kwargs)
            return list(response["stream"])

        async def gen() -> AsyncIterator[CompletionChunk]:
            try:
                events = await asyncio.to_thread(drain)
            except botocore.exceptions.ClientError as exc:
                raise _map_client_error(exc) from exc
            for event in events:
                if "contentBlockDelta" in event:
                    yield CompletionChunk(
                        delta=event["contentBlockDelta"]["delta"]["text"], finish=False
                    )
                elif "messageStop" in event:
                    yield CompletionChunk(delta="", finish=True)

        return gen()
