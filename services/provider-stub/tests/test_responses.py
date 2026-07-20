"""Unit tests for deterministic response generation."""

import hashlib
import json

from provider_stub.responses import chunk_response, deterministic_response, judge_verdict_response


def test_deterministic_response_is_stable(tmp_path) -> None:
    messages = [{"role": "user", "content": "What is my balance?"}]
    first = deterministic_response(messages, tmp_path)
    second = deterministic_response(messages, tmp_path)
    assert first == second
    assert "What is my balance?" in first


def test_deterministic_response_fallback_format(tmp_path) -> None:
    content = "hello world"
    digest = hashlib.sha256(content.encode()).hexdigest()[:16]
    out = deterministic_response([{"role": "user", "content": content}], tmp_path)
    assert out == f"[stub:{digest}] Acknowledged: {content}"


def test_canned_file_preferred_over_fallback(tmp_path) -> None:
    content = "give me json"
    digest = hashlib.sha256(content.encode()).hexdigest()[:16]
    (tmp_path / f"{digest}.txt").write_text('{"canned": true}\n', encoding="utf-8")
    out = deterministic_response([{"role": "user", "content": content}], tmp_path)
    assert out == '{"canned": true}'


def test_judge_verdict_pass_and_fail_branches() -> None:
    ok = json.loads(judge_verdict_response("normal grading prompt"))
    assert ok["passed"] is True and ok["score"] == 5 and isinstance(ok["rationale"], str)
    bad = json.loads(judge_verdict_response("please FAIL_JUDGE this one"))
    assert bad["passed"] is False and bad["score"] == 1


def test_chunk_response_even_split() -> None:
    assert chunk_response("abcdefgh", 4) == ["ab", "cd", "ef", "gh"]


def test_chunk_response_remainder_goes_last() -> None:
    chunks = chunk_response("abcdefghi", 4)
    assert "".join(chunks) == "abcdefghi"
    assert len(chunks) == 4


def test_chunk_response_degenerate_cases() -> None:
    assert chunk_response("abcde", 1) == ["abcde"]
    assert chunk_response("", 5) == [""]
    assert "".join(chunk_response("ab", 5)) == "ab"
