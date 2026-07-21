"""Unit tests for the provider factory."""

from types import SimpleNamespace

import pytest

from gateway.providers.base import make_provider
from gateway.providers.bedrock import BedrockProvider
from gateway.providers.openai_compat import OpenAICompatProvider


def _settings(**overrides) -> SimpleNamespace:
    base = {
        "provider": "openai_compat",
        "provider_base_url": "http://provider-stub:8080/v1",
        "provider_api_key": "",
        "bedrock_model_id": "anthropic.claude-3-haiku-20240307-v1:0",
        "bedrock_endpoint_url": None,
        "request_timeout_s": 10.0,
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def test_openai_compat_selected() -> None:
    provider = make_provider(_settings())
    assert isinstance(provider, OpenAICompatProvider)


def test_bedrock_selected() -> None:
    provider = make_provider(_settings(provider="bedrock"))
    assert isinstance(provider, BedrockProvider)


def test_unknown_provider_raises() -> None:
    with pytest.raises(ValueError, match="unknown provider: nope"):
        make_provider(_settings(provider="nope"))
