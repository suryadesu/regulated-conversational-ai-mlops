"""Unit tests for the Bedrock provider adapter (botocore Stubber; no network)."""

import botocore.session
import pytest
from botocore.stub import Stubber

from gateway.providers.base import Message
from gateway.providers.bedrock import BedrockProvider
from gateway.providers.errors import ProviderRateLimited, ProviderUnavailable

MODEL_ID = "anthropic.claude-3-haiku-20240307-v1:0"
MESSAGES = [Message(role="user", content="hello")]


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def _stubbed_provider() -> tuple[BedrockProvider, Stubber]:
    provider = BedrockProvider(model_id=MODEL_ID, endpoint_url=None, timeout_s=5.0)
    client = botocore.session.get_session().create_client(
        "bedrock-runtime", region_name="us-east-1"
    )
    provider._client = client
    return provider, Stubber(client)


@pytest.mark.anyio
async def test_complete_success() -> None:
    provider, stubber = _stubbed_provider()
    stubber.add_response(
        "converse",
        {
            "output": {"message": {"role": "assistant", "content": [{"text": "hi from bedrock"}]}},
            "usage": {"inputTokens": 4, "outputTokens": 3, "totalTokens": 7},
            "stopReason": "end_turn",
            "metrics": {"latencyMs": 10},
        },
        {
            "modelId": MODEL_ID,
            "messages": [{"role": "user", "content": [{"text": "hello"}]}],
            "inferenceConfig": {"maxTokens": 64, "temperature": 0.2},
        },
    )
    with stubber:
        result = await provider.complete(MESSAGES, MODEL_ID, 64, 0.2)
    assert result.content == "hi from bedrock"
    assert result.model == MODEL_ID
    assert result.prompt_tokens == 4
    assert result.completion_tokens == 3


@pytest.mark.anyio
async def test_throttling_maps_to_rate_limited() -> None:
    provider, stubber = _stubbed_provider()
    stubber.add_client_error("converse", service_error_code="ThrottlingException")
    with stubber, pytest.raises(ProviderRateLimited):
        await provider.complete(MESSAGES, MODEL_ID, 64, 0.2)


@pytest.mark.anyio
async def test_other_client_error_maps_to_unavailable() -> None:
    provider, stubber = _stubbed_provider()
    stubber.add_client_error("converse", service_error_code="InternalServerException")
    with stubber, pytest.raises(ProviderUnavailable):
        await provider.complete(MESSAGES, MODEL_ID, 64, 0.2)


@pytest.mark.anyio
async def test_stream_yields_deltas_then_finish(monkeypatch) -> None:
    # botocore's Stubber cannot fabricate EventStream payloads, so the stream test
    # swaps converse_stream for a shape-identical dict return instead.
    provider, _ = _stubbed_provider()
    events = [
        {"contentBlockDelta": {"delta": {"text": "he"}}},
        {"contentBlockDelta": {"delta": {"text": "llo"}}},
        {"messageStop": {"stopReason": "end_turn"}},
    ]
    monkeypatch.setattr(provider._client, "converse_stream", lambda **kwargs: {"stream": events})
    chunks = [c async for c in provider.stream(MESSAGES, MODEL_ID, 64, 0.2)]
    assert [c.delta for c in chunks] == ["he", "llo", ""]
    assert [c.finish for c in chunks] == [False, False, True]
