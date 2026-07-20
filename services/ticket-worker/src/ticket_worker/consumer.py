"""SQS long-poll consumer for escalation events."""

import hashlib
import json

import boto3


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
        self.queue_url = queue_url
        self.wait_time_s = wait_time_s
        self.visibility_timeout_s = visibility_timeout_s
        self._client = boto3.client("sqs", endpoint_url=endpoint_url, region_name="us-east-1")

    def receive(self) -> list[dict]:
        """Long-poll for a batch of messages.

        Returns:
            list[dict] — received SQS messages (possibly empty).
        """
        response = self._client.receive_message(
            QueueUrl=self.queue_url,
            MaxNumberOfMessages=10,
            WaitTimeSeconds=self.wait_time_s,
            VisibilityTimeout=self.visibility_timeout_s,
        )
        return response.get("Messages", [])

    def delete(self, receipt_handle: str) -> None:
        """Acknowledge (delete) a successfully processed message.

        Args:
            receipt_handle: str — receipt handle of the message to delete.
        """
        self._client.delete_message(QueueUrl=self.queue_url, ReceiptHandle=receipt_handle)

    def message_idempotency_key(self, message: dict) -> str:
        """Derive a stable idempotency key from a message.

        Falls back to a body hash when the event carries no event_id, so a
        malformed/poison message stays identifiable for the DLQ path instead
        of raising here.

        Args:
            message: dict — an SQS message.

        Returns:
            str — the idempotency key to claim before processing.
        """
        body = message["Body"]
        try:
            event_id = json.loads(body).get("event_id")
        except json.JSONDecodeError:
            event_id = None
        if event_id:
            return str(event_id)
        return hashlib.sha256(body.encode()).hexdigest()
