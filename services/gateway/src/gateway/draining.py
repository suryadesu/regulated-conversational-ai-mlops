"""In-flight request tracking for graceful drain on shutdown."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import AbstractAsyncContextManager, asynccontextmanager


class DrainState:
    """Tracks in-flight requests so open streams finish before the process exits."""

    def __init__(self) -> None:
        self._draining = False
        self._count = 0
        self._zero_event = asyncio.Event()
        self._zero_event.set()  # starts empty

    def begin_drain(self) -> None:
        """Enter draining so readiness reports 503 and the pod leaves the Service endpoints."""
        self._draining = True

    def track_request(self) -> AbstractAsyncContextManager[None]:
        """Return an async context manager that increments then decrements the in-flight counter.

        Returns:
            AbstractAsyncContextManager[None] — scope whose exit decrements the counter.
        """

        @asynccontextmanager
        async def scope() -> AsyncIterator[None]:
            self._count += 1
            self._zero_event.clear()
            try:
                yield
            finally:
                self._count -= 1
                if self._count == 0:
                    self._zero_event.set()

        return scope()

    async def wait_for_drain(self, timeout_s: float) -> bool:
        """Block until in-flight requests reach zero or the timeout elapses.

        Args:
            timeout_s: float — maximum seconds to wait for open streams to finish.

        Returns:
            bool — True if drained cleanly, False if the timeout was hit.
        """
        try:
            await asyncio.wait_for(self._zero_event.wait(), timeout=timeout_s)
        except TimeoutError:
            return False
        return True

    @property
    def is_draining(self) -> bool:
        """Whether the service has begun draining and readiness should report 503."""
        return self._draining
