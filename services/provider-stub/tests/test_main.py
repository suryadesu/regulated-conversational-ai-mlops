"""Integration tests for the stub app over ASGI transport."""

import json

import httpx
import pytest

from provider_stub import main as stub_main


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def client() -> httpx.AsyncClient:
    # Fresh app per test; reset the module-level fault config so tests stay isolated.
    stub_main._fault_config = stub_main.FaultConfig()
    app = stub_main.create_app()
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://stub")


@pytest.mark.anyio
async def test_healthz(client) -> None:
    r = await client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


@pytest.mark.anyio
async def test_chat_completion_deterministic(client) -> None:
    body = {"messages": [{"role": "user", "content": "I need help with my account balance"}]}
    r = await client.post("/v1/chat/completions", json=body)
    assert r.status_code == 200
    data = r.json()
    content = data["choices"][0]["message"]["content"]
    assert "account balance" in content
    assert data["usage"]["prompt_tokens"] > 0
    assert data["usage"]["total_tokens"] == (
        data["usage"]["prompt_tokens"] + data["usage"]["completion_tokens"]
    )


@pytest.mark.anyio
async def test_fault_injection_via_control_endpoint(client) -> None:
    r = await client.post("/__faults", json={"error_rate": 1.0})
    assert r.status_code == 200
    r = await client.post(
        "/v1/chat/completions", json={"messages": [{"role": "user", "content": "hi"}]}
    )
    assert r.status_code == 500


@pytest.mark.anyio
async def test_judge_mode_fail_marker(client) -> None:
    body = {"model": "judge", "messages": [{"role": "user", "content": "rubric FAIL_JUDGE x"}]}
    r = await client.post("/v1/chat/completions", json=body)
    assert r.status_code == 200
    verdict = json.loads(r.json()["choices"][0]["message"]["content"])
    assert verdict["passed"] is False


@pytest.mark.anyio
async def test_streaming_ends_with_done(client) -> None:
    body = {"messages": [{"role": "user", "content": "stream me"}], "stream": True}
    async with client.stream("POST", "/v1/chat/completions", json=body) as r:
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/event-stream")
        raw = (await r.aread()).decode()
    frames = [line[len("data: ") :] for line in raw.splitlines() if line.startswith("data: ")]
    assert frames[-1] == "[DONE]"
    deltas = [
        json.loads(f)["choices"][0]["delta"].get("content", "") for f in frames[:-1]
    ]
    assert "".join(deltas).endswith("stream me")
