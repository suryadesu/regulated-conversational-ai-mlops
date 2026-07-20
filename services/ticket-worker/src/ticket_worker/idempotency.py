"""DynamoDB-backed idempotency claims for exactly-once side effects."""


class IdempotencyStore:
    """Claims and finalizes idempotency keys via DynamoDB conditional writes."""

    def __init__(self, table_name: str, endpoint_url: str | None) -> None:
        """Create an idempotency store bound to a DynamoDB table.

        Args:
            table_name: str — DynamoDB idempotency table name.
            endpoint_url: str | None — floci endpoint locally; None uses real AWS.
        """
        raise NotImplementedError

    def claim(self, key: str, ttl_s: int) -> bool:
        """Attempt to claim a key with a conditional put.

        Args:
            key: str — idempotency key to claim.
            ttl_s: int — time-to-live for the claim record in seconds.

        Returns:
            bool — True if newly claimed, False if already processed.
        """
        raise NotImplementedError

    def mark_done(self, key: str) -> None:
        """Mark a claimed key as fully processed.

        Args:
            key: str — idempotency key to finalize.
        """
        raise NotImplementedError
