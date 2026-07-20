"""Unit tests for judge scoring and verdict parsing."""

import httpx
import pytest

from eval_harness.judge import judge_response, parse_verdict
from provider_stub.responses import judge_verdict_response


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def test_parse_wellformed_json() -> None:
    v = parse_verdict('{"passed": true, "score": 5, "rationale": "good"}')
    assert v.passed is True and v.score == 5 and v.rationale == "good"


def test_parse_fenced_json() -> None:
    raw = '```json\n{"passed": false, "score": 2, "rationale": "weak"}\n```'
    v = parse_verdict(raw)
    assert v.passed is False and v.score == 2


def test_parse_garbage_is_failed_vote_not_crash() -> None:
    v = parse_verdict("I think it's fine, ship it")
    assert v.passed is False and v.score == 0
    assert "unparseable" in v.rationale


@pytest.mark.anyio
async def test_judge_response_agrees_with_stub_format(monkeypatch) -> None:
    """The judge call shape and the stub's reply shape must agree end to end."""
    captured = {}

    def handler(request: httpx.Request) -> httpx.Response:
        import json

        body = json.loads(request.content)
        captured["model"] = body["model"]
        content = judge_verdict_response(body["messages"][-1]["content"])
        return httpx.Response(
            200,
            json={"choices": [{"message": {"role": "assistant", "content": content}}]},
        )

    real_client = httpx.AsyncClient

    def patched(*args, **kwargs):
        kwargs["transport"] = httpx.MockTransport(handler)
        return real_client(*args, **kwargs)

    monkeypatch.setattr("eval_harness.judge.httpx.AsyncClient", patched)
    verdict = await judge_response(
        "http://judge", rubric="stays professional", prompt="p", response="r"
    )
    assert captured["model"] == "judge"
    assert verdict.passed is True and verdict.score == 5

    failing = await judge_response(
        "http://judge", rubric="FAIL_JUDGE marker", prompt="p", response="r"
    )
    assert failing.passed is False
