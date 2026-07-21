"""Ticket-worker entrypoint and SQS poll loop."""

import asyncio
import json
import logging
import os

from gateway.config import get_settings
from gateway.prompts.loader import PromptTemplate, load_prompt
from gateway.providers.base import ProviderClient, make_provider
from ticket_worker.consumer import SqsConsumer
from ticket_worker.idempotency import IdempotencyStore
from ticket_worker.ticket import draft_ticket, persist_ticket

logger = logging.getLogger(__name__)

CLAIM_TTL_S = 300


def main() -> None:
    """Process entrypoint: build config, consumer, idempotency store, and provider, then poll.

    WORKER_QUEUE_URL is required (a worker without a queue is a fatal
    misconfiguration); the provider and prompt reuse the gateway's GATEWAY_*
    settings — same ProviderClient, same versioned prompt.
    """
    logging.basicConfig(level=logging.INFO)
    queue_url = os.environ["WORKER_QUEUE_URL"]
    endpoint_url = os.environ.get("WORKER_ENDPOINT_URL") or None
    consumer = SqsConsumer(
        queue_url=queue_url,
        endpoint_url=endpoint_url,
        wait_time_s=int(os.environ.get("WORKER_WAIT_TIME_S", "20")),
        visibility_timeout_s=int(os.environ.get("WORKER_VISIBILITY_TIMEOUT_S", "60")),
    )
    store = IdempotencyStore(
        table_name=os.environ.get("WORKER_IDEMPOTENCY_TABLE", "idempotency"),
        endpoint_url=endpoint_url,
    )
    settings = get_settings()
    provider = make_provider(settings)
    prompt = load_prompt(settings.prompt_dir, settings.prompt_name, settings.prompt_version)
    asyncio.run(
        run_poll_loop(
            consumer,
            store,
            provider,
            prompt,
            tickets_table=os.environ.get("WORKER_TICKETS_TABLE", "tickets"),
            endpoint_url=endpoint_url,
        )
    )


async def run_poll_loop(
    consumer: SqsConsumer,
    store: IdempotencyStore,
    provider: ProviderClient,
    prompt: PromptTemplate,
    tickets_table: str,
    endpoint_url: str | None,
    max_iterations: int | None = None,
) -> None:
    """Long-poll SQS and process each escalation event exactly once, end to end.

    A message that fails processing is deliberately left undeleted: SQS
    visibility timeout redelivers it, and after maxReceiveCount the queue's
    redrive policy moves it to the DLQ — no manual DLQ code here.

    Args:
        consumer: SqsConsumer — SQS long-poll receiver/acker.
        store: IdempotencyStore — DynamoDB-backed idempotency claim store.
        provider: ProviderClient — inference client used to draft ticket text.
        prompt: PromptTemplate — pinned drafting prompt shared with the gateway.
        tickets_table: str — DynamoDB tickets table name.
        endpoint_url: str | None — floci endpoint locally; None uses real AWS.
        max_iterations: int | None — bound the loop for tests; None polls forever.
    """
    iteration = 0
    while max_iterations is None or iteration < max_iterations:
        iteration += 1
        messages = await asyncio.to_thread(consumer.receive)
        for message in messages:
            key = consumer.message_idempotency_key(message)
            if await asyncio.to_thread(store.claim, key, CLAIM_TTL_S):
                try:
                    event = json.loads(message["Body"])
                    ticket = await draft_ticket(event, provider, prompt)
                    await asyncio.to_thread(persist_ticket, ticket, tickets_table, endpoint_url)
                    await asyncio.to_thread(store.mark_done, key)
                    await asyncio.to_thread(consumer.delete, message["ReceiptHandle"])
                except Exception:
                    logger.exception("failed to process message %s; leaving for redelivery", key)
                    continue
            else:
                # Already processed: ack without re-executing the side effect.
                await asyncio.to_thread(consumer.delete, message["ReceiptHandle"])


if __name__ == "__main__":
    main()
