"""Retry policy: classify retryable failures and run attempts with backoff + full jitter."""

from collections.abc import Awaitable, Callable


def is_retryable(status_code: int) -> bool:
    """Whether an HTTP status should be retried (429 and transient 5xx only).

    Args:
        status_code: int — HTTP status returned by the provider.

    Returns:
        bool — True for 429/500/502/503/504, False otherwise.
    """
    raise NotImplementedError


async def with_retries[T](
    fn: Callable[[], Awaitable[T]],
    max_attempts: int,
    base_delay_s: float,
    max_delay_s: float,
) -> T:
    """Run an async provider call with exponential backoff and full jitter on retryable failures.

    Args:
        fn: Callable[[], Awaitable[T]] — zero-arg coroutine factory performing one provider attempt.
        max_attempts: int — total attempts including the first; retries only on 429/5xx.
        base_delay_s: float — initial backoff delay before jitter.
        max_delay_s: float — upper bound on any single backoff sleep.
    """
    raise NotImplementedError
