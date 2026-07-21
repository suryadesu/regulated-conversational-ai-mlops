"""Integration tests for the gateway app, bridged in-process to the provider stub."""

import json
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

import provider_stub.main as stub_main
from gateway.config import Settings
from gateway.main import create_app

TEST_SETTINGS = Settings(
    provider="openai_compat",
    provider_base_url="http://stub/v1",
    price_table_path=Path("services/gateway/config/prices.yaml"),
    prompt_dir=Path("prompts"),
    otlp_endpoint=None,
)


@pytest.fixture
def client(monkeypatch) -> TestClient:
    """Gateway TestClient whose provider HTTP layer is the real stub app over ASGI."""
    stub_main._fault_config = stub_main.FaultConfig()
    stub_transport = httpx.ASGITransport(app=stub_main.create_app())
    real_async_client = httpx.AsyncClient

    def bridged(*args, **kwargs):
        kwargs["transport"] = stub_transport
        return real_async_client(*args, **kwargs)

    monkeypatch.setattr("gateway.providers.openai_compat.httpx.AsyncClient", bridged)
    with TestClient(create_app(settings=TEST_SETTINGS)) as test_client:
        yield test_client


def test_healthz(client: TestClient) -> None:
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_readyz_ready_before_drain(client: TestClient) -> None:
    r = client.get("/readyz")
    assert r.status_code == 200
    assert r.json() == {"status": "ready"}


def test_chat_completion_unary(client: TestClient) -> None:
    r = client.post(
        "/v1/chat/completions",
        json={"messages": [{"role": "user", "content": "I need help with my account balance"}]},
    )
    assert r.status_code == 200
    data = r.json()
    assert set(data) == {"id", "model", "content", "usage"}
    assert "Acknowledged: I need help with my account balance" in data["content"]
    assert data["usage"]["prompt_tokens"] > 0


def test_chat_completion_stream(client: TestClient) -> None:
    with client.stream(
        "POST",
        "/v1/chat/completions",
        json={"messages": [{"role": "user", "content": "stream this"}], "stream": True},
    ) as r:
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/event-stream")
        body = r.read().decode()
    frames = [line[len("data: ") :] for line in body.splitlines() if line.startswith("data: ")]
    assert len(frames) >= 2
    assert frames[-1] == "[DONE]"
    deltas = [json.loads(f)["delta"] for f in frames[:-1]]
    assert "".join(deltas).endswith("stream this")


def test_malformed_body_maps_to_bad_request_envelope(client: TestClient) -> None:
    r = client.post("/v1/chat/completions", json={"intent": "no-messages"})
    assert r.status_code == 400
    err = r.json()["error"]
    assert err["code"] == "bad_request"
    assert err["retryable"] is False
    assert err["request_id"]


def test_provider_failure_maps_to_error_envelope(client: TestClient) -> None:
    # Force every upstream call to 500: retries exhaust, envelope surfaces as 502.
    r = client.post("/__faults_proxy", json={})  # no such route on the gateway
    assert r.status_code in (404, 405)
    fault_client = TestClient(stub_main.create_app())
    fault_client.post("/__faults", json={"fail_next": 10})
    r = client.post(
        "/v1/chat/completions", json={"messages": [{"role": "user", "content": "boom"}]}
    )
    assert r.status_code == 502
    err = r.json()["error"]
    assert err["code"] == "provider_unavailable"


def test_metrics_endpoint_mounted(client: TestClient) -> None:
    client.post(
        "/v1/chat/completions", json={"messages": [{"role": "user", "content": "measure me"}]}
    )
    r = client.get("/metrics/")
    assert r.status_code == 200
    assert "gateway_tokens_total" in r.text


def test_canary_probe_result_endpoint_sets_gauge(client: TestClient) -> None:
    from gateway.observability.metrics import CANARY_PROBE_SUCCESS

    r = client.post("/internal/canary-probe-result", json={"success": True})
    assert r.status_code == 200
    assert CANARY_PROBE_SUCCESS._value.get() == 1.0
    client.post("/internal/canary-probe-result", json={"success": False})
    assert CANARY_PROBE_SUCCESS._value.get() == 0.0
