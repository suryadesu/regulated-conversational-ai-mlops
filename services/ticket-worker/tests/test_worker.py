"""End-to-end worker tests against in-process moto AWS (SQS + DynamoDB)."""

import json
import uuid

import boto3
import pytest
from moto import mock_aws

from gateway.prompts.loader import PromptTemplate
from gateway.providers.base import CompletionResult, Message
from ticket_worker.consumer import SqsConsumer
from ticket_worker.idempotency import IdempotencyStore
from ticket_worker.main import run_poll_loop

REGION = "us-east-1"
DRAFT = "Drafted ticket body from the fake provider."


class FakeProvider:
    """Minimal ProviderClient double (Protocol duck-typing, no mock library)."""

    def __init__(self, fail: bool = False) -> None:
        self.fail = fail
        self.calls: list[list[Message]] = []

    async def complete(
        self, messages: list[Message], model: str, max_tokens: int, temperature: float
    ) -> CompletionResult:
        self.calls.append(messages)
        if self.fail:
            raise RuntimeError("provider exploded")
        return CompletionResult(content=DRAFT, model=model, prompt_tokens=3, completion_tokens=7)


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
def prompt() -> PromptTemplate:
    return PromptTemplate(
        id="customer-support",
        version="v1.0.0",
        system="Draft support tickets for {bank_name} in a {tone} tone.",
        variables={"bank_name": "the bank", "tone": "concise"},
    )


@pytest.fixture
def aws():
    with mock_aws():
        sqs = boto3.client("sqs", region_name=REGION)
        queue_url = sqs.create_queue(QueueName="escalations")["QueueUrl"]
        ddb = boto3.client("dynamodb", region_name=REGION)
        ddb.create_table(
            TableName="idempotency",
            AttributeDefinitions=[{"AttributeName": "pk", "AttributeType": "S"}],
            KeySchema=[{"AttributeName": "pk", "KeyType": "HASH"}],
            BillingMode="PAY_PER_REQUEST",
        )
        ddb.create_table(
            TableName="tickets",
            AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
            KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
            BillingMode="PAY_PER_REQUEST",
        )
        yield {"sqs": sqs, "queue_url": queue_url, "ddb": ddb}


def _publish(aws, event: dict) -> None:
    aws["sqs"].send_message(QueueUrl=aws["queue_url"], MessageBody=json.dumps(event))


def _consumer(aws) -> SqsConsumer:
    return SqsConsumer(
        queue_url=aws["queue_url"], endpoint_url=None, wait_time_s=0, visibility_timeout_s=30
    )


def _queue_depth(aws) -> int:
    attrs = aws["sqs"].get_queue_attributes(
        QueueUrl=aws["queue_url"],
        AttributeNames=["ApproximateNumberOfMessages", "ApproximateNumberOfMessagesNotVisible"],
    )["Attributes"]
    return int(attrs["ApproximateNumberOfMessages"]) + int(
        attrs["ApproximateNumberOfMessagesNotVisible"]
    )


def _tickets(aws) -> list[dict]:
    ddb = boto3.resource("dynamodb", region_name=REGION)
    return ddb.Table("tickets").scan()["Items"]


@pytest.mark.anyio
async def test_happy_path_drafts_persists_acks(aws, prompt) -> None:
    event_id = str(uuid.uuid4())
    _publish(aws, {"event_id": event_id, "summary": "Card blocked", "customer_id": "c-1"})
    provider = FakeProvider()

    await run_poll_loop(
        _consumer(aws),
        IdempotencyStore(table_name="idempotency", endpoint_url=None),
        provider,
        prompt,
        tickets_table="tickets",
        endpoint_url=None,
        max_iterations=1,
    )

    tickets = _tickets(aws)
    assert len(tickets) == 1
    assert tickets[0]["body"] == DRAFT
    assert tickets[0]["source_event_id"] == event_id
    assert tickets[0]["title"] == "Card blocked"
    # system prompt was rendered from the shared PromptTemplate
    assert provider.calls[0][0].role == "system"
    assert "the bank" in provider.calls[0][0].content

    claim = boto3.resource("dynamodb", region_name=REGION).Table("idempotency").get_item(
        Key={"pk": event_id}
    )["Item"]
    assert claim["status"] == "done"
    assert _queue_depth(aws) == 0


@pytest.mark.anyio
async def test_duplicate_event_processed_once(aws, prompt) -> None:
    event_id = str(uuid.uuid4())
    event = {"event_id": event_id, "summary": "Duplicate escalation"}
    _publish(aws, event)
    _publish(aws, event)

    await run_poll_loop(
        _consumer(aws),
        IdempotencyStore(table_name="idempotency", endpoint_url=None),
        FakeProvider(),
        prompt,
        tickets_table="tickets",
        endpoint_url=None,
        max_iterations=3,
    )

    assert len(_tickets(aws)) == 1  # second delivery hit the claim and was acked without effect
    assert _queue_depth(aws) == 0


@pytest.mark.anyio
async def test_failed_processing_leaves_message_for_redelivery(aws, prompt) -> None:
    _publish(aws, {"event_id": str(uuid.uuid4()), "summary": "Poison message"})

    await run_poll_loop(
        _consumer(aws),
        IdempotencyStore(table_name="idempotency", endpoint_url=None),
        FakeProvider(fail=True),
        prompt,
        tickets_table="tickets",
        endpoint_url=None,
        max_iterations=1,
    )

    assert _tickets(aws) == []
    assert _queue_depth(aws) == 1  # not deleted: visibility timeout -> redelivery -> DLQ redrive


def test_idempotency_key_falls_back_to_body_hash(aws) -> None:
    consumer = _consumer(aws)
    keyed = consumer.message_idempotency_key({"Body": json.dumps({"event_id": "abc"})})
    assert keyed == "abc"
    hashed = consumer.message_idempotency_key({"Body": json.dumps({"summary": "no id"})})
    assert len(hashed) == 64  # sha256 hex of the raw body
