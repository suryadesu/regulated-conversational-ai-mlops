"""Native-process end-to-end smoke test: real uvicorn stub + gateway + eval gate.

Spawns both services as subprocesses on localhost (no containers), proving the
full HTTP path: client -> gateway -> provider-stub, SSE streaming, and the
blocking eval gate's exit-code contract.
"""

import os
import subprocess
import sys
import time

import httpx
import pytest

STUB_PORT = 18080
GATEWAY_PORT = 18000
STUB_URL = f"http://127.0.0.1:{STUB_PORT}"
GATEWAY_URL = f"http://127.0.0.1:{GATEWAY_PORT}"


def _wait_healthy(url: str, timeout_s: float = 20.0) -> None:
    deadline = time.monotonic() + timeout_s
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            if httpx.get(f"{url}/healthz", timeout=2.0).status_code == 200:
                return
        except httpx.HTTPError as exc:
            last_error = exc
        time.sleep(0.5)
    raise TimeoutError(f"{url} never became healthy: {last_error}")


@pytest.fixture(scope="module")
def stack():
    env = os.environ.copy()
    env.update(
        {
            "GATEWAY_PROVIDER": "openai_compat",
            "GATEWAY_PROVIDER_BASE_URL": f"{STUB_URL}/v1",
            "GATEWAY_OTLP_ENDPOINT": "",
        }
    )
    procs = [
        subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "provider_stub.main:create_app", "--factory",
             "--host", "127.0.0.1", "--port", str(STUB_PORT)],
            env=env,
        ),
        subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "gateway.main:create_app", "--factory",
             "--host", "127.0.0.1", "--port", str(GATEWAY_PORT)],
            env=env,
        ),
    ]
    try:
        _wait_healthy(STUB_URL)
        _wait_healthy(GATEWAY_URL)
        yield
    finally:
        for proc in procs:
            proc.terminate()
        for proc in procs:
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()


@pytest.mark.e2e
def test_unary_completion_round_trip(stack) -> None:
    r = httpx.post(
        f"{GATEWAY_URL}/v1/chat/completions",
        json={"messages": [{"role": "user", "content": "I need help with my account balance"}]},
        timeout=30.0,
    )
    assert r.status_code == 200
    body = r.json()
    assert "Acknowledged: I need help with my account balance" in body["content"]
    assert body["usage"]["total_tokens"] > 0


@pytest.mark.e2e
def test_sse_stream_terminates_with_done(stack) -> None:
    with httpx.stream(
        "POST",
        f"{GATEWAY_URL}/v1/chat/completions",
        json={"messages": [{"role": "user", "content": "stream please"}], "stream": True},
        timeout=30.0,
    ) as r:
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/event-stream")
        body = r.read().decode()
    frames = [line for line in body.splitlines() if line.startswith("data: ")]
    assert frames[-1] == "data: [DONE]"
    assert len(frames) >= 2


@pytest.mark.e2e
def test_eval_gate_passes_against_live_stack(stack, monkeypatch, tmp_path) -> None:
    from eval_harness.gate import main as gate_main

    monkeypatch.setenv("EVAL_GATEWAY_URL", GATEWAY_URL)
    monkeypatch.setenv("EVAL_JUDGE_URL", STUB_URL)
    monkeypatch.setenv("EVAL_REPORT_PATH", str(tmp_path / "eval-report.json"))
    assert gate_main() == 0
    assert (tmp_path / "eval-report.json").is_file()


@pytest.mark.e2e
def test_eval_gate_blocks_when_provider_degrades(stack, monkeypatch, tmp_path) -> None:
    from eval_harness.gate import main as gate_main

    monkeypatch.setenv("EVAL_GATEWAY_URL", GATEWAY_URL)
    monkeypatch.setenv("EVAL_JUDGE_URL", STUB_URL)
    monkeypatch.setenv("EVAL_REPORT_PATH", str(tmp_path / "eval-report.json"))
    # Force every stub call to fail: the gate must exit non-zero (blocking behavior).
    httpx.post(f"{STUB_URL}/__faults", json={"fail_next": 1000}, timeout=5.0)
    try:
        exit_code = gate_main()
    except Exception:
        exit_code = 1  # a crashed suite must also block
    finally:
        httpx.post(f"{STUB_URL}/__faults", json={}, timeout=5.0)  # reset faults
    assert exit_code != 0
