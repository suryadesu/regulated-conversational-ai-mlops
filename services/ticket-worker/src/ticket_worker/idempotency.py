"""DynamoDB-backed idempotency claims for exactly-once side effects."""

import time

import boto3
import botocore.exceptions

# Table schema (must match deploy/terraform/modules/dynamodb and scripts/seed-aws.sh):
# partition key "pk" (S); attributes "status" (S) and "expires_at" (N, epoch TTL).


class IdempotencyStore:
    """Claims and finalizes idempotency keys via DynamoDB conditional writes."""

    def __init__(self, table_name: str, endpoint_url: str | None) -> None:
        """Create an idempotency store bound to a DynamoDB table.

        Args:
            table_name: str — DynamoDB idempotency table name.
            endpoint_url: str | None — floci endpoint locally; None uses real AWS.
        """
        self._table = boto3.resource(
            "dynamodb", endpoint_url=endpoint_url, region_name="us-east-1"
        ).Table(table_name)

    def claim(self, key: str, ttl_s: int) -> bool:
        """Attempt to claim a key with a conditional put.

        Args:
            key: str — idempotency key to claim.
            ttl_s: int — time-to-live for the claim record in seconds.

        Returns:
            bool — True if newly claimed, False if already processed.
        """
        try:
            self._table.put_item(
                Item={"pk": key, "status": "claimed", "expires_at": int(time.time()) + ttl_s},
                ConditionExpression="attribute_not_exists(pk)",
            )
        except botocore.exceptions.ClientError as exc:
            if exc.response["Error"]["Code"] == "ConditionalCheckFailedException":
                return False
            raise
        return True

    def mark_done(self, key: str) -> None:
        """Mark a claimed key as fully processed.

        Args:
            key: str — idempotency key to finalize.
        """
        self._table.update_item(
            Key={"pk": key},
            UpdateExpression="SET #s = :done",
            ExpressionAttributeNames={"#s": "status"},
            ExpressionAttributeValues={":done": "done"},
        )
