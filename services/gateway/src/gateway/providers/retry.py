"""Retry policy: classify retryable failures and run attempts with backoff + full jitter."""

import asyncio
import random
from collections.abc import Awaitable, Callable

from gateway.providers.errors import ProviderRateLimited, ProviderUnavailable

_RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})


def is_retryable(status_code: int) -> bool:
    """Whether an HTTP status should be retried (429 and transient 5xx only).

    Args:
        status_code: int — HTTP status returned by the provider.

    Returns:
        bool — True for 429/500/502/503/504, False otherwise.
    """
    return status_code in _RETRYABLE_STATUS


async def with_retries[T](
    fn: Callable[[], Awaitable[T]],
    max_attempts: int,
    base_delay_s: float,
    max_delay_s: float,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> T:
    """Run an async provider call with exponential backoff and full jitter on retryable failures.

    Retries only ``ProviderRateLimited``/``ProviderUnavailable`` with ``retryable=True``;
    everything else (including ``ProviderTimeout``) re-raises immediately. A
    ``Retry-After`` hint on ``ProviderRateLimited`` sets the delay floor. The
    injectable ``sleep`` exists so tests never wait on real backoff.

    Args:
        fn: Callable[[], Awaitable[T]] — zero-arg coroutine factory performing one provider attempt.
        max_attempts: int — total attempts including the first; retries only on 429/5xx.
        base_delay_s: float — initial backoff delay before jitter.
        max_delay_s: float — upper bound on any single backoff sleep.
        sleep: Callable[[float], Awaitable[None]] — awaitable sleep, injectable for tests.
    """
    for attempt in range(1, max_attempts + 1):
        try:
            return await fn()
        except (ProviderRateLimited, ProviderUnavailable) as exc:
            if not exc.retryable or attempt == max_attempts:
                raise
            capped = min(max_delay_s, base_delay_s * 2 ** (attempt - 1))
            delay = random.uniform(0, capped)
            retry_after = getattr(exc, "retry_after", None)
            if retry_after is not None:
                delay = max(delay, retry_after)
            await sleep(delay)
    raise AssertionError("unreachable: loop returns or raises")  # pragma: no cover
