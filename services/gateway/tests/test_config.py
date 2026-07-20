"""Unit tests for gateway settings."""

from pathlib import Path

import pytest

from gateway.config import get_settings


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch) -> None:
    # Ensure no ambient GATEWAY_* env leaks into default-value assertions.
    import os

    for key in list(os.environ):
        if key.startswith("GATEWAY_"):
            monkeypatch.delenv(key, raising=False)


def test_defaults() -> None:
    s = get_settings()
    assert s.provider == "openai_compat"
    assert s.provider_base_url == "http://provider-stub:8080/v1"
    assert s.provider_api_key == ""
    assert s.default_model == "qwen2.5-0.5b-instruct"
    assert s.max_tokens == 512
    assert s.temperature == 0.2
    assert s.request_timeout_s == 10.0
    assert s.total_timeout_s == 30.0
    assert s.max_retries == 3
    assert s.prompt_name == "customer-support"
    assert s.prompt_version == "v1.0.0"
    assert s.prompt_dir == Path("prompts")
    assert s.drain_timeout_s == 160.0
    assert s.otlp_endpoint is None


def test_env_overrides(monkeypatch) -> None:
    monkeypatch.setenv("GATEWAY_PROVIDER", "bedrock")
    monkeypatch.setenv("GATEWAY_MAX_TOKENS", "256")
    s = get_settings()
    assert s.provider == "bedrock"
    assert s.max_tokens == 256
