"""Ticket-worker entrypoint and SQS poll loop."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ticket_worker.consumer import SqsConsumer
from ticket_worker.idempotency import IdempotencyStore

if TYPE_CHECKING:
    from gateway.providers.base import ProviderClient


def main() -> None:
    """Process entrypoint: build config, consumer, idempotency store, and provider, then poll."""
    raise NotImplementedError


async def run_poll_loop(
    consumer: SqsConsumer, store: IdempotencyStore, provider: ProviderClient
) -> None:
    """Long-poll SQS and process each escalation event exactly once, end to end.

    Args:
        consumer: SqsConsumer — SQS long-poll receiver/acker.
        store: IdempotencyStore — DynamoDB-backed idempotency claim store.
        provider: ProviderClient — inference client used to draft ticket text.
    """
    raise NotImplementedError
