"""Unit tests for the retry policy."""

import pytest

from gateway.providers.errors import ProviderRateLimited, ProviderTimeout, ProviderUnavailable
from gateway.providers.retry import is_retryable, with_retries


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.mark.parametrize(
    ("code", "expected"),
    [(429, True), (500, True), (502, True), (503, True), (504, True), (400, False), (200, False)],
)
def test_is_retryable_table(code: int, expected: bool) -> None:
    assert is_retryable(code) is expected


@pytest.mark.anyio
async def test_retries_then_succeeds() -> None:
    calls = {"n": 0}
    sleeps: list[float] = []

    async def fn() -> str:
        calls["n"] += 1
        if calls["n"] <= 2:
            raise ProviderUnavailable("upstream error", retryable=True)
        return "ok"

    async def fake_sleep(delay: float) -> None:
        sleeps.append(delay)

    result = await with_retries(
        fn, max_attempts=3, base_delay_s=0.5, max_delay_s=8.0, sleep=fake_sleep
    )
    assert result == "ok"
    assert calls["n"] == 3
    assert len(sleeps) == 2
    # full jitter: each delay within [0, min(max, base * 2**(attempt-1))]
    assert 0 <= sleeps[0] <= 0.5
    assert 0 <= sleeps[1] <= 1.0


@pytest.mark.anyio
async def test_exhausts_attempts_and_reraises() -> None:
    calls = {"n": 0}

    async def fn() -> str:
        calls["n"] += 1
        raise ProviderRateLimited("rate limited")

    async def fake_sleep(_: float) -> None:
        pass

    with pytest.raises(ProviderRateLimited):
        await with_retries(fn, max_attempts=3, base_delay_s=0.1, max_delay_s=1.0, sleep=fake_sleep)
    assert calls["n"] == 3


@pytest.mark.anyio
async def test_non_retryable_fails_immediately() -> None:
    calls = {"n": 0}

    async def fn() -> str:
        calls["n"] += 1
        raise ProviderUnavailable("client error", retryable=False)

    with pytest.raises(ProviderUnavailable):
        await with_retries(fn, max_attempts=3, base_delay_s=0.1, max_delay_s=1.0)
    assert calls["n"] == 1


@pytest.mark.anyio
async def test_timeout_is_not_retried() -> None:
    calls = {"n": 0}

    async def fn() -> str:
        calls["n"] += 1
        raise ProviderTimeout("attempt timed out")

    with pytest.raises(ProviderTimeout):
        await with_retries(fn, max_attempts=3, base_delay_s=0.1, max_delay_s=1.0)
    assert calls["n"] == 1


@pytest.mark.anyio
async def test_retry_after_floor_is_honored() -> None:
    calls = {"n": 0}
    sleeps: list[float] = []

    async def fn() -> str:
        calls["n"] += 1
        if calls["n"] == 1:
            raise ProviderRateLimited("slow down", retry_after=2.5)
        return "ok"

    async def fake_sleep(delay: float) -> None:
        sleeps.append(delay)

    result = await with_retries(
        fn, max_attempts=2, base_delay_s=0.1, max_delay_s=8.0, sleep=fake_sleep
    )
    assert result == "ok"
    assert sleeps == [pytest.approx(2.5, abs=0.01)] or sleeps[0] >= 2.5
