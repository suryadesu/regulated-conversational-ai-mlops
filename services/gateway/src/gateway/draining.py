"""In-flight request tracking for graceful drain on shutdown."""

from contextlib import AbstractAsyncContextManager


class DrainState:
    """Tracks in-flight requests so open streams finish before the process exits."""

    def begin_drain(self) -> None:
        """Enter draining so readiness reports 503 and the pod leaves the Service endpoints."""
        raise NotImplementedError

    def track_request(self) -> AbstractAsyncContextManager[None]:
        """Return an async context manager that increments then decrements the in-flight counter.

        Returns:
            AbstractAsyncContextManager[None] — scope whose exit decrements the counter.
        """
        raise NotImplementedError

    async def wait_for_drain(self, timeout_s: float) -> bool:
        """Block until in-flight requests reach zero or the timeout elapses.

        Args:
            timeout_s: float — maximum seconds to wait for open streams to finish.

        Returns:
            bool — True if drained cleanly, False if the timeout was hit.
        """
        raise NotImplementedError

    @property
    def is_draining(self) -> bool:
        """Whether the service has begun draining and readiness should report 503."""
        raise NotImplementedError
