"""Unit tests for the OpenAI-compatible provider adapter (httpx.MockTransport)."""

import json

import httpx
import pytest

from gateway.providers.base import Message
from gateway.providers.errors import ProviderRateLimited, ProviderTimeout, ProviderUnavailable
from gateway.providers.openai_compat import OpenAICompatProvider

MESSAGES = [Message(role="user", content="hello there")]


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def _provider(handler) -> OpenAICompatProvider:
    return OpenAICompatProvider(
        base_url="http://upstream/v1",
        api_key="test-key",
        timeout_s=5.0,
        transport=httpx.MockTransport(handler),
    )


@pytest.mark.anyio
async def test_complete_success() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/chat/completions"
        assert request.headers["authorization"] == "Bearer test-key"
        body = json.loads(request.content)
        assert body["stream"] is False
        assert body["max_tokens"] == 64
        return httpx.Response(
            200,
            json={
                "model": "test-model",
                "choices": [{"message": {"role": "assistant", "content": "hi!"}}],
                "usage": {"prompt_tokens": 2, "completion_tokens": 1},
            },
        )

    result = await _provider(handler).complete(MESSAGES, "test-model", 64, 0.2)
    assert result.content == "hi!"
    assert result.model == "test-model"
    assert result.prompt_tokens == 2
    assert result.completion_tokens == 1


@pytest.mark.anyio
async def test_429_raises_rate_limited_with_retry_after() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, headers={"Retry-After": "3"}, json={})

    with pytest.raises(ProviderRateLimited) as exc_info:
        await _provider(handler).complete(MESSAGES, "m", 64, 0.2)
    assert exc_info.value.retry_after == 3.0


@pytest.mark.anyio
async def test_503_raises_retryable_unavailable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={})

    with pytest.raises(ProviderUnavailable) as exc_info:
        await _provider(handler).complete(MESSAGES, "m", 64, 0.2)
    assert exc_info.value.retryable is True


@pytest.mark.anyio
async def test_404_raises_non_retryable_unavailable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={})

    with pytest.raises(ProviderUnavailable) as exc_info:
        await _provider(handler).complete(MESSAGES, "m", 64, 0.2)
    assert exc_info.value.retryable is False


@pytest.mark.anyio
async def test_timeout_raises_provider_timeout() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow upstream")

    with pytest.raises(ProviderTimeout):
        await _provider(handler).complete(MESSAGES, "m", 64, 0.2)


@pytest.mark.anyio
async def test_missing_usage_estimated_from_word_counts() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"choices": [{"message": {"role": "assistant", "content": "three word reply"}}]},
        )

    result = await _provider(handler).complete(MESSAGES, "m", 64, 0.2)
    assert result.completion_tokens == 3
    assert result.prompt_tokens == 2  # "hello there"


@pytest.mark.anyio
async def test_stream_yields_chunks_until_done() -> None:
    frames = [
        'data: {"choices": [{"delta": {"content": "he"}, "finish_reason": null}]}',
        'data: {"choices": [{"delta": {"content": "llo"}, "finish_reason": null}]}',
        'data: {"choices": [{"delta": {}, "finish_reason": "stop"}]}',
        "data: [DONE]",
        'data: {"never": "reached"}',
    ]

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            headers={"content-type": "text/event-stream"},
            content="\n".join(frames).encode(),
        )

    chunks = [c async for c in _provider(handler).stream(MESSAGES, "m", 64, 0.2)]
    assert [c.delta for c in chunks] == ["he", "llo", ""]
    assert [c.finish for c in chunks] == [False, False, True]


@pytest.mark.anyio
async def test_stream_maps_status_before_first_chunk() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={})

    with pytest.raises(ProviderRateLimited):
        async for _ in _provider(handler).stream(MESSAGES, "m", 64, 0.2):
            raise AssertionError("no chunk should be yielded")
