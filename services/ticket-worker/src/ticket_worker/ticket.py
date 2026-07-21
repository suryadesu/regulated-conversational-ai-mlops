"""Ticket model, drafting via the shared provider contract, and persistence."""

import json
from datetime import UTC, datetime
from uuid import uuid4

import boto3
from pydantic import BaseModel

from gateway.prompts.loader import PromptTemplate, render_system_prompt
from gateway.providers.base import Message, ProviderClient


class Ticket(BaseModel):
    """A support ticket drafted from an escalation event."""

    id: str  # ticket identifier
    source_event_id: str  # originating escalation event id
    title: str  # short ticket summary
    body: str  # LLM-drafted ticket body
    created_at: str  # ISO-8601 creation timestamp


async def draft_ticket(event: dict, provider: ProviderClient, prompt: PromptTemplate) -> Ticket:
    """Draft a support ticket from an escalation event using the shared provider and prompt.

    Args:
        event: dict — the escalation event payload.
        provider: ProviderClient — inference client (the gateway's provider contract).
        prompt: PromptTemplate — the pinned, versioned drafting prompt.

    Returns:
        Ticket — the drafted ticket ready to persist.
    """
    messages = [
        Message(role="system", content=render_system_prompt(prompt, {})),
        Message(
            role="user",
            content=f"Draft a support ticket for this escalation: {json.dumps(event)}",
        ),
    ]
    result = await provider.complete(
        messages, model="qwen2.5-0.5b-instruct", max_tokens=512, temperature=0.2
    )
    return Ticket(
        id=str(uuid4()),
        source_event_id=event.get("event_id", "unknown"),
        title=event.get("summary", "Escalation")[:80],
        body=result.content,
        created_at=datetime.now(UTC).isoformat(),
    )


def persist_ticket(ticket: Ticket, table_name: str, endpoint_url: str | None) -> None:
    """Persist a drafted ticket to the DynamoDB tickets table.

    Args:
        ticket: Ticket — the ticket to store.
        table_name: str — DynamoDB tickets table name (partition key "id").
        endpoint_url: str | None — floci endpoint locally; None uses real AWS.
    """
    boto3.resource("dynamodb", endpoint_url=endpoint_url, region_name="us-east-1").Table(
        table_name
    ).put_item(Item=ticket.model_dump())
