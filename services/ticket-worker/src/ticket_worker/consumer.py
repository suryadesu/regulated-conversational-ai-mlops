"""SQS long-poll consumer for escalation events."""


class SqsConsumer:
    """Receives, acks, and derives idempotency keys for SQS escalation messages."""

    def __init__(
        self, queue_url: str, endpoint_url: str | None, wait_time_s: int, visibility_timeout_s: int
    ) -> None:
        """Create an SQS consumer bound to a queue.

        Args:
            queue_url: str — URL of the SQS main queue.
            endpoint_url: str | None — floci endpoint locally; None uses real AWS.
            wait_time_s: int — long-poll wait time in seconds.
            visibility_timeout_s: int — message visibility timeout in seconds.
        """
        raise NotImplementedError

    def receive(self) -> list[dict]:
        """Long-poll for a batch of messages.

        Returns:
            list[dict] — received SQS messages (possibly empty).
        """
        raise NotImplementedError

    def delete(self, receipt_handle: str) -> None:
        """Acknowledge (delete) a successfully processed message.

        Args:
            receipt_handle: str — receipt handle of the message to delete.
        """
        raise NotImplementedError

    def message_idempotency_key(self, message: dict) -> str:
        """Derive a stable idempotency key from a message.

        Args:
            message: dict — an SQS message.

        Returns:
            str — the idempotency key to claim before processing.
        """
        raise NotImplementedError
