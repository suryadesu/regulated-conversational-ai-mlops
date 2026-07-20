"""Ticket model, drafting via the shared provider contract, and persistence."""

from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel

if TYPE_CHECKING:
    from gateway.prompts.loader import PromptTemplate
    from gateway.providers.base import ProviderClient


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
    raise NotImplementedError


def persist_ticket(ticket: Ticket, table_name: str, endpoint_url: str | None) -> None:
    """Persist a drafted ticket to the DynamoDB tickets table.

    Args:
        ticket: Ticket — the ticket to store.
        table_name: str — DynamoDB tickets table name.
        endpoint_url: str | None — floci endpoint locally; None uses real AWS.
    """
    raise NotImplementedError
