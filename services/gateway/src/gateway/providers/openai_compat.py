"""OpenAI-compatible HTTP provider adapter (local stub, self-hosted server, or managed API)."""

import json
from collections.abc import AsyncIterator

import httpx

from gateway.providers.base import CompletionChunk, CompletionResult, Message
from gateway.providers.errors import ProviderRateLimited, ProviderTimeout, ProviderUnavailable


def _raise_for_status(response: httpx.Response) -> None:
    """Map a non-2xx upstream status onto the provider error hierarchy."""
    status = response.status_code
    if status == 429:
        retry_after_raw = response.headers.get("Retry-After")
        retry_after = float(retry_after_raw) if retry_after_raw else None
        raise ProviderRateLimited("rate limited", retryable=True, retry_after=retry_after)
    if status in (500, 502, 503, 504):
        raise ProviderUnavailable(f"upstream error {status}", retryable=True)
    if 400 <= status < 500:
        raise ProviderUnavailable(f"upstream client error {status}", retryable=False)


class OpenAICompatProvider:
    """Provider adapter speaking the OpenAI chat-completions wire format over HTTP."""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout_s: float,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        """Create an OpenAI-compatible client.

        Args:
            base_url: str — root URL of the OpenAI-compatible API.
            api_key: str — bearer token sent as the Authorization header.
            timeout_s: float — per-attempt request timeout in seconds.
            transport: httpx.AsyncBaseTransport | None — test-injection hook
                (httpx.MockTransport in unit tests); None uses the real network.
        """
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self._client = httpx.AsyncClient(
            base_url=base_url, timeout=timeout_s, headers=headers, transport=transport
        )

    def _body(
        self, messages: list[Message], model: str, max_tokens: int, temperature: float, stream: bool
    ) -> dict:
        return {
            "model": model,
            "messages": [m.model_dump() for m in messages],
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": stream,
        }

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
        try:
            response = await self._client.post(
                "/chat/completions",
                json=self._body(messages, model, max_tokens, temperature, stream=False),
            )
        except httpx.TimeoutException as exc:
            raise ProviderTimeout("upstream timed out") from exc
        _raise_for_status(response)
        body = response.json()
        content = body["choices"][0]["message"]["content"]
        usage = body.get("usage") or {}
        prompt_estimate = sum(len(m.content.split()) for m in messages)
        return CompletionResult(
            content=content,
            model=body.get("model", model),
            prompt_tokens=usage.get("prompt_tokens", prompt_estimate),
            completion_tokens=usage.get("completion_tokens", len(content.split())),
        )

    def stream(
        self, messages: list[Message], model: str, max_tokens: int, temperature: float
    ) -> AsyncIterator[CompletionChunk]:
        """Return an async iterator of completion chunks via streaming POST /chat/completions.

        Timeout/status failures are mapped to provider errors only before the first
        chunk; once bytes have been yielded no retry or remapping happens (a
        partially delivered stream must never be replayed).

        Args:
            messages: list[Message] — conversation turns.
            model: str — model identifier.
            max_tokens: int — maximum tokens to generate.
            temperature: float — sampling temperature.
        """
        body = self._body(messages, model, max_tokens, temperature, stream=True)

        async def gen() -> AsyncIterator[CompletionChunk]:
            ctx = self._client.stream("POST", "/chat/completions", json=body)
            try:
                response = await ctx.__aenter__()
            except httpx.TimeoutException as exc:
                raise ProviderTimeout("upstream timed out") from exc
            try:
                if response.status_code != 200:
                    await response.aread()
                    _raise_for_status(response)
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    payload = line[len("data: ") :]
                    if payload == "[DONE]":
                        return
                    parsed = json.loads(payload)
                    choice = parsed["choices"][0]
                    yield CompletionChunk(
                        delta=choice.get("delta", {}).get("content") or "",
                        finish=choice.get("finish_reason") is not None,
                    )
            finally:
                await ctx.__aexit__(None, None, None)

        return gen()
